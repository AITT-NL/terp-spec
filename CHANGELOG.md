# Changelog — the Terp Standard

The change history of the spec, keyed to `VERSION` (the semver of the
standard). Pre-1.0, a **changed contract** bumps the minor; purely additive
fields and new rules also bump the minor; prose bumps the patch (see
"Growing the spec" in the README). The top entry's version must equal the
checked-in `VERSION` — held by `tests/test_changelog.py`. A checker certified
against an earlier version reads this file to see exactly what changed since.

## 0.6.0

Additive contract growth (no existing field changed meaning):

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

## 0.5.0

- Mandatory `runtime` block on every catalog entry: the per-rule
  runtime-applicability classification (`required` / `not-applicable` /
  `deferred`) with rationale, held coherent by the spec suite.

## 0.4.x and earlier

- Initial extraction of the standard from the framework (ADRs 0080–0082):
  the rule catalog, the violation corpus with its `PENDING.json` ratchet,
  the finding format, the refused surface, and the two thin package
  manifests (`terp-spec` / `@terp/spec`) over one data set.
