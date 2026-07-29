# Changelog — the Terp Standard

The change history of the spec, keyed to `VERSION` (the semver of the
standard). Pre-1.0, a **changed contract** bumps the minor; purely additive
fields and new rules also bump the minor; prose bumps the patch (see
"Growing the spec" in the README). The top entry's version must equal the
checked-in `VERSION` — held by `tests/test_changelog.py`. A checker certified
against an earlier version reads this file to see exactly what changed since.

## 0.17.0

One new backend rule. Everything else is byte-identical to 0.16.0, so a checker
certified against 0.16.0 stays certified on the invariants it already covers.

- **`backend/migration_history_is_intact`** — each migration history must be one
  unbroken chain from a single first revision. A revision whose declared parent
  names no revision in the same history, or a second revision declaring no
  parent at all, means an existing chain was edited rather than extended: every
  database that applied the removed revision becomes unupgradable, while the
  build stays green, because a database rebuilt from the rewritten history is
  perfectly consistent with the models. Classified `not-applicable` for the
  runtime half — chain integrity is a property of the authored files. The
  complementary live-database invariant (an applied revision the code no longer
  defines) is a different check on a different input and is not claimed here.

Migration for a checker: implement the new rule, or report it unimplemented.

## 0.16.0

Reference metadata only — every rule's title, intent and normative prose is
byte-identical to 0.15.0, so a checker certified against 0.15.0 stays certified
on the invariants. What changes is the name each rule's enforcing tool is
recorded under.

- **The catalog's `enforcement[].tool` ids move to the published scope.** The
  17 entries naming `@terp/eslint-boundaries`, `@terp/conformance` and
  `@terp/react-core` now name `@terpjs/*` — the scope the reference
  implementation's packages actually publish under (0.15.0 moved the spec's own
  npm package there). The same rename lands in the non-normative `reference`
  fields, the frontend corpus fixtures' import specifiers, and the generated
  rule pages.

Migration for a checker that attributes findings by tool id: read the new ids.
A checker that only matches catalog rule ids needs no change.

## 0.15.0

A distribution change only — the catalog, corpus, schemas and refused surface
are byte-identical to 0.14.0, so a checker certified against 0.14.0 stays
certified. What changes is how the standard is obtained.

- **The standard is published** (ADR 0086). `terp-spec` goes to PyPI and the npm
  package to the registry, both from the tag workflow via Trusted Publishing
  (OIDC), gated on certification against the reference implementation and bound
  to the verified commit. Consumers pin a **version** instead of a git tag; the
  tag pin keeps working for anyone who prefers it.
- **The npm package is renamed `@terp/spec` → `@terpjs/spec`.** The `@terp`
  scope is not ours; the reference implementation's packages already publish
  under `@terpjs/*` and the spec joins them. Only the manifest name changes —
  the data, the layout and the resolution idiom are untouched
  (`require.resolve("@terpjs/spec/package.json")`).

Migration for a JavaScript consumer: replace the `@terp/spec` dependency with
`@terpjs/spec` at this version and update the resolve specifier. Python
consumers replace the git pin with `terp-spec>=0.15`; the import path
(`terp_spec.spec_dir()`) is unchanged.

## 0.14.0

One additive backend rule closing the storage half of an invariant the standard
already covered in memory — no existing contract changes, so a checker certified
against 0.13.0 stays valid and simply gains coverage.

- `backend/datetime_columns_are_timezone_aware` — a stored timestamp column must
  keep its timezone. `backend/no_naive_datetime` keeps the zone on the value
  while it is in memory, but a column declared without an explicit timezone maps
  to a naive database type and discards that zone on the way in, leaving the
  stored moment ambiguous and any ordering or comparison across zones silently
  wrong. Columns a table inherits from a mixin count as the table's own.

This is the standard's first `deferred` runtime classification (ADR 0084). The
in-memory rule is honestly `not-applicable` — the zone is already gone by the
time a value reaches any runtime seam. This one is not: the mapped column type
is inspectable on the ORM metadata a framework collects at boot, so a
fail-closed boot check would add independent fidelity, and the entry's
`runtime.tracking` names the seam that would close it.

## 0.13.0

The portable backend surface grows with a batch of additive, source-observable
rules — no existing contract changes, so a checker certified against 0.12.0
stays valid and simply gains coverage.

Optimistic concurrency and time:

- `backend/no_naive_datetime` — timestamps must be timezone-aware; a naive
  `datetime` is refused.
- `backend/update_schemas_inherit_base_update_schema` — an update request
  contract must carry the optimistic-concurrency token.
- `backend/no_manual_version_assignment` — that token is never assigned by
  hand; the persistence layer owns it.

Source hygiene:

- `backend/no_eval_or_exec` — a string is never executed as code.
- `backend/no_star_imports` — names are imported explicitly, never by wildcard.
- `backend/no_blocking_sleep` — the thread is never blocked by a synchronous
  sleep.
- `backend/no_print` — diagnostics go through the logger, never a bare print.
- `backend/no_todo_fixme` — no placeholder comments stand in for deferred work.
- `backend/no_mutable_default_args` — no mutable value is used as a default
  argument.
- `backend/no_empty_tests` — every test asserts a real outcome.

Size, query and migration correctness:

- `backend/no_oversized_python_files` — no source file grows past the
  line-count cap.
- `backend/path_id_params_are_uuid` — a route path parameter naming a resource
  id is typed as a UUID.
- `backend/offset_queries_declare_ordering` — an offset-paginated query must
  declare an explicit ordering.
- `backend/alembic_downgrades_not_empty` — a migration's downgrade reverses the
  change rather than being an empty stub.

## 0.12.0

Row ownership now remains structural across background workflows. A worker
identity is not blanket authority over every user's rows, and application code
cannot remove ownership merely to make unattended cross-owner maintenance pass.

- `backend/no_manual_ownership_checks` now also covers a job-bearing module
  whose declared service model omits the ownership trait.
- The reference runtime rejects the same declared module shape at composition,
  while the existing write chokepoint continues to enforce owned rows.
- New `violation-03` freezes the unsafe nightly-maintenance trade as a portable
  corpus case.

## 0.11.0

The generated-client-only reference now has a sanctioned realtime path: raw
`WebSocket` / `EventSource` remain refused in app modules, while the reference
realisation points at `useRealtimeChannel()` for typed subscriptions. The hook
mints a short-lived, one-use connection ticket through the generated,
authenticated client before opening the native transport inside react-core —
the bearer token never enters a URL and app code stays on one governed egress
surface.

- `frontend/generated-client-only.reference` now distinguishes request/response
  (`useTerpClient()` + `unwrap`) from typed SSE/WebSocket subscriptions
  (`useRealtimeChannel()`). Normative title/intent are unchanged and remain
  stack-neutral; raw transports are still in the refused surface.
- New `frontend/generated-client-only/compliant-04` exercises the sanctioned
  hook with a runtime type guard. It raises the corpus certification bar: a
  conforming checker must keep the replacement clean while continuing to flag
  the existing raw transport cases.

## 0.10.0

The **assurance profile**: release readiness as a checkable artifact.

- New `assurance-profile.schema.json` — the machine-readable release-assurance
  claim a toolchain emits from its release verification profile, composing the
  Terp-specific evidence (the standard's own enforcement surfaces) with the
  generic lanes a release also stands on. The lane vocabulary and each lane's
  requirement level are normative and fixed by the spec (README, "Assurance
  profile"): `terp-standard`, `appsec-baseline` and `dependency-audit` are
  **required** — the claim (`ok`) is true only when all three passed — while
  `a11y` and `blackbox-conformance` are **recommended**. Requirement levels
  are deliberately not a document field (an emitter cannot demote a required
  lane); every lane appears exactly once, an unrealised lane is reported
  `not-run` (never dropped, never passed), and each realised lane names the
  verification-check ids composing its verdict so the claim traces into the
  toolchain's own verification envelope.
- The schema ships in both distributions (`terp-spec` / `@terp/spec`), and the
  spec suite pins the schema's lane enum to the README's normative table so
  the two statements of the vocabulary cannot drift.

## 0.9.0

Corpus depth for the authz, migration, egress and sensitive-field rule
families: adversarial cases for the evasion shapes the rules must see
through, and exact `expected-findings.json` manifests — the per-case contract
hardens from "flags something" to "flags the right line" wherever a manifest
now exists. No catalog entry changes; the corpus IS the interoperability
contract, so the certification bar rises (minor bump).

- **New violation cases** (each with an exact manifest):
  `backend/no_adhoc_permission_literals` violation-03 (`read=` /
  `write_role=` literals — the other authority keywords);
  `backend/safe_methods_are_read_only` violation-02 (imperative
  `add_api_route(..., methods=["GET"])` calling a mutating service method)
  and violation-03 (mixed-method `api_route(["GET", "POST"])` calling a
  `_remove` helper); `backend/mutations_require_write_role` violation-03
  (explicit static rank inversion, `read=ADMIN`/`write=EDITOR`, behind a
  PATCH route); `backend/public_modules_are_read_only` violation-02
  (`Policy.public` with an imperative DELETE registration);
  `backend/no_destructive_migrations` violation-04 (`drop_column` +
  `alter_column(type_=...)`) and violation-05 (`DELETE FROM` / `TRUNCATE
  TABLE` through `op.execute` literals); `backend/tables_have_migrations`
  violation-02 (two table models, one module — one deduplicated finding at
  the first table's line); `backend/no_unique_columns_on_soft_delete_models`
  violation-02 (transitively soft-delete-capable model with a
  `UniqueConstraint`) and violation-03 (partial unique `Index` missing one of
  the two verified dialect predicates); `backend/no_raw_outbound_http`
  violation-06 (`requests` and an `aiohttp` submodule);
  `backend/schemas_exclude_sensitive_fields` violation-02 (a DTO exposed via
  `response_model` without a schema base class) and violation-03
  (`client_secret` / `private_key` / `refresh_token` in one read schema);
  `backend/no_hardcoded_credentials` violation-05 (destructured parallel
  literals — `user, password = "svc", "hunter2"` — plus a `ghp_` token
  literal); `backend/input_schemas_exclude_managed_columns` violation-02 (an
  off-convention request-body DTO declaring `owner_id`/`tenant_id`);
  `frontend/generated-client-only` violation-04 (bare `XMLHttpRequest` /
  `EventSource` global references without a call or `new`).
- **New compliant (near-miss) cases**:
  `backend/no_adhoc_permission_literals` compliant-02 (`require_permission`
  with a typed constant); `backend/safe_methods_are_read_only` compliant-02
  (`merged.update(...)` on a plain dict inside a GET route — not a service
  mutation); `backend/no_destructive_migrations` compliant-02 (destructive
  DDL in `downgrade` only, an `UPDATE …` DML literal, `DROP INDEX`, and an
  `alter_column` without `type_`); `backend/tables_have_migrations`
  compliant-02 (a table model under `capabilities/` — outside the rule's
  module scope); `backend/schemas_exclude_sensitive_fields` compliant-02
  (`passwordless`/`tokens_issued`/`secretive_mode` near-miss names and a
  credential column on a `table=True` model).
- **Backfilled `expected-findings.json` manifests** for the existing
  violation cases of those same families (`no_adhoc_permission_literals`,
  `safe_methods_are_read_only`, `mutations_require_write_role`,
  `public_modules_are_read_only`, `no_destructive_migrations`,
  `tables_have_migrations`, `no_unique_columns_on_soft_delete_models`,
  `no_raw_outbound_http`, `schemas_exclude_sensitive_fields`,
  `no_hardcoded_credentials`, `input_schemas_exclude_managed_columns`) —
  every manifest generated from and verified against the reference checker,
  bringing the corpus from 6 to 32 exact-findings manifests.

## 0.8.0

The two-layer discipline closes its last declared gaps: **zero rules remain
`deferred`** — every rule is now either `required` with a shipped fail-closed
runtime control or `not-applicable` by recorded decision.

- **Runtime applicability**: `backend/no_adhoc_middleware`,
  `backend/no_dependency_overrides` and `backend/tables_have_migrations` flip
  `deferred` → `required`, each declaring its reference control as a `runtime`
  enforcement entry — the composition freeze now refuses post-composition
  middleware registration (both spellings) and rebinding of the composed
  dependency-override map (outside the local environment: overrides remain the
  sanctioned test-only seam, recorded in the rationale), and the migration
  boot guard refuses a declared package whose table models ship no migration
  history at all (the standalone missing-history case the rule exists for).
  A Level 3 stack now reproduces 27 runtime controls (was 24).
- **Corpus**: a new `frontend/escape-hatch` violation case pins that a marker
  spelled with a retired tool-internal rule id waives nothing — the violation
  underneath still fires and the stale marker is itself reported (previously
  proven only in the reference adapter's own suite).

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
