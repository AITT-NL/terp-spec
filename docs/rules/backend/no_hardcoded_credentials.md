# `backend/no_hardcoded_credentials`

**App modules do not hard-code credentials or recognizable secret tokens**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_hardcoded_credentials.json`.

## Why this rule exists

A credential-shaped assignment to a non-empty string literal is almost always a secret that should come from sealed config / environment wiring, not source. The rule also rejects common high-confidence secret literal formats anywhere in a module so leaked keys are caught even when assigned to a bland variable name. As a security rule this also scans test and migration files inside a module — a real secret is a leak wherever it is committed. One shape is exempt: an enum member whose literal is its own name (SECRET_REFERENCE = "secret_reference") is vocabulary, not secret material.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-no-hardcoded-credentials: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `terp.arch` — `check_no_hardcoded_credentials`
