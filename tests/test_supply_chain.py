"""The workflows that publish the standard are held to the bar the standard sets.

This repository declares Terp's secure-by-default bar and holds OIDC publishing
rights to two registries. The reference implementation installs the published
``terp-spec``/``@terpjs/spec``, so every consumer's gate resolves an artifact these
workflows produce. That made it the least-hardened repository in the platform while
being the one that defines hardening: sixteen of seventeen ``uses:`` were floating
tags, several of them inside ``environment: release`` jobs holding ``id-token:
write``, and there was no updater, no workflow audit and no secret scan.

A floating tag is not a version — it is a pointer someone else can move, and moving
it changes what runs inside the job that holds the publishing credential.

String-level, like ``test_release_workflow``: this repository is dependency-free
(no YAML parser), and the contract is about the presence of specific fail-closed
properties rather than YAML structure.
"""

from __future__ import annotations

import pathlib
import re

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_WORKFLOWS = _ROOT / ".github" / "workflows"

#: `uses: owner/repo@<40 hex>`, optionally followed by the `# vX.Y.Z` comment that
#: makes the pin readable and lets an updater recognise what it is looking at.
_PINNED = re.compile(r"uses:\s*\S+@[0-9a-f]{40}\b")
_ANY_USES = re.compile(r"^\s*(?:-\s*)?uses:\s*(\S+)", re.M)

#: The commit of the reference implementation this standard certifies against.
_REFERENCE_SHA = _ROOT / "REFERENCE_SHA"


def _workflows() -> list[pathlib.Path]:
    return sorted(_WORKFLOWS.glob("*.yml"))


def test_the_workflows_are_discovered() -> None:
    """Discovery that quietly finds nothing would make every assertion below pass."""
    names = {path.name for path in _workflows()}
    assert {"ci.yml", "release.yml"} <= names, names


def test_every_action_is_pinned_by_digest() -> None:
    """A tag is a pointer its owner can move; a digest is the code that runs.

    Both publish jobs run with ``id-token: write`` against PyPI and npm trusted
    publishing, so a third-party action in this pipeline runs with that reach.
    """
    floating = []
    for path in _workflows():
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = _ANY_USES.match(line)
            if match and not _PINNED.search(line):
                floating.append(f"{path.name}:{line_number}: {match.group(1)}")
    assert floating == [], (
        "these actions are referenced by a movable tag rather than by digest: "
        f"{floating} — pin as `owner/repo@<sha> # vX.Y.Z`, which is also the form "
        "dependabot updates"
    )


def test_an_updater_keeps_the_pins_from_going_stale() -> None:
    """Pinning without an updater trades a live supply-chain risk for a stale one."""
    config = _ROOT / ".github" / "dependabot.yml"
    assert config.is_file(), (
        "every action here is digest-pinned, which freezes each pin at whatever was "
        "current the day it was written — .github/dependabot.yml is the other half"
    )
    text = config.read_text(encoding="utf-8")
    for ecosystem in ("github-actions", "pip", "npm"):
        assert f"package-ecosystem: {ecosystem}" in text, (
            f"dependabot watches no {ecosystem} surface, and this repository ships one"
        )


def test_the_workflow_audit_and_the_secret_scan_run() -> None:
    """The reference implementation runs both on itself; the repository that
    defines the bar cannot run fewer."""
    ci = (_WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    assert "zizmor" in ci, "no workflow-hygiene audit runs on the publishing pipeline"
    assert "gitleaks" in ci, "nothing scans this repository's history for secrets"


def test_the_downloaded_scanner_is_checksum_verified() -> None:
    """A binary fetched over the network and run unverified is the supply-chain
    hole the scanner is there to prevent, one layer down."""
    ci = (_WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    assert "GITLEAKS_SHA256" in ci and "sha256sum -c -" in ci, (
        "the gitleaks download must be verified against a pinned SHA256 before it runs"
    )


# --------------------------------------------------------------------------- #
# The pinned reference (the certification seam)                                #
# --------------------------------------------------------------------------- #
def test_the_reference_commit_is_recorded() -> None:
    assert _REFERENCE_SHA.is_file(), (
        "REFERENCE_SHA records the reference-implementation commit this standard "
        "certifies against — without it the cross-repo checkout takes whatever the "
        "default branch happened to be, and the certification claim names no commit"
    )
    sha = _REFERENCE_SHA.read_text(encoding="utf-8").strip()
    assert re.fullmatch(r"[0-9a-f]{40}", sha), (
        f"REFERENCE_SHA must be one full 40-character commit sha, not {sha!r}"
    )


def test_the_certifying_workflows_check_out_the_pinned_reference() -> None:
    """An unpinned cross-repo checkout compounds twice: a spec pull request's
    green-ness comes to depend on a repository nobody in it touched, so the
    reference going red for any reason blocks all spec work and reads as a spec
    problem — and the commit a release certified against is unrecorded, so the
    claim cannot be reproduced."""
    for name in ("ci.yml", "release.yml"):
        text = (_WORKFLOWS / name).read_text(encoding="utf-8")
        block = text.split("repository: AITT-NL/terp-framework", 1)
        assert len(block) == 2, f"{name} no longer checks out the reference implementation"
        following = block[1].split("path: framework", 1)[0]
        assert "ref:" in following, (
            f"{name} checks out the reference implementation with no `ref:` — pin it to "
            "REFERENCE_SHA, and let reference-drift.yml watch the default branch"
        )


def test_exactly_one_workflow_tracks_the_default_branch_on_purpose() -> None:
    """Pinning has a cost that has to be paid somewhere: nothing would otherwise
    notice the reference moving until the next deliberate bump. `reference-drift`
    pays it on its own schedule, where a divergence is its own named red build."""
    drift = _WORKFLOWS / "reference-drift.yml"
    assert drift.is_file(), (
        "REFERENCE_SHA pins the certification; reference-drift.yml is what keeps the "
        "pin honest by certifying against the reference's default branch on a schedule"
    )
    text = drift.read_text(encoding="utf-8")
    assert "schedule:" in text and "workflow_dispatch:" in text, (
        "the drift job must run on a schedule (so drift surfaces without being asked) "
        "and on demand (so a bump can be proven before it is made)"
    )
    assert "repository: AITT-NL/terp-framework" in text
    following = text.split("repository: AITT-NL/terp-framework", 1)[1].split(
        "path: framework", 1
    )[0]
    assert "ref:" not in following, (
        "reference-drift.yml exists to watch the DEFAULT BRANCH — pinning its checkout "
        "would make it certify the same commit ci.yml already does, twice"
    )
