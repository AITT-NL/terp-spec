# `backend/mutations_emit_audit`

**Modules never write to the session directly; mutations go through the audited chokepoint**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/mutations_emit_audit.json`.

## Why this rule exists

Audit is auto-emitted from the single ``BaseService`` ``create`` / ``update`` / ``delete`` (``_save`` / ``_remove``) chokepoint inside the write's transaction. A module that calls ``session.add`` / ``delete`` / ``merge`` / ``commit`` / ``flush`` / a ``bulk_*`` helper itself — or smuggles a write through ``session.execute`` / ``exec`` with a DML statement (``insert`` / ``update`` / ``delete`` / raw ``text``) — bypasses that chokepoint and would persist a mutation with **no** audit trail. The receiver is recognised by the conventional session names **and** by any parameter annotated ``Session`` / ``SessionDep`` (so renaming the variable does not evade the rule). Routing every write through ``BaseService`` keeps the trail structural — a method call on the model's service (e.g. ``_service.delete(...)``) is fine; a raw ``session.*`` write is not.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-mutations-emit-audit: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Yes — the framework also enforces this while the app runs (fail closed).
- `build-time`: `terp.arch` — `check_mutations_emit_audit`
- `runtime`: `terp.core` — `WriteGuardedSession`
