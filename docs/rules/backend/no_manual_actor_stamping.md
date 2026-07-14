# `backend/no_manual_actor_stamping`

**Modules never set the framework-managed actor-stamp columns by hand**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_manual_actor_stamping.json`.

## Why this rule exists

Who created and last modified a row is **provenance**, applied **centrally**: ``BaseService._save`` fills ``created_by_id`` (on insert) and ``modified_by_id`` (on every write) from the request actor (:class:`~terp.core.ActorStampedMixin`, ADR 0012). A module that assigns ``<x>.created_by_id`` / ``<x>.modified_by_id`` is forging or clobbering that trail — the actor must come from the authenticated request, never from caller-supplied data. As with the scope columns, a read DTO may still *expose* the column (an annotation is fine); only attribute access (set / compare) is policed.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-no-manual-actor-stamping: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Yes — the framework also enforces this while the app runs (fail closed).
- `build-time`: `terp.arch` — `check_no_manual_actor_stamping`
- `runtime`: `terp.core` — `_save`
