# `backend/no_dynamic_sql`

**Raw SQL text in app modules must be a static literal, never dynamically built**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_dynamic_sql.json`.

## Why this rule exists

Dynamic ``text(...)`` / ``sqlalchemy.text(...)`` calls (f-strings, string concatenation, ``.format``, ``%`` formatting, or a variable) are not statically reviewable and are easy to turn into SQL injection. Keep SQL as a literal and pass data through SQLAlchemy parameters / ORM expressions instead. As a security rule this also scans ``tests/`` and ``migrations/`` dirs inside a module — they are importable Python, so they are application surface too.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-no-dynamic-sql: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `terp.arch` — `check_no_dynamic_sql`
