# `backend/reads_use_base_query`

**A scope-trait model is read through ``base_query``, never a raw ``select()``**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/reads_use_base_query.json`.

## Why this rule exists

A model that mixes :class:`~terp.core.SoftDeleteMixin` or ``TenantScopedMixin`` carries row scope (soft-delete / tenant). A bespoke read that issues ``select(<Model>)`` directly — instead of building on ``base_query()`` — drops that scope, leaking soft-deleted or cross-tenant rows (the F1 follow-up to ADR 0017: closing ``base_query`` to overrides did not close a *new* read method that never calls it). Build reads on ``base_query()`` / ``business_filters()``; the request session re-applies the scope to any single-entity ``select`` as the runtime backstop, and this rule is the build-time early warning. ``base_query`` itself — the one sanctioned ``select(model)`` — lives in the framework, not a module, so it is never scanned here.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-reads-use-base-query: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Yes — the framework also enforces this while the app runs (fail closed).
- `build-time`: `terp.arch` — `check_reads_use_base_query`
- `runtime`: `terp.core` — `apply_row_scope`
