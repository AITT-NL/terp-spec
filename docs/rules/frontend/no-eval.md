# `frontend/no-eval`

**eval() and new Function() are refused in app modules**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/frontend/no-eval.json`.

## Why this rule exists

Runtime code evaluation defeats every static guarantee the boundary provides and is a classic injection primitive. There is no sanctioned dynamic-code path in an app module.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
// terp-allow-no-eval: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `@terp/eslint-boundaries` — `terp/no-eval`
