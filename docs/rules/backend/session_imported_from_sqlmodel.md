# `backend/session_imported_from_sqlmodel`

**The ORM ``Session`` is imported from ``sqlmodel``, never from ``sqlalchemy``**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/session_imported_from_sqlmodel.json`.

## Why this rule exists

SQLModel re-exports SQLAlchemy's ``Session``, and the framework standardises on that one everywhere — ``SessionDep``, ``BaseService``, the write guard, and the migrations all speak ``sqlmodel.Session``. Importing ``Session`` from ``sqlalchemy`` / ``sqlalchemy.orm`` quietly forks the app onto a second session type, so the rule names the one canonical import. (Constructing a session is separately banned by ``no_raw_session_construction`` — this only fixes the spelling.)

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-session-imported-from-sqlmodel: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `terp.arch` — `check_session_imported_from_sqlmodel`
