# `backend/no_app_instantiation`

**App code never constructs ``FastAPI()`` directly**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_app_instantiation.json`.

## Why this rule exists

``terp.core.create_app`` owns app composition (deny-by-default guards, the control plane, the error envelope). A hand-built ``FastAPI()`` is an application assembled outside the framework.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-no-app-instantiation: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `terp.arch` — `check_no_app_instantiation`
