# `frontend/no-untranslated-ui`

**Static user-facing text participates in localization**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/frontend/no-untranslated-ui.json`.

## Why this rule exists

Static user-facing text anywhere in app-authored frontend source must use the translation seam. Bare visible copy, accessibility labels, component text properties, labels stored in data, and standard toast feedback are otherwise absent from every translation catalog and silently remain in the source language.

## What to do instead

Use UiText descriptors and Trans from @terpjs/react-core throughout app-authored frontend source. (reference stack; another stack ships its own realisation.)

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
// terp-allow-no-untranslated-ui: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `@terpjs/eslint-boundaries` — `terp/no-untranslated-ui`
