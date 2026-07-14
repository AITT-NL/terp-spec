# `backend/no_adhoc_config_decrypt`

**Sealed config is never decrypted ad hoc; one budgeted call site only**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_adhoc_config_decrypt.json`.

## Why this rule exists

A sealed configuration value (``enc:v1:...``) stays opaque in app code: a module renders ``mask_config`` and never calls ``decrypt_config``. The single sanctioned decrypt site (design §5.4) carries a justified ``# arch-allow-no-adhoc-config-decrypt`` marker counted against the app's escape-hatch budget. Its runtime half is :func:`terp.core.secrets.decrypt_config`, which fails closed unless called from the one site registered via ``register_decrypt_call_site``.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-no-adhoc-config-decrypt: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? Yes — the framework also enforces this while the app runs (fail closed).
- `build-time`: `terp.arch` — `check_no_adhoc_config_decrypt`
- `runtime`: `terp.core` — `decrypt_config`
