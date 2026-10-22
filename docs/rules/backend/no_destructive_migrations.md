# `backend/no_destructive_migrations`

**Destructive migration steps require a reason-bearing marker**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_destructive_migrations.json`.

## Why this rule exists

A deploy migrates while the previous release still serves, and a rollback runs that release against the migrated schema, so an upgrade has two audiences its author's empty test database never shows: the rows production already holds, and the release still running. Five kinds of step fail one of them, whether spelled as a schema operation, on a batch block, through an alias, or smuggled into a raw statement. A drop (of a table or a column, or a statement that truncates or deletes rows) destroys data nothing brings back. A rename of a table or a column breaks the running release, which reads the old name. A type change can truncate or refuse existing values. Tightening an existing column to NOT NULL fails on the first row that holds NULL. And a constraint added to an existing table (unique, check, foreign key, primary key, a unique index, or the validation of one first added without checking the existing rows) fails on the first row that breaks it. Each such step is one finding, and its message says what to do instead: expand (add the new name or column beside the old one), backfill the rows outside the upgrade, and contract (drop, tighten or constrain) in a later release. The contract step is the destructive one; a reviewed one is justified through the standard governed escape hatch, a justified marker on (or immediately above) the operation, counted against the app's budget ratchet, so every accepted risk is explicit, reviewable, greppable, and ratcheted like any other opt-out. Two shapes meet no row that can break them and are not findings: a step on a table the same upgrade creates, and a unique, foreign-key or unique-index constraint on columns the same upgrade adds nullable with no default. Not being a finding does not make a step an expand step: whether the previous release keeps working after an upgrade is a separate question this rule does not answer.

## How the reference stack realises this

In upgrade(), on op, a batch_alter_table handle or any alias: drop_table / drop_column; rename_table and alter_column(new_column_name=...); alter_column(type_=...); alter_column(nullable=False) unless it restates existing_nullable=False or the table is created in the same upgrade(); create_unique_constraint / create_check_constraint / create_foreign_key / create_primary_key / create_exclude_constraint / create_index(unique=True) on a table that upgrade() does not create, a unique, foreign-key or unique-index constraint on columns that upgrade() adds nullable with no server_default excepted; and execute(...) / exec_driver_sql(...) of a statement written as a literal, an f-string or a + of strings, read one statement at a time: DROP TABLE / DROP COLUMN / TRUNCATE / DELETE FROM / ALTER TABLE ... DROP (DROP NOT NULL excepted), ALTER TABLE ... RENAME (a constraint rename excepted) / RENAME TABLE, ALTER COLUMN ... TYPE, SET NOT NULL, ADD [CONSTRAINT] UNIQUE / PRIMARY KEY / CHECK / FOREIGN KEY / EXCLUDE (a check or a foreign key added NOT VALID excepted), CREATE UNIQUE INDEX and VALIDATE CONSTRAINT. Each operation is one finding, with the message for its kind; the standard # arch-allow-no-destructive-migrations marker (budgeted) justifies a reviewed one. The pre-0.6.0 file-level terp-allow-destructive-migration waiver is retired. (reference stack; another stack ships its own realisation.)

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-no-destructive-migrations: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## What the check is not required to catch

A check precise enough to have no false positives has limits. The spec
records this rule's limits as data (`corpus/RESIDUALS.json`) so two
independent checkers agree on where detection ends instead of each
guessing:

- a statement the source does not spell out (a variable, a value a helper returns, a file read at run time) is not required to be read: only a statement written as a literal, an f-string or a concatenation of strings is
- a unique, foreign-key or unique-index constraint on a column the same upgrade adds nullable is not required to be reported when that upgrade fills the column before adding the constraint, which is the one order in which the existing rows can break it
- a constraint written inline in a raw column addition (`ADD COLUMN slug text UNIQUE DEFAULT 'x'`, `ADD COLUMN rank int NOT NULL`) is not required to be read as a step the existing rows can break

**These are not exemptions.** The rule governs those forms exactly as it
governs any other — a checker is simply not required to find them, so
review is the control there. The list only shrinks: closing one means
adding the corpus case that contracts it.

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `terp.arch` — `check_no_destructive_migrations`
