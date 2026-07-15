# `backend/no_dynamic_sql`

**Raw SQL text in app modules must be a static literal, never dynamically built**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_dynamic_sql.json`.

## Why this rule exists

A raw-SQL construct built dynamically — through interpolation, concatenation, format calls, or a variable — is not statically reviewable and is easy to turn into SQL injection. Keep SQL as a literal and pass data through bound parameters / the query builder's typed expressions instead. As a security rule this also scans test and migration files inside a module — they are importable code, so they are application surface too.

## What to do instead

text(...) / sqlalchemy.text(...) with an f-string, concatenation, .format, % formatting, or a variable is refused; SQLAlchemy bound parameters / ORM expressions are the compliant path. (reference stack; another stack ships its own realisation.)

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
