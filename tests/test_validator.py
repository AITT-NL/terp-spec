"""The minimal schema validator is itself tested (negative-case coverage).

``tests/test_standard.py`` ships a deliberately minimal, dependency-free JSON
Schema subset validator and every catalog entry passes through it — so the
validator is load-bearing spec infrastructure. These negative cases prove it
actually REJECTS malformed data (a validator that accepts everything would
pass the whole catalog suite silently), and that it fails loudly on schema
constructs outside its supported subset instead of skipping them.
"""

from __future__ import annotations

from test_standard import _validate


def _errors(instance: object, schema: dict) -> list[str]:
    return _validate(instance, schema, "root")


def test_unknown_schema_keyword_fails_loudly() -> None:
    assert _errors("x", {"type": "string", "oneOf": []}), (
        "an unsupported schema keyword must be reported, never silently ignored"
    )


def test_unknown_schema_type_fails_loudly() -> None:
    # "number" is supported since the deployment declaration needed it; "null" is not.
    assert _errors(None, {"type": "null"}), (
        "an unsupported schema type must be reported, never silently ignored"
    )
    assert _errors("x", {"type": ["string", "null"]})


def test_enum_mismatch_is_rejected() -> None:
    assert _errors("purple", {"enum": ["backend", "frontend"]})
    assert _errors("backend", {"enum": ["backend", "frontend"]}) == []


def test_type_mismatches_are_rejected() -> None:
    assert _errors(42, {"type": "string"})
    assert _errors("42", {"type": "integer"})
    assert _errors(True, {"type": "integer"}), "bool must not pass as integer"
    assert _errors([], {"type": "object"})
    assert _errors({}, {"type": "array"})
    assert _errors("yes", {"type": "boolean"})


def test_missing_required_field_is_rejected() -> None:
    schema = {"type": "object", "required": ["id"], "properties": {"id": {"type": "string"}}}
    assert _errors({}, schema)
    assert _errors({"id": "x"}, schema) == []


def test_additional_properties_false_rejects_unknown_fields() -> None:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"id": {"type": "string"}},
    }
    assert _errors({"id": "x", "extra": 1}, schema)
    assert _errors({"id": "x"}, schema) == []


def test_string_constraints_are_enforced() -> None:
    assert _errors("", {"type": "string", "minLength": 1})
    assert _errors("   ", {"type": "string", "minLength": 1}), (
        "whitespace-only must not satisfy minLength"
    )
    assert _errors("nope", {"type": "string", "pattern": r"^\d+$"})
    assert _errors("123", {"type": "string", "pattern": r"^\d+$"}) == []


def test_array_constraints_are_enforced() -> None:
    schema = {"type": "array", "minItems": 1, "items": {"type": "string"}}
    assert _errors([], schema)
    assert _errors([1], schema), "item type violations inside arrays must be reported"
    assert _errors(["ok"], schema) == []


def test_integer_minimum_is_enforced() -> None:
    assert _errors(0, {"type": "integer", "minimum": 1})
    assert _errors(1, {"type": "integer", "minimum": 1}) == []


def test_a_boolean_is_never_a_number() -> None:
    """JSON equality, not Python's: ``True == 1`` in Python, never in JSON. Without this a
    boolean would pass an enum or const of numbers, and ``"schemaVersion": true`` would
    read as version 1."""
    assert _errors(True, {"enum": [1]})
    assert _errors(1, {"enum": [True]})
    assert _errors(True, {"const": 1})
    assert _errors(1, {"const": 1}) == []
    assert _errors(1.0, {"const": 1}) == [], "1.0 and 1 are one JSON number"
    assert _errors([1], {"const": [True]})


def test_const_is_enforced() -> None:
    assert _errors("client", {"type": "string", "const": "client"}) == []
    errors = _errors("owner", {"type": "string", "const": "client"})
    assert errors and "'client'" in errors[0], "the message names the one allowed value"


def test_upper_bounds_are_enforced() -> None:
    assert _errors("abcd", {"type": "string", "maxLength": 3})
    assert _errors("abc", {"type": "string", "maxLength": 3}) == []
    assert _errors([1, 2], {"type": "array", "maxItems": 1})
    assert _errors([1], {"type": "array", "maxItems": 1}) == []


def test_unique_items_are_enforced() -> None:
    schema = {"type": "array", "uniqueItems": True}
    assert _errors(["a", "b", "a"], schema)
    assert _errors(["a", "b"], schema) == []
    assert _errors([1, True], schema) == [], "a boolean and a number are different items"


def test_numbers_and_their_bounds_are_enforced() -> None:
    schema = {"type": "number", "exclusiveMinimum": 0}
    assert _errors(0.5, schema) == []
    assert _errors(2, schema) == [], "an integer is a number"
    assert _errors(0, schema), "exclusiveMinimum excludes the bound itself"
    assert _errors(-1.5, schema)
    assert _errors(True, schema), "bool must not pass as a number"
    assert _errors("0.5", schema)


def test_dependent_required_is_enforced() -> None:
    schema = {"type": "object", "dependentRequired": {"kind": ["version"]}}
    assert _errors({"kind": "x"}, schema)
    assert _errors({"kind": "x", "version": "1"}, schema) == []
    assert _errors({}, schema) == [], "the dependency binds only when its key is present"


def test_pattern_properties_admit_keys_that_additional_properties_refuses() -> None:
    schema = {
        "type": "object",
        "additionalProperties": False,
        "properties": {"id": {"type": "string"}},
        "patternProperties": {"^\\$": {"type": "string"}},
    }
    assert _errors({"id": "x", "$comment": "note"}, schema) == []
    assert _errors({"$comment": 1}, schema), "a matched key's value is still validated"
    errors = _errors({"id": "x", "extra": 1}, schema)
    assert errors and "allowed: id" in errors[0], (
        f"an unknown field names the fields that are allowed: {errors}"
    )


def test_if_then_else_applies_one_branch() -> None:
    schema = {
        "type": "object",
        "if": {"required": ["unmanaged"]},
        "then": {"required": ["reason"]},
        "else": {"required": ["units"]},
    }
    assert _errors({"unmanaged": True, "reason": "x"}, schema) == []
    assert _errors({"unmanaged": True}, schema), "then binds when if holds"
    assert _errors({"units": []}, schema) == []
    assert _errors({}, schema), "else binds when if does not"


def test_keywords_apply_by_the_instance_type_without_a_declared_type() -> None:
    """A subschema need not repeat ``type`` for its keywords to bind. An earlier form of
    this validator applied ``required`` only under ``"type": "object"``, so every ``if``
    written the ordinary way held for every instance and its ``then`` applied to all."""
    assert _errors({}, {"required": ["id"]}), "required binds on an object with no type"
    assert _errors({"a": 1}, {"properties": {"a": {"type": "string"}}})
    assert _errors("", {"minLength": 1})
    assert _errors([1, 1], {"uniqueItems": True})
    assert _errors("x", {"required": ["id"]}) == [], "object keywords ignore a non-object"


def test_annotations_are_not_constraints() -> None:
    schema = {"type": "string", "default": "one", "$defs": {"x": {"enum": ["y"]}}}
    assert _errors("anything", schema) == [], "$defs and default validate nothing"


def test_nested_errors_carry_their_path() -> None:
    schema = {
        "type": "object",
        "properties": {"items": {"type": "array", "items": {"type": "string"}}},
    }
    errors = _errors({"items": ["ok", 3]}, schema)
    assert errors and "root.items[1]" in errors[0], (
        f"a nested violation must name its path: {errors}"
    )
