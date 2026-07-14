# `backend/no_adhoc_permission_literals`

**Modules reference typed authority objects, never bare permission strings**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_adhoc_permission_literals.json`.

## Why this rule exists

Modules reference typed authority objects, never bare permission strings

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-no-adhoc-permission-literals: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Yes — the framework also enforces this while the app runs (fail closed).
- `build-time`: `terp.arch` — `check_no_adhoc_permission_literals`
- `runtime`: `terp.core` — `requirement_from`
