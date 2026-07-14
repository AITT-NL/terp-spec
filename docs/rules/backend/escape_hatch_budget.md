# `backend/escape_hatch_budget`

**``# arch-allow-*`` marker counts must match the checked-in budget (a ratchet)**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/escape_hatch_budget.json`.

## Why this rule exists

The budget is a JSON object ``{marker: count}`` checked into the client repo. Actual usage must equal it **exactly**: a marker that *rose* needs a justified budget bump in the same change; one that *dropped* must be lowered to lock in the win; an unbudgeted marker must be added with a justified count. This keeps every secure-by-default opt-out visible, greppable, and governed (design §8).

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-escape-hatch-budget: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `terp.arch` — `check_escape_hatch_budget`
