#!/usr/bin/env python3
"""Generate the plain-language rule pages (docs/rules/) from the catalog.

The catalog is data-first precisely so consumers can be generated from it;
this is the non-technical-reader consumer: one Markdown page per rule stating
what the rule is, why it exists, what to do instead, and how to opt out —
without reading JSON. The pages are checked in and held to the catalog by
``tests/test_rule_docs.py`` (regenerate-and-compare), following the same
"docs can't lie" discipline as the rest of the spec suite.

Usage: python tools/generate_rule_docs.py   (from the spec root; stdlib only)
"""

from __future__ import annotations

import json
import pathlib

_ROOT = pathlib.Path(__file__).resolve().parents[1]
_CATALOG = _ROOT / "catalog"
_DOCS = _ROOT / "docs" / "rules"

_RUNTIME_LABEL = {
    "required": "Yes — the framework also enforces this while the app runs (fail closed).",
    "not-applicable": "No — this is a property of the written source only; the build-time check is the control, by recorded decision.",
    "deferred": "Not yet — a runtime control is planned; the gap is explicit and tracked.",
}


def render(entry: dict) -> str:
    """The Markdown page for one catalog entry (deterministic)."""
    surface, name = entry["id"].split("/", 1)
    lines = [
        f"# `{entry['id']}`",
        "",
        f"**{entry['title']}**",
        "",
        "> Generated from the catalog by `tools/generate_rule_docs.py` — do not",
        "> edit by hand; the parity test holds this page to",
        f"> `catalog/{surface}/{name}.json`.",
        "",
        "## Why this rule exists",
        "",
        entry["intent"],
        "",
    ]
    if entry.get("reference"):
        lines += [
            "## What to do instead",
            "",
            f"{entry['reference']} (reference stack; another stack ships its own realisation.)",
            "",
        ]
    lines += [
        "## If you really need an exception",
        "",
    ]
    if entry.get("opt_out"):
        lines += [
            "Add a justified marker on (or immediately above) the line, and record it",
            "in your app's escape-hatch budget:",
            "",
            "```",
            entry["opt_out"],
            "```",
            "",
            "An unjustified marker is itself a violation, and marker counts must",
            "exactly match the checked-in budget (which can only shrink).",
            "",
        ]
    else:
        lines += [
            "There is none. This rule governs the escape-hatch mechanism itself,",
            "so it cannot be waived by that mechanism.",
            "",
        ]
    lines += [
        "## Enforcement",
        "",
        f"- Checked while the app runs? {_RUNTIME_LABEL[entry['runtime']['applicability']]}",
    ]
    for enforcement in entry["enforcement"]:
        lines.append(
            f"- `{enforcement['kind']}`: `{enforcement['tool']}` — `{enforcement['ref']}`"
        )
    lines.append("")
    return "\n".join(lines)


def generate() -> dict[pathlib.Path, str]:
    """Every page the catalog implies, as {absolute path: content}."""
    pages: dict[pathlib.Path, str] = {}
    for surface in ("backend", "frontend"):
        for path in sorted((_CATALOG / surface).glob("*.json")):
            entry = json.loads(path.read_text(encoding="utf-8"))
            pages[_DOCS / surface / f"{path.stem}.md"] = render(entry)
    return pages


def main() -> None:
    pages = generate()
    for path, content in pages.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    print(f"wrote {len(pages)} rule pages under {_DOCS.relative_to(_ROOT)}/")


if __name__ == "__main__":
    main()
