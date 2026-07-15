# `backend/no_manual_scope_filtering`

**Modules never touch the framework-managed scope columns**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_manual_scope_filtering.json`.

## Why this rule exists

Soft-delete and tenant scoping are applied centrally: the composed base read query filters out soft-deleted rows and applies every registered row predicate (e.g. the tenant filter), and the audited delete chokepoint stamps the deletion. A module that references deleted_at / tenant_id — to filter, set, or compare — is re-implementing that scope predicate by hand, which can leak or destroy scoped rows. The composed scoped read is the only path; expose the column in a read DTO if you must surface it, but never filter or assign it in module code.

## What to do instead

BaseService.base_query composes the scope (deleted_at IS NULL + registered predicates); deleted_at / tenant_id attribute access in module code is refused. (reference stack; another stack ships its own realisation.)

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
