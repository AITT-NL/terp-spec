# `backend/no_destructive_migrations`

**Destructive migration operations require a reason-bearing marker**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_destructive_migrations.json`.

## Why this rule exists

Dropping a table or column, changing a column's type, and executing raw destructive statements in an upgrade can destroy data or make rollback unsafe — whether spelled directly, on a batch block, through an alias, or smuggled into a raw statement. Each destructive operation is a violation; a reviewed one is justified through the standard governed escape hatch — a justified marker on (or immediately above) the operation, counted against the app's budget ratchet — so every accepted risk is explicit, reviewable, greppable, and ratcheted like any other opt-out.

## What to do instead

drop_table / drop_column / type-changing alter_column and execute(...) of DROP TABLE / DROP COLUMN / TRUNCATE / DELETE FROM / ALTER TABLE ... DROP in upgrade() are flagged per operation; the standard # arch-allow-no-destructive-migrations marker (budgeted) justifies a reviewed one. The pre-0.6.0 file-level terp-allow-destructive-migration waiver is retired. (reference stack; another stack ships its own realisation.)

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-no-destructive-migrations: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `terp.arch` — `check_no_destructive_migrations`
