# `backend/session_imported_from_sqlmodel`

**The ORM session type is imported from the framework's canonical source, never the underlying library**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/session_imported_from_sqlmodel.json`.

## Why this rule exists

The framework standardises on one session type everywhere — the injected request session, the service layer, the write guard, and the migrations all speak the same type, re-exported from one canonical source. Importing the session type from the underlying ORM library instead quietly forks the app onto a second session type, so the rule names the one canonical import. (Constructing a session is separately banned by no_raw_session_construction — this only fixes the spelling.)

## What to do instead

from sqlmodel import Session is canonical (SQLModel re-exports SQLAlchemy's); imports from sqlalchemy / sqlalchemy.orm are refused. (reference stack; another stack ships its own realisation.)

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
