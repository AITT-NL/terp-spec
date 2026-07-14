# `backend/tables_have_migrations`

**Every app module that defines a table model ships a packaged migration history**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/tables_have_migrations.json`.

## Why this rule exists

A deployed Terp app builds its schema from packaged migrations, not ``create_all`` (the production boot guard ``assert_migrations_current`` applies them) — so an ``app/modules/<name>`` that declares a ``table=True`` model but has no ``migrations/versions/`` revision would deploy with that table **missing**: the boot guard checks only *declared* histories, so it never notices, and the first request 500s on a nonexistent table. This rule fails the build instead, the build-time complement to the runtime boot guard (the two halves of the migration control). Run ``terp migrate make <name>`` and commit the generated revision.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-tables-have-migrations: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Not yet — a runtime control is planned; the gap is explicit and tracked.
- `build-time`: `terp.arch` — `check_tables_have_migrations`
