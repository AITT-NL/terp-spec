# `backend/no_raw_connection_access`

**Modules never reach the raw DB connection / engine behind the session**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_raw_connection_access.json`.

## Why this rule exists

The runtime write guard (ADR 0015) covers the request ``Session``'s own persistence methods, but the bound ``Engine`` / ``Connection`` it exposes can issue DML directly -- ``session.get_bind().connect().execute(insert(...))`` or ``session.connection().execute(...)`` -- bypassing the audited chokepoint (the F3 follow-up). A module must never call ``get_bind`` / ``connection``; persist through ``BaseService`` so every write is audited. A ``get_bind().connect()`` escape is already caught here at the ``get_bind`` call, and raw ``Session`` / engine *construction* (``create_engine`` / ``sessionmaker``) is separately banned by ``no_raw_session_construction`` -- so an unrelated ``.connect()`` on a domain object (a websocket / cache / search client) is deliberately *not* flagged.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-no-raw-connection-access: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Yes — the framework also enforces this while the app runs (fail closed).
- `build-time`: `terp.arch` — `check_no_raw_connection_access`
- `runtime`: `terp.core` — `WriteGuardedSession`
