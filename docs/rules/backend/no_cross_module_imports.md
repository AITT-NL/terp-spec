# `backend/no_cross_module_imports`

**A module never imports a sibling module (leaf domains stay independent)**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_cross_module_imports.json`.

## Why this rule exists

Modules couple only through the platform surface and their own files — a sibling import creates hidden coupling that breaks module isolation and independent evolution. Both absolute and relative sibling imports are caught: a relative import is resolved to its absolute module first, so renaming the import style does not re-couple two leaf modules.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-no-cross-module-imports: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `terp.arch` — `check_no_cross_module_imports`
