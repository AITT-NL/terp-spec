# `backend/base_query_not_overridden`

**A service never overrides ``base_query`` — add read filters via ``business_filters``**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/base_query_not_overridden.json`.

## Why this rule exists

``BaseService.base_query`` composes the **non-droppable** row scope (soft-delete + every registered capability predicate, e.g. tenancy) with the service's ``business_filters``. Overriding it — the old, footgun-y seam — can silently drop soft-delete / tenant scoping the moment the override forgets ``super().base_query()``, leaking soft-deleted or cross-tenant rows. Add static conditions via ``business_filters()`` (you return conditions, not a query, so you cannot drop scope and need no ``super()``); a per-call filter belongs in a custom ``list`` that builds on ``base_query().where(...)`` (ADR 0017).

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-base-query-not-overridden: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Yes — the framework also enforces this while the app runs (fail closed).
- `build-time`: `terp.arch` — `check_base_query_not_overridden`
- `runtime`: `terp.core` — `apply_row_scope`
