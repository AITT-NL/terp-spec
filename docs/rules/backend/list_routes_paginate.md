# `backend/list_routes_paginate`

**A list route returns a capped ``Page[T]``, never a bare ``list[...]``**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/list_routes_paginate.json`.

## Why this rule exists

Pagination is a mandatory cross-cutting control (ADR 0006, Tier A): a route whose ``response_model`` is a bare ``list[...]`` / ``Sequence[...]`` serializes an **unbounded** collection -- a resource-exhaustion and over-exposure footgun on a large table, and a ``Page[T]`` guarantee that was previously only a convention. Wrap the Read DTO in ``terp.core.Page[...]`` (returned via ``Page.of(...)`` with ``PaginationDep``) so every list is capped and uniformly shaped. A single-object ``response_model`` (``NoteRead``) is unaffected; both decorator routes and imperative ``add_api_route`` registration are checked.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-list-routes-paginate: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Yes — the framework also enforces this while the app runs (fail closed).
- `build-time`: `terp.arch` — `check_list_routes_paginate`
- `black-box`: `@terp/conformance` — `standard: list routes return a capped Page envelope`
- `runtime`: `terp.core` — `_validate_list_routes_paginate`
