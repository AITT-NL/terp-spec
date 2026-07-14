# `backend/no_raw_session_construction`

**App code never constructs a ``Session`` / engine directly; it uses ``SessionDep``**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_raw_session_construction.json`.

## Why this rule exists

App code never constructs a ``Session`` / engine directly; it uses ``SessionDep``

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-no-raw-session-construction: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `terp.arch` — `check_no_raw_session_construction`
