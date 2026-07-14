# `backend/no_manual_table_schema`

**Table models never hand-write a ``schema=`` placement (the layout is managed)**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_manual_table_schema.json`.

## Why this rule exists

The physical schema layout is a **deployment** decision (``DB_SCHEMA_LAYOUT``, ADR 0070): under ``flat`` every table lives in the default schema, and under ``per-module`` the migration runtime routes each package's tables into its own PostgreSQL schema via the search_path — in both layouts the model metadata stays schema-free. A hand-written ``__table_args__ = {"schema": ...}`` pins one table to a fixed schema, silently escaping the managed layout (and breaking SQLite dev/test, which parses a schema prefix as an ATTACH database name).

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-no-manual-table-schema: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `terp.arch` — `check_no_manual_table_schema`
