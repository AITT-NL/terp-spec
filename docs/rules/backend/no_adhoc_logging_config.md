# `backend/no_adhoc_logging_config`

**App code never configures logging globally; redaction is centralized**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_adhoc_logging_config.json`.

## Why this rule exists

Structured logging + PII redaction is installed once by ``configure_logging`` (called by ``create_app``). A module calling ``logging.basicConfig`` / ``dictConfig`` / ``fileConfig`` re-points logging and can silently bypass the central secret-redaction filter.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-no-adhoc-logging-config: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `terp.arch` — `check_no_adhoc_logging_config`
