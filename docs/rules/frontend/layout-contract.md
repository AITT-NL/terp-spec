# `frontend/layout-contract`

**An opted-in app's archetype body slots accept only the contract's components**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/frontend/layout-contract.json`.

## Why this rule exists

With a checked-in layout declaration, each page archetype's body slot is constrained to the contract's sanctioned components, so screens stay structurally consistent and the failure message tells an agent exactly how to build the screen. Paired with the fail-closed runtime check on the rendered slot. The declaration is the single source for the opt-in and for the shell's own shape (layout-declaration.schema.json): a build-time checker and the running app read the same document, so neither can enforce a contract the other does not, and a key declared both in the document and in the app's own code is refused rather than resolved by an invisible precedence.

## What to do instead

frontend/layout-contract.json, the document layout-declaration.schema.json describes (ADR 0079); the app imports it and the reference stack's bootstrap resolves it, refusing an unknown key, a value outside its enum, and any key declared twice. verifySlotChildren in @terpjs/react-core is the runtime DOM check. (reference stack; another stack ships its own realisation.)

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
- `build-time`: `@terpjs/eslint-boundaries` — `terp/layout-contract`
- `runtime`: `@terpjs/react-core` — `verifySlotChildren`
