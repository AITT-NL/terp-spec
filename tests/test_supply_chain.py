"""The workflows that publish the contracts are held to the bar the framework sets.

This repository holds OIDC publishing rights to two registries. The framework
installs the published ``terp-spec``/``@terpjs/spec``, so every consumer's gate
resolves an artifact these workflows produce. That made it the least-hardened repository in the platform while
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
import tomllib

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_WORKFLOWS = _ROOT / ".github" / "workflows"

#: `uses: owner/repo@<40 hex>`, optionally followed by the `# vX.Y.Z` comment that
#: makes the pin readable and lets an updater recognise what it is looking at.
_PINNED = re.compile(r"uses:\s*\S+@[0-9a-f]{40}\b")
_ANY_USES = re.compile(r"^\s*(?:-\s*)?uses:\s*(\S+)", re.M)

#: The one path the secret scan steps aside for, and only in history: the credential
#: rule's violation samples, invented by construction, before the corpus moved to the
#: framework in 0.44.0.
_HISTORY_ONLY_PATHS = frozenset({"^corpus/backend/no_hardcoded_credentials/violation-"})


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
    """The scan steps aside for one path, and only for commits from before the corpus left.

    Until 0.44.0 the corpus lived here, and a violation sample for
    ``backend/no_hardcoded_credentials`` that held no credential-shaped literal was a
    broken sample. CI scans every commit, so those four invented literals would fail it
    forever. A per-line baseline would do the same job less legibly.

    This holds the parsed configuration to one shape rather than searching its text:
    ``[extend]`` keeps the default ruleset on and disables none of it; nothing else is
    declared at the top level; each allowlist carries only a description and paths,
    so nothing is allowed by value, by commit or for a chosen rule; the paths are exactly
    the one sanctioned prefix; and no file at that path exists, so the allowance cannot
    hide a literal committed from now on.
    """
    config = _ROOT / ".gitleaks.toml"
    assert config.is_file(), (
        "the history holds invented credential-shaped samples; .gitleaks.toml is where "
        "that is recorded, scoped and reviewable"
    )
    parsed = tomllib.loads(config.read_text(encoding="utf-8"))
    assert parsed.get("extend") == {"useDefault": True}, (
        f".gitleaks.toml declares [extend] as {parsed.get('extend')!r}. It must be exactly "
        "`useDefault = true`: without it the file REPLACES the default ruleset, and "
        "`disabledRules`, `path` or `url` would switch detectors off or swap them"
    )
    extra = sorted(set(parsed) - {"extend", "allowlists"})
    assert not extra, (
        f".gitleaks.toml declares {extra}. Only [extend] and [[allowlists]] belong here: "
        "`rules` adds or overrides detectors, and a singular `allowlist` is a second, "
        "unguarded place to narrow the scan"
    )
    paths: set[str] = set()
    for allowlist in parsed.get("allowlists", []):
        widening = sorted(set(allowlist) - {"description", "paths"})
        assert not widening, (
            f"an allowlist declares {widening}. Allow by path alone: `regexes` and "
            "`stopwords` allow a match by value, `commits` by commit, and either hides the "
            "same literal anywhere; `targetRules` and `condition` change what a path means"
        )
        paths.update(allowlist.get("paths", []))
    assert paths == _HISTORY_ONLY_PATHS, (
        f"the secret scan is taken off {sorted(paths)}; it may be taken off exactly "
        f"{sorted(_HISTORY_ONLY_PATHS)}, the invented samples in history. Anywhere else a "
        "match may be a real credential, and the answer to one of those is to rotate it"
    )
    assert not (_ROOT / "corpus").exists(), (
        "corpus/ is back. The allowance covers the samples in history only; the corpus "
        "lives in terp-framework, beside the checks it holds"
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
    assert {"verify", "publish-pypi", "publish-npm", "github-release"} <= names, names
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
    `id: reference` went in beside an existing one while a cross-repository
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
