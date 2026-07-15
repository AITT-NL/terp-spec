# Changelog — the Terp Standard

The change history of the spec, keyed to `VERSION` (the semver of the
standard). Pre-1.0, a **changed contract** bumps the minor; purely additive
fields and new rules also bump the minor; prose bumps the patch (see
"Growing the spec" in the README). The top entry's version must equal the
checked-in `VERSION` — held by `tests/test_changelog.py`. A checker certified
against an earlier version reads this file to see exactly what changed since.

## 0.7.0

Additive: the application check report joins the interoperability contract.

- **Check-report format**: new `app-check-report.schema.json` — the complete,
  self-describing result of one checker invocation over one application tree:
  a format marker (`terp_check_report: 1`), the spec version the rule ids
  resolve against, the checker's identity (the same identity the scorecard
  carries), the run verdict (`ok`, plus an explicit `error` for runs that
  failed to complete), the evaluated-rule inventory, the opt-in rules
  published as `not_applicable`, findings in exactly the finding format's
  shape (`fix_hint` / `fingerprint` included; the spec suite holds the
  embedded item shape identical to `findings.schema.json`), and
  `unattributed` messages surfaced rather than dropped. A consumer joins
  per-rule verdicts to the catalog exclusively through the report's own
  inventory — fail closed: a rule the run did not publish as evaluated can
  never render as passing.

## 0.6.0

One changed contract (the escape-hatch marker naming), otherwise additive
growth:

- **Escape-hatch contract**: a marker names the **catalog rule name** (the
  `<rule>` half of the id — never a tool-internal rule id, mirroring findings
  attribution), so a marker can never waive a sibling rule that shares a
  checker-internal id; the `opt_out` spelling is derived from the rule id and
  held by the spec suite. The escape-hatch **governance rules themselves**
  (`backend/escape_hatch_budget`, `backend/ungoverned_escape_hatch`,
  `frontend/escape-hatch`) now declare **no `opt_out`**: governance cannot be
  waived by the mechanism it governs. The uncatalogued
  `escape_hatch_requires_justification` finding id is retired — an unjustified
  marker reports as `backend/ungoverned_escape_hatch`.
- **Normative prose is stack-neutral, enforced**: `title` + `intent` are held
  free of reference-implementation vocabulary (framework symbols, docstring
  markup, marker spellings, repo-internal pointers) by the spec suite;
  reference realisation lives in `enforcement` / `reference` / `opt_out` /
  `guide_topic`.
- **Catalog**: new optional `restricted_surface` field — the structural half
  of a frontend prohibition rule's refused-surface citation (the spec suite
  now resolves the linkage through this field instead of parsing `intent`
  prose); new optional `runtime.tracking` field, **mandatory for
  `deferred`** — a deferral must name where it is tracked, so an explicit
  gap has a lifecycle.
- **Finding format**: new optional `fix_hint` (the compliant construct, for
  agent consumers) and `fingerprint` (a stable per-instance identifier)
  fields.
- **Expected-findings manifests**: a corpus case may ship an
  `expected-findings.json` at its root (shaped by `findings.schema.json`),
  hardening the per-case contract from "flags something" to "flags the right
  line" for harnesses that opt in; the loose contract remains the floor.
- **Residual ratchet**: the detector residuals deliberately outside the
  corpus contract moved from README prose into `corpus/RESIDUALS.json` —
  machine-readable, per rule, and shrink-only like `corpus/PENDING.json`.
- **Scorecard format**: new `scorecard.schema.json` — the machine-readable
  certification summary a conformant checker emits (spec version, per-rule
  verdicts, residuals claimed), making a certification claim verifiable.
- **Escape-hatch metadata convention**: a marker's reason may carry optional
  `owner:` / `ticket:` / `review-by:` tokens (see README) so long-lived
  exceptions stay visible and auditable; semantics of the marker are
  unchanged.
- **Corpus**: evasion-shape and near-miss coverage extended for the
  tenancy / authority rules (`no_manual_scope_filtering`,
  `no_manual_ownership_checks`, `no_manual_actor_stamping`,
  `mutations_require_write_role`, `reads_use_base_query`,
  `tenant_scoped_models_use_scoped_service`, `base_query_not_overridden`).
- **Docs**: generated plain-language rule pages under `docs/rules/`, held to
  the catalog by a parity test.
- **Deferral closures**: `routes_declare_response_model`,
  `schemas_exclude_sensitive_fields`, and `list_routes_paginate` move from
  `runtime.applicability: deferred` to `required` — the reference
  implementation ships fail-closed boot-time route-scan controls for all
  three on the composition seam (terp-framework commit `c19a01e`, ADR 0084:
  `_validate_routes_declare_response_model`,
  `_validate_schemas_exclude_sensitive_fields`,
  `_validate_list_routes_paginate`). No rule's meaning or corpus coverage
  changed, only its runtime classification.

## 0.5.0

- Mandatory `runtime` block on every catalog entry: the per-rule
  runtime-applicability classification (`required` / `not-applicable` /
  `deferred`) with rationale, held coherent by the spec suite.

## 0.4.x and earlier

- Initial extraction of the standard from the framework (ADRs 0080–0082):
  the rule catalog, the violation corpus with its `PENDING.json` ratchet,
  the finding format, the refused surface, and the two thin package
  manifests (`terp-spec` / `@terp/spec`) over one data set.
