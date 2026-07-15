# `backend/no_manual_ownership_checks`

**Modules never gate a row write on the framework-managed owner column by hand**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_manual_ownership_checks.json`.

## Why this rule exists

Object-level authorization is applied centrally: the framework stamps owner_id from the request actor on create and authorizes every update / delete of an owned row at the write chokepoint (a non-owner write fails closed with 403). A module that references owner_id — to compare it against a principal, filter on it, or set it — is hand-rolling that per-row check, the easy-to-get-wrong pattern the seam replaces (it leaks if forgotten, and a hand-written ownership filter also drops the soft-delete / tenant row scope). Declare the ownership trait on the model and let the framework gate the write; register an object-authorization predicate for a richer policy. As with the scope / actor columns, a read DTO may still expose owner_id (an annotation is fine); only attribute access (set / filter / compare) is policed.

## What to do instead

OwnedMixin declares ownership; BaseService stamps owner_id and apply_object_authz gates writes (ADR 0029); a custom object-authz predicate can be registered. (reference stack; another stack ships its own realisation.)

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
