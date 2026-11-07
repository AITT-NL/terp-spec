"""The release workflow's fail-closed contract (ADR 0082).

The Git tag IS the release artifact (consumers pin ``uv``/``npm`` to it), so
the workflow that turns a tag into a GitHub Release is itself part of the
contracts' integrity story. These assertions hold the checked-in workflow to
its contract the same way ``test_contracts.py`` holds the packaging to the
repository: reading the repository's own artifacts, no framework required.

String-level on purpose: the repository is dependency-free (no YAML parser),
and the contract is about the presence of specific fail-closed steps, not
about YAML structure.
"""

from __future__ import annotations

import pathlib
import re

_WORKFLOW = (
    pathlib.Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "release.yml"
)


def _workflow_text() -> str:
    assert _WORKFLOW.is_file(), (
        f"{_WORKFLOW} is missing — the release seam (ADR 0082) requires the "
        "fail-closed tag workflow"
    )
    return _WORKFLOW.read_text(encoding="utf-8")


def _job_block(text: str, job: str) -> str:
    """The lines belonging to one top-level job — string-level, like the rest
    of this module: a job starts at two-space indent and runs until the next
    key at that indent."""
    match = re.search(rf"^  {re.escape(job)}:\n(.*?)(?=^  \S|\Z)", text, re.M | re.S)
    assert match, f"the release workflow declares no {job!r} job"
    return match.group(1)


def test_release_workflow_verifies_tag_against_version() -> None:
    text = _workflow_text()
    assert "VERSION" in text and "GITHUB_REF_NAME#v" in text, (
        "the release workflow must refuse a tag that does not match the "
        "checked-in VERSION"
    )


def test_release_workflow_proves_tag_provenance() -> None:
    """A release tag is accepted only when the tagged commit is reachable
    from the repository's default branch — full history, fail-closed."""
    text = _workflow_text()
    assert "fetch-depth: 0" in text, (
        "the ancestry check needs full history (fetch-depth: 0) — a shallow "
        "clone cannot prove reachability"
    )
    assert "github.event.repository.default_branch" in text, (
        "the default branch must be resolved from the repository, not hardcoded"
    )
    assert "merge-base --is-ancestor" in text, (
        "the tagged commit must be proven reachable from the default branch "
        "(git merge-base --is-ancestor), fail closed"
    )
    assert re.search(r"rev-parse .*\^\{commit\}", text), (
        "the tag must be dereferenced to its commit (annotated and lightweight "
        "tags alike) before the ancestry check"
    )


def test_release_is_bound_to_the_verified_commit() -> None:
    """The release job must release exactly the commit the verify job proved
    — a tag force-moved (or deleted) between the two jobs is refused, and
    ``gh release create`` may never create the tag as a side effect."""
    text = _workflow_text()
    assert "needs.verify.outputs.verified_sha" in text, (
        "the release job must consume the verify job's verified_sha output — "
        "releasing by tag NAME alone races a tag retarget"
    )
    assert re.search(r'"sha=\$tagged"\s*>>\s*"\$GITHUB_OUTPUT"', text), (
        "the verify job must export the exact commit it verified"
    )
    assert 'git fetch --no-tags origin "refs/tags/${GITHUB_REF_NAME}"' in text, (
        "the release job must re-resolve the tag from the REMOTE at release "
        "time (the local checkout could be stale)"
    )
    assert "--verify-tag" in text, (
        "gh release create must use --verify-tag so a deleted tag is never "
        "re-created as a side effect of releasing"
    )
    assert re.search(r"^concurrency:", text, re.M), (
        "one run per tag ref: concurrent runs of the same tag must not race "
        "verification against release"
    )


def test_no_workflow_checks_out_another_repository() -> None:
    """Nothing here waits on another repository (framework ADR 0203).

    The rules, their corpus and the checks that hold them live in terp-framework, so the
    certification job that checked the framework out at a pinned commit went with them.
    A workflow that checked out another repository again would bring back the coupling
    that made a new rule need a fixed push order across two repositories.
    """
    workflows = _WORKFLOW.parent
    offenders = sorted(
        path.name
        for path in workflows.glob("*.yml")
        if re.search(r"^\s+repository:", path.read_text(encoding="utf-8"), re.M)
    )
    assert not offenders, f"these workflows check out another repository: {offenders}"
    assert not (workflows / "reference-drift.yml").exists(), (
        "reference-drift.yml watched a reference implementation this repository no "
        "longer certifies against"
    )


def test_release_workflow_keeps_permissions_minimal() -> None:
    text = _workflow_text()
    assert re.search(r"^permissions:\s*\n\s+contents: read", text, re.M), (
        "the workflow's default permissions must stay contents: read"
    )
    writes = re.findall(r"contents: write", text)
    assert len(writes) <= 1, (
        "only the release-creation job may hold contents: write"
    )


def test_release_publishes_to_both_registries() -> None:
    """ADR 0086: a tag publishes the contracts, it does not only announce them.
    Both distributions go out from this workflow, gated on verification and
    bound to the verified commit, with no long-lived registry token."""
    text = _workflow_text()
    assert "publish-pypi:" in text and "publish-npm:" in text, (
        "the release must publish both distributions (terp-spec on PyPI, "
        "@terpjs/spec on npm) \u2014 ADR 0086"
    )
    for job in ("publish-pypi", "publish-npm"):
        block = _job_block(text, job)
        needs = re.search(r"needs:\s*\[([^\]]*)\]", block)
        assert needs and "verify" in {
            name.strip() for name in needs.group(1).split(",")
        }, (
            f"{job} must require verification \u2014 a version whose tag, provenance "
            "or self-consistency was not proven may never reach a registry"
        )
        assert "ref: ${{ needs.verify.outputs.verified_sha }}" in block, (
            f"{job} must check out the VERIFIED COMMIT, not the tag name \u2014 "
            "a tag force-moved mid-workflow must not change what is published"
        )
        assert "id-token: write" in block, (
            f"{job} must publish via Trusted Publishing (OIDC), which needs "
            "id-token: write"
        )
        assert "environment: release" in block, (
            f"{job} must run in the 'release' environment \u2014 it is part of "
            "the OIDC identity both registries' trusted publishers verify, so "
            "dropping it makes the registry refuse the publish"
        )


def test_release_is_gated_on_publishing() -> None:
    """A GitHub Release may never announce a version the registries do not
    have: the release job requires both publish jobs (fail closed)."""
    block = _job_block(_workflow_text(), "github-release")
    needs = re.search(r"needs:\s*\[([^\]]*)\]", block)
    assert needs, "the release job must declare its dependencies"
    for job in ("publish-pypi", "publish-npm"):
        assert job in needs.group(1), (
            f"the GitHub Release must require {job} \u2014 a failed publish "
            "must refuse the release, not leave a Release pointing at a "
            "version nobody can install"
        )


def test_publishing_stores_no_registry_token() -> None:
    """Trusted Publishing only: a long-lived npm/PyPI credential in this
    workflow would reintroduce exactly the risk OIDC removes."""
    text = _workflow_text()
    for marker in ("NPM_TOKEN", "NODE_AUTH_TOKEN", "PYPI_API_TOKEN", "TWINE_PASSWORD"):
        assert marker not in text, (
            f"{marker} must not appear \u2014 both registries publish via "
            "Trusted Publishing (OIDC), ADR 0086"
        )


def test_publishing_cannot_half_publish_a_version() -> None:
    """Both registries are immutable, so a version only one of them accepted can
    never be completed or withdrawn — it is burned, and still pinnable. Running
    the publishes in parallel makes that outcome reachable from any one-sided
    failure; ordering them makes the failure leave nothing published and the
    version free to re-cut. PyPI goes first because it is the half that builds
    an artifact and can therefore fail on one (npm publishes checked-in data).
    0.21.0 is the worked example: npm accepted it, PyPI rejected the wheel."""
    block = _job_block(_workflow_text(), "publish-npm")
    needs = re.search(r"needs:\s*\[([^\]]*)\]", block)
    assert needs, "publish-npm must declare its dependencies"
    assert "publish-pypi" in {name.strip() for name in needs.group(1).split(",")}, (
        "publish-npm must require publish-pypi — published in parallel, a wheel "
        "PyPI refuses still leaves the version published on npm, where it can "
        "neither be completed nor withdrawn"
    )


def test_publishing_is_idempotent() -> None:
    """A partially failed release must be re-runnable: neither registry job
    may fail because a sibling job already published its half."""
    text = _workflow_text()
    assert "skip-existing: true" in text, (
        "the PyPI upload must skip an already-published version"
    )
    assert "npm view" in text, (
        "the npm publish must skip a version already on the registry"
    )
