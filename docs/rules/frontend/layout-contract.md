# `frontend/layout-contract`

**An opted-in app's archetype body slots accept only the contract's components**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/frontend/layout-contract.json`.

## Why this rule exists

With a checked-in layout-contract.json, each page archetype's body slot is constrained to the contract's sanctioned components (ADR 0079), so screens stay structurally consistent and the failure message tells an agent exactly how to build the screen. Paired with the fail-closed runtime DOM check in @terp/react-core.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
// terp-allow-layout-contract: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Yes — the framework also enforces this while the app runs (fail closed).
- `build-time`: `@terp/eslint-boundaries` — `terp/layout-contract`
- `runtime`: `@terp/react-core` — `verifySlotChildren`
