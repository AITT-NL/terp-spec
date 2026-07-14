# `backend/no_raw_app_routes`

**App code never registers HTTP surface on the composed app object**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_raw_app_routes.json`.

## Why this rule exists

``terp.core.create_app`` mounts every module router behind the deny-by-default policy guard. Surface registered on the composed app itself — ``app.mount(...)``, ``app.include_router(...)``, ``app.add_route(...)``, a verb decorator on a ``create_app``-produced app, or a lifecycle hook (``app.on_event`` / ``app.add_event_handler``) — is served or executed WITHOUT that guard and is invisible to the module permission model. Modules declare one flat router on their ``ModuleSpec``; composition mounts it.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-no-raw-app-routes: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Yes — the framework also enforces this while the app runs (fail closed).
- `build-time`: `terp.arch` — `check_no_raw_app_routes`
- `runtime`: `terp.core` — `_freeze_app_route_registration`
