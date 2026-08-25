"""The Terp Standard is self-consistent — no framework required (ADR 0082).

The spec-only half of the validations that used to live in the framework's
``tests/architecture/test_spec_catalog.py``: everything here reads only the
spec's own artifacts (catalog, corpus, schemas, the refused surface, VERSION),
so this suite runs standalone — it is the CI of a future spec-only repository.
The parity assertions that hold the catalog to the *live implementations*
(``terp.arch`` rules, the ESLint adapter, conformance probe titles) stay
framework-side, where those implementations live.

* the spec is versioned, and the packaging manifests carry the same version;
* every entry validates against the checked-in ``spec/catalog/schema.json``
  (the spec is self-describing, so the schema travels with a repo split);
* the finding format and the declared refused surface are well-formed, and
  every catalog citation of the refused surface resolves;
* the ``corpus`` flag matches the truth on disk (cases exist iff the flag says
  so, no corpus directory is orphaned), and ``corpus/PENDING.json`` — the
  coverage ratchet — lists exactly the rules still without corpus cases.
"""

from __future__ import annotations

import json
import re

from terp_spec import spec_dir, spec_version

_SPEC = spec_dir()
_CATALOG = _SPEC / "catalog"
_CORPUS = _SPEC / "corpus"


def _entries(surface: str) -> dict[str, dict]:
    entries: dict[str, dict] = {}
    for path in sorted((_CATALOG / surface).glob("*.json")):
        entry = json.loads(path.read_text(encoding="utf-8"))
        assert entry["id"] == f"{surface}/{path.stem}", (
            f"{path}: id {entry['id']!r} must match its path ({surface}/{path.stem})"
        )
        entries[path.stem] = entry
    return entries


# --------------------------------------------------------------------------- #
# schema validity: every entry validates against the checked-in schema.json
# --------------------------------------------------------------------------- #
def _validate(instance: object, schema: dict, path: str) -> list[str]:
    """Validate *instance* against the JSON Schema subset spec/catalog/schema.json uses.

    Deliberately minimal (type / enum / pattern / minLength / minItems / required /
    properties / additionalProperties / items) so the spec stays dependency-free;
    an unknown constraint keyword fails loudly rather than passing silently.
    """
    _KNOWN = {
        "$schema", "$id", "title", "description",  # annotations
        "type", "enum", "pattern", "minLength", "minimum", "minItems",
        "required", "properties", "additionalProperties", "items",
    }
    errors = [f"{path}: unknown schema keyword {key!r}" for key in schema if key not in _KNOWN]
    if "enum" in schema and instance not in schema["enum"]:
        return errors + [f"{path}: {instance!r} not in {schema['enum']}"]
    expected = schema.get("type")
    supported_types = {"object", "array", "string", "integer", "boolean"}
    if expected is not None and (
        not isinstance(expected, str) or expected not in supported_types
    ):
        return errors + [f"{path}: unsupported schema type {expected!r}"]
    if expected == "object":
        if not isinstance(instance, dict):
            return errors + [f"{path}: expected object, got {type(instance).__name__}"]
        for field in schema.get("required", []):
            if field not in instance:
                errors.append(f"{path}: missing required field {field!r}")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            errors.extend(
                f"{path}: unexpected field {key!r}" for key in instance if key not in properties
            )
        for key, value in instance.items():
            if key in properties:
                errors.extend(_validate(value, properties[key], f"{path}.{key}"))
    elif expected == "array":
        if not isinstance(instance, list):
            return errors + [f"{path}: expected array, got {type(instance).__name__}"]
        if len(instance) < schema.get("minItems", 0):
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        for index, item in enumerate(instance):
            errors.extend(_validate(item, schema.get("items", {}), f"{path}[{index}]"))
    elif expected == "string":
        if not isinstance(instance, str):
            return errors + [f"{path}: expected string, got {type(instance).__name__}"]
        if len(instance.strip()) < schema.get("minLength", 0):
            errors.append(f"{path}: shorter than minLength {schema['minLength']}")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            errors.append(f"{path}: {instance!r} does not match {schema['pattern']!r}")
    elif expected == "integer":
        if not isinstance(instance, int) or isinstance(instance, bool):
            return errors + [f"{path}: expected integer, got {type(instance).__name__}"]
        if instance < schema.get("minimum", instance):
            errors.append(f"{path}: below minimum {schema['minimum']}")
    elif expected == "boolean":
        if not isinstance(instance, bool):
            return errors + [f"{path}: expected boolean, got {type(instance).__name__}"]
    return errors


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
_SHIPPED_DIRECTORIES = ("catalog", "corpus")
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


# --------------------------------------------------------------------------- #
# the escape-hatch contract is uniform: a marker names the CATALOG RULE NAME
# (never a tool-internal rule id — the suppression analogue of findings
# attribution), and the governance rules themselves carry no opt-out
# --------------------------------------------------------------------------- #
_GOVERNANCE_RULES_WITHOUT_OPT_OUT = {
    "backend/escape_hatch_budget",
    "backend/ungoverned_escape_hatch",
    "frontend/escape-hatch",
}

_OPT_OUT_TEMPLATES = {
    "backend": "# arch-allow-{name}: <reason>",
    "frontend": "// terp-allow-{name}: <reason>",
}


def test_opt_outs_derive_from_the_catalog_rule_name() -> None:
    """Every opt-out marker spelling is the rule's own catalog name (backend
    snake_case rendered with dashes), so a marker can never waive a sibling
    rule that happens to share a tool-internal rule id — and the escape-hatch
    governance rules declare no opt-out at all: governance cannot be waived by
    the mechanism it governs."""
    for surface in ("backend", "frontend"):
        for name, entry in _entries(surface).items():
            rule_id = f"{surface}/{name}"
            opt_out = entry.get("opt_out")
            if rule_id in _GOVERNANCE_RULES_WITHOUT_OPT_OUT:
                assert opt_out is None, (
                    f"{rule_id}: an escape-hatch governance rule must not declare an "
                    "opt_out — waiving governance with governance is refused"
                )
                continue
            expected = _OPT_OUT_TEMPLATES[surface].format(name=name.replace("_", "-"))
            assert opt_out == expected, (
                f"{rule_id}: opt_out must name the catalog rule "
                f"({expected!r}), got {opt_out!r}"
            )


def test_every_catalog_entry_validates_against_the_checked_in_schema() -> None:
    schema = json.loads((_CATALOG / "schema.json").read_text(encoding="utf-8"))
    for surface in ("backend", "frontend"):
        for name, entry in _entries(surface).items():
            errors = _validate(entry, schema, f"{surface}/{name}")
            assert errors == [], "\n".join(errors)
            assert entry["surface"] == surface, f"{surface}/{name}: wrong surface"
            kinds = [enforcement["kind"] for enforcement in entry["enforcement"]]
            assert kinds[0] == "build-time", (
                f"{surface}/{name}: the first enforcement entry is the build-time reference"
            )


def test_the_findings_schema_is_checked_in() -> None:
    findings = json.loads((_SPEC / "findings.schema.json").read_text(encoding="utf-8"))
    assert findings["type"] == "array", "a checker's output is an array of findings"
    assert set(findings["items"]["required"]) == {"rule", "path"}, (
        "a finding is attributed to a catalog rule id at a path"
    )


# --------------------------------------------------------------------------- #
# runtime applicability: every rule states whether the two-layer discipline
# pairs it with a fail-closed runtime control, and the statement is coherent —
# 'required' iff a kind 'runtime' enforcement entry exists; an exemption
# ('not-applicable' / 'deferred') always carries a rationale and never a
# runtime entry. The schema makes the field mandatory; these assertions hold
# the cross-field consistency the minimal schema subset cannot express.
# --------------------------------------------------------------------------- #
def test_runtime_applicability_is_coherent() -> None:
    for surface in ("backend", "frontend"):
        for name, entry in _entries(surface).items():
            runtime = entry["runtime"]
            applicability = runtime["applicability"]
            kinds = {enforcement["kind"] for enforcement in entry["enforcement"]}
            if applicability == "required":
                assert "runtime" in kinds, (
                    f"{surface}/{name}: runtime.applicability is 'required' but no "
                    "enforcement entry has kind 'runtime' — declare the fail-closed "
                    "runtime control (tool + ref), or reclassify with a rationale"
                )
            else:
                assert "runtime" not in kinds, (
                    f"{surface}/{name}: a kind 'runtime' enforcement entry exists but "
                    f"runtime.applicability is {applicability!r} — a declared runtime "
                    "control means the rule is 'required'"
                )
                assert runtime.get("rationale", "").strip(), (
                    f"{surface}/{name}: runtime.applicability {applicability!r} is an "
                    "exemption from the two-layer discipline and must carry a non-empty "
                    "rationale"
                )
            if applicability == "deferred":
                assert runtime.get("tracking", "").strip(), (
                    f"{surface}/{name}: a deferred runtime control is an explicit, "
                    "reviewed gap and must carry a 'tracking' reference (an issue URL "
                    "or the reference tracker document plus the named seam) — an "
                    "untracked deferral is an open-ended gap"
                )
            else:
                assert "tracking" not in runtime, (
                    f"{surface}/{name}: runtime.tracking is the deferral lifecycle "
                    f"field and is meaningless for {applicability!r}"
                )


# --------------------------------------------------------------------------- #
# the declared refused surface (restricted-surface.json) is well-formed and
# every catalog citation of it resolves to a real key — the stack-neutral,
# normative half of the portable prohibition rules travels with the spec, not the
# adapter (the adapter-side parity lives in eslint-boundaries/src/surface.test.js)
# --------------------------------------------------------------------------- #
_SURFACE_LIST_KEYS = (
    "restrictedElements",
    "restrictedAttributes",
    "restrictedGlobals",
    "restrictedMemberCalls",
    "styleImportExtensions",
    "deepImportPathSegments",
)


def test_the_declared_refused_surface_is_well_formed() -> None:
    surface = json.loads((_SPEC / "restricted-surface.json").read_text(encoding="utf-8"))
    for key in _SURFACE_LIST_KEYS:
        values = surface[key]
        assert isinstance(values, list) and values, f"{key}: must be a non-empty array"
        assert all(isinstance(v, str) and v.strip() for v in values), (
            f"{key}: entries must be non-empty strings"
        )
        assert values == sorted(values) and len(values) == len(set(values)), (
            f"{key}: entries must be sorted and unique"
        )


def test_the_layout_declaration_schema_is_well_formed() -> None:
    """The document an app checks in to declare its layout, held to the same
    discipline as the refused-surface file: sorted, unique, non-empty enums, and
    nothing outside the validator subset this spec ships.

    The subset check is not pedantry. This schema exists to be applied by a
    consumer, and the smallest consumer available is the validator in this file —
    so if the schema reaches for a keyword that validator cannot honour, the
    schema is unusable by exactly the audience it was written for. Exercised by
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


def test_the_layout_declaration_schema_is_claimed_by_a_rule() -> None:
    """Normative data joins this spec when a rule realises it, not before.

    The same standard the refused-surface linkage holds: an unclaimed file is dead
    spec data. This one is claimed by the rule that enforces the contract the
    document opts into, which is also the rule whose two halves the document exists
    to keep from disagreeing."""
    claimants = [
        f"frontend/{name}"
        for name, entry in _entries("frontend").items()
        if "layout-declaration.schema.json" in entry.get("reference", "")
        or "layout-declaration.schema.json" in entry["intent"]
    ]
    assert claimants, (
        "no catalog entry cites layout-declaration.schema.json — normative data with no "
        "rule realising it is dead spec data"
    )


def test_catalog_citations_of_the_refused_surface_resolve() -> None:
    """The structural linkage: a rule's ``restricted_surface`` field lists the
    refused-surface keys it realises (schema-validated against the key enum);
    every key must be claimed by some rule (an unclaimed key is dead spec
    data), and a prose mention in ``intent`` must agree with the field —
    the field is authoritative, prose is free-form commentary."""
    cited: set[str] = set()
    for surface in ("backend", "frontend"):
        for name, entry in _entries(surface).items():
            declared = set(entry.get("restricted_surface", []))
            assert declared <= set(_SURFACE_LIST_KEYS), (
                f"{surface}/{name}: restricted_surface cites unknown keys "
                f"{sorted(declared - set(_SURFACE_LIST_KEYS))}"
            )
            cited |= declared
            for match in re.finditer(
                r"restricted-surface\.json \(([A-Za-z, ]+)\)", entry["intent"]
            ):
                prose = {part.strip() for part in match.group(1).split(",")}
                assert prose <= declared, (
                    f"{surface}/{name}: intent prose cites refused-surface keys "
                    f"{sorted(prose - declared)} the restricted_surface field does "
                    "not declare — the field is the structural citation; keep them "
                    "in agreement"
                )
    assert cited == set(_SURFACE_LIST_KEYS), (
        "every refused-surface key must be claimed by a catalog entry's "
        "restricted_surface field (an unclaimed key is dead spec data): "
        f"unclaimed {sorted(set(_SURFACE_LIST_KEYS) - cited)}"
    )


# --------------------------------------------------------------------------- #
# corpus coverage ratchet: uncovered rules are explicitly listed, and only shrink
# --------------------------------------------------------------------------- #
def test_pending_corpus_ratchet_matches_the_catalog() -> None:
    pending = set(json.loads((_CORPUS / "PENDING.json").read_text(encoding="utf-8"))["pending"])
    uncovered = {
        f"{surface}/{name}"
        for surface in ("backend", "frontend")
        for name, entry in _entries(surface).items()
        if not entry["corpus"]
    }
    assert pending == uncovered, (
        "corpus/PENDING.json (the coverage ratchet) disagrees with the catalog — "
        f"seeded but still listed: {sorted(pending - uncovered)}; "
        f"uncovered but unlisted: {sorted(uncovered - pending)}"
    )


def test_every_portable_backend_rule_has_corpus_cases() -> None:
    """The corpus is the acceptance test for a second-stack rule pack, so every
    static-portable backend rule must ship cases (frontend portable rules are
    already fully covered; the ratchet governs the bespoke remainder)."""
    uncovered = [
        name
        for name, entry in _entries("backend").items()
        if entry["layer"] == "static-portable" and not entry["corpus"]
    ]
    assert uncovered == [], (
        f"static-portable backend rules without corpus cases: {sorted(uncovered)}"
    )


# --------------------------------------------------------------------------- #
# corpus flag <-> corpus directories, both directions
# --------------------------------------------------------------------------- #
def test_corpus_flags_match_the_corpus_directories() -> None:
    for surface in ("backend", "frontend"):
        entries = _entries(surface)
        on_disk = {p.name for p in (_CORPUS / surface).iterdir() if p.is_dir()} if (
            _CORPUS / surface
        ).is_dir() else set()
        flagged = {name for name, entry in entries.items() if entry["corpus"]}
        assert on_disk - set(entries) == set(), (
            f"orphan corpus dirs without a catalog entry: {sorted(on_disk - set(entries))}"
        )
        assert flagged == on_disk, (
            f"{surface}: corpus flags disagree with corpus/{surface}/ — "
            f"flagged-but-missing {sorted(flagged - on_disk)}, present-but-unflagged {sorted(on_disk - flagged)}"
        )
        for name in on_disk:
            cases = {p.name for p in (_CORPUS / surface / name).iterdir() if p.is_dir()}
            assert any(case.startswith("violation-") for case in cases), (
                f"{surface}/{name}: corpus needs at least one violation-* case"
            )
            assert any(case.startswith("compliant-") for case in cases), (
                f"{surface}/{name}: corpus needs at least one compliant-* case"
            )
            assert all(case.startswith(("violation-", "compliant-")) for case in cases), (
                f"{surface}/{name}: unexpected case dirs {sorted(cases)}"
            )


# --------------------------------------------------------------------------- #
# the normative prose is stack-neutral: title and intent state the invariant
# in plain prose — reference-implementation vocabulary (framework symbols,
# docstring markup, marker spellings, repo-internal pointers) belongs in the
# non-normative fields (enforcement / reference / opt_out / guide_topic)
# --------------------------------------------------------------------------- #
_REFERENCE_LEAKAGE: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"``"), "RST literal markup — write plain prose"),
    (re.compile(r":[a-z]+:`"), "a Sphinx role — write plain prose"),
    (re.compile(r"\bterp\.[a-z_]"), "a terp.* package path — reference metadata"),
    (re.compile(r"@terpjs?/"), "an @terpjs/* package path — reference metadata"),
    (re.compile(r"\bterp +(?:check|guide|migrate)\b"), "the reference CLI — reference metadata"),
    (re.compile(r"(?:arch|terp)-allow"), "a marker spelling — belongs in opt_out / reference"),
    (re.compile(r"\bADR +\d"), "a framework ADR pointer — unresolvable for a spec consumer"),
    (
        re.compile(
            r"\b(?:BaseService|BaseTable|BaseSchema|BaseUpdateSchema|ModuleSpec|SessionDep"
            r"|create_app|FastAPI|SQLModel|sqlmodel|SQLAlchemy|sqlalchemy|Alembic|alembic"
            r"|base_query|business_filters|response_model|TenantScopedService|TenantScopedMixin"
            r"|SoftDeleteMixin|OwnedMixin|ActorStampedMixin|FileRef|WriteGuardedSession"
            r"|ControlPlane|EventDefinition|JobDefinition|LifecycleEventMap|PaginationDep"
            r"|SecurityConfig|configure_logging|basicConfig|dictConfig|fileConfig"
            r"|dependency_overrides|add_middleware|BaseHTTPMiddleware|assert_app_clean"
            r"|ArchViolation|assert_migrations_current|create_all|httpx|Celery|APScheduler"
            r"|React)\b"
        ),
        "a reference-implementation symbol — belongs in reference / enforcement",
    ),
    (
        re.compile(r"Page\[|Policy\.[a-z_]|Roles\.[A-Z]"),
        "a reference API shape — belongs in reference / enforcement",
    ),
]


def test_normative_prose_is_stack_neutral() -> None:
    """``title`` and ``intent`` are the normative, stack-neutral statement of a
    rule; the reference realisation lives in ``enforcement`` / ``reference`` /
    ``opt_out`` / ``guide_topic``. Hold the prose to that split, so
    docstring-flavoured markup and framework symbols cannot drift back in.
    Sibling rules are cited by their catalog rule name — that is catalog
    vocabulary, not leakage, so rule names are scrubbed before matching."""
    rule_names = sorted(
        (name for surface in ("backend", "frontend") for name in _entries(surface)),
        key=len,
        reverse=True,
    )
    problems: list[str] = []
    for surface in ("backend", "frontend"):
        for name, entry in _entries(surface).items():
            if entry["intent"].strip() == entry["title"].strip():
                problems.append(
                    f"{surface}/{name}: intent merely repeats the title — say why the rule exists"
                )
            for field in ("title", "intent"):
                text = entry[field]
                for token in rule_names:
                    text = text.replace(token, " ")
                for pattern, why in _REFERENCE_LEAKAGE:
                    match = pattern.search(text)
                    if match:
                        problems.append(f"{surface}/{name}.{field}: {match.group(0)!r} is {why}")
    assert problems == [], "normative prose must stay stack-neutral:\n" + "\n".join(problems)


# --------------------------------------------------------------------------- #
# the detector-residual ratchet (corpus/RESIDUALS.json): the statically-erased
# or renamed forms deliberately outside the corpus contract, per rule — a
# machine-readable, shrink-only list (like PENDING.json) instead of README
# folklore. Closing a residual means seeding the corpus case and deleting the
# entry, never silently widening or narrowing the contract.
# --------------------------------------------------------------------------- #
def test_the_residual_ratchet_is_well_formed() -> None:
    residuals = json.loads((_CORPUS / "RESIDUALS.json").read_text(encoding="utf-8"))["residuals"]
    catalogued = {
        f"{surface}/{name}" for surface in ("backend", "frontend") for name in _entries(surface)
    }
    assert list(residuals) == sorted(residuals), "residual rule ids must be sorted"
    for rule, entries in residuals.items():
        assert rule in catalogued, (
            f"RESIDUALS.json names unknown rule {rule!r} — a residual belongs to a "
            "catalogued rule"
        )
        assert isinstance(entries, list) and entries, (
            f"{rule}: residuals must be a non-empty array (an empty list is a "
            "closed residual — delete the key)"
        )
        assert all(isinstance(e, str) and e.strip() for e in entries), (
            f"{rule}: each residual is a non-empty description of the "
            "out-of-contract form"
        )
        assert len(entries) == len(set(entries)), f"{rule}: duplicate residual entries"


# --------------------------------------------------------------------------- #
# expected-findings manifests: a corpus case MAY ship expected-findings.json at
# its root — the exact findings (path + line) a maximally-precise checker emits
# for the rule under test, shaped by findings.schema.json. A harness may assert
# it exactly (hardening "flags something" to "flags the right line"); the loose
# per-case contract stays the floor for cases without one. These assertions
# hold every checked-in manifest to the shape and to the case it sits in.
# --------------------------------------------------------------------------- #
def test_expected_findings_manifests_are_coherent() -> None:
    findings_schema = json.loads((_SPEC / "findings.schema.json").read_text(encoding="utf-8"))
    manifests = sorted(_CORPUS.glob("*/*/*/expected-findings.json"))
    for manifest in manifests:
        case_dir = manifest.parent
        rule_id = f"{case_dir.parent.parent.name}/{case_dir.parent.name}"
        findings = json.loads(manifest.read_text(encoding="utf-8"))
        errors = _validate(findings, findings_schema, str(manifest.relative_to(_SPEC)))
        assert errors == [], "\n".join(errors)
        assert case_dir.name.startswith("violation-"), (
            f"{manifest}: only a violation-* case carries expected findings — a "
            "compliant case's contract is already exact (no findings)"
        )
        assert findings, f"{manifest}: a violation case's manifest must be non-empty"
        for finding in findings:
            assert finding["rule"] == rule_id, (
                f"{manifest}: finding attributed to {finding['rule']!r}, but the case "
                f"belongs to {rule_id!r} — a manifest states the rule under test only"
            )
            assert (case_dir / finding["path"]).is_file(), (
                f"{manifest}: finding path {finding['path']!r} does not exist in the case"
            )
            assert "line" in finding, (
                f"{manifest}: an expected finding pins the violating line — without it "
                "the manifest adds nothing over the loose contract"
            )
