"""The development-loop declaration's schema and fixtures hold together.

``workbench-declaration.schema.json`` is the normative vocabulary of the
``workbench.json`` an app checks in to say which parts of its development loop are
load-bearing, and it has two kinds of reader: the checker in the app's own gate, and
the development tools that drive the loop from the file as data. Neither owns the
words, which is why they live here: two readers that each wrote their own once
disagreed about which fields and which command slots existed.

It is a vocabulary with readers and no catalog rule. What the checker does with the
file against the compose file it names is the reference stack's own check of its own
development loop, not a rule every stack must implement; what every reader must agree
on is how the file itself reads, and that is what the fixtures fix. This suite is the
spec's half: the schema's own discipline, a small reference reader of the refusals the
schema's keyword subset cannot state (from the lists it names in ``$defs``), and every
fixture read as it says.
"""

from __future__ import annotations

import json
import re

import pytest
from terp_spec import spec_dir

from test_deployment_declaration import _field, _subschemas
from test_standard import _validate

_SPEC = spec_dir()
_SCHEMA = json.loads((_SPEC / "workbench-declaration.schema.json").read_text(encoding="utf-8"))
_FIXTURES = json.loads(
    (_SPEC / "workbench-declaration.fixtures.json").read_text(encoding="utf-8")
)
_DEPLOYMENT = json.loads(
    (_SPEC / "deployment-declaration.schema.json").read_text(encoding="utf-8")
)

_DECLARED = _SCHEMA["else"]
_OPTED_OUT = _SCHEMA["then"]
_ENTRY = _DECLARED["properties"]["services"]["items"]
_ENV = _DECLARED["properties"]["env"]
_COMMANDS = _DECLARED["properties"]["commands"]
_DEFS = {name: definition["enum"] for name, definition in _SCHEMA["$defs"].items()}

_KNOWN_ROLES = set(_DEFS["knownRoles"])
_ROLE_RESOLVED = tuple(_DEFS["roleResolvedFields"])
_SEAMS = set(_ENV["properties"])
_SLOTS = set(_COMMANDS["properties"])
_DEFAULT_COMPOSE = _DECLARED["properties"]["compose"]["properties"]["file"]["default"]

#: The root-level declaration vocabularies no catalog rule realises, by name. Normative
#: data joins the spec when something realises it: a rule, or - for a vocabulary whose
#: point is that two readers read one file the same way - the fixtures every reader
#: runs. Listed rather than inferred, so a schema cannot exempt itself.
_VOCABULARIES_READ_BY_FIXTURES = {"workbench-declaration.schema.json"}


def _errors(document: object) -> list[str]:
    return _validate(document, _SCHEMA, "$")


def _beyond_schema(document: object) -> list[tuple[str, str]]:
    """``(field, list)`` for every refusal of *document* a reader makes from ``$defs``.

    The refusals the schema describes and cannot state in its keyword subset: a field
    resolved by role under a role no reader resolves, a reserved variable name or
    prefix, and a deployment profile. (A commands block without a start is the fourth
    the schema describes, and its keyword subset does state that one.)
    """
    if not isinstance(document, dict) or document.get("unmanaged") is True:
        return []
    refused: list[tuple[str, str]] = []

    def name_refusal(field: str, name: object) -> None:
        if not isinstance(name, str):
            return
        if name in _DEFS["reservedEnvironmentNames"]:
            refused.append((field, "reservedEnvironmentNames"))
        elif name.startswith(tuple(_DEFS["reservedEnvironmentPrefixes"])):
            refused.append((field, "reservedEnvironmentPrefixes"))

    services = document.get("services")
    for index, entry in enumerate(services if isinstance(services, list) else []):
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        if isinstance(role, str) and role and role not in _KNOWN_ROLES:
            refused.extend(
                (f"$.services[{index}].{name}", "roleResolvedFields")
                for name in _ROLE_RESOLVED
                if name in entry
            )
        name_refusal(f"$.services[{index}].hostPortEnv", entry.get("hostPortEnv"))
    env = document.get("env")
    for label, name in (env.items() if isinstance(env, dict) else ()):
        name_refusal(f"$.env.{label}", name)
    compose = document.get("compose")
    file = compose.get("file") if isinstance(compose, dict) else None
    if isinstance(file, str) and any(marker in file for marker in _DEFS["deploymentProfileMarkers"]):
        refused.append(("$.compose.file", "deploymentProfileMarkers"))
    return refused


def _refused_fields(document: object) -> set[str]:
    return {_field(message) for message in _errors(document)} | {
        field for field, _ in _beyond_schema(document)
    }


def _reads(document: dict) -> dict:
    """What a reader resolves from a readable declaration, in the fixtures' shape."""
    if document.get("unmanaged") is True:
        return {"state": "unmanaged", "reason": document["reason"]}
    roles: dict[str, dict[str, str]] = {}
    for entry in document["services"]:
        role = entry.get("role")
        if role not in _KNOWN_ROLES:
            continue
        resolved = roles.setdefault(role, {})
        for name in ("service", *_ROLE_RESOLVED):
            if name in entry and name not in resolved:
                resolved[name] = entry[name]
    return {
        "state": "declared",
        "composeFile": document.get("compose", {}).get("file", _DEFAULT_COMPOSE),
        "roles": roles,
        "env": {label: name for label, name in document.get("env", {}).items() if label in _SEAMS},
        "commands": {
            slot: line.strip()
            for slot, line in document.get("commands", {}).items()
            if slot in _SLOTS
        },
    }


def _documents(expect: str) -> list[dict]:
    return [case for case in _FIXTURES["documents"] if case["expect"] == expect]


# --------------------------------------------------------------------------- #
# the schema's own discipline                                                  #
# --------------------------------------------------------------------------- #
_CONTROLS = ("\u0000", "\u0007", "\u000a", "\u001b", "\u007f", "\u0085", "\u009b")


def test_the_schema_is_a_draft_2020_12_schema_inside_the_validator_subset() -> None:
    assert _SCHEMA["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert _SCHEMA["$id"].endswith("/workbench-declaration.schema.json")
    # `_validate` reports an unknown schema KEYWORD, so validating a document of each
    # state through it proves the schema stays inside the subset the smallest reader
    # can honour.
    assert _errors(_documents("valid")[0]["document"]) == []
    assert _errors({"unmanaged": True, "reason": "Started from a make target."}) == []


def test_every_shape_and_every_field_says_what_it_means() -> None:
    shapes = [
        (path, schema)
        for path, schema in _subschemas(_SCHEMA)
        if schema.get("type") == "object" and path not in {"#", "#/if"}
    ]
    assert len(shapes) >= 6, "the walk found the schema's object shapes"
    for path, schema in shapes:
        assert schema.get("description", "").strip(), f"{path}: say what the shape is"
        for name, definition in schema.get("properties", {}).items():
            assert definition.get("description", "").strip(), (
                f"{path}/properties/{name}: say what the field means"
            )


def test_every_string_is_capped_and_refuses_control_characters() -> None:
    """The file is input an agent writes and a tool acts on: every string a reader
    keeps has a length cap and refuses control characters."""
    strings = [
        (path, schema) for path, schema in _subschemas(_SCHEMA) if schema.get("type") == "string"
    ]
    assert len(strings) >= 10
    for path, schema in strings:
        assert isinstance(schema.get("maxLength"), int), f"{path}: a string needs a length cap"
        pattern = schema.get("pattern")
        assert pattern, f"{path}: a string needs a pattern that refuses control characters"
        for control in _CONTROLS:
            for probe in (f"A{control}", f"{control}A", f"/a{control}", f"make dev{control}"):
                assert re.search(pattern, probe) is None, (
                    f"{path}: {probe!r} passes {pattern!r} - a control character got through"
                )


def test_every_pattern_ends_at_the_end_of_the_input() -> None:
    """``$`` also matches before a final newline in Python; ``(?![\\s\\S])`` is the end
    of the input in Python and ECMA-262 alike."""
    patterns = {
        schema["pattern"] for _, schema in _subschemas(_SCHEMA) if "pattern" in schema
    } | {
        key for _, schema in _subschemas(_SCHEMA) for key in schema.get("patternProperties", {})
    }
    assert patterns
    for pattern in sorted(patterns):
        assert pattern.startswith("^") and pattern.endswith("(?![\\s\\S])"), pattern
    name = _ENTRY["properties"]["hostPortEnv"]["pattern"]
    assert re.search(name, "WEB_PORT") and not re.search(name, "WEB_PORT\n")


def test_the_named_lists_are_sorted_described_and_coherent() -> None:
    for name, definition in _SCHEMA["$defs"].items():
        values = definition["enum"]
        assert values and values == sorted(values) and len(values) == len(set(values)), name
        assert definition.get("description", "").strip(), f"$defs/{name}: say what it lists"
    role = _ENTRY["properties"]["role"]["pattern"]
    assert all(re.search(role, known) for known in _KNOWN_ROLES)
    assert "enum" not in _ENTRY["properties"]["role"], "an unknown role is information"
    assert set(_ROLE_RESOLVED) <= set(_ENTRY["properties"]), "a field resolved by role is an entry field"
    assert _KNOWN_ROLES <= set(_DEPLOYMENT["$defs"]["knownRoles"]["enum"]), (
        "a role word means one thing in both declarations"
    )
    name = _ENTRY["properties"]["hostPortEnv"]["pattern"]
    for reserved in _DEFS["reservedEnvironmentNames"]:
        assert re.search(name, reserved), f"{reserved}: a reserved name is one a file could write"
    for prefix in _DEFS["reservedEnvironmentPrefixes"]:
        assert prefix.endswith("_") and re.search(name, f"{prefix}X"), prefix
    for marker in _DEFS["deploymentProfileMarkers"]:
        assert re.search(_DECLARED["properties"]["compose"]["properties"]["file"]["pattern"], f"a{marker}yml")


def test_every_variable_a_reader_sets_has_one_shape() -> None:
    """hostPortEnv and every env seam are names a reader puts into an environment."""
    shapes = [_ENTRY["properties"]["hostPortEnv"], *_ENV["properties"].values()]
    shapes += list(_ENV["patternProperties"].values())
    described = {
        json.dumps({k: v for k, v in shape.items() if k != "description"}, sort_keys=True)
        for shape in shapes
    }
    assert len(described) == 1


def test_any_command_means_a_start_and_the_slots_are_the_blocks_own() -> None:
    required = _COMMANDS["dependentRequired"]
    assert set(required) == _SLOTS - {"start"}
    assert all(needed == ["start"] for needed in required.values())
    lines = {
        json.dumps({k: v for k, v in schema.items() if k != "description"}, sort_keys=True)
        for schema in _COMMANDS["properties"].values()
    }
    assert len(lines) == 1, "every slot holds one command line, held the same way"
    assert {"containerLogs", "recreate"} <= _SLOTS, "the slots a workbench runs are the vocabulary's"


def test_the_three_states_are_exactly_three() -> None:
    assert set(_DECLARED["required"]) == {"schemaVersion", "services"}
    assert set(_OPTED_OUT["required"]) == {"unmanaged", "reason"}
    assert _errors({"schemaVersion": 1}), "a declaration with nothing in it is in no state"
    assert _errors({"unmanaged": True}), "an escape without a reason is a hole"
    assert _errors({"unmanaged": True, "reason": "Started by hand.", "schemaVersion": 1}) == []
    assert _DECLARED["properties"]["schemaVersion"]["const"] == _OPTED_OUT["properties"]["schemaVersion"]["const"] == 1


def test_every_default_validates_against_its_own_field() -> None:
    defaults = [(path, schema) for path, schema in _subschemas(_SCHEMA) if "default" in schema]
    assert len(defaults) >= 4
    for path, schema in defaults:
        assert _validate(schema["default"], schema, path) == [], path


# --------------------------------------------------------------------------- #
# the fixtures                                                                 #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("case", _documents("valid"), ids=lambda case: case["id"])
def test_a_valid_fixture_reads_as_it_says(case: dict) -> None:
    assert _refused_fields(case["document"]) == set(), case["about"]
    assert _reads(case["document"]) == case["reads"], case["about"]


@pytest.mark.parametrize("case", _documents("invalid"), ids=lambda case: case["id"])
def test_an_invalid_fixture_is_refused_at_its_field(case: dict) -> None:
    document = case["document"]
    assert case["field"] in _refused_fields(document), (
        f"{case['id']} ({case['about']}): refused at {sorted(_refused_fields(document))}, "
        f"the fixture says {case['field']}"
    )
    assert case["allowed"].strip(), f"{case['id']}: say what the field allows"
    schema_alone = _errors(document)
    if case.get("beyondSchema"):
        assert schema_alone == [], f"{case['id']}: marked beyond the schema, and the schema refuses it"
    else:
        assert schema_alone, f"{case['id']}: the schema alone must refuse it"


@pytest.mark.parametrize("case", _FIXTURES["texts"], ids=lambda case: case["id"])
def test_a_text_fixture_is_not_one_declaration(case: dict) -> None:
    try:
        document = json.loads(case["text"])
    except json.JSONDecodeError:
        return
    assert not isinstance(document, dict), case["id"]


def test_the_fixtures_are_well_formed_and_cover_the_vocabulary() -> None:
    ids = [case["id"] for case in _FIXTURES["documents"]] + [case["id"] for case in _FIXTURES["texts"]]
    assert len(ids) == len(set(ids))
    for case in _FIXTURES["documents"]:
        keys = {"id", "expect", "about", "document"}
        keys |= {"reads"} if case["expect"] == "valid" else {"field", "allowed", "beyondSchema"}
        assert set(case) <= keys, case["id"]
    assert len(_documents("invalid")) >= 30 and len(_documents("valid")) >= 10
    fields = {case["field"] for case in _documents("invalid")}
    touched = " ".join(sorted(fields))
    for name in ("schemaVersion", "services", "service", "role", *_ROLE_RESOLVED, "compose",
                 "compose.file", "env", "commands", "reason", "unmanaged", *_SEAMS):
        assert name in touched, f"no invalid fixture is about {name}"
    lists = {
        rule
        for case in _documents("invalid")
        if case.get("beyondSchema")
        for field, rule in _beyond_schema(case["document"])
        if field == case["field"]
    }
    assert lists == set(_DEFS) - {"knownRoles"}, "every list a reader refuses from is exercised"
    read_slots = set().union(*(case["reads"].get("commands", {}) for case in _documents("valid")))
    assert read_slots == _SLOTS, "every slot is read by some valid fixture"
    read_roles = set().union(*(case["reads"].get("roles", {}) for case in _documents("valid")))
    assert {"web", "api"} <= read_roles
    assert any(case["reads"]["state"] == "unmanaged" for case in _documents("valid"))


def test_a_vocabulary_no_rule_realises_is_claimed_by_its_fixtures() -> None:
    """Normative data joins the spec when something realises it, never before."""
    cited = " ".join(
        f"{entry['intent']} {entry.get('reference', '')}"
        for surface in ("backend", "frontend")
        for entry in (
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted((_SPEC / "catalog" / surface).glob("*.json"))
        )
    )
    for schema in sorted(_SPEC.glob("*-declaration.schema.json")):
        if schema.name in _VOCABULARIES_READ_BY_FIXTURES:
            assert schema.name not in cited, f"{schema.name} is listed as rule-free and a rule cites it"
            fixtures = schema.with_name(schema.name.replace(".schema.json", ".fixtures.json"))
            assert fixtures.is_file(), f"{schema.name}: a vocabulary read by fixtures ships them"
        else:
            assert schema.name in cited, f"no catalog entry cites {schema.name}"
