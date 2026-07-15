"""The standard has a changelog, and the changelog cannot lie (spec hygiene).

``VERSION`` is the semver of the standard; ``CHANGELOG.md`` is the change
history keyed to it — what a checker certified against an earlier version
reads to see exactly what changed since. Held consistent the same way the
release workflow is: the top entry's version must equal the checked-in
``VERSION``, so a version bump cannot ship without its changelog entry (and a
changelog entry cannot claim an unreleased version).
"""

from __future__ import annotations

import re

from terp_spec import spec_dir, spec_version

_CHANGELOG = spec_dir() / "CHANGELOG.md"


def test_the_changelog_exists() -> None:
    assert _CHANGELOG.is_file(), (
        "CHANGELOG.md is missing — a version bump must ship its change history"
    )


def test_the_top_changelog_entry_matches_the_version() -> None:
    text = _CHANGELOG.read_text(encoding="utf-8")
    versions = re.findall(r"^## (\S+)", text, re.MULTILINE)
    assert versions, "CHANGELOG.md must contain at least one '## <version>' entry"
    assert versions[0] == spec_version(), (
        f"the top CHANGELOG.md entry ({versions[0]}) must equal VERSION "
        f"({spec_version()}) — bump both together"
    )


def test_changelog_entries_do_not_repeat_versions() -> None:
    text = _CHANGELOG.read_text(encoding="utf-8")
    versions = re.findall(r"^## (\d+\.\d+\.\d+)$", text, re.MULTILINE)
    assert len(versions) == len(set(versions)), (
        f"duplicate CHANGELOG.md version entries: {sorted(set(v for v in versions if versions.count(v) > 1))}"
    )
