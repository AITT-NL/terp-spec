"""The JSON Schema subset every contract here is written in, and its one validator.

Deliberately minimal so the package stays dependency-free. Every schema-reading suite
imports ``_validate`` from here, and ``test_validator.py`` holds it to failing loudly
on a keyword it cannot honour rather than passing silently.
"""

from __future__ import annotations

import re


def _same(left: object, right: object) -> bool:
    """JSON equality, which is not Python equality: ``True`` is not ``1``.

    Python says ``True == 1`` and ``1 in [True]``, so an ``enum`` or ``const`` compared with
    ``==`` would accept a boolean where a schema version is required. JSON Schema compares
    by JSON value, where a boolean and a number are never equal.
    """
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    if type(left) is not type(right):
        return False
    if isinstance(left, list):
        return len(left) == len(right) and all(map(_same, left, right))
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(_same(left[k], right[k]) for k in left)
    return left == right


def _validate(instance: object, schema: dict, path: str) -> list[str]:
    """Validate *instance* against the JSON Schema subset the spec's schemas use.

    Deliberately minimal so the spec stays dependency-free: type / enum / const /
    pattern / minLength / maxLength / minimum / maximum / exclusiveMinimum / minItems / maxItems
    / uniqueItems / required / dependentRequired / properties / patternProperties /
    additionalProperties / items / if-then-else, with ``$defs`` and ``default`` read as
    annotations. An unknown constraint keyword fails loudly rather than passing
    silently. Every message names the field it is about and, where the schema states
    them, the values that field allows.

    A keyword applies by the type of the INSTANCE, as JSON Schema specifies, not by
    whether the schema also says ``type``: ``{"required": ["unmanaged"]}`` constrains an
    object although it names no type, which is the whole of how an ``if`` reads.
    """
    _KNOWN = {
        "$schema", "$id", "$defs", "title", "description", "default",  # annotations
        "type", "enum", "const", "pattern", "minLength", "maxLength", "minimum", "maximum",
        "exclusiveMinimum", "minItems", "maxItems", "uniqueItems", "required",
        "dependentRequired", "properties", "patternProperties", "additionalProperties",
        "items", "if", "then", "else",
    }
    errors = [f"{path}: unknown schema keyword {key!r}" for key in schema if key not in _KNOWN]
    if "enum" in schema and not any(_same(instance, value) for value in schema["enum"]):
        return errors + [f"{path}: {instance!r} not in {schema['enum']}"]
    if "const" in schema and not _same(instance, schema["const"]):
        return errors + [f"{path}: {instance!r} is not the allowed value {schema['const']!r}"]
    expected = schema.get("type")
    supported_types = {"object", "array", "string", "integer", "number", "boolean"}
    if expected is not None and (
        not isinstance(expected, str) or expected not in supported_types
    ):
        return errors + [f"{path}: unsupported schema type {expected!r}"]
    is_number = isinstance(instance, (int, float)) and not isinstance(instance, bool)
    matches = {
        "object": isinstance(instance, dict),
        "array": isinstance(instance, list),
        "string": isinstance(instance, str),
        "integer": isinstance(instance, int) and not isinstance(instance, bool),
        "number": is_number,
        "boolean": isinstance(instance, bool),
    }
    if expected is not None and not matches[expected]:
        return errors + [f"{path}: expected {expected}, got {type(instance).__name__}"]
    if isinstance(instance, dict):
        for field in schema.get("required", []):
            if field not in instance:
                errors.append(f"{path}: missing required field {field!r}")
        for field, needed in schema.get("dependentRequired", {}).items():
            if field in instance:
                errors.extend(
                    f"{path}: {field!r} requires {other!r}"
                    for other in needed
                    if other not in instance
                )
        properties = schema.get("properties", {})
        patterns = schema.get("patternProperties", {})
        if schema.get("additionalProperties") is False:
            allowed = ", ".join(sorted(properties)) or "none"
            if patterns:
                allowed += "; or a key matching " + " or ".join(
                    repr(pattern) for pattern in sorted(patterns)
                )
            errors.extend(
                f"{path}: unexpected field {key!r} (allowed: {allowed})"
                for key in instance
                if key not in properties
                and not any(re.search(pattern, key) for pattern in patterns)
            )
        for key, value in instance.items():
            if key in properties:
                errors.extend(_validate(value, properties[key], f"{path}.{key}"))
            for pattern, definition in patterns.items():
                if re.search(pattern, key):
                    errors.extend(_validate(value, definition, f"{path}.{key}"))
    elif isinstance(instance, list):
        if len(instance) < schema.get("minItems", 0):
            errors.append(f"{path}: fewer than {schema['minItems']} items")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{path}: more than {schema['maxItems']} items")
        if schema.get("uniqueItems") is True:
            errors.extend(
                f"{path}[{index}]: repeats an earlier item, {item!r} - items must be unique"
                for index, item in enumerate(instance)
                if any(_same(item, earlier) for earlier in instance[:index])
            )
        for index, item in enumerate(instance):
            errors.extend(_validate(item, schema.get("items", {}), f"{path}[{index}]"))
    elif isinstance(instance, str):
        if len(instance.strip()) < schema.get("minLength", 0):
            errors.append(f"{path}: shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append(f"{path}: longer than maxLength {schema['maxLength']}")
        if "pattern" in schema and re.search(schema["pattern"], instance) is None:
            errors.append(f"{path}: {instance!r} does not match {schema['pattern']!r}")
    elif is_number:
        if instance < schema.get("minimum", instance):
            errors.append(f"{path}: below minimum {schema['minimum']}")
        if instance > schema.get("maximum", instance):
            errors.append(f"{path}: above maximum {schema['maximum']}")
        if "exclusiveMinimum" in schema and instance <= schema["exclusiveMinimum"]:
            errors.append(f"{path}: must be above {schema['exclusiveMinimum']}")
    if "if" in schema:
        branch = "then" if not _validate(instance, schema["if"], path) else "else"
        if branch in schema:
            errors.extend(_validate(instance, schema[branch], path))
    return errors
