# `backend/no_adhoc_background_runtime`

**App modules don't import a background engine / runtime directly — only adapter caps do**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_adhoc_background_runtime.json`.

## Why this rule exists

Background work (a scheduled sync, an export, a webhook) goes through the typed :func:`terp.core.enqueue` chokepoint and the context-binding kernel runner, so the engine that actually runs it — Celery, Azure Service Bus, Redis, APScheduler — stays a composition-root choice wired into an **opt-in adapter capability**, never an import baked into domain code. This rule forbids importing those broker / scheduler engines (and a raw ``threading`` / ``multiprocessing`` *execution* construct — ``Thread`` / ``Process`` / a pool, or a bare ``import threading`` that can reach one) anywhere in an app module; an explicit synchronization primitive (``from threading import RLock``) is a correctness tool, not background execution, and stays allowed. Its runtime half is the jobs seam itself: every job runs through :func:`terp.core.enqueue` and the active :class:`~terp.core.JobQueue`, so an adapter swap never touches a call site. An adapter capability legitimately imports its engine under a budgeted ``# arch-allow-*`` marker.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-no-adhoc-background-runtime: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `terp.arch` — `check_no_adhoc_background_runtime`
