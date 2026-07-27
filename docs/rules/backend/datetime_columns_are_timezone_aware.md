# `backend/datetime_columns_are_timezone_aware`

**Stored timestamp columns must keep their timezone**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/datetime_columns_are_timezone_aware.json`.

## Why this rule exists

A timestamp column declared without an explicit timezone maps to a naive database type, which discards the zone of even a correctly-built aware value on the way in — so the moment the row records is ambiguous, and ordering or comparison across zones is silently wrong on read. This is the storage half of the hole whose in-memory half the naive-timestamp rule closes: capturing an aware value is worth nothing if the column cannot keep it. Every persisted timestamp column must declare timezone-aware storage.

## What to do instead

On a table model, a datetime (or datetime | None) field is refused unless its declaration pins a timezone-aware column type — Field(sa_type=DateTime(timezone=True)) or Field(sa_column=Column(DateTime(timezone=True), ...)); the TIMESTAMP spelling and a qualified name (sa.DateTime) count equally. A bare annotation, a Field() that never names the column type, and an explicit timezone=False are all naive storage. Fields a table inherits from a mixin declared in the same file are in scope, since the column lands on the table either way. Classes no table inherits (DTOs, unrelated payloads) declare no columns and are out of scope. (reference stack; another stack ships its own realisation.)

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-datetime-columns-are-timezone-aware: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Not yet — a runtime control is planned; the gap is explicit and tracked.
- `build-time`: `terp.arch` — `check_datetime_columns_are_timezone_aware`
