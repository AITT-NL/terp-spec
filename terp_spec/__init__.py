"""terp-spec — the Terp contracts' on-disk root, as a dependency (ADR 0082).

The package is data: the ``*.schema.json`` contracts more than one program reads,
their ``*.fixtures.json`` and ``VERSION``. The rule catalog and its corpus are the
framework's own and ship with its checkers (terp-framework ADR 0203). This tiny
accessor is the only code here. Consumers locate the contracts through
:func:`spec_dir` instead of a repo-relative path, so depending on them is a declared
package dependency.

Layer-neutral: no dependencies, no ``terp.*`` imports.
"""

from __future__ import annotations

import pathlib

__all__ = ["spec_dir", "spec_version"]

#: Present in every release, in both layouts: what tells the data directory apart from
#: a plausible-but-empty path.
_MARKERS = ("VERSION", "findings.schema.json")


def spec_dir() -> pathlib.Path:
    """The directory holding the contracts (the schemas, their fixtures, VERSION).

    In an editable/workspace install the package sits inside the repository root,
    so the data lives one level up; in a built wheel the data is force-included
    inside the package. Both layouts are recognised by the markers, and a missing
    data directory fails loudly rather than returning a plausible-but-empty path.
    """
    package = pathlib.Path(__file__).resolve().parent
    for candidate in (package, package.parent):
        if all((candidate / marker).is_file() for marker in _MARKERS):
            return candidate
    raise FileNotFoundError(
        f"terp-spec data not found beside {package} (expected {' + '.join(_MARKERS)})"
    )


def spec_version() -> str:
    """The semver of the contracts release (the ``VERSION`` artifact)."""
    return (spec_dir() / "VERSION").read_text(encoding="utf-8").strip()
