# `frontend/locale-catalogs-complete`

**Every declared target locale translates every authored message**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/frontend/locale-catalogs-complete.json`.

## Why this rule exists

Every stable user-interface message identifier must have a non-empty translation in every declared target locale. A missing or malformed catalog, empty entries, and undocumented source-language copies fail the gate instead of silently rendering source-language text after a user switches locale.

## What to do instead

Declare sourceLocale and locale message maps in frontend/i18n.json; the boundary rule and defineAppLocales validate that declaration, while LocaleProvider refuses missing target entries at render time. (reference stack; another stack ships its own realisation.)

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
// terp-allow-locale-catalogs-complete: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Yes — the framework also enforces this while the app runs (fail closed).
- `build-time`: `@terpjs/eslint-boundaries` — `terp/locale-catalogs-complete`
- `runtime`: `@terpjs/react-core` — `LocaleProvider`
