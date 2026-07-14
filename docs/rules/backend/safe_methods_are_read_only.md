# `backend/safe_methods_are_read_only`

**A handler reachable via a safe HTTP method (``GET`` / ``HEAD`` / ``OPTIONS``) must not mutate**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/safe_methods_are_read_only.json`.

## Why this rule exists

The deny-by-default guard derives the required role tier from the **HTTP method**: a safe method is authorized against the policy's *read* requirement, a mutating one (``POST`` / ``PUT`` / ``PATCH`` / ``DELETE``) against the *write* requirement. So a handler reachable through a safe method that calls a mutating ``BaseService`` method (``create`` / ``update`` / ``delete`` / ``_save`` / ``_remove``) performs a write a *read-tier* caller cleared — a privilege-tier escape (a viewer triggering an editor/admin write via a ``GET``). This holds for a mixed-method route too (``["GET", "POST"]``): the ``GET`` invocation runs at the read tier, so a handler that always mutates is flagged (split it, or branch on the method behind a ``POST``). Both decorator and imperative ``add_api_route`` registration are checked. Put the write behind a ``POST`` / ``PUT`` / ``PATCH`` / ``DELETE`` route so it is authorized at the write tier. The runtime half (``create_app`` marks a safe-method request read-only, so the chokepoint refuses the write) is the paired control.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-safe-methods-are-read-only: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Yes — the framework also enforces this while the app runs (fail closed).
- `build-time`: `terp.arch` — `check_safe_methods_are_read_only`
- `runtime`: `terp.core` — `build_read_only_request_binder`
- `black-box`: `@terp/conformance` — `standard: safe methods observably mutate nothing`
