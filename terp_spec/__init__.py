"""terp-spec — the Terp Standard's on-disk root, as a dependency (ADR 0082).

The spec is data (``catalog/``, ``corpus/``, the ``*.schema.json`` formats,
``restricted-surface.json``, ``VERSION``); this tiny accessor is the only code
it ships. Consumers locate the spec through :func:`spec_dir` instead of a
repo-relative path, so the framework's dependency on the standard is a declared
package dependency — the seam a repository split cuts along.

Layer-neutral: no dependencies, no ``terp.*`` imports.
"""

from __future__ import annotations

import pathlib

__all__ = ["spec_dir", "spec_version"]


def spec_dir() -> pathlib.Path:
    """The directory holding the spec artifacts (catalog/, corpus/, schemas, VERSION).

    In an editable/workspace install the package sits inside the spec directory
    itself, so the data lives one level up; in a built wheel the data is force-
    included inside the package. Both layouts are recognised by the presence of
    the ``VERSION`` marker, and a missing spec fails loudly rather than
    returning a plausible-but-empty path.
    """
    package = pathlib.Path(__file__).resolve().parent
    for candidate in (package, package.parent):
        if (candidate / "VERSION").is_file() and (candidate / "catalog").is_dir():
            return candidate
    raise FileNotFoundError(
        f"terp-spec data not found beside {package} (expected VERSION + catalog/)"
    )


def spec_version() -> str:
    """The semver of the standard (the ``VERSION`` artifact, ADR 0081)."""
    return (spec_dir() / "VERSION").read_text(encoding="utf-8").strip()
