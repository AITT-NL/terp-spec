# `backend/list_routes_paginate`

**A list route returns a capped page envelope, never a bare unbounded collection**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/list_routes_paginate.json`.

## Why this rule exists

Pagination is a mandatory cross-cutting control: a route whose declared response type is a bare collection serializes an unbounded result — a resource-exhaustion and over-exposure footgun on a large table, and a page-envelope guarantee that was previously only a convention. Wrap the read DTO in the framework's capped page envelope so every list is bounded and uniformly shaped. A single-object response is unaffected; both decorator routes and imperative route registration are checked.

## What to do instead

response_model=Page[ReadDTO] returned via Page.of(...) with PaginationDep (ADR 0006, Tier A); bare list[...] / Sequence[...] response models are refused. (reference stack; another stack ships its own realisation.)

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-list-routes-paginate: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Not yet — a runtime control is planned; the gap is explicit and tracked.
- `build-time`: `terp.arch` — `check_list_routes_paginate`
- `black-box`: `@terp/conformance` — `standard: list routes return a capped Page envelope`
