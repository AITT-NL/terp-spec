"""The resolved deployment's schema and fixtures hold together.

``resolved-deployment.schema.json`` is the closed document a release tool writes into the
signed release manifest, at ``outputs.deployment``, and the document an executor runs
instead of reading the app's Compose files. It is written for three readers: a release
tool, which refuses before it signs; an executor, which refuses again when it reads; and a
control plane, which shows it to the person who approves a deploy. They agree by running
the same fixtures. No program reads it yet.

The document is read against the release that carries it: the units its deployment
declaration declares, the images the release built, and the datastore table it records.
Each fixture names the release it reads against, from the file's ``releases``.
This suite is the spec's half: the schema's own discipline, a small reference reader of
the refusals the schema's keyword subset cannot state, and every fixture read as it says.
"""

from __future__ import annotations

import copy
import json
import re

import pytest
from terp_spec import spec_dir

from schema_subset import _validate
from test_deployment_declaration import _field, _subschemas

_SPEC = spec_dir()
_SCHEMA = json.loads((_SPEC / "resolved-deployment.schema.json").read_text(encoding="utf-8"))
_FIXTURES = json.loads((_SPEC / "resolved-deployment.fixtures.json").read_text(encoding="utf-8"))
_DECLARATION = json.loads(
    (_SPEC / "deployment-declaration.schema.json").read_text(encoding="utf-8")
)

_SERVICE = _SCHEMA["properties"]["services"]["items"]
_FIELDS = _SERVICE["properties"]
_VARIABLE = _FIELDS["environment"]["items"]
_MOUNT = _FIELDS["mounts"]["items"]
_PROBE = _FIELDS["healthcheck"]
_AFTER = _FIELDS["after"]["items"]
_DEFS = {name: definition["enum"] for name, definition in _SCHEMA["$defs"].items()}
_UNIT = _DECLARATION["else"]["properties"]["units"]["items"]["properties"]

#: What the reference reader refuses beyond the schema. A rule named after a list in
#: ``$defs`` is read from that list.
_RULES = {
    "after-completed",
    "after-cycle",
    "after-healthy",
    "after-order",
    "after-unit",
    "built-image",
    "datastore-image",
    "declaration-order",
    "declared-unit",
    "environment-order",
    "migration-command",
    "migration-database",
    "migration-service",
    "missing-unit",
    "mount-order",
    "refusedEnvironmentNames",
    "refusedEnvironmentPrefixes",
    "unique-service-ids",
    "unit-datastore",
    "unit-role",
    "volume-listed",
    "volume-mounted",
    "volume-order",
}

#: Keys of a Compose service that an executor owns, or that a release tool resolves
#: away before it signs. None of them is a field of a resolved service.
_NEVER_A_FIELD = {
    "build", "cap_add", "cap_drop", "cgroup_parent", "configs", "container_name", "deploy",
    "depends_on", "devices", "dns", "entrypoint", "env_file", "extends", "external_links",
    "extra_hosts", "hostname", "ipc", "labels", "links", "logging", "network_mode", "networks",
    "pid", "platform", "ports", "privileged", "profiles", "pull_policy", "resources", "restart",
    "runtime", "secrets", "security_opt", "stop_grace_period", "stop_signal", "sysctls", "tmpfs",
    "ulimits", "user", "userns_mode", "volumes", "volumes_from", "working_dir",
}


def _errors(document: object) -> list[str]:
    return _validate(document, _SCHEMA, "$")


def _items(value: object) -> list:
    return value if isinstance(value, list) else []


def _text(value: object) -> str | None:
    """*value* when it is a string: what a reader may use as a name or a key."""
    return value if isinstance(value, str) else None


def _beyond_schema(document: object, release: dict) -> list[tuple[str, str]]:
    """``(field, rule)`` for every refusal of *document* a reader makes beyond the schema.

    What the keyword subset cannot state: that ids, names, targets and units are unique
    and in their order, that every reference resolves, and that the document agrees with
    the release that carries it. A reader applies these to a document of any shape, so
    each one looks only at the members it can read.
    """
    if not isinstance(document, dict):
        return []
    refused: list[tuple[str, str]] = []
    services = [
        (index, service)
        for index, service in enumerate(_items(document.get("services")))
        if isinstance(service, dict)
    ]
    units = {unit["id"]: unit for unit in release["units"]}
    order = [unit["id"] for unit in release["units"]]
    tables = {(entry["kind"], entry["version"]): entry["image"] for entry in release["datastores"]}
    by_id: dict[str, dict] = {}
    for index, service in services:
        ident = service.get("id")
        if not isinstance(ident, str):
            continue
        if ident in by_id:
            refused.append((f"$.services[{index}].id", "unique-service-ids"))
        elif ident not in units:
            refused.append((f"$.services[{index}].id", "declared-unit"))
        by_id.setdefault(ident, service)
    if any(ident not in by_id for ident in order):
        refused.append(("$.services", "missing-unit"))
    declared = [
        (index, ident)
        for index, service in services
        if (ident := _text(service.get("id"))) is not None and ident in units
    ]
    for (_, before), (index, ident) in zip(declared, declared[1:]):
        if order.index(ident) <= order.index(before):
            refused.append((f"$.services[{index}].id", "declaration-order"))
            break

    volumes = [name for name in _items(document.get("volumes")) if isinstance(name, str)]
    for position in range(1, len(volumes)):
        if volumes[position] <= volumes[position - 1]:
            refused.append((f"$.volumes[{position}]", "volume-order"))
    mounted: set[str] = set()

    for index, service in services:
        at = f"$.services[{index}]"
        unit = units.get(_text(service.get("id")))
        if unit is not None:
            if "role" in service and service["role"] != unit["role"]:
                refused.append((f"{at}.role", "unit-role"))
            wanted = (
                {"kind": unit["kind"], "version": unit["version"]} if "kind" in unit else None
            )
            if service.get("datastore") != wanted:
                refused.append((f"{at}.datastore", "unit-datastore"))
        image = service.get("image")
        store = service.get("datastore")
        if isinstance(image, str):
            if isinstance(store, dict):
                key = (_text(store.get("kind")), _text(store.get("version")))
                if None not in key and tables.get(key) != image:
                    refused.append((f"{at}.image", "datastore-image"))
            elif image not in release["images"]:
                refused.append((f"{at}.image", "built-image"))

        names: list[str] = []
        for position, entry in enumerate(_items(service.get("environment"))):
            name = entry.get("name") if isinstance(entry, dict) else None
            if not isinstance(name, str):
                continue
            field = f"{at}.environment[{position}].name"
            if names and name <= names[-1]:
                refused.append((field, "environment-order"))
            names.append(name)
            if name in _DEFS["refusedEnvironmentNames"]:
                refused.append((field, "refusedEnvironmentNames"))
            elif name.startswith(tuple(_DEFS["refusedEnvironmentPrefixes"])):
                refused.append((field, "refusedEnvironmentPrefixes"))

        targets: list[str] = []
        for position, mount in enumerate(_items(service.get("mounts"))):
            if not isinstance(mount, dict):
                continue
            target = mount.get("target")
            if isinstance(target, str):
                if targets and target <= targets[-1]:
                    refused.append((f"{at}.mounts[{position}].target", "mount-order"))
                targets.append(target)
            source = mount.get("source")
            if mount.get("type") == "volume" and isinstance(source, str):
                mounted.add(source)
                if source not in volumes:
                    refused.append((f"{at}.mounts[{position}].source", "volume-listed"))

        after: list[str] = []
        for position, entry in enumerate(_items(service.get("after"))):
            if not isinstance(entry, dict) or not isinstance(entry.get("unit"), str):
                continue
            field = f"{at}.after[{position}]"
            other = entry["unit"]
            if after and other <= after[-1]:
                refused.append((f"{field}.unit", "after-order"))
            after.append(other)
            if other == service.get("id") or other not in by_id:
                refused.append((f"{field}.unit", "after-unit"))
                continue
            target = by_id[other]
            if entry.get("condition") == "completed" and target.get("lifecycle") != "one-shot":
                refused.append((f"{field}.condition", "after-completed"))
            if entry.get("condition") == "healthy" and "healthcheck" not in target:
                refused.append((f"{field}.condition", "after-healthy"))

    for position, name in enumerate(volumes):
        if name not in mounted:
            refused.append((f"$.volumes[{position}]", "volume-mounted"))

    refused.extend(_cycles(services, by_id))

    migration = document.get("migration")
    if isinstance(migration, str):
        service = by_id.get(migration)
        if service is None or service.get("lifecycle") != "one-shot":
            refused.append(("$.migration", "migration-service"))
        else:
            index = next(i for i, candidate in services if candidate is service)
            if "command" in service:
                refused.append((f"$.services[{index}].command", "migration-command"))
            for position, entry in enumerate(_items(service.get("environment"))):
                if isinstance(entry, dict) and entry.get("source") == "database":
                    refused.append(
                        (f"$.services[{index}].environment[{position}].source", "migration-database")
                    )
    return refused


def _cycles(services: list[tuple[int, dict]], by_id: dict[str, dict]) -> list[tuple[str, str]]:
    """Each ``after`` entry that closes a loop of two or more services."""

    def waits_for(service: dict) -> list[str]:
        return [
            entry["unit"]
            for entry in _items(service.get("after"))
            if isinstance(entry, dict) and _text(entry.get("unit")) in by_id
        ]

    def reaches(start: str, goal: str) -> bool:
        stack, visited = [start], set()
        while stack:
            current = stack.pop()
            if current == goal:
                return True
            if current in visited:
                continue
            visited.add(current)
            stack.extend(waits_for(by_id[current]))
        return False

    refused = []
    for index, service in services:
        ident = _text(service.get("id"))
        if ident is None or by_id.get(ident) is not service:
            continue
        for position, entry in enumerate(_items(service.get("after"))):
            other = _text(entry.get("unit")) if isinstance(entry, dict) else None
            if other in by_id and other != ident and reaches(other, ident):
                refused.append((f"$.services[{index}].after[{position}].unit", "after-cycle"))
    return refused


def _release(case: dict) -> dict:
    return _FIXTURES["releases"][case["release"]]


def _refused_fields(case: dict) -> set[str]:
    document = case["document"]
    return {_field(message) for message in _errors(document)} | {
        field for field, _ in _beyond_schema(document, _release(case))
    }


def _documents(expect: str) -> list[dict]:
    return [case for case in _FIXTURES["documents"] if case["expect"] == expect]


# --------------------------------------------------------------------------- #
# the schema's own discipline                                                  #
# --------------------------------------------------------------------------- #
_CONTROLS = ("\u0000", "\u0007", "\u000a", "\u001b", "\u007f", "\u0085", "\u009b")


def test_the_schema_is_a_draft_2020_12_schema_inside_the_validator_subset() -> None:
    assert _SCHEMA["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert _SCHEMA["$id"] == "https://terp.dev/spec/resolved-deployment.schema.json"
    # `_validate` reports an unknown schema KEYWORD, so validating a document through it
    # proves the schema stays inside the subset the smallest reader can honour.
    assert _errors(_documents("valid")[0]["document"]) == []


def test_every_shape_and_every_field_says_what_it_means() -> None:
    shapes = [(path, schema) for path, schema in _subschemas(_SCHEMA) if schema.get("type") == "object"]
    assert len(shapes) >= 8, "the walk found the schema's object shapes"
    for path, schema in shapes:
        assert schema.get("description", "").strip(), f"{path}: say what the shape is"
        assert schema.get("additionalProperties") is False, f"{path}: a reader refuses a field it does not know"
        for name, definition in schema.get("properties", {}).items():
            assert definition.get("description", "").strip(), (
                f"{path}/properties/{name}: say what the field means"
            )


def test_every_string_is_capped_and_refuses_control_characters() -> None:
    strings = [(path, schema) for path, schema in _subschemas(_SCHEMA) if schema.get("type") == "string"]
    assert len(strings) >= 12
    for path, schema in strings:
        assert isinstance(schema.get("maxLength"), int), f"{path}: a string needs a length cap"
        pattern = schema.get("pattern")
        assert pattern, f"{path}: a string needs a pattern that refuses control characters"
        for control in _CONTROLS:
            for probe in (f"A{control}", f"{control}A", f"/a{control}", f"terp serve{control}"):
                assert re.search(pattern, probe) is None, (
                    f"{path}: {probe!r} passes {pattern!r} - a control character got through"
                )


def test_every_pattern_ends_at_the_end_of_the_input() -> None:
    """``$`` also matches before a final newline in Python; ``(?![\\s\\S])`` is the end
    of the input in Python and ECMA-262 alike."""
    patterns = {schema["pattern"] for _, schema in _subschemas(_SCHEMA) if "pattern" in schema}
    assert patterns
    for pattern in sorted(patterns):
        assert pattern.startswith("^") and pattern.endswith("(?![\\s\\S])"), pattern


def test_every_array_and_every_integer_is_bounded() -> None:
    """The canonical form refuses an integer past 2^53 - 1, and a reader caps what it holds."""
    arrays = [(path, schema) for path, schema in _subschemas(_SCHEMA) if schema.get("type") == "array"]
    assert arrays
    for path, schema in arrays:
        assert isinstance(schema.get("maxItems"), int), f"{path}: an array needs a cap"
    integers = [(path, schema) for path, schema in _subschemas(_SCHEMA) if schema.get("type") == "integer"]
    assert len(integers) >= 5
    for path, schema in integers:
        if "const" in schema:
            continue
        assert isinstance(schema.get("minimum"), int) and isinstance(schema.get("maximum"), int), path
        assert -(2**53 - 1) <= schema["minimum"] <= schema["maximum"] <= 2**53 - 1, path
    assert not [path for path, schema in _subschemas(_SCHEMA) if schema.get("type") == "number"], (
        "the canonical form has no floats: every number is an integer"
    )


def test_nothing_is_defaulted_and_nothing_is_null() -> None:
    """The release tool writes every field that applies, and a field that does not apply is
    absent: a default would let two documents mean one thing, and the subset has no null."""
    assert not [path for path, schema in _subschemas(_SCHEMA) if "default" in schema]
    assert not [path for path, schema in _subschemas(_SCHEMA) if schema.get("type") == "null"]
    assert _errors({**_documents("valid")[0]["document"], "migration": None})


def test_a_word_means_what_it_means_in_the_declaration() -> None:
    """A unit id, a role, a datastore and a variable name are the deployment declaration's."""
    same = {
        "id": _UNIT["id"],
        "role": _UNIT["role"],
        "healthPath": _UNIT["healthPath"],
    }
    mine = {
        "id": _FIELDS["id"],
        "role": _FIELDS["role"],
        "healthPath": _FIELDS["serves"]["properties"]["healthPath"],
    }
    for name, theirs in same.items():
        for keyword in ("pattern", "maxLength"):
            assert mine[name][keyword] == theirs[keyword], f"{name}.{keyword}"
    store = _FIELDS["datastore"]["properties"]
    for name in ("kind", "version"):
        assert store[name]["pattern"] == _UNIT[name]["pattern"], name
        assert store[name]["maxLength"] == _UNIT[name]["maxLength"], name
    assert _VARIABLE["properties"]["name"]["pattern"] == _UNIT["env"]["items"]["pattern"]
    for reference in (_AFTER["properties"]["unit"], _SCHEMA["properties"]["migration"]):
        assert reference["pattern"] == _UNIT["id"]["pattern"]
    assert _SCHEMA["properties"]["services"]["maxItems"] == (
        _DECLARATION["else"]["properties"]["units"]["maxItems"]
    ), "one service per declared unit"


def test_the_named_lists_are_sorted_described_and_coherent() -> None:
    assert set(_DEFS) == {"refusedEnvironmentNames", "refusedEnvironmentPrefixes"}
    for name, definition in _SCHEMA["$defs"].items():
        values = definition["enum"]
        assert values and values == sorted(values) and len(values) == len(set(values)), name
        assert definition.get("description", "").strip(), f"$defs/{name}: say what it lists"
    name = _VARIABLE["properties"]["name"]["pattern"]
    for refused in _DEFS["refusedEnvironmentNames"]:
        assert re.search(name, refused), f"{refused}: a refused name is one a document could write"
        assert not refused.startswith(tuple(_DEFS["refusedEnvironmentPrefixes"])), (
            f"{refused}: a prefix already refuses it"
        )
    for prefix in _DEFS["refusedEnvironmentPrefixes"]:
        assert re.search(name, f"{prefix}X"), prefix
    for executor_owned in ("PATH", "HOME", "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"):
        assert executor_owned in _DEFS["refusedEnvironmentNames"], executor_owned
    for prefix in ("PYTHONPATH", "LD_PRELOAD", "SSL_CERT_FILE", "DOCKER_HOST", "COMPOSE_FILE"):
        assert prefix.startswith(tuple(_DEFS["refusedEnvironmentPrefixes"])), prefix


def test_each_variant_allows_exactly_its_own_members() -> None:
    def variable(entry: dict) -> list[str]:
        return _validate(entry, _VARIABLE, "$")

    assert variable({"name": "A", "source": "value", "value": ""}) == []
    assert variable({"name": "A", "source": "config", "key": "A"}) == []
    assert variable({"name": "A", "source": "secret", "key": "A"}) == []
    assert variable({"name": "A", "source": "database", "key": "runtime"}) == []
    assert variable({"name": "A", "source": "value", "value": "x", "key": "A"})
    assert variable({"name": "A", "source": "config", "key": "A", "value": "x"})
    assert variable({"name": "A", "source": "database", "key": "OWNER"})
    assert variable({"name": "A", "source": "secret", "key": "runtime"})

    def mount(entry: dict) -> list[str]:
        return _validate(entry, _MOUNT, "$")

    assert mount({"type": "volume", "target": "/data", "source": "data", "readOnly": False}) == []
    assert mount({"type": "anonymous", "target": "/data"}) == []
    assert mount({"type": "volume", "target": "/data", "source": "data"})
    assert mount({"type": "anonymous", "target": "/data", "readOnly": True})
    assert mount({"type": "bind", "target": "/data"})

    timing = {"intervalSeconds": 1, "timeoutSeconds": 1, "retries": 1, "startPeriodSeconds": 0}

    def probe(entry: dict) -> list[str]:
        return _validate({**entry, **timing}, _PROBE, "$")

    assert probe({"form": "exec", "argv": ["true"]}) == []
    assert probe({"form": "shell", "script": "true"}) == []
    assert probe({"form": "exec", "script": "true"})
    assert probe({"form": "shell", "argv": ["true"], "script": "true"})


def test_what_an_executor_owns_has_no_field() -> None:
    assert not _NEVER_A_FIELD & set(_FIELDS), sorted(_NEVER_A_FIELD & set(_FIELDS))
    assert set(_SCHEMA["properties"]) == {"schemaVersion", "services", "volumes", "migration"}


def test_the_mount_target_keeps_code_out_of_volumes() -> None:
    target = _MOUNT["properties"]["target"]["pattern"]
    for allowed in ("/srv/var/files", "/var/lib/postgresql/data", "/srvx", "/data/.cache"):
        assert re.search(target, allowed), allowed
    for refused in ("/srv", "/srv/app", "/srv/var", "/srv/var/files/x", "/", "relative",
                    "/data/", "//data", "/data/./x", "/data/../srv/app"):
        assert re.search(target, refused) is None, refused


# --------------------------------------------------------------------------- #
# the fixtures                                                                 #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("case", _documents("valid"), ids=lambda case: case["id"])
def test_a_valid_fixture_reads_as_it_says(case: dict) -> None:
    assert _errors(case["document"]) == [], case["about"]
    assert _beyond_schema(case["document"], _release(case)) == [], case["about"]


@pytest.mark.parametrize("case", _documents("invalid"), ids=lambda case: case["id"])
def test_an_invalid_fixture_is_refused_at_its_field(case: dict) -> None:
    refused = _refused_fields(case)
    assert case["field"] in refused, (
        f"{case['id']} ({case['about']}): refused at {sorted(refused)}, "
        f"the fixture says {case['field']}"
    )
    assert case["allowed"].strip(), f"{case['id']}: say what the field allows"
    schema_alone = _errors(case["document"])
    if case.get("beyondSchema"):
        assert schema_alone == [], f"{case['id']}: marked beyond the schema, and the schema refuses it"
    else:
        assert schema_alone, f"{case['id']}: the schema alone must refuse it"


#: Values of the wrong type, each in a document no reader validated first.
_MISTYPED = {
    "an id that is a list": lambda d: d["services"][0].update(id=["db"]),
    "an id that is a number": lambda d: d["services"][2].update(id=7),
    "a datastore kind that is a list": lambda d: d["services"][0]["datastore"].update(kind=["postgres"]),
    "a datastore that is a list": lambda d: d["services"][0].update(datastore=["postgres", "17"]),
    "an after unit that is a list": lambda d: d["services"][2]["after"][0].update(unit=["db"]),
    "an after unit that is an object": lambda d: d["services"][2]["after"][0].update(unit={"id": "db"}),
    "an after entry that is text": lambda d: d["services"][2]["after"].append("db"),
    "a variable that is a list": lambda d: d["services"][2]["environment"].append(["X"]),
    "a variable name that is a list": lambda d: d["services"][2]["environment"][0].update(name=["X"]),
    "a mount target that is a list": lambda d: d["services"][2]["mounts"][0].update(target=["/srv/var/files"]),
    "a mount source that is a list": lambda d: d["services"][2]["mounts"][0].update(source=["files"]),
    "a volume that is a list": lambda d: d.update(volumes=[["db-data"], "files"]),
    "a migration that is a list": lambda d: d.update(migration=["migrate"]),
    "a service that is text": lambda d: d["services"].append("web"),
    "services that are an object": lambda d: d.update(services={"api": {}}),
}


@pytest.mark.parametrize("name", sorted(_MISTYPED))
def test_a_mistyped_value_is_refused_and_never_raises(name: str) -> None:
    """A reader meets documents before anything validated them: the wrong type is a refusal."""
    case = copy.deepcopy(_documents("valid")[0])
    _MISTYPED[name](case["document"])
    assert _refused_fields(case), f"{name}: nothing refused it"


def test_the_release_facts_are_well_formed() -> None:
    image = _FIELDS["image"]["pattern"]
    named = {case["release"] for case in _FIXTURES["documents"]}
    assert named == set(_FIXTURES["releases"]), "every case names a release, and every release is read"
    for release in _FIXTURES["releases"].values():
        assert set(release) == {"units", "images", "datastores"}
        ids = [unit["id"] for unit in release["units"]]
        assert ids and len(ids) == len(set(ids))
        for unit in release["units"]:
            assert set(unit) in ({"id", "role"}, {"id", "role", "kind", "version"}), unit
            assert re.search(_UNIT["id"]["pattern"], unit["id"])
        for reference in release["images"]:
            assert re.search(image, reference), reference
        for entry in release["datastores"]:
            assert set(entry) == {"kind", "version", "image"} and re.search(image, entry["image"])


def test_the_fixtures_are_well_formed_and_cover_the_vocabulary() -> None:
    assert set(_FIXTURES) == {"_comment", "releases", "documents"}
    ids = [case["id"] for case in _FIXTURES["documents"]]
    assert len(ids) == len(set(ids))
    for case in _FIXTURES["documents"]:
        required = {"id", "expect", "about", "release", "document"}
        required |= set() if case["expect"] == "valid" else {"field", "allowed"}
        assert required <= set(case) <= required | {"beyondSchema"}, case["id"]
        assert case["expect"] in ("valid", "invalid"), case["id"]
    assert len(_documents("invalid")) >= 40 and len(_documents("valid")) >= 5

    exercised = {
        rule
        for case in _documents("invalid")
        if case.get("beyondSchema")
        for field, rule in _beyond_schema(case["document"], _release(case))
        if field == case["field"]
    }
    assert exercised == _RULES, f"rules no fixture exercises: {sorted(_RULES - exercised)}"
    assert set(_DEFS) <= exercised, "every list a reader refuses from is exercised"

    services = [service for case in _documents("valid") for service in case["document"]["services"]]
    variables = [entry for service in services for entry in service["environment"]]
    mounts = [mount for service in services for mount in service["mounts"]]
    after = [entry for service in services for entry in service["after"]]
    probes = [service["healthcheck"] for service in services if "healthcheck" in service]
    assert {service["lifecycle"] for service in services} == set(_FIELDS["lifecycle"]["enum"])
    assert {entry["source"] for entry in variables} == set(_VARIABLE["properties"]["source"]["enum"])
    assert {mount["type"] for mount in mounts} == set(_MOUNT["properties"]["type"]["enum"])
    assert {probe["form"] for probe in probes} == set(_PROBE["properties"]["form"]["enum"])
    assert {entry["condition"] for entry in after} == set(_AFTER["properties"]["condition"]["enum"])
    assert any("command" in service for service in services)
    assert any("datastore" in service for service in services)
    assert any("serves" in service for service in services)
    assert any(mount.get("readOnly") is True for mount in mounts)
    assert any("migration" in case["document"] for case in _documents("valid"))
    assert any("migration" not in case["document"] for case in _documents("valid"))
