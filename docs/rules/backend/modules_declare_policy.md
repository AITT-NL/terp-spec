# `backend/modules_declare_policy`

**Every ``modules/<name>/module.py`` declares a ``ModuleSpec`` with a ``policy=``**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/modules_declare_policy.json`.

## Why this rule exists

Every ``modules/<name>/module.py`` declares a ``ModuleSpec`` with a ``policy=``

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-modules-declare-policy: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Yes — the framework also enforces this while the app runs (fail closed).
- `build-time`: `terp.arch` — `check_modules_declare_policy`
- `runtime`: `terp.core` — `build_guard`
