# `backend/no_raw_file_references`

**A table model's ``*file_id`` column is declared with ``FileRef(...)``, never bare**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_raw_file_references.json`.

## Why this rule exists

A stored pointer to a file object carries **authorization semantics**: the files capability serves delegated reads only through a *declared* reference (``FileService.load_for`` fail-closes on an undeclared column — the runtime half of this rule, ADR 0057). A bare ``file_id: uuid.UUID`` column on a ``table=True`` model is an undeclared reference: nothing ties the file's access to the referencing row, which is the classic object-level (BOLA) drift. Declare the column with ``FileRef(...)`` (from ``terp-cap-files``) so the reference is greppable, verified at runtime, and served through the module's own already-authorized row — never hand-rolled. A non-table schema (a Read DTO exposing ``file_id``) is fine and not policed; only the persisted column is.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-no-raw-file-references: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Yes — the framework also enforces this while the app runs (fail closed).
- `build-time`: `terp.arch` — `check_no_raw_file_references`
- `runtime`: `terp.capabilities.files` — `load_for`
