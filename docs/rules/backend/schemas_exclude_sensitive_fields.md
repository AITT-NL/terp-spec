# `backend/schemas_exclude_sensitive_fields`

**A read / response DTO never exposes a credential-shaped field**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/schemas_exclude_sensitive_fields.json`.

## Why this rule exists

Routes serialize a response DTO out of the boundary, so a field whose name reads like a secret -- ``password`` / ``hashed_password`` / ``*secret`` / ``*api_key`` / ``*token`` -- would leak the credential to every caller. A response DTO is a ``BaseSchema`` / ``BaseUpdateSchema`` model **or** any class wired as a ``response_model=`` (so an input ``*Create`` / ``*Update`` mistakenly reused as a response is caught), excluding the inputs that are only ever request bodies (a client *supplies* a password) and ``table=True`` models (a table may store the hash). Plain helper classes are not policed. This guards the gap ``response_model_not_table_model`` leaves: a hand-rolled Read model that copies the stored hash. (``token_version`` / ``version`` are integer counters, not secrets.)

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-schemas-exclude-sensitive-fields: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Not yet — a runtime control is planned; the gap is explicit and tracked.
- `build-time`: `terp.arch` — `check_schemas_exclude_sensitive_fields`
- `black-box`: `@terp/conformance` — `standard: responses never expose credential-shaped fields`
