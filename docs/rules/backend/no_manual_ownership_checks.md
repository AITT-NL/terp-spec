# `backend/no_manual_ownership_checks`

**Modules preserve structural row ownership and never reimplement it by hand**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_manual_ownership_checks.json`.

## Why this rule exists

Object-level authorization belongs to the platform's write boundary: user-owned rows retain their ownership declaration across request and background workflows, and a worker identity never becomes a blanket cross-owner authority. Application code must not compare, filter or assign the managed owner column, nor remove ownership merely to let unattended maintenance mutate every user's rows. Cross-owner maintenance requires a separately reviewed authority mechanism whose scope is explicit; ordinary background work remains subject to the same row ownership as interactive writes.

## What to do instead

OwnedMixin declares ownership; BaseService stamps owner_id and apply_object_authz gates writes. create_app refuses a job-bearing ModuleSpec whose declared service model omits OwnedMixin. A custom object-authz predicate can be registered. (reference stack; another stack ships its own realisation.)

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-no-manual-ownership-checks: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Yes — the framework also enforces this while the app runs (fail closed).
- `build-time`: `terp.arch` — `check_no_manual_ownership_checks`
- `runtime`: `terp.core` — `apply_object_authz`
- `runtime`: `terp.core` — `_validate_background_jobs_preserve_ownership`
