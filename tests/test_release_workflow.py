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
    assert "uv pip install -e ../spec" in text and "node_modules/@terp/spec" in text, (
        "certification must substitute the tagged checkout for BOTH pinned "
        "spec packages (terp-spec and @terp/spec)"
    )
    assert re.search(r"needs:\s*\[verify,\s*certify-against-reference\]", text), (
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


def test_release_workflow_stays_registry_free() -> None:
    """ADR 0082: the Git tag is the release artifact; registry publishing is
    out of scope — the workflow must not grow it silently."""
    text = _workflow_text()
    for marker in ("npm publish", "twine", "pypi-publish", "uv publish"):
        assert marker not in text, (
            f"registry publishing ({marker!r}) is out of ADR 0082's scope — "
            "revisit the ADR before adding it"
        )
