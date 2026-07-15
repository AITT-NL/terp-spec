# `backend/routes_declare_response_model`

**Every content route declares its response type (no bare data out)**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/routes_declare_response_model.json`.

## Why this rule exists

A route with neither a declared response type nor a no-body status code can serialize a bare stored object out of the boundary — whatever the handler happens to return, including columns that were never meant to leave the app. Declaring the response type makes the boundary shape explicit and reviewable; both decorator routes and imperative route registration are checked.

## What to do instead

response_model= on @router.<verb>(...) decorators and router.add_api_route(...); a no-body status_code (204/205/304) is the accepted alternative. (reference stack; another stack ships its own realisation.)

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-routes-declare-response-model: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Not yet — a runtime control is planned; the gap is explicit and tracked.
- `build-time`: `terp.arch` — `check_routes_declare_response_model`
