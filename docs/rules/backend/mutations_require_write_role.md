# `backend/mutations_require_write_role`

**A module with a mutating route must not gate writes below its read tier**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/mutations_require_write_role.json`.

## Why this rule exists

A module that exposes ``POST`` / ``PUT`` / ``PATCH`` / ``DELETE`` is a write surface, so its ``Policy`` must gate writes **at or above** the read tier — otherwise anyone who can read can also mutate (privilege inversion). Two shapes are caught statically: the write tier set to the read floor ``VIEWER`` (``Policy(write=Roles.VIEWER)`` / ``Policy.tiers(write=…)``), and a default-ladder inversion where the write rank is below the read rank (``Policy(read=Roles.ADMIN, write=Roles.EDITOR)``, or ``Policy(read=Roles.ADMIN)`` where write defaults to the lower ``EDITOR``). ``Policy.default()`` (read=VIEWER, write=EDITOR) is the safe default; ``ADMIN`` is fine. A *custom* role ladder's ranks are not knowable from a source scan, so those are enforced by the boot-time check (``create_app`` -> ``_validate_policy_write_tiers``) — this rule is the early-warning build-time half. A public module is governed by ``public_modules_are_read_only`` instead. The check is tied to the policy bound to the module's ``ModuleSpec(policy=…)``.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-mutations-require-write-role: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Yes — the framework also enforces this while the app runs (fail closed).
- `build-time`: `terp.arch` — `check_mutations_require_write_role`
- `runtime`: `terp.core` — `build_guard`
- `runtime`: `terp.core` — `_validate_policy_write_tiers`
