# `backend/no_raw_outbound_http`

**App modules do not import raw HTTP clients; outbound calls use a capability**

> Generated from the catalog by `tools/generate_rule_docs.py` — do not
> edit by hand; the parity test holds this page to
> `catalog/backend/no_raw_outbound_http.json`.

## Why this rule exists

Direct ``httpx`` / ``requests`` / ``urllib.request`` / ``urllib3`` / ``aiohttp`` imports — and the lower-level ``socket`` / ``http.client`` escape routes to the same network — make SSRF protection, allowlists, egress auditing, and timeout policy a per-call-site choice. Outbound traffic belongs behind a declared capability that centralizes those controls. As a security rule this also scans ``tests/`` and ``migrations/`` dirs inside a module — they are importable Python, so they are application surface too.

## If you really need an exception

Add a justified marker on (or immediately above) the line, and record it
in your app's escape-hatch budget:

```
# arch-allow-no-raw-outbound-http: <reason>
```

An unjustified marker is itself a violation, and marker counts must
exactly match the checked-in budget (which can only shrink).

## Enforcement

- Checked while the app runs? No — this is a property of the written source only; the build-time check is the control, by recorded decision.
- `build-time`: `terp.arch` — `check_no_raw_outbound_http`
