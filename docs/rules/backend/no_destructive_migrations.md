# `backend/no_destructive_migrations`

**Destructive migration operations require a reason-bearing marker**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_destructive_migrations.json`.

## Why this rule exists

``drop_table(...)``, ``drop_column(...)``, type-changing ``alter_column(..., type_=...)`` (on ``op``, a batch block, or any alias), and ``execute(...)`` of a statement containing ``DROP TABLE`` / ``DROP COLUMN`` / ``TRUNCATE`` / ``DELETE FROM`` / ``ALTER TABLE ... DROP`` in ``upgrade()`` can destroy data or make rollback unsafe. A revision may still perform one, but only when the file carries ``# terp-allow-destructive-migration: <reason>`` so the risk is explicit, reviewable, and greppable.

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
