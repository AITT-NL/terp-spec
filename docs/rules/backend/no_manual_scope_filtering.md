# `backend/no_manual_scope_filtering`

**Modules never touch framework-managed scope columns (``deleted_at`` / ``tenant_id``)**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_manual_scope_filtering.json`.

## Why this rule exists

Soft-delete and tenant scoping are applied **centrally**: ``BaseService.base_query`` filters ``deleted_at IS NULL`` for a soft-delete model and applies every registered row predicate (e.g. the tenant filter) for a scoped one, and the audited ``delete`` chokepoint stamps ``deleted_at``. A module that references ``<x>.deleted_at`` / ``<x>.tenant_id`` — to filter, set, or compare — is re-implementing that scope predicate by hand, which can leak or destroy scoped rows. The framework's ``base_query`` is the only path; expose the column in a read DTO if you must surface it, but never filter or assign it in module code.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-no-manual-scope-filtering: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Yes — the framework also enforces this while the app runs (fail closed).
- `build-time`: `terp.arch` — `check_no_manual_scope_filtering`
- `runtime`: `terp.core` — `apply_row_scope`
