# `backend/tables_have_migrations`

**Every app module that defines a table model ships a packaged migration history**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/tables_have_migrations.json`.

## Why this rule exists

A deployed Terp app builds its schema from packaged migrations, never from dev-time schema auto-creation (the production boot guard applies the packaged histories) — so a module that declares a table model but ships no migration revision would deploy with that table missing: the boot guard checks only declared histories, so it never notices, and the first request fails on a nonexistent table. This rule fails the build instead, the build-time complement to the runtime boot guard (the two halves of the migration control). Generate and commit the module's migration revision.

## What to do instead

terp migrate make <name> generates the module's migrations/versions/ revision; assert_migrations_current is the production boot guard, create_all the refused dev shortcut. (reference stack; another stack ships its own realisation.)

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
