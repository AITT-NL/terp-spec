# `frontend/escape-hatch`

**Every terp-allow marker is justified and governed by the budget ratchet**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/frontend/escape-hatch.json`.

## Why this rule exists

The one opt-out is a // terp-allow-<rule>: <reason> marker; an unjustified marker is itself an error, and marker counts must exactly match the app's checked-in escape-hatch-budget.json (ADR 0059) so opt-outs stay visible and can only shrink.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
// terp-allow-escape-hatch: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `@terp/eslint-boundaries` — `terp/escape-hatch`
