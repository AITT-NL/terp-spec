# `backend/response_model_not_table_model`

**A route's ``response_model`` is a read DTO, never a ``table=True`` ORM model**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/response_model_not_table_model.json`.

## Why this rule exists

:func:`check_routes_declare_response_model` proves a model is *declared*; this rule proves it is not the persisted table itself. A ``response_model`` set to a ``table=True`` model -- directly or wrapped in ``Page[...]`` / ``list[...]`` -- serializes the ORM row, so a column such as ``hashed_password`` leaks straight through the boundary (the ``Page[User]`` footgun). Return a ``*Read`` schema (:class:`terp.core.BaseSchema`) listing exactly the safe fields instead.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-response-model-not-table-model: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Yes — the framework also enforces this while the app runs (fail closed).
- `build-time`: `terp.arch` — `check_response_model_not_table_model`
- `runtime`: `terp.core` — `_validate_router_response_models`
