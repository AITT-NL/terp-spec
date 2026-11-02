"""The deployment declaration's schema, corpus and fixtures hold together.

``deployment-declaration.schema.json`` is the normative vocabulary of the file an app
checks in to declare its deployable units, and two readers are held to it before
anything else reads it: the reference stack's check, and the tools that drive a deploy
from the file as data. This suite is the spec's own half. It holds the schema to the
discipline its description promises (every object closed, every string capped and free
of control characters, the named key lists coherent), exercises every field valid and
invalid, applies the stated defaults, and reads the corpus with a small reference reader
of the file-local refusals - so a violation case that the schema and those refusals do
not refuse, or a compliant case they do, fails here rather than in a reader's gate.

The reader below is deliberately partial. It reads the declaration and the files beside
it as JSON only; the rules that need the deployment profile (YAML) or the composed app
are the reference implementation's to prove, against the same corpus.
"""

from __future__ import annotations

import copy
import json
import os
import pathlib
import re

import pytest
from terp_spec import spec_dir

from test_standard import _validate

_SPEC = spec_dir()
_SCHEMA = json.loads((_SPEC / "deployment-declaration.schema.json").read_text(encoding="utf-8"))
_FIXTURES = json.loads(
    (_SPEC / "deployment-declaration.fixtures.json").read_text(encoding="utf-8")
)
_CORPUS = _SPEC / "corpus" / "backend"
_READABLE = "backend/deployment_declaration_is_readable"
_TRUTH = "backend/deployment_declaration_tells_the_truth"
_RENDER = "backend/deployment_generated_files_match_their_render"
_RULES = (_READABLE, _TRUTH, _RENDER)

_MANAGED = _SCHEMA["else"]
_UNMANAGED = _SCHEMA["then"]
_UNIT = _MANAGED["properties"]["units"]["items"]
_VOLUME = _MANAGED["properties"]["volumes"]["items"]
_GENERATOR = _MANAGED["properties"]["generator"]
_POLICY_KEYS = set(_SCHEMA["$defs"]["deployPolicyKeys"]["enum"])
_POLICY_MESSAGE = (
    "{key} is deploy policy: it belongs to the deploying tool's environment policy, "
    "not to this file"
)

#: The seed a fresh app is rendered with: exactly the reference template's production
#: profile (db, migrate, api, web).
_SEED = {
    "schemaVersion": 1,
    "build": "own",
    "compose": {"file": "docker-compose.prod.yml"},
    "units": [
        {"id": "db", "role": "database", "kind": "postgres", "version": "17",
         "stateful": True, "backup": {"every": "P1D", "keep": "P30D"}},
        {"id": "migrate", "role": "one-shot", "dependsOn": ["db"]},
        {"id": "api", "role": "api", "healthPath": "/health/ready",
         "livenessPath": "/health/live", "dependsOn": ["db", "migrate"]},
        {"id": "web", "role": "web", "dependsOn": ["api"]},
    ],
}


def _errors(document: object) -> list[str]:
    return _validate(document, _SCHEMA, "$")


def _seed(**changes: object) -> dict:
    document = copy.deepcopy(_SEED)
    document.update(changes)
    return document


def _seed_unit(index: int, **changes: object) -> dict:
    document = copy.deepcopy(_SEED)
    document["units"][index].update(changes)
    return document


# --------------------------------------------------------------------------- #
# the reference reader of the file-local refusals                              #
# --------------------------------------------------------------------------- #
def _field(message: str) -> str:
    """The JSON path a validator message is about: the member, not its parent."""
    path, _, rest = message.partition(": ")
    member = re.match(r"(?:unexpected field|missing required field) '([^']+)'", rest)
    if member:
        return f"{path}.{member.group(1)}"
    needed = re.match(r"'[^']+' requires '([^']+)'", rest)
    if needed:
        return f"{path}.{needed.group(1)}"
    return path


def _inside(base: pathlib.Path, written: str, checkout: pathlib.Path) -> bool:
    """Does *written*, resolved from *base* with every link followed, stay in *checkout*?"""
    landed = pathlib.Path(os.path.realpath(base / written))
    boundary = pathlib.Path(os.path.realpath(checkout))
    return landed == boundary or boundary in landed.parents


def _development_profile(project: pathlib.Path) -> str:
    """The development compose file: the one the development declaration names, else
    ``docker-compose.yml`` at the project root."""
    declaration = project / "workbench.json"
    if declaration.is_file():
        workbench = json.loads(declaration.read_text(encoding="utf-8"))
        if isinstance(workbench, dict) and isinstance(workbench.get("compose"), dict):
            named = workbench["compose"].get("file")
            if isinstance(named, str):
                return named
    return "docker-compose.yml"


def _read(project: pathlib.Path) -> list[tuple[str, str]]:
    """Every file-local refusal of ``deployment.json`` under *project*, as (field, message).

    The checkout is the project root: a corpus case is read as a copied tree, which lies
    in no work tree. A deploy-policy key is reported with its own message rather than as
    an unknown key, which is the one message the schema asks every reader to give.
    """
    file = project / "deployment.json"
    if not file.is_file():
        return []
    try:
        document = json.loads(file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [("$", f"$: not valid JSON ({exc}); the declaration is one JSON object")]
    refusals: list[tuple[str, str]] = []
    for message in _errors(document):
        field = _field(message)
        key = field.rsplit(".", 1)[-1]
        if "unexpected field" in message and key in _POLICY_KEYS:
            message = f"{field}: " + _POLICY_MESSAGE.format(key=key)
        refusals.append((field, message))
    if not isinstance(document, dict) or "unmanaged" in document:
        return refusals

    units = document.get("units") if isinstance(document.get("units"), list) else []
    for collection, items in (("units", units), ("volumes", document.get("volumes"))):
        seen: set[str] = set()
        for index, item in enumerate(items if isinstance(items, list) else []):
            ident = item.get("id") if isinstance(item, dict) else None
            if isinstance(ident, str) and ident in seen:
                refusals.append((
                    f"$.{collection}[{index}].id",
                    f"$.{collection}[{index}].id: {ident!r} is the id of an earlier entry; "
                    "an id names one entry",
                ))
            if isinstance(ident, str):
                seen.add(ident)

    if document.get("build") == "own" and "generator" in document:
        # The schema refuses this at build (a generator block asks for build generated);
        # every reader names the block itself, which is what the person removes.
        refusals.append((
            "$.generator",
            "$.generator: the generator's words are valid only beside build generated",
        ))
    generator = document.get("generator") if isinstance(document.get("generator"), dict) else {}
    packages = generator.get("systemPackages")
    package_file = project / "system-package-table.json"
    if isinstance(packages, list) and package_file.is_file():
        offered = json.loads(package_file.read_text(encoding="utf-8"))["packages"]
        for index, name in enumerate(packages):
            if isinstance(name, str) and name not in offered:
                refusals.append((
                    f"$.generator.systemPackages[{index}]",
                    f"$.generator.systemPackages[{index}]: {name!r} is not in the "
                    f"system-package table (packages: {', '.join(sorted(offered)) or 'none'})",
                ))
    declared = {unit.get("id") for unit in units if isinstance(unit, dict)}
    volumes = document.get("volumes") if isinstance(document.get("volumes"), list) else []
    for index, volume in enumerate(volumes):
        mount = volume.get("mount") if isinstance(volume, dict) else None
        named = mount.get("units") if isinstance(mount, dict) else None
        for position, ident in enumerate(named if isinstance(named, list) else []):
            if isinstance(ident, str) and ident not in declared:
                refusals.append((
                    f"$.volumes[{index}].mount.units[{position}]",
                    f"$.volumes[{index}].mount.units[{position}]: {ident!r} is no declared "
                    f"unit (declared: {', '.join(sorted(filter(None, declared)))})",
                ))

    sizes = document.get("sizes") if isinstance(document.get("sizes"), dict) else {}
    table_file = project / "datastore-table.json"
    table = (
        json.loads(table_file.read_text(encoding="utf-8"))["kinds"]
        if table_file.is_file()
        else None
    )
    for index, unit in enumerate(units):
        if not isinstance(unit, dict):
            continue
        size = unit.get("size")
        if isinstance(size, str) and size not in sizes:
            refusals.append((
                f"$.units[{index}].size",
                f"$.units[{index}].size: {size!r} is no key of sizes "
                f"(declared: {', '.join(sorted(sizes)) or 'none'})",
            ))
        kind, version = unit.get("kind"), unit.get("version")
        if table is not None and isinstance(kind, str):
            if kind not in table:
                refusals.append((
                    f"$.units[{index}].kind",
                    f"$.units[{index}].kind: {kind!r} is not in the datastore table "
                    f"(kinds: {', '.join(sorted(table))})",
                ))
            elif isinstance(version, str) and version not in table[kind]["versions"]:
                refusals.append((
                    f"$.units[{index}].version",
                    f"$.units[{index}].version: the datastore table carries {kind} "
                    f"{', '.join(sorted(table[kind]['versions']))}, not {version!r}",
                ))

    compose = document.get("compose") if isinstance(document.get("compose"), dict) else {}
    named = [("$.compose.file", compose.get("file"))]
    overrides = compose.get("overrides")
    named += [
        (f"$.compose.overrides[{index}]", override)
        for index, override in enumerate(overrides if isinstance(overrides, list) else [])
    ]
    development = os.path.realpath(project / _development_profile(project))
    for field, written in named:
        if not isinstance(written, str):
            continue
        if not _inside(project, written, project):
            refusals.append((field, f"{field}: {written!r} resolves outside the checkout"))
        elif os.path.realpath(project / written) == development:
            refusals.append((
                field,
                f"{field}: {written!r} is the development profile; name the deployment one",
            ))
    return refusals


def _cases(rule: str) -> list[pathlib.Path]:
    return sorted(path for path in (_CORPUS / rule.split("/", 1)[1]).iterdir() if path.is_dir())


def _member(document: object, path: str) -> bool:
    """Whether the JSON path *path* ('$', '$.a[0].b') names a member of *document*."""
    node = document
    for name, index in re.findall(r"\.([^.\[]+)|\[(\d+)\]", path.removeprefix("$")):
        if name:
            if not isinstance(node, dict) or name not in node:
                return False
            node = node[name]
        else:
            if not isinstance(node, list) or int(index) >= len(node):
                return False
            node = node[int(index)]
    return True


# --------------------------------------------------------------------------- #
# the schema's own discipline                                                  #
# --------------------------------------------------------------------------- #
def _subschemas(schema: object, path: str = "#"):
    if isinstance(schema, dict):
        yield path, schema
        for key, value in schema.items():
            if key == "$defs":
                continue
            yield from _subschemas(value, f"{path}/{key}")
    elif isinstance(schema, list):
        for index, value in enumerate(schema):
            yield from _subschemas(value, f"{path}/{index}")


_CONTROLS = ("\u0000", "\u0007", "\u000a", "\u001b", "\u007f", "\u0085", "\u009b")


def test_the_schema_is_a_draft_2020_12_schema_inside_the_validator_subset() -> None:
    assert _SCHEMA["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert _SCHEMA["$id"].endswith("/deployment-declaration.schema.json")
    # `_validate` reports an unknown schema KEYWORD, so validating both states through it
    # proves the schema stays inside the subset the smallest reader can honour.
    assert _errors(_SEED) == []
    assert _errors({"unmanaged": True, "reason": "Deployed by the operator's own pipeline."}) == []


def test_every_object_is_closed_and_every_field_says_what_it_means() -> None:
    """An unknown key must be refused at every level, not only at the top: a misspelt
    key one level down is the same policy that silently does nothing."""
    objects = [
        (path, schema)
        for path, schema in _subschemas(_SCHEMA)
        if schema.get("type") == "object" and path != "#"
    ]
    assert len(objects) >= 10, "the walk found the schema's object shapes"
    for path, schema in objects:
        assert schema.get("additionalProperties") is False, f"{path}: refuse an unknown key"
        assert "^\\$" in schema.get("patternProperties", {}), (
            f"{path}: a $-prefixed annotation key is exempt at every level, or at none"
        )
        assert schema.get("description", "").strip(), f"{path}: say what the shape is"
        for field, definition in schema.get("properties", {}).items():
            assert definition.get("description", "").strip(), (
                f"{path}/properties/{field}: say what the field means"
            )


def test_every_string_is_capped_and_refuses_control_characters() -> None:
    """The decision behind the file: every string has a length cap and refuses control
    characters, because the file is input an agent wrote and a person reads."""
    strings = [
        (path, schema) for path, schema in _subschemas(_SCHEMA) if schema.get("type") == "string"
    ]
    assert strings
    for path, schema in strings:
        if "const" in schema or "enum" in schema:
            continue
        assert isinstance(schema.get("maxLength"), int), f"{path}: a string needs a length cap"
        pattern = schema.get("pattern")
        assert pattern, f"{path}: a string needs a pattern that refuses control characters"
        for control in _CONTROLS:
            for probe in (f"a{control}", f"{control}a", f"/a{control}", f"P1D{control}"):
                assert re.search(pattern, probe) is None, (
                    f"{path}: {probe!r} passes {pattern!r} - a control character got through"
                )
    # The keys of the size table are strings too, capped and held by their pattern.
    size_keys = [key for key in _MANAGED["properties"]["sizes"]["patternProperties"] if key != "^\\$"]
    assert len(size_keys) == 1 and "{0,31}" in size_keys[0], size_keys
    for control in _CONTROLS:
        assert re.search(size_keys[0], f"small{control}") is None
    assert re.search(size_keys[0], "s" * 33) is None, "a size name past 32 characters"


def test_every_pattern_ends_at_the_end_of_the_input() -> None:
    """In Python's regular expressions ``$`` also matches before a final newline, so
    ``^[a-z]+$`` accepts ``"api\\n"`` - which would let a newline through every pattern
    whose purpose is to refuse control characters, in exactly the language most readers
    of this file are written in. ``(?![\\s\\S])`` means the end of the input in Python and
    in ECMA-262 alike, which is the dialect JSON Schema names."""
    patterns = {
        schema["pattern"] for _, schema in _subschemas(_SCHEMA) if "pattern" in schema
    } | {
        key
        for _, schema in _subschemas(_SCHEMA)
        for key in schema.get("patternProperties", {})
        if key != "^\\$"
    }
    assert patterns
    for pattern in sorted(patterns):
        assert pattern.startswith("^") and pattern.endswith("(?![\\s\\S])"), pattern
        assert not pattern.endswith("$"), pattern
    assert re.search(_UNIT["properties"]["id"]["pattern"], "api") is not None
    assert re.search(_UNIT["properties"]["id"]["pattern"], "api\n") is None


def test_closed_vocabularies_are_sorted_and_the_named_lists_are_coherent() -> None:
    for path, schema in _subschemas(_SCHEMA):
        values = schema.get("enum")
        if values is None:
            continue
        assert values == sorted(values) and len(values) == len(set(values)), (
            f"{path}: enum entries must be sorted and unique"
        )
    for name, definition in _SCHEMA["$defs"].items():
        values = definition["enum"]
        assert values == sorted(values) and len(values) == len(set(values)), f"$defs/{name}"
        assert definition.get("description", "").strip(), f"$defs/{name}: say what it lists"

    role = _UNIT["properties"]["role"]
    for known in _SCHEMA["$defs"]["knownRoles"]["enum"]:
        assert re.search(role["pattern"], known), f"known role {known!r} must be a valid role"
    assert "enum" not in role, "the role vocabulary is open: an unknown role is information"
    assert set(_SCHEMA["$defs"]["roleResolvedFields"]["enum"]) <= set(_UNIT["properties"]), (
        "a field resolved by role must be a unit field"
    )
    # A deploy-policy key is refused at every level because it is no property anywhere.
    declared = {
        field
        for _, schema in _subschemas(_SCHEMA)
        for field in schema.get("properties", {})
    }
    assert not _POLICY_KEYS & declared, (
        f"deploy-policy keys may not be properties anywhere: {sorted(_POLICY_KEYS & declared)}"
    )


def test_the_four_states_are_exactly_four() -> None:
    """Absent, own, generated, opted out - and a file in none of them, or two, is refused."""
    assert _MANAGED["properties"]["build"]["enum"] == ["generated", "own"]
    assert set(_MANAGED["required"]) >= {"schemaVersion", "build", "units"}
    assert _errors(_seed(build="generated")) == [], "generated is in the vocabulary from v1"
    no_build = _seed()
    del no_build["build"]
    assert _errors(no_build), "units without build are in no state"
    assert _errors({"unmanaged": True, "reason": "x", "build": "own"}), "two states at once"
    assert _errors({"unmanaged": True, "reason": "x", "units": _SEED["units"]})
    assert _errors({"unmanaged": True}), "an escape without a reason is a hole"
    assert _errors({"unmanaged": True, "reason": " \t "}), "a blank reason is no reason"
    assert _errors({"unmanaged": False, **_SEED}), "unmanaged is only ever true"
    assert _errors({"schemaVersion": 1}), "a file with nothing in it is in no state"
    assert _errors({"unmanaged": True, "reason": "x", "schemaVersion": 2})
    assert _errors({"unmanaged": True, "reason": "x", "schemaVersion": 1}) == []


# --------------------------------------------------------------------------- #
# every field valid and invalid                                                 #
# --------------------------------------------------------------------------- #
_VALID = {
    "schemaVersion 1": _seed(),
    "build generated": _seed(build="generated"),
    "compose overrides": _seed(compose={"file": "deploy/compose.yml",
                                        "overrides": ["deploy/compose.tls.yml"]}),
    "a profile of any name": _seed(compose={"file": "compose.production.yml"}),
    "a unit with only id and role": _seed(units=[{"id": "api", "role": "api"}]),
    "an unknown role": _seed(units=[{"id": "scanner", "role": "virus-scanner"}]),
    "every known role": _seed(units=[
        {"id": role, "role": role} for role in _SCHEMA["$defs"]["knownRoles"]["enum"]
    ]),
    "an argv command with metacharacters": _seed_unit(
        1, command=["sh", "-c", "a;b|c&&$(d)`e`>f"]
    ),
    "health and liveness paths": _seed_unit(2, healthPath="/api/health/ready?x".split("?")[0],
                                            livenessPath="/health/live"),
    "migrations by label": _seed_unit(2, migrations=["app", "audit", "notes_v2", "billing.core"]),
    "env names": _seed_unit(2, env=["SOME_API_BASE_URL", "SECRET_KEY"]),
    "an empty start order": _seed_unit(1, dependsOn=[]),
    "instances many": _seed_unit(2, instances="many"),
    "instances one": _seed_unit(2, instances="one"),
    "a size": _seed(sizes={"small": {"cpu": 0.5, "memoryMiB": 512},
                           "large": {"cpu": 4, "memoryMiB": 8192}},
                    units=[{"id": "api", "role": "api", "size": "large"}]),
    "stateful with no backup": _seed(units=[{"id": "db", "role": "database", "stateful": True}]),
    "a backup in hours": _seed_unit(0, backup={"every": "PT6H", "keep": "P2W"}),
    "a store by kind": _seed(units=[{"id": "cache", "role": "store", "kind": "redis",
                                     "version": "7.2"}]),
    "a files volume": _seed(volumes=[{"id": "files", "backup": {"every": "P1D", "keep": "P30D"}}]),
    "a volume with no backup": _seed(volumes=[{"id": "files"}]),
    "an external database": _seed(units=_SEED["units"][1:], externalDatabase={"backup": "client"}),
    "a rollback": _seed(rollback={"strategy": "redeploy-previous-release"}),
    "a restated mount": _seed(volumes=[{"id": "files", "mount": {"path": "var/files",
                                                                 "units": ["api", "migrate"]}}]),
    "a mount deeper in var": _seed(volumes=[{"id": "cache", "mount": {"path": "var/cache/v2.1",
                                                                       "units": ["api"]}}]),
    "a generated volume with its mount": _seed(build="generated", volumes=[
        {"id": "files", "mount": {"path": "var/files", "units": ["api"]},
         "backup": {"every": "P1D", "keep": "P30D"}}
    ]),
    "a generator block": _seed(build="generated", generator={"systemPackages": ["libpq5"]}),
    "a package name with its punctuation": _seed(
        build="generated", generator={"systemPackages": ["g++", "libstdc++6", "python3.13-venv"]}
    ),
    "an empty generator block": _seed(build="generated", generator={}),
    "annotations": {**_seed(), "$schema": "https://terp.dev/spec/deployment-declaration.schema.json",
                    "$comment": "the hardened profile"},
}

_INVALID = {
    "schemaVersion 2": _seed(schemaVersion=2),
    "schemaVersion as text": _seed(schemaVersion="1"),
    "schemaVersion true": _seed(schemaVersion=True),
    "build off the vocabulary": _seed(build="managed"),
    "no compose": {k: v for k, v in _SEED.items() if k != "compose"},
    "compose without file": _seed(compose={"overrides": ["x.yml"]}),
    "an absolute profile": _seed(compose={"file": "/etc/compose.yml"}),
    "a backslash path": _seed(compose={"file": "deploy\\compose.yml"}),
    "a drive letter": _seed(compose={"file": "C:compose.yml"}),
    "an override twice": _seed(compose={"file": "a.yml", "overrides": ["b.yml", "b.yml"]}),
    "no units": _seed(units=[]),
    "units not a list": _seed(units={"api": {"role": "api"}}),
    "a unit without role": _seed(units=[{"id": "api"}]),
    "a unit without id": _seed(units=[{"role": "api"}]),
    "an id that is not a service name": _seed(units=[{"id": "my api", "role": "api"}]),
    "an id past its cap": _seed(units=[{"id": "a" * 64, "role": "api"}]),
    "a role in capitals": _seed(units=[{"id": "api", "role": "API"}]),
    "an image": _seed_unit(0, image="postgres:17-alpine"),
    "a dockerfile": _seed_unit(2, dockerfile="Dockerfile.prod"),
    "a kind with no version": _seed(units=[{"id": "db", "role": "database", "kind": "postgres"}]),
    "a version with no kind": _seed(units=[{"id": "db", "role": "database", "version": "17"}]),
    "a version as a number": _seed_unit(0, version=17),
    "a shell-string command": _seed_unit(1, command="terp migrate upgrade"),
    "an empty command": _seed_unit(1, command=[]),
    "a command with a control character": _seed_unit(1, command=["terp", "x\u001b[2J"]),
    "a health path that is a URL": _seed_unit(2, healthPath="http://api:8000/health/ready"),
    "a health path with a query": _seed_unit(2, healthPath="/health?ready=1"),
    "a liveness path with no slash": _seed_unit(2, livenessPath="health/live"),
    "a migration label twice": _seed_unit(2, migrations=["app", "app"]),
    "a migration label with a space": _seed_unit(2, migrations=["my app"]),
    "an env name in lower case": _seed_unit(2, env=["some_url"]),
    "an env name twice": _seed_unit(2, env=["A_B", "A_B"]),
    "a start order as text": _seed_unit(1, dependsOn="db"),
    "instances as a number": _seed_unit(2, instances=2),
    "a size in capitals": _seed_unit(2, size="Large"),
    "stateful as text": _seed_unit(0, stateful="yes"),
    "a backup on a unit not declared stateful": _seed(units=[
        {"id": "db", "role": "database", "backup": {"every": "P1D", "keep": "P30D"}}
    ]),
    "a backup on a unit declared not stateful": _seed(units=[
        {"id": "db", "role": "database", "stateful": False,
         "backup": {"every": "P1D", "keep": "P30D"}}
    ]),
    "a backup left to the client on a unit": _seed_unit(0, backup="client"),
    "a backup with no keep": _seed_unit(0, backup={"every": "P1D"}),
    "a backup cadence in words": _seed_unit(0, backup={"every": "daily", "keep": "P30D"}),
    "an empty duration": _seed_unit(0, backup={"every": "P", "keep": "P30D"}),
    "an empty time duration": _seed_unit(0, backup={"every": "PT", "keep": "P30D"}),
    "a backup destination": _seed_unit(0, backup={"every": "P1D", "keep": "P30D",
                                                  "to": "s3://bucket"}),
    "a volume without id": _seed(volumes=[{"backup": {"every": "P1D", "keep": "P30D"}}]),
    "a volume backup left to the client": _seed(volumes=[{"id": "files", "backup": "client"}]),
    "a size without memory": _seed(sizes={"small": {"cpu": 0.5}}),
    "a size of no cpu": _seed(sizes={"small": {"cpu": 0, "memoryMiB": 512}}),
    "memory as a fraction": _seed(sizes={"small": {"cpu": 1, "memoryMiB": 0.5}}),
    "a size key in capitals": _seed(sizes={"Small": {"cpu": 1, "memoryMiB": 512}}),
    "an external database backed up by policy": _seed(
        externalDatabase={"backup": {"every": "P1D", "keep": "P30D"}}
    ),
    "an external database with a connection": _seed(
        externalDatabase={"backup": "client", "url": "postgresql://db.example.invalid/app"}
    ),
    "a rollback strategy unknown to v1": _seed(rollback={"strategy": "blue-green"}),
    "a rollback that claims no restore": _seed(
        rollback={"strategy": "redeploy-previous-release", "restoreFree": True}
    ),
    "an annotation that is not text": {**_seed(), "$comment": ["a", "b"]},
    "an annotation with a control character": {**_seed(), "$comment": "a\u0007"},
    "a terp version key": _seed(terp="0.40.0"),
    "an environment": _seed(environments={"production": {}}),
    "a domain": _seed(domain="app.example.invalid"),
    "a generator block beside own": _seed(generator={"systemPackages": []}),
    "an empty generator block beside own": _seed(generator={}),
    "a generator word it lacks": _seed(build="generated", generator={"aptPackages": ["curl"]}),
    "a package list as text": _seed(build="generated", generator={"systemPackages": "curl"}),
    "a package named like an option": _seed(
        build="generated", generator={"systemPackages": ["-oDir::Etc=/tmp"]}
    ),
    "a package in capitals": _seed(build="generated", generator={"systemPackages": ["Curl"]}),
    "a package of one letter": _seed(build="generated", generator={"systemPackages": ["c"]}),
    "a package with a space": _seed(build="generated", generator={"systemPackages": ["a b"]}),
    "a package twice": _seed(build="generated", generator={"systemPackages": ["curl", "curl"]}),
    "a generated volume without its mount": _seed(build="generated", volumes=[{"id": "files"}]),
    "a mount outside var": _seed(volumes=[{"id": "files", "mount": {"path": "data",
                                                                    "units": ["api"]}}]),
    "a mount that is var itself": _seed(volumes=[{"id": "files", "mount": {"path": "var",
                                                                          "units": ["api"]}}]),
    "an absolute mount": _seed(volumes=[{"id": "files", "mount": {"path": "/srv/var/files",
                                                                  "units": ["api"]}}]),
    "a mount that climbs out": _seed(volumes=[{"id": "files", "mount": {"path": "var/../etc",
                                                                        "units": ["api"]}}]),
    "a mount into a hidden directory": _seed(volumes=[{"id": "files", "mount": {
        "path": "var/.ssh", "units": ["api"]}}]),
    "a mount with a backslash": _seed(volumes=[{"id": "files", "mount": {"path": "var\\files",
                                                                         "units": ["api"]}}]),
    "a mount with no units": _seed(volumes=[{"id": "files", "mount": {"path": "var/files",
                                                                      "units": []}}]),
    "a mount without units": _seed(volumes=[{"id": "files", "mount": {"path": "var/files"}}]),
    "a mount without a path": _seed(volumes=[{"id": "files", "mount": {"units": ["api"]}}]),
    "a mount naming a unit twice": _seed(volumes=[{"id": "files", "mount": {
        "path": "var/files", "units": ["api", "api"]}}]),
    "a mount as a string": _seed(volumes=[{"id": "files", "mount": "var/files"}]),
    "a mount with a read-only flag": _seed(volumes=[{"id": "files", "mount": {
        "path": "var/files", "units": ["api"], "readOnly": True}}]),
}


@pytest.mark.parametrize("name", sorted(_VALID))
def test_a_valid_field_validates(name: str) -> None:
    assert _errors(_VALID[name]) == [], f"{name}: {_errors(_VALID[name])}"


@pytest.mark.parametrize("name", sorted(_INVALID))
def test_an_invalid_field_is_refused(name: str) -> None:
    assert _errors(_INVALID[name]), f"{name}: the schema accepted it"


def test_every_unit_field_is_exercised_both_ways() -> None:
    """The tables above are only worth their names if every field appears in both."""
    def touched(documents: dict[str, object]) -> set[str]:
        return {
            field
            for document in documents.values()
            if isinstance(document, dict)
            for unit in document.get("units", []) if isinstance(document.get("units"), list)
            if isinstance(unit, dict)
            for field in unit
        }

    unit_fields = set(_UNIT["properties"])
    assert unit_fields <= touched(_VALID), sorted(unit_fields - touched(_VALID))
    # Required fields are exercised by their absence, which removes them from the unit.
    assert unit_fields - {"id", "role"} <= touched(_INVALID), sorted(
        unit_fields - {"id", "role"} - touched(_INVALID)
    )


def test_an_unknown_key_is_refused_at_every_level_and_an_annotation_nowhere() -> None:
    def at(document: dict, *path: object) -> dict:
        node: object = document
        for step in path:
            node = node[step]  # type: ignore[index]
        assert isinstance(node, dict)
        return node

    full = _seed(
        volumes=[{"id": "files", "backup": {"every": "P1D", "keep": "P30D"}}],
        sizes={"small": {"cpu": 0.5, "memoryMiB": 512}},
        rollback={"strategy": "redeploy-previous-release"},
        units=[*copy.deepcopy(_SEED["units"][1:]), {"id": "files-db", "role": "database",
                                                   "stateful": True,
                                                   "backup": {"every": "P1D", "keep": "P7D"}}],
        externalDatabase={"backup": "client"},
    )
    assert _errors(full) == []
    levels = [(), ("compose",), ("units", 0), ("units", 3, "backup"), ("volumes", 0),
              ("volumes", 0, "backup"), ("sizes",), ("sizes", "small"),
              ("externalDatabase",), ("rollback",)]
    for level in levels:
        misspelt = copy.deepcopy(full)
        at(misspelt, *level)["statefull"] = True
        assert _errors(misspelt), f"{level}: an unknown key must be refused"
        annotated = copy.deepcopy(full)
        at(annotated, *level)["$comment"] = "an annotation"
        assert _errors(annotated) == [], f"{level}: a $-prefixed annotation is exempt"
    opted_out = {"unmanaged": True, "reason": "x"}
    assert _errors({**opted_out, "statefull": True})
    assert _errors({**opted_out, "$comment": "an annotation"}) == []
    generated = _seed(
        build="generated",
        generator={"systemPackages": []},
        volumes=[{"id": "files", "mount": {"path": "var/files", "units": ["api"]}}],
    )
    assert _errors(generated) == []
    for level in (("generator",), ("volumes", 0, "mount")):
        misspelt = copy.deepcopy(generated)
        at(misspelt, *level)["statefull"] = True
        assert _errors(misspelt), f"{level}: an unknown key must be refused"
        annotated = copy.deepcopy(generated)
        at(annotated, *level)["$comment"] = "an annotation"
        assert _errors(annotated) == [], f"{level}: a $-prefixed annotation is exempt"


def test_deploy_policy_is_refused_with_its_own_message_at_every_level_and_in_every_state(
    tmp_path: pathlib.Path,
) -> None:
    """The keys the schema names are refused with the one message every reader gives,
    including beside unmanaged - the opted-out state carries nothing else, so it can
    never carry a policy."""
    for key in sorted(_POLICY_KEYS):
        for document, field in (
            (_seed(**{key: 1}), f"$.{key}"),
            (_seed_unit(2, **{key: 1}), f"$.units[2].{key}"),
            ({"unmanaged": True, "reason": "x", key: 1}, f"$.{key}"),
        ):
            (tmp_path / "deployment.json").write_text(json.dumps(document), encoding="utf-8")
            refusals = dict(_read(tmp_path))
            assert field in refusals, f"{key}: not refused at {field}"
            assert refusals[field].endswith(_POLICY_MESSAGE.format(key=key)), refusals[field]
    # A word from the list as a VALUE is not a key and is not refused.
    words = _seed(units=[{"id": "gate", "role": "approvals", "env": ["APPROVAL_WEBHOOK_URL"]}])
    words["$comment"] = "approvals, access and publish rights live on the environment record"
    assert _errors(words) == []


# --------------------------------------------------------------------------- #
# defaults                                                                      #
# --------------------------------------------------------------------------- #
def _apply_defaults(value: object, schema: dict) -> object:
    """Fill every absent property that has a stated default, as a reader does."""
    if not isinstance(value, dict):
        if isinstance(value, list) and "items" in schema:
            return [_apply_defaults(item, schema["items"]) for item in value]
        return value
    if "if" in schema:
        branch = "then" if not _validate(value, schema["if"], "$") else "else"
        if branch in schema and "properties" in schema[branch]:
            value = _apply_defaults(value, schema[branch])
    filled = dict(value)
    for field, definition in schema.get("properties", {}).items():
        if field not in filled and "default" in definition:
            filled[field] = copy.deepcopy(definition["default"])
        if field in filled:
            filled[field] = _apply_defaults(filled[field], definition)
    return filled


def test_every_default_validates_against_its_own_field() -> None:
    defaulted = [(path, schema) for path, schema in _subschemas(_SCHEMA) if "default" in schema]
    assert defaulted
    for path, schema in defaulted:
        assert _validate(schema["default"], schema, path) == [], f"{path}: default is invalid"


def test_defaults_are_applied() -> None:
    minimal = {"schemaVersion": 1, "build": "own", "compose": {"file": "docker-compose.prod.yml"},
               "units": [{"id": "api", "role": "api"}]}
    filled = _apply_defaults(minimal, _SCHEMA)
    assert _errors(filled) == [], "a document with its defaults applied still validates"
    assert filled["compose"]["overrides"] == []
    assert filled["volumes"] == [] and filled["sizes"] == {}
    unit = filled["units"][0]
    assert unit["instances"] == "one", "a unit not declared scalable runs one copy"
    assert unit["stateful"] is False
    assert unit["migrations"] == [] and unit["env"] == []
    # A restated fact has no default: an absent command or start order is NOT restated,
    # which is not the same as one that is empty, and defaulting it would turn every
    # declaration that leaves it out into a disagreement with its profile.
    assert "command" not in unit and "dependsOn" not in unit
    assert "default" not in _UNIT["properties"]["command"]
    assert "default" not in _UNIT["properties"]["dependsOn"]
    # Nor do the facts whose absence means "not declared": a rollback, an external
    # database, a kind, a size.
    for absent in ("rollback", "externalDatabase"):
        assert absent not in filled and "default" not in _MANAGED["properties"][absent]
    for absent in ("kind", "version", "size", "backup", "healthPath", "livenessPath"):
        assert absent not in unit
    opted_out = {"unmanaged": True, "reason": "x"}
    assert _apply_defaults(opted_out, _SCHEMA) == opted_out, "the opted-out state has no defaults"


def test_the_declaration_round_trips() -> None:
    """Two programs read these bytes: what one writes, the other reads back unchanged."""
    for document in (_SEED, _VALID["a files volume"], _VALID["annotations"],
                     {"unmanaged": True, "reason": "Deployed elsewhere."}):
        again = json.loads(json.dumps(document, indent=2))
        assert again == document and _errors(again) == []


# --------------------------------------------------------------------------- #
# the corpus reads as its cases say                                             #
# --------------------------------------------------------------------------- #
def test_the_readable_corpus_reads_as_its_cases_say() -> None:
    refusals = _FIXTURES["refusals"][_READABLE]
    for case in _cases(_READABLE):
        found = _read(case)
        if case.name.startswith("compliant-"):
            assert found == [], f"{case.name}: a compliant case is refused: {found}"
            continue
        expected = refusals[case.name]
        if "in" in expected:
            # The refusal is in the profile, which this JSON-only reader does not read;
            # the declaration itself must then be clean, so the profile is what is wrong.
            assert found == [], f"{case.name}: the declaration itself is refused: {found}"
            assert (case / expected["in"]).is_file(), f"{case.name}: {expected['in']} missing"
            continue
        assert found, f"{case.name}: nothing refuses this violation case"
        assert expected["field"] in {field for field, _ in found}, (
            f"{case.name}: refused, but not at {expected['field']}: {found}"
        )


def test_the_truth_corpus_is_readable_so_it_tests_only_the_truth() -> None:
    """A truth case that is also unreadable proves nothing about the truth check: a
    reader stops at the first. So every one of them reads cleanly."""
    for case in _cases(_TRUTH):
        assert _read(case) == [], f"{case.name}: {_read(case)}"


def test_every_violation_case_names_its_field_and_what_it_allows() -> None:
    refusals = _FIXTURES["refusals"]
    assert set(refusals) == set(_RULES)
    for rule in _RULES:
        violations = {case.name for case in _cases(rule) if case.name.startswith("violation-")}
        assert set(refusals[rule]) == violations, (
            f"{rule}: refusals and violation cases differ - "
            f"unlisted {sorted(violations - set(refusals[rule]))}, "
            f"listed but absent {sorted(set(refusals[rule]) - violations)}"
        )
        for name, expected in refusals[rule].items():
            assert set(expected) <= {"field", "allowed", "in"}, f"{rule}/{name}"
            assert expected["field"].strip() and expected["allowed"].strip(), f"{rule}/{name}"
            if rule == _RENDER:
                continue  # held by test_a_render_refusal_names_a_file_the_case_holds
            if rule == _TRUTH:
                document = json.loads(
                    (_CORPUS / rule.split("/")[1] / name / "deployment.json").read_text(
                        encoding="utf-8"
                    )
                )
                assert _member(document, expected["field"]), (
                    f"{rule}/{name}: {expected['field']} names no declared fact"
                )


def test_the_corpus_holds_the_twenty_broken_declarations_and_the_never_red_cases() -> None:
    """The corpus holds at least twenty broken declarations refused with the field and
    the allowed values, and the cases that must never be red: an absent file and
    the opted-out state with a reason."""
    readable = _cases(_READABLE)
    assert sum(case.name.startswith("violation-") for case in readable) >= 20
    for rule in _RULES:
        compliant = [case for case in _cases(rule) if case.name.startswith("compliant-")]
        assert any(not (case / "deployment.json").exists() for case in compliant), (
            f"{rule}: an absent file is never red, and a compliant case says so"
        )
        assert any(
            json.loads((case / "deployment.json").read_text(encoding="utf-8")).get("unmanaged")
            is True
            for case in compliant
            if (case / "deployment.json").is_file()
        ), f"{rule}: the opted-out state with a reason is never red, and a compliant case says so"


def test_a_case_that_names_a_kind_ships_the_table_it_resolves_against() -> None:
    """Which datastore kinds, versions and digests exist is per stack, so a case that names
    one carries the table a checker must resolve it against - as the escape-hatch budget
    cases carry their budget - and stays stack-independent."""
    for rule in _RULES:
        for case in _cases(rule):
            file = case / "deployment.json"
            try:
                document = json.loads(file.read_text(encoding="utf-8")) if file.is_file() else {}
            except json.JSONDecodeError:
                continue
            units = document.get("units", []) if isinstance(document, dict) else []
            kinds = [u for u in units if isinstance(u, dict) and "kind" in u]
            table_file = case / "datastore-table.json"
            if not kinds:
                continue
            assert table_file.is_file(), f"{rule}/{case.name}: names a kind and ships no table"
            table = json.loads(table_file.read_text(encoding="utf-8"))
            assert set(table) == {"kinds"}, f"{rule}/{case.name}: the table is {{'kinds': ...}}"
            for kind, entry in table["kinds"].items():
                assert set(entry) == {"role", "versions"}, f"{rule}/{case.name}: {kind}"
                assert entry["role"] in {"database", "store"}, f"{rule}/{case.name}: {kind}"
                for version, image in entry["versions"].items():
                    assert re.fullmatch(r"[a-z0-9./-]+@sha256:[0-9a-f]{64}", image), (
                        f"{rule}/{case.name}: {kind} {version} is pinned by digest"
                    )


def test_the_generator_words_stand_only_in_the_generated_state() -> None:
    """``generator`` asks a generator for something, so beside ``own`` - where nothing
    renders - it is refused, and beside ``unmanaged`` it is one more key of a state that
    carries none. In the generated state the generator renders each volume's mount, so a
    volume without one is refused there and only there."""
    with_block = {"systemPackages": []}
    assert _errors(_seed(build="generated", generator=with_block)) == []
    assert any(error.startswith("$.build:") for error in _errors(_seed(generator=with_block)))
    assert _errors({"unmanaged": True, "reason": "x", "generator": with_block})
    unmounted = [{"id": "files", "backup": {"every": "P1D", "keep": "P30D"}}]
    assert _errors(_seed(volumes=unmounted)) == [], "own: a mount is a restatement, optional"
    for document in (_seed(build="generated", volumes=unmounted),
                     _seed(build="generated", volumes=unmounted, generator=with_block)):
        assert "$.volumes[0]: missing required field 'mount'" in _errors(document)
    # No default: an absent block asks for nothing, so filling one in would turn every own
    # declaration into a refusal.
    assert "default" not in _GENERATOR
    assert _GENERATOR["properties"]["systemPackages"]["default"] == []
    assert "default" not in _VOLUME["properties"]["mount"]


def test_a_package_name_can_never_be_read_as_an_option() -> None:
    """A name reaches a package manager's argument list, where a leading dash is an
    option: the pattern refuses one, and a name shorter than two characters, which no
    package has."""
    pattern = _GENERATOR["properties"]["systemPackages"]["items"]["pattern"]
    for name in ("libpq5", "g++", "python3.13-venv", "ca-certificates"):
        assert re.search(pattern, name), name
    for name in ("-y", "--allow-unauthenticated", "-oDir::Etc=/tmp", "+x", ".x", "Curl", "a b",
                 "curl=7.88", "curl/stable", "c"):
        assert re.search(pattern, name) is None, name


def _render_cases(prefix: str) -> list[pathlib.Path]:
    return [case for case in _cases(_RENDER) if case.name.startswith(prefix)]


def test_the_render_corpus_holds_only_what_every_stack_can_judge() -> None:
    """No case carries the expected render: the generator's bytes are the stack's, and
    they move with every framework release's base-image digests. So every violation is a
    readable generated declaration that is red whatever the render is, and every compliant
    case is a state the rule is silent in - and each of the four such states is sampled."""
    for case in _render_cases("violation-"):
        document = json.loads((case / "deployment.json").read_text(encoding="utf-8"))
        assert document.get("build") == "generated", f"{case.name}: red only when generated"
        assert _read(case) == [], f"{case.name}: the readable rule would stop first: {_read(case)}"
    silent: set[str] = set()
    for case in _render_cases("compliant-"):
        file = case / "deployment.json"
        if not file.is_file():
            silent.add("undeclared")
            continue
        document = json.loads(file.read_text(encoding="utf-8"))
        if _read(case):
            silent.add("unreadable")
        elif document.get("unmanaged") is True:
            silent.add("opted out")
        else:
            assert document.get("build") == "own", f"{case.name}: a generated case is judged"
            silent.add("own")
    assert silent == {"undeclared", "unreadable", "opted out", "own"}, sorted(silent)


def test_a_render_refusal_names_a_file_the_case_holds() -> None:
    """A refusal about a file (a build file, an ignore file, pyproject.toml, the template's
    answers) names it in ``in``, and the case holds that file - the stale file the render
    does not produce included, since that file is the finding."""
    for name, expected in _FIXTURES["refusals"][_RENDER].items():
        case = _CORPUS / _RENDER.split("/")[1] / name
        if "in" in expected:
            assert (case / expected["in"]).is_file(), f"{name}: {expected['in']} missing"
        else:
            # A refusal may be about a field the unit lacks (a command the role has no
            # default for), so the field's own container is what has to be declared.
            document = json.loads((case / "deployment.json").read_text(encoding="utf-8"))
            container = re.sub(r"(\.[^.\[]+|\[\d+\])$", "", expected["field"])
            assert _member(document, container), f"{name}: {expected['field']}"


def test_a_case_that_names_a_system_package_ships_the_table_it_resolves_against() -> None:
    """Which packages exist is per stack, as datastore kinds are, so a case that names one
    carries the table it resolves against, and stays stack-independent."""
    for rule in _RULES:
        for case in _cases(rule):
            file = case / "deployment.json"
            try:
                document = json.loads(file.read_text(encoding="utf-8")) if file.is_file() else {}
            except json.JSONDecodeError:
                continue
            generator = document.get("generator") if isinstance(document, dict) else None
            if not (isinstance(generator, dict) and generator.get("systemPackages")):
                continue
            table = json.loads((case / "system-package-table.json").read_text(encoding="utf-8"))
            assert set(table) == {"packages"} and isinstance(table["packages"], dict), case.name


# --------------------------------------------------------------------------- #
# the tree fixtures a corpus case cannot carry                                  #
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("tree", _FIXTURES["trees"], ids=lambda tree: tree["id"])
def test_the_tree_fixtures_resolve_as_they_say(tree: dict, tmp_path: pathlib.Path) -> None:
    assert tree["rule"] in _RULES
    assert tree["expect"] in {"violation", "compliant"}
    assert set(tree) <= {"id", "rule", "expect", "field", "in", "projectRoot", "workTree",
                         "files", "links", "resolve"}, tree["id"]
    for name, text in tree["files"].items():
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    for link, destination in tree["links"].items():
        try:
            os.symlink(destination, tmp_path / link, target_is_directory=True)
        except OSError as exc:  # pragma: no cover - a platform that refuses links
            pytest.skip(f"this platform refuses symbolic links ({exc})")
    project = tmp_path / tree["projectRoot"]
    declaration = json.loads((project / "deployment.json").read_text(encoding="utf-8"))
    assert _errors(declaration) == [], f"{tree['id']}: the refusal must be a path, not a key"
    checkout = tmp_path / tree["workTree"] if "workTree" in tree else project
    outcomes = []
    for entry in tree["resolve"]:
        inside = _inside(tmp_path / entry["base"], entry["path"], checkout)
        assert ("inside" if inside else "outside") == entry["lands"], (
            f"{tree['id']}: {entry['path']} from {entry['base']} lands "
            f"{'inside' if inside else 'outside'}, the fixture says {entry['lands']}"
        )
        outcomes.append(inside)
    assert (tree["expect"] == "violation") == (not all(outcomes)), (
        f"{tree['id']}: a violation is exactly a tree with a path that lands outside"
    )
    if tree["expect"] == "violation":
        assert tree.get("field"), f"{tree['id']}: a violation names its field"


def test_the_fixtures_and_the_schema_are_claimed_by_a_rule() -> None:
    """Normative data joins the spec when a rule realises it, not before."""
    entries = {
        rule: json.loads((_SPEC / "catalog" / f"{rule}.json").read_text(encoding="utf-8"))
        for rule in _RULES
    }
    for name in ("deployment-declaration.schema.json", "deployment-declaration.fixtures.json"):
        assert any(
            name in entry["intent"] or name in entry.get("reference", "")
            for entry in entries.values()
        ), f"no catalog entry cites {name}"
