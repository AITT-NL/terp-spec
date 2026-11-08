"""The contracts are self-consistent — no framework required (ADR 0082).

Everything here reads only this repository's own artifacts, so the suite runs
standalone:

* the package is versioned, and both packaging manifests carry the same version;
* both manifests ship exactly the artifacts on disk, in both directions;
* the finding format is checked in, and the layout declaration schema stays inside
  the validator subset its consumers apply.

The rule catalog, its corpus and the checks that hold them live in terp-framework
(its ADR 0203), beside the checkers that enforce the rules.
"""

from __future__ import annotations

import json
import re

from schema_subset import _validate
from terp_spec import spec_dir, spec_version

_SPEC = spec_dir()


def test_the_spec_is_versioned() -> None:
    version = spec_version()
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), (
        f"spec/VERSION must be a semver string, got {version!r}"
    )


def test_the_packaging_manifests_carry_the_spec_version() -> None:
    """The distribution version IS the spec version (ADR 0082): terp-spec and
    @terpjs/spec are two thin manifests over one data directory, so all three
    version declarations must agree."""
    version = spec_version()
    pyproject = (_SPEC / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', pyproject, re.MULTILINE)
    assert match and match.group(1) == version, (
        f"spec/pyproject.toml version must equal spec/VERSION ({version})"
    )
    manifest = json.loads((_SPEC / "package.json").read_text(encoding="utf-8"))
    assert manifest["version"] == version, (
        f"spec/package.json version must equal spec/VERSION ({version})"
    )


#: What the spec ships, beside the root-level ``*.json`` artifacts discovered below.
#: ``package.json`` is the npm manifest itself, never a payload.
_SHIPPED_DIRECTORIES: tuple[str, ...] = ()
_SHIPPED_FILES = ("VERSION",)


def test_every_shipped_artifact_is_in_both_packaging_manifests() -> None:
    """A data artifact the repository holds but neither manifest names is invisible to
    every consumer, and the absence is SILENT.

    0.26.1 exists because of exactly this: 0.26.0 added
    ``layout-declaration.schema.json`` to the repository and to neither manifest, so the
    schema the release announced as normative reached no wheel and no tarball. Nothing
    failed — the reference implementation's parity test for it *skipped*, because a schema
    that is absent and a schema that is satisfied are the same silence. Version parity
    (above) could not see it: both manifests agreed on the version and disagreed with the
    repository about the contents.

    So this holds the two manifests to the directory in BOTH directions. An artifact on
    disk that no manifest names fails here; a manifest entry with nothing behind it fails
    here too, which is what stops the fix for the first failure from being a stale line.
    """
    pyproject = (_SPEC / "pyproject.toml").read_text(encoding="utf-8")
    force_include = re.search(
        r"^\[tool\.hatch\.build\.targets\.wheel\.force-include\]\n((?:.+\n)*)",
        pyproject,
        re.MULTILINE,
    )
    assert force_include, "spec/pyproject.toml declares no wheel force-include table"
    wheel_keys = set(re.findall(r'^"([^"]+)" = ', force_include.group(1), re.MULTILINE))
    npm_files = set(json.loads((_SPEC / "package.json").read_text(encoding="utf-8"))["files"])

    shipped = {
        path.name for path in _SPEC.glob("*.json") if path.name != "package.json"
    } | set(_SHIPPED_FILES)
    shipped |= {name for name in _SHIPPED_DIRECTORIES if (_SPEC / name).is_dir()}

    assert not shipped - wheel_keys, (
        "artifacts in the repository that the wheel does not carry — add them to "
        f"[tool.hatch.build.targets.wheel.force-include]: {sorted(shipped - wheel_keys)}"
    )
    assert not shipped - npm_files, (
        "artifacts in the repository that the npm tarball does not carry — add them to "
        f'package.json "files": {sorted(shipped - npm_files)}'
    )
    assert not wheel_keys - shipped, (
        f"wheel force-include names artifacts that do not exist: {sorted(wheel_keys - shipped)}"
    )
    assert not npm_files - shipped, (
        f'package.json "files" names artifacts that do not exist: {sorted(npm_files - shipped)}'
    )


def test_the_findings_schema_is_checked_in() -> None:
    findings = json.loads((_SPEC / "findings.schema.json").read_text(encoding="utf-8"))
    assert findings["type"] == "array", "a checker's output is an array of findings"
    assert set(findings["items"]["required"]) == {"rule", "path"}, (
        "a finding is attributed to a catalog rule id at a path"
    )


def test_the_layout_declaration_schema_is_well_formed() -> None:
    """The document an app checks in to declare its layout: sorted, unique,
    non-empty enums, and nothing outside the validator subset this package ships.

    The subset check is not pedantry. This schema exists to be applied by a
    consumer, and the smallest consumer available is the validator in
    ``schema_subset.py`` — so if the schema reaches for a keyword that validator
    cannot honour, the schema is unusable by exactly the audience it was written
    for. Exercised by
    validating documents through it rather than by inspecting its keys, which is
    the only form that proves both at once."""
    schema = json.loads((_SPEC / "layout-declaration.schema.json").read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False, (
        "an unknown top-level key must be refused, not ignored — a declaration that "
        "does nothing must not look like one that works"
    )
    # The per-stack keys: a plain string because the values are a stack's to publish,
    # which is exactly why each one owes a description saying what naming it means. An
    # enum-free string with no prose would be a key a consumer can read and cannot act on.
    for key in sorted(schema["properties"]):
        definition = schema["properties"][key]
        if definition.get("type") != "string":
            continue
        assert definition.get("minLength") == 1, (
            f"{key}: a per-stack name must refuse the empty string — an empty name is not "
            "the app declining to declare, it is a declaration of nothing"
        )
        assert definition.get("description", "").strip(), (
            f"{key}: say what naming it means — the schema is the normative statement"
        )

    shell = schema["properties"]["shell"]
    assert shell["additionalProperties"] is False
    for key, definition in sorted(shell["properties"].items()):
        assert definition.get("description", "").strip(), (
            f"shell.{key}: say what the key means — the schema is the normative statement"
        )
        values = definition.get("enum")
        if values is None:
            # Not every shell key is a choice between fixed values; the structured one is
            # held to its own discipline below rather than skipped.
            continue
        assert isinstance(values, list) and len(values) > 1, (
            f"shell.{key}: an enum of one is a constant, not a choice"
        )
        assert all(isinstance(v, str) and v.strip() for v in values), f"shell.{key}"
        assert values == sorted(values) and len(values) == len(set(values)), (
            f"shell.{key}: enum entries must be sorted and unique"
        )

    # Every shell key that is a SHAPE rather than a choice between fixed values. What is fixed
    # normatively is the shape, so it is held to the same rules the document itself is: refuse
    # an unknown field, declare a type for each one so a consumer never has to guess, and say
    # what every field means. Written over all of them rather than over the first one, because
    # the first one is how the second arrives unchecked — `brand` did.
    for key, definition in sorted(shell["properties"].items()):
        if "enum" in definition:
            continue
        assert definition.get("type") in {"object", "array"}, (
            f"shell.{key}: a key that is not a choice must say what shape it is"
        )
        entry = definition["items"] if definition["type"] == "array" else definition
        assert entry.get("type") == "object", f"shell.{key}: entries are objects"
        assert entry.get("additionalProperties") is False, (
            f"shell.{key}: an unknown field must be refused, not ignored"
        )
        assert entry.get("properties"), f"shell.{key}: an empty shape declares nothing"
        for field, field_definition in sorted(entry["properties"].items()):
            assert field_definition.get("type"), f"shell.{key}.{field}: declare a type"
            assert field_definition.get("description", "").strip(), (
                f"shell.{key}.{field}: say what the field means"
            )

    # And the navigation group's own two decisions, which are not derivable from the shape.
    group = shell["properties"]["navGroups"]["items"]
    assert group["type"] == "object" and group["additionalProperties"] is False, (
        "an unknown field on a navigation group must be refused, not ignored"
    )
    assert set(group["required"]) == {"id", "label"}, (
        "a group with no id is one nothing can name, and a group with no label leaves "
        "'renders no label' an omission rather than a decision the document states"
    )
    assert group["properties"]["id"].get("minLength") == 1
    assert "minLength" not in group["properties"]["label"], (
        "the empty label is the declared way to say 'positioning-only group' — refusing it "
        "would remove the only way to state that"
    )
    # The brand's two keys are BOTH optional and both floored: an empty path is a mark a
    # consumer would try to load and fail on, where an absent key is the app saying it has no
    # second asset — which is a different and legitimate statement.
    brand = shell["properties"]["brand"]["properties"]
    assert "required" not in shell["properties"]["brand"], (
        "an app with one mark declares one; requiring the dark counterpart would force every "
        "app to claim a second asset it may not have"
    )
    for field, definition in sorted(brand.items()):
        assert definition.get("minLength") == 1, f"brand.{field}: an empty path is not a mark"

    # A compliant document, and one per way of being wrong. `_validate` reports an
    # unknown schema KEYWORD too, so a green pass here also proves the schema stays
    # inside the subset.
    assert _validate({}, schema, "root") == [], "every key is optional"
    assert (
        _validate(
            {"contract": "standard", "shell": {"density": "compact"}}, schema, "root"
        )
        == []
    )
    assert _validate({"defaultTheme": "midnight"}, schema, "root") == [], (
        "the palette an app opens on is per-stack, so any non-empty name validates here "
        "and it is the consumer that refuses one it does not ship"
    )
    assert _validate({"defaultTheme": "system"}, schema, "root") == [], (
        "the one reserved name, and it must validate like any other"
    )
    # "theme", not "defaultTheme": a near-miss of a real key is the interesting case, because
    # that is the shape a hand-edit produces and the shape `additionalProperties` exists for.
    assert _validate({"theme": "dark"}, schema, "root"), "an unknown top-level key"
    assert _validate({"shell": {"sidebarWidth": "20rem"}}, schema, "root"), "an unknown shell key"
    assert _validate({"shell": {"density": "compakt"}}, schema, "root"), "a value off the enum"
    assert _validate({"contract": ""}, schema, "root"), "an empty contract name"
    assert _validate({"contract": 1}, schema, "root"), "a contract that is not a string"
    assert _validate({"defaultTheme": ""}, schema, "root"), "an empty palette name"
    assert _validate({"defaultTheme": 1}, schema, "root"), "a palette that is not a string"

    # The navigation groups, whose entries are the only nested shape in the document.
    def groups(*entries: object) -> dict:
        return {"shell": {"navGroups": list(entries)}}

    assert _validate(groups(), schema, "root") == [], "declaring no groups is legal"
    assert (
        _validate(groups({"id": "work", "label": "Workspace", "order": 1}), schema, "root") == []
    )
    assert _validate(groups({"id": "work", "label": ""}), schema, "root") == [], (
        "the positioning-only group: an empty label is a declaration, not an omission"
    )
    assert _validate(groups({"id": "", "label": "Workspace"}), schema, "root"), "an empty id"
    assert _validate(groups({"id": "work"}), schema, "root"), "a group with no label at all"
    assert _validate(
        groups({"id": "work", "label": "Workspace", "colour": "red"}), schema, "root"
    ), "an unknown field on a group"
    assert _validate(
        groups({"id": "work", "label": "Workspace", "order": "1"}), schema, "root"
    ), "a sort key that is not an integer"
    assert _validate({"shell": {"navGroups": {}}}, schema, "root"), "groups that are not a list"

    # The brand mark.
    assert _validate({"shell": {"brand": {"logo": "/logo.png"}}}, schema, "root") == [], (
        "one mark is a complete declaration"
    )
    assert (
        _validate(
            {"shell": {"brand": {"logo": "/logo.png", "logoDark": "/logo-dark.png"}}},
            schema,
            "root",
        )
        == []
    )
    assert _validate({"shell": {"brand": {}}}, schema, "root") == [], (
        "declaring the group and nothing in it is legal, like every other absent key"
    )
    assert _validate({"shell": {"brand": {"logo": ""}}}, schema, "root"), "an empty path"
    assert _validate({"shell": {"brand": {"icon": "/x.png"}}}, schema, "root"), "an unknown mark"
    assert _validate({"shell": {"brand": {"logo": 1}}}, schema, "root"), "a path that is not text"
