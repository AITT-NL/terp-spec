# `backend/public_modules_are_read_only`

**A public (unauthenticated) module must not expose a mutating route**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/public_modules_are_read_only.json`.

## Why this rule exists

``Policy.public(reason=…)`` drops authentication for the **whole** module, so a ``POST`` / ``PUT`` / ``PATCH`` / ``DELETE`` under it is an *unauthenticated write* — almost always an accident (applying ``Policy.public`` to a module that also has writes), and the broken-access-control footgun the deny-by-default posture exists to prevent. A genuinely public write (a sign-up / contact form / webhook receiver) is rare and deliberate, so it stays available through the governed escape hatch: a justified ``# arch-allow-public-modules-are-read-only: <reason>`` marker (ratcheted by the escape-hatch budget), making the unauthenticated write **visible and budgeted** rather than silent. Gate the writes behind a Policy with a write role, or justify the public write explicitly. The runtime half is the boot refusal: ``create_app`` -> ``_validate_public_modules_read_only`` refuses a public module that exposes a mutating route unless the policy opts in explicitly via ``Policy.public_write(reason=…)`` — each layer carries its own justified opt-out.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-public-modules-are-read-only: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Yes — the framework also enforces this while the app runs (fail closed).
- `build-time`: `terp.arch` — `check_public_modules_are_read_only`
- `runtime`: `terp.core` — `_validate_public_modules_read_only`
