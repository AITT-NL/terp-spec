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
    assert _errors(1.5, {"type": "number"}), (
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


def test_nested_errors_carry_their_path() -> None:
    schema = {
        "type": "object",
        "properties": {"items": {"type": "array", "items": {"type": "string"}}},
    }
    errors = _errors({"items": ["ok", 3]}, schema)
    assert errors and "root.items[1]" in errors[0], (
        f"a nested violation must name its path: {errors}"
    )
