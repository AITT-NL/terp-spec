# `backend/routes_declare_response_model`

**Every content route declares ``response_model=`` (no bare ORM/data out)**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/routes_declare_response_model.json`.

## Why this rule exists

Covers both decorator routes (``@router.get(...)``) and imperative registration (``router.add_api_route(...)``): a route with neither a ``response_model`` nor a no-body ``status_code`` (204/205/304) can serialize a bare ORM object out of the boundary, so both forms are checked.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-routes-declare-response-model: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Yes — the framework also enforces this while the app runs (fail closed).
- `build-time`: `terp.arch` — `check_routes_declare_response_model`
- `runtime`: `terp.core` — `_validate_routes_declare_response_model`
