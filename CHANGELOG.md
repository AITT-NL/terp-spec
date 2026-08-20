# Changelog — the Terp Standard

The change history of the spec, keyed to `VERSION` (the semver of the
standard). Pre-1.0, a **changed contract** bumps the minor; purely additive
fields and new rules also bump the minor; prose bumps the patch (see
"Growing the spec" in the README). The top entry's version must equal the
checked-in `VERSION` — held by `tests/test_changelog.py`. A checker certified
against an earlier version reads this file to see exactly what changed since.

## 0.25.0

### Added

- **`backend/no_manual_lease_columns`** — an application table may no longer
  declare its own lease bookkeeping: a holder column paired with an expiry, a
  heartbeat stamp, or an equivalent claim deadline. The pattern shows up wherever
  a table is used as a queue, and it is refused because the hand-rolled version
  reliably omits the half that makes a lease safe.

  Expiry is the easy half. It establishes that a holder *may* have died, and a
  reader can act on that. What it cannot do is stop a holder that merely
  **paused** — a stalled process, a long GC, a suspended container — from waking
  after its own deadline, finding its name still written on the row, and
  completing work a successor has already taken over. Two writers then believe
  they own one unit of work, which is precisely the condition the columns were
  added to prevent. Preventing it needs a *fence*: a monotonic grant token that
  every subsequent write is matched against, so a superseded holder is refused
  rather than trusted. Nothing about a holder-plus-deadline pair provides one, and
  the omission is invisible until the day it matters.

  The rule therefore names four properties a conformant platform must supply
  rather than leave to each table: the grant is **fenced**; it is taken
  **atomically** with the state change it guards (a claim that commits while the
  row change rolls back strands the resource just as badly as the reverse); it is
  renewable by a **heartbeat that fails closed**, so a holder that has lost its
  grant is told to stop instead of receiving a flag it can forget to check; and it
  is **recoverable** — an expired grant triggers the owning domain's declared
  recovery, so work a crashed holder abandoned returns to a retryable state
  instead of needing a hand-written `UPDATE` from someone with database access.
  That last property is the one no table-local pattern can express, because only
  the domain knows whether the right answer is "queue it again", "close it failed"
  or "leave it for a human".

  The related need reads from the other side: "at most one active run per
  pipeline" is the same primitive expressed as a mutex, on a resource that is not
  a row at all — which is why the rule's reference implementation keys custody on
  an opaque `(kind, key)` pair rather than on a table.

  Platform-owned delivery infrastructure is a reviewed exception, not an
  application pattern: a durable outbox claims *batches* of its own rows for
  throughput and needs no domain recovery, since a lapsed claim is simply
  reclaimed and re-delivered. `layer` is `static-portable` (the violating shape is
  a column declaration any checker can see) and `runtime.applicability` is
  `not-applicable`, with the rationale recording why: column presence is
  observable at runtime but not *attributable*, because one shared model registry
  holds both the application's tables and the platform's own delivery table, which
  legitimately declares exactly these columns.

## 0.24.0

### Changed

- **`backend/schemas_avoid_positional_tuples` is scoped to the positional shape
  only: a variadic `tuple[X, ...]` is now compliant.** The 0.23.0 intent named
  `tuple[str, ...]` among the violating spellings, but the rule's own rationale
  is the *positional* array shape (`prefixItems`, or the list form of `items`)
  that client generators disagree on — and a variadic tuple never produces it:
  `tuple[X, ...]` serialises byte-identically to `list[X]`. Refusing it forced
  apps into source rewrites with provably zero wire effect while the violation
  message asserted something false, and it penalised the natural annotation for
  a frozen value object (an immutable, hashable homogeneous sequence). The
  fixed-length form stays refused wherever it sits, including nested inside a
  variadic one (`tuple[tuple[str, int], ...]`, corpus `violation-03`); the
  variadic form is pinned compliant by corpus `compliant-02`.

  The runtime rationale now also records what the reference implementation
  learned enforcing it: the check validates the generated OpenAPI document
  itself rather than the annotations that produced it (a discriminated-union
  member can hide a positional shape from any annotation walk, but not from the
  document), and it reports every offending location in one pass instead of
  raising on the first.

## 0.23.0

### Added

- **`backend/schemas_avoid_positional_tuples`** — a schema field may no longer cross
  the wire as a positional tuple. A fixed-length tuple annotation serialises into the
  contract as an array whose element types are positional (`prefixItems`, or the list
  form of `items`), and client generators do not agree on that shape: one emits the
  positional form, another the widened element array. The two descriptions of the same
  field then come out structurally unrelated, and an app that exposes a tuple anywhere
  in its API cannot type its own calls against it. What makes this worth a rule rather
  than a note is the failure mode, not the frequency: the error lands at the *call
  site* as an opaque generic-instantiation mismatch, nowhere near the field that caused
  it, and the two types it names are printed identically unless error truncation is
  disabled. The fix is one line per field once you know; finding it is an afternoon.
  A tuple is a weak contract regardless — the positions carry meaning that no name
  records — so the compliant shapes are a nested model with named fields, or a
  homogeneous sequence.

  Enforced in both layers, and deliberately so: the build-time half reads the
  annotation, while the runtime half walks the generated OpenAPI document and so also
  catches a tuple that reaches the contract through a type alias, a generic parameter,
  or a custom `__get_pydantic_core_schema__` — the vectors a source scan cannot see.

  A checker certified against 0.22.x remains correct for every rule it already
  implements; this is additive, and a checker that does not implement it simply
  reports one fewer rule.

## 0.22.0

### Added

- **`backend/declared_read_only_routes_do_not_write`** — a route may now declare
  that it computes and never persists, and be held to it. Write authority is
  derived from the HTTP method, which is right for almost every route and blind to
  one: the handler that uses an unsafe method because its *input* is a body, not
  because it writes — validating a candidate document, previewing an import,
  costing a plan. Undeclared, such a route is pure only by the absence of a write,
  a guarantee made of missing code that holds until an edit adds a line. The rule
  is enforced in both layers (build-time against the declaration, runtime at the
  write chokepoint) and does **not** change authorization: a declared route is
  still authorized at the write tier, because declaring purity narrows what the
  handler may do, never what the caller must hold.

  A checker certified against 0.21.x remains correct for every rule it already
  implements; this is additive, and a checker that does not implement it simply
  reports one fewer rule.

## 0.21.1

No change to the standard. 0.21.0 reached npm but never reached PyPI: the
release job built the wheel with an unpinned build backend that had moved on to
`Metadata-Version: 2.5`, which the digest-pinned publisher's twine refused as
invalid. Two pins that were each defensible on their own drifted apart, and the
result was a version consumers could only half-install. **Pin `0.21.1`, not
`0.21.0`** — the catalog content of the two is identical.

## 0.21.0

One backend rule is added; nothing else changes.

- **`backend/forwarded_filters_are_declared`** — new. Every filter name a
  read endpoint forwards must be a declared filter. An endpoint forwards its
  optional query parameters unchanged, so a name that matches no declaration
  carries no value on any request that omits that parameter: the narrowing
  appears applied while the read stays unnarrowed, and no test that omits the
  parameter can observe the difference. Classified `required` — the read layer
  resolves each name against the declarations while serving the request and
  rejects an undeclared one before the read is built, so the invariant is
  observable and enforced fail-closed. Names that are not statically knowable
  (a filter mapping built elsewhere, a computed name) are not judged.

## 0.20.0

One backend rule is added; nothing else changes.

- **`backend/emitted_events_are_declared`** — new. A module emits only the
  events its manifest declares. The emits list is the module's published
  contract — what the control plane validates, what an operator reads to know
  what a module produces, what another team subscribes against — and an
  undeclared emit makes that contract quietly untrue: the event really does go
  out, so nothing fails, while the document everyone reasons from says it
  cannot happen. This is the same defect class as 0.19.0's owning-package
  rule, seen from the other side: there a declaration had no reality behind
  it, here a reality has no declaration in front of it.

  Build-time only, by recorded decision. An emit call carries no module
  identity, so the running system cannot attribute an emit to the manifest
  that should have declared it; the association exists only in the source
  layout. Passing a module handle to the emit call to make it checkable at
  runtime would put the answer in the caller's hands, which is exactly what
  the rule is verifying.

## 0.19.0

Modules gain a declared way to depend on each other, and a table gains one
owning package. Three backend rules are added and one is restated; nothing
else changes.

Until now the standard said only that a module never imports a sibling. That
is the right default, but it left a real dependency with nowhere to go: the
observed consequence is that apps hand-roll dependency inversion — a protocol,
a module-global registry and a composition-root adapter — which is the same
coupling, unchecked, spread across three files and carrying mutable global
state. The standard now names the sanctioned form instead.

- **`backend/no_cross_module_imports`** — restated. A sibling import is
  refused unless the depending module **declares** the edge in its own
  manifest. What is forbidden is undeclared coupling, not coupling.
- **`backend/cross_module_imports_use_public_surface`** — new. A declared
  edge grants the dependency's `models` / `schemas` / `service` / `events`
  only. Never its router (that couples the two through HTTP shapes and lets
  an in-process call walk past the policy guarding those routes), never an
  underscore-prefixed internal, and never the bare package.
- **`backend/module_dependency_graph_is_acyclic`** — new, and the one rule of
  the three with a runtime half: the composition root sees every manifest, so
  it refuses to boot on a cycle. A cycle means two "independent" modules have
  become one.

Separately, a table now has exactly one owning package. Per-package migration
histories are independent, so splitting a table's model from the history that
creates it emits no schema change at all: the losing package no longer owns
the table and cannot propose dropping it, and the gaining package sees a
database where it already exists and cannot propose creating it. Every
existing database keeps upgrading and the build stays green. The next
ordinary change to that model is then authored into the gaining package's
history, which - ordered only by foreign keys - a fresh install may run
before the history that creates the table. Only fresh installs break, months
later, blamed on an unrelated change.

- **`backend/table_ownership_is_not_split`** - new. The package whose models
  declare a table must be the package whose history creates it. Move a table
  between packages by expand/contract, never by moving the declaration alone.

## 0.18.0

One existing backend rule is strengthened. Everything else is byte-identical
to 0.17.0.

- **`backend/migration_history_is_intact`** — a non-empty history must now have
  exactly one first revision, and every revision must be reachable from it.
  The 0.17.0 wording required every parent to exist and allowed at most one
  first revision; a closed cycle can satisfy both conditions while still
  providing no valid baseline, and a disconnected cycle can hide next to one.
  The corpus now carries the zero-root cycle explicitly.

Migration for a checker: reject a history with no first revision and reject
revisions not reachable from its sole first revision.

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
