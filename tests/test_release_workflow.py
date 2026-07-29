"""The release workflow's fail-closed contract (ADR 0082).

The Git tag IS the release artifact (consumers pin ``uv``/``npm`` to it), so
the workflow that turns a tag into a GitHub Release is itself part of the
standard's integrity story. These assertions hold the checked-in workflow to
its contract the same way ``test_standard.py`` holds the catalog to its
schema: reading the repository's own artifacts, no framework required.

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


def test_release_requires_certification_against_the_reference() -> None:
    """A tag can never publish a spec no conformant checker exists for: the
    release runs the same reference-substitution certification as ci.yml and
    the GitHub Release requires it (fail closed)."""
    text = _workflow_text()
    assert "certify-against-reference:" in text, (
        "the release workflow must certify the tagged spec against the "
        "reference implementation (the ci.yml substitution), not only "
        "self-consistency"
    )
    assert "repository: AITT-NL/terp-framework" in text, (
        "certification checks out the reference framework"
    )
    assert "uv pip install -e ../spec" in text and "node_modules/@terpjs/spec" in text, (
        "certification must substitute the tagged checkout for BOTH pinned "
        "spec packages (terp-spec and @terpjs/spec)"
    )
    assert 'ln -s "$GITHUB_WORKSPACE/spec" node_modules/@terpjs/spec' in text, (
        "the npm substitution must cover the @terpjs scope (ADR 0086)"
    )
    assert re.search(
        r"needs:\s*\[verify,\s*certify-against-reference(,[^\]]*)?\]", text
    ), (
        "the GitHub Release must require the certification job — a failed "
        "certification refuses the release"
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
    """ADR 0086: a tag publishes the standard, it does not only announce it.
    Both distributions go out from this workflow, gated on certification and
    bound to the verified commit, with no long-lived registry token."""
    text = _workflow_text()
    assert "publish-pypi:" in text and "publish-npm:" in text, (
        "the release must publish both distributions (terp-spec on PyPI, "
        "@terpjs/spec on npm) \u2014 ADR 0086"
    )
    for job in ("publish-pypi", "publish-npm"):
        block = _job_block(text, job)
        assert re.search(r"needs:\s*\[verify,\s*certify-against-reference\]", block), (
            f"{job} must require certification \u2014 a version no conformant "
            "checker exists for may never reach a registry"
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
