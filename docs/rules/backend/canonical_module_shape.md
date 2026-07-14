# `backend/canonical_module_shape`

**Every wired ``modules/<name>`` dir carries ``models`` / ``schemas`` / ``service`` / ``router`` / ``module``**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/canonical_module_shape.json`.

## Why this rule exists

Terp modules are uniform on purpose: the table lives in ``models``, the DTOs in ``schemas``, the logic in ``service``, the routes in ``router``, and the manifest in ``module`` — so the shape is predictable to discover and the other rules (response models, input caps, audited writes, the declared ``Policy``) have the surface they scan. A directory under ``modules/`` is treated as a module once it ships a manifest (``module.py``) **or** a mounted ``router.py``; it must then carry **all** of the canonical files, and the rule names each missing one. Including ``module.py`` in the required set is deliberate: a dir that ships a router with no manifest would otherwise be invisible to this rule *and* to ``modules_declare_policy`` (which only scans ``module.py``), so it could mount a router with no declared Policy unnoticed. A dir with neither signal (a partial or a shared-asset / helper dir) is left alone.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-canonical-module-shape: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `terp.arch` — `check_canonical_module_shape`
