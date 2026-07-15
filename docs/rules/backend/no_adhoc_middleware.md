# `backend/no_adhoc_middleware`

**App code never wires HTTP middleware itself; security is centralized**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_adhoc_middleware.json`.

## Why this rule exists

Cross-cutting HTTP security (headers, CORS, rate-limit, body-size, request-id) is declared once as central security configuration and installed at composition. A module that registers middleware itself — by call, decorator, or subclassing — is assembling a security posture outside that single control plane.

## What to do instead

SecurityConfig declared once and installed by create_app; add_middleware(...), the @app.middleware("http") decorator, and BaseHTTPMiddleware subclasses are refused in app modules. (reference stack; another stack ships its own realisation.)

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-no-adhoc-middleware: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Not yet — a runtime control is planned; the gap is explicit and tracked.
- `build-time`: `terp.arch` — `check_no_adhoc_middleware`
