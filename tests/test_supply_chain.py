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
def test_the_secret_scan_is_narrowed_only_where_a_match_cannot_be_real() -> None:
    """`corpus/` is the one tree whose files must carry credential-shaped literals.

    A violation sample for ``backend/no_hardcoded_credentials`` that holds no
    credential-shaped literal is a broken sample — the checker it exists to contract
    would have nothing to flag. So the scan finds four there today and would find one
    more with every sample added, and a per-line baseline would grow an entry each
    time until appending to it is the reflex rather than the exception.

    Scoping is only defensible while it stays that narrow, so this asserts the shape
    of the narrowing rather than merely that a config file exists: the default
    ruleset stays on, every allowed path is under ``corpus/``, and nothing is allowed
    by *value* or by commit — a value-shaped allowance is not confined to a
    directory, so it would hide the same literal anywhere in the repository.
    """
    config = _ROOT / ".gitleaks.toml"
    assert config.is_file(), (
        "corpus samples carry credential-shaped literals by construction; "
        ".gitleaks.toml is where that is recorded, scoped and reviewable"
    )
    text = config.read_text(encoding="utf-8")

    assert re.search(r"useDefault\s*=\s*true", text), (
        "a .gitleaks.toml without `[extend] useDefault = true` REPLACES the default "
        "ruleset rather than extending it — the scan would then check almost nothing, "
        "which on the terminal reads exactly like a clean scan"
    )

    blocks = re.findall(r"paths\s*=\s*\[(.*?)\]", text, re.S)
    assert blocks, "the allowlist declares no paths; delete the file instead"
    quoted = re.findall(r"'''(.*?)'''|\"(.*?)\"", "\n".join(blocks), re.S)
    patterns = [first or second for first, second in quoted]
    assert patterns, f"no path patterns parsed out of {blocks!r}"
    for pattern in patterns:
        assert pattern.startswith("^corpus/"), (
            f"{pattern!r} takes the secret scan off a tree outside `corpus/`. Only "
            "corpus samples are invented by construction; anywhere else a match may be "
            "a real credential, and the answer to one of those is to rotate it"
        )

    for widening in ("regexes", "stopwords", "commits"):
        assert not re.search(rf"^\s*{widening}\s*=", text, re.M), (
            f"`{widening}` allows a match by value or by commit rather than by path, so "
            "it would hide the same literal anywhere in the repository — including a "
            "real credential committed outside `corpus/`"
        )


def _steps_by_job(text: str) -> list[tuple[str, list[str]]]:
    """Job blocks and the step ids each declares, at this file's string level.

    A job starts at two-space indent inside the top-level ``jobs:`` mapping; every
    ``id:`` below it until the next such line belongs to that job.
    """
    found: list[tuple[str, list[str]]] = []
    inside = False
    job: str | None = None
    ids: list[str] = []
    for line in text.splitlines():
        if re.match(r"^jobs:\s*$", line):
            inside = True
            continue
        if not inside:
            continue
        if re.match(r"^\S", line):  # left the jobs mapping again
            break
        start = re.match(r"^  ([A-Za-z_][A-Za-z0-9_-]*):\s*$", line)
        if start:
            if job is not None:
                found.append((job, ids))
            job, ids = start.group(1), []
            continue
        declared = re.match(r"^\s+id:\s*(\S+)", line)
        if declared and job is not None:
            ids.append(declared.group(1))
    if job is not None:
        found.append((job, ids))
    return found


def test_the_jobs_and_their_steps_are_discovered() -> None:
    """Discovery that quietly found nothing would make the assertion below pass."""
    release = _steps_by_job((_WORKFLOWS / "release.yml").read_text(encoding="utf-8"))
    names = {job for job, _ in release}
    assert {"verify", "certify-against-reference", "publish-pypi"} <= names, names
    assert any(ids for _, ids in release), "no step ids parsed out of release.yml"


def test_no_job_declares_one_step_id_twice() -> None:
    """A duplicate step id is a workflow GitHub refuses to START, not one that fails.

    It is the worst-shaped failure a publishing pipeline can carry. There is no
    job, so there is no log and no failing step to read; the run is named after
    the FILE PATH rather than the workflow, because the `name:` key was never
    reached. Nothing in this suite, and nothing zizmor checks, looks at it —
    zizmor parses the file happily, since the YAML is valid and only the Actions
    schema is not.

    And `release.yml` runs on `push: tags: ["v*"]` alone, so the first run that
    would have surfaced it is the release itself: the tag is already pushed, and
    the fix is a new tag. This assertion exists because that shipped — the second
    `id: reference` went in beside an existing one while the certification
    checkout was being pinned, and every run of the publishing workflow failed at
    startup from that commit until it was noticed.
    """
    for path in _workflows():
        for job, ids in _steps_by_job(path.read_text(encoding="utf-8")):
            repeated = sorted({one for one in ids if ids.count(one) > 1})
            assert not repeated, (
                f"{path.name} job `{job}` declares {repeated} more than once. GitHub "
                "rejects the workflow before it starts, so this never appears as a "
                "failing step — give the later step its own id"
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
