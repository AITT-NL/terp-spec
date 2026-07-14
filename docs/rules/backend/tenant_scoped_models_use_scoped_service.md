# `backend/tenant_scoped_models_use_scoped_service`

**A ``TenantScopedMixin`` model's service must extend ``TenantScopedService``**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/tenant_scoped_models_use_scoped_service.json`.

## Why this rule exists

This makes tenant isolation structural on the **write** side: reads of a tenant-scoped model are already filtered centrally by the registered tenant scope predicate (ADR 0017), but ``TenantScopedService`` is what stamps ``tenant_id`` on create — so a plain ``BaseService`` (which would insert an unstamped, never-visible row) is rejected at build time.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-tenant-scoped-models-use-scoped-service: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `terp.arch` — `check_tenant_scoped_models_use_scoped_service`
