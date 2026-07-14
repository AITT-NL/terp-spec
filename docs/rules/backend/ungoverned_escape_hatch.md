# `backend/ungoverned_escape_hatch`

**The fail-closed ungoverned-opt-out condition, as structured violations**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/ungoverned_escape_hatch.json`.

## Why this rule exists

:func:`assert_app_clean` refuses (with a plain ``AssertionError``) to honour any ``# arch-allow-*`` marker when no escape-hatch budget governs it. This is the same condition projected as :class:`ArchViolation` values (rule ``ungoverned_escape_hatch``, one per marker line), so a structured renderer (``terp check --format json``) reports it in-band instead of crashing.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-ungoverned-escape-hatch: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `terp.arch` — `ungoverned_marker_violations`
