# `frontend/generated-client-only`

**All network egress goes through the generated, typed client**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/frontend/generated-client-only.json`.

## Why this rule exists

Raw fetch / XMLHttpRequest / WebSocket / EventSource (and navigator.sendBeacon) bypass the app's single audited, typed egress path. One client means one place for auth, errors, and contract types. The refused globals and member calls are declared in restricted-surface.json (restrictedGlobals, restrictedMemberCalls).

## What to do instead

useTerpClient() + unwrap from @terp/react-core — the generated, typed client. (reference stack; another stack ships its own realisation.)

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
// terp-allow-no-restricted-globals: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `@terp/eslint-boundaries` — `BOUNDARY_SPEC.restrictedGlobals`
