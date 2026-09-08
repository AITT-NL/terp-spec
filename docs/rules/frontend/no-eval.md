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

## What the check is not required to catch

A check precise enough to have no false positives has limits. The spec
records this rule's limits as data (`corpus/RESIDUALS.json`) so two
independent checkers agree on where detection ends instead of each
guessing:

- `Function("...")` called without `new` is not required
- a computed global (`window["eval"]`) is not required to be recognised

**These are not exemptions.** The rule governs those forms exactly as it
governs any other — a checker is simply not required to find them, so
review is the control there. The list only shrinks: closing one means
adding the corpus case that contracts it.

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `@terpjs/eslint-boundaries` — `terp/no-eval`
