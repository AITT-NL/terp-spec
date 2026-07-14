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
    @terp/spec are two thin manifests over one data directory, so all three
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
# the escape-hatch spelling is held to the rule id: the normative contract says
# the marker NAMES THE RULE, so a typo'd opt_out would document a marker no
# checker honours — an unenforceable escape hatch.
# --------------------------------------------------------------------------- #
def test_opt_out_markers_name_their_rule() -> None:
    for name, entry in _entries("backend").items():
        expected = f"# arch-allow-{name.replace('_', '-')}: <reason>"
        assert entry["opt_out"] == expected, (
            f"backend/{name}: opt_out {entry['opt_out']!r} must spell the reference "
            f"marker for this rule exactly ({expected!r}) — a typo'd marker is an "
            "unenforceable opt-out"
        )
    for name, entry in _entries("frontend").items():
        # Suppression happens at the ESLint layer, so the marker names the rule
        # violations are REPORTED AS (several catalog rules share a core rule id),
        # with the terp/ plugin prefix dropped from the marker spelling.
        reported = entry["enforcement"][0].get("reported_as", f"terp/{name}")
        expected = f"// terp-allow-{reported.removeprefix('terp/')}: <reason>"
        assert entry["opt_out"] == expected, (
            f"frontend/{name}: opt_out {entry['opt_out']!r} must spell the marker for "
            f"the rule id violations surface as ({expected!r}) — a typo'd marker is an "
            "unenforceable opt-out"
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
