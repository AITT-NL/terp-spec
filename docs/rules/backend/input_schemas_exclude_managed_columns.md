# `backend/input_schemas_exclude_managed_columns`

**No input schema declares a framework-managed column**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/input_schemas_exclude_managed_columns.json`.

## Why this rule exists

An input schema is a ``*Create`` / ``*Update`` **or** any class used as a request body (a route handler's body parameter, or a ``build_crud_router`` create/update schema) -- the same role-based definition the input-cap rule uses, so an off-convention DTO (``UserProvision``, ``LoginRequest``) is covered too. ``BaseService.create`` / ``update`` copy a schema's fields onto the model, so a client-settable ``id`` / ``version`` / ``tenant_id`` / ``created_by_id`` is an over-posting (mass-assignment) hole -- a client could forge the primary key, defeat optimistic concurrency, or cross a tenant boundary. The framework assigns every managed column centrally; an input schema must never expose one. (``BaseService`` also strips the same set at runtime -- this rule is the build-time half of that two-layer control.)

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-input-schemas-exclude-managed-columns: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Yes — the framework also enforces this while the app runs (fail closed).
- `build-time`: `terp.arch` — `check_input_schemas_exclude_managed_columns`
- `runtime`: `terp.core` — `_without_managed_columns`
