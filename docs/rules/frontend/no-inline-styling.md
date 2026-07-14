# `frontend/no-inline-styling`

**style and className attributes are refused in app modules**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/frontend/no-inline-styling.json`.

## Why this rule exists

A style or className attribute is a side channel into hand-authored CSS that drifts per screen; styling flows from the app's design tokens and sanctioned layout primitives only. The refused attributes are declared in restricted-surface.json (restrictedAttributes).

## What to do instead

Layout via Stack, DetailList and the page archetypes from @terp/react-core; theming via the app's token source. (reference stack; another stack ships its own realisation.)

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
// terp-allow-no-restricted-syntax: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `@terp/eslint-boundaries` — `BOUNDARY_SPEC.restrictedAttributes`
