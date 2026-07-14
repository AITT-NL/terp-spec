# `backend/table_models_use_base_table`

**Every ORM table model inherits ``BaseTable`` (no bare ``SQLModel`` tables)**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/table_models_use_base_table.json`.

## Why this rule exists

A ``table=True`` model that skips ``BaseTable`` bypasses the framework's UUID id, timestamps, and optimistic-concurrency ``version`` — a model living outside the control-plane contract.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-table-models-use-base-table: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `terp.arch` — `check_table_models_use_base_table`
