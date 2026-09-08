# Changelog — the Terp Standard

The change history of the spec, keyed to `VERSION` (the semver of the
standard). Pre-1.0, a **changed contract** bumps the minor; purely additive
fields and new rules also bump the minor; prose bumps the patch (see
"Growing the spec" in the README). The top entry's version must equal the
checked-in `VERSION` — held by `tests/test_changelog.py`. A checker certified
against an earlier version reads this file to see exactly what changed since.

## 0.33.0

### Changed

- **`frontend/no-untranslated-ui` does not reach a comparison operand.** The rule's
  subject is text that is rendered, and an operand of a comparison is not: the expression
  evaluates to a boolean, so the literal in `status === "paused"` is a state token being
  tested and reaches no screen in any locale. The reference implementation walked both
  sides of every binary and logical expression, so the ordinary React status guard could
  not be written without hoisting the comparison into a variable above the JSX - done
  eighteen times in one feature slice before anyone asked whether the rule meant it. It
  did not: this is the entry stating a boundary the intent already implied, and a
  `compliant-02` case contracting it. The left operand of `&&` is the test and is likewise
  out of scope; `||`, `??` and string concatenation can render either side and stay in
  scope on both. **A checker that reports a comparison operand no longer conforms.**

### Added

- **`backend/no_manual_actor_stamping` names the fourth shape, which is uniqueness.** The
  entry classified three - assignment forges the trail, comparison against a principal is
  inline object-level authorization, a read is neither - and an author who wants "one
  decision per reviewer per record" has none of them. That is uniqueness keyed on the
  actor: it forges nothing and decides nothing about who may act on a row, it asks whether
  a SECOND row may exist, and the ownership seam the entry redirects to has nothing to say
  about that. Reaching for the query form and being refused reads as the requirement being
  unavailable, and one was removed from a governance table on exactly that reading.

  It is available. The entry now names the shape that expresses it - a
  `UniqueConstraint("record_id", "created_by_id")` in `__table_args__`, contracted by a
  new `compliant-05` case - and says why the query form stays refused: no static check can
  tell a uniqueness probe from an inline authorization filter, because they are the same
  expression. So the refusal pushes an author toward the constraint, which is also the
  race-free implementation where a check-then-insert is not, since two concurrent requests
  both pass the probe. Nothing about the rule changes; what changes is that its scope is
  discoverable without trying both.

  Neither entry adds a rule. Both are the legibility half ADR 0122 redirects effort to:
  the catalog's breadth is frozen and explaining an existing refusal is the work that
  remains.

## 0.32.0

### Added

- **`test-adequacy` joins the assurance lane vocabulary (RECOMMENDED) — the five existing
  lanes can all pass over a suite that asserts nothing.** Every one of them runs checks and
  reports verdicts; not one asks whether the suite *could have failed*. The catalog reaches
  the syntactic form of that gap and, by construction, cannot reach the rest:
  `no_empty_tests` refuses an empty body, a bare `pass`, a constant assertion, and is blind
  to a test whose assertion is trivially satisfied by the path it exercises. A boundary test
  goes vacuous the moment the boundary it was named for moves, and stays green while it does.

  Only a deliberate change to the code under test settles it, and that is a different *kind*
  of enforcement from the build-time/runtime pair every catalog rule declares — hence a lane
  rather than a rule. **Coverage does not evidence this lane**: it reports which lines ran,
  not whether anything would have noticed them changing.

  RECOMMENDED, following `a11y`: a lane no toolchain realises yet is emitted `not-run` with
  no composing checks, never dropped and never counted as passed. Making it required would
  turn every existing `ok` false overnight and say nothing true about those releases. As with
  every vocabulary addition, an emitter must now report the lane — omitting one hides it —
  so a toolchain pinned to this version emits `test-adequacy: not-run` until it realises it.

- **`backend/modules_ship_tests` — the canonical module shape was five production files,
  and a module could satisfy every structural rule in this Standard while shipping no
  tests at all.** That is not a corner an application cuts by accident. A scaffolder that
  emits the canonical shape emits an *untested* module by default, so untested was the
  shape the platform handed out, and the gate agreed with it. `no_empty_tests` sharpens
  the point rather than covering it: the Standard had an opinion about whether a test that
  exists can fail, and none about whether one exists.

  The rule requires every wired module — the same "ships a manifest or a mounted router"
  signal `canonical_module_shape` uses — to have at least one test the project attributes
  to it. **Two layouts satisfy it, and the asymmetry is deliberate.** A per-module
  `tests/<module>/` package is the canonical form and what a scaffolder should emit,
  because a module accumulates test files and a directory holds them without anyone
  inventing a naming convention. A flat `tests/test_<module>_*.py` is *recognised* rather
  than prescribed: refusing it would fail applications whose modules are in fact tested,
  whose only way through would be an opt-out marker claiming they are not — and a rule
  satisfiable only by a false statement is worse than one that accepts the same true claim
  written two ways. The separator is required, so a module named as a prefix of another is
  not credited with its sibling's tests.

  Tests belong to the project's `tests/` tree rather than the module directory, because a
  test that drives the composed application has to live where the application fixtures
  are. A reference checker resolves that tree beside the scanned root, and accepts one
  inside it so a corpus case can express the rule at all — a case is copied *into* the
  root and cannot create a true sibling of it.

  Additive: an application that already tests its modules in either shape passes
  unchanged. One that does not gets a finding naming both shapes, and a governed opt-out
  if the answer is genuinely "not yet". The rule asks only that tests exist and are
  attributable; whether they are any good remains `no_empty_tests` and the application's
  own coverage gate. Six corpus cases contract the boundary, including the two that a
  looser check would get wrong: a `tests/<module>/` directory holding no test, and one
  module credited with another's file.

  The frontend surface has no test rule and does not gain one here. Its rules are lint
  rules, and a linter cannot assert that a file is *absent*; that needs a project-level
  check the surface does not yet have.

- **Three rules for a per-module role, which is a tier a person holds inside one module and
  nowhere else.** The Standard already required every module to declare a coarse access
  policy. A module may now additionally accept a *role of its own*, so an administrator can
  raise one person's tier inside it without raising it everywhere — and that opt-in brings
  three failure modes the existing rules do not reach.

  **`backend/grantable_modules_are_named`** — a module that accepts a role of its own says
  what to call it. The screen offering the choice renders one strip per such module, headed
  by the declared name, and that name is the only text about the module a reader ever sees
  there; headed by an identifier instead, the strip asks someone to hand out authority over
  something the interface has not named. Required, and the platform enforces the same
  pairing when the declaration is constructed — the build-time half adds a file and a line
  before the application is imported, which is the difference between a fixable message and
  a traceback out of composition.

  **`backend/platform_modules_refuse_module_roles`** — a module that can hand authority out
  never accepts a role of its own. This is the escalation guard, and the reason it exists is
  that the failure looks small: whoever holds an administrator tier *inside* the module that
  administers grants can grant themselves anything, everywhere, while the tier that allowed
  it reads as narrowly scoped. Such a module declares outright that it is never per-module
  assignable, and declares why, so the refusal is legible to whoever reads the access
  surface rather than an absence they have to notice. Deliberately syntactic: holding the
  service is the trigger, with no attempt to decide whether a call site only reads, because
  a read is the first half of a write and nothing static can tell a module that lists grants
  from one about to create one. Build-time only, and the rationale is recorded: the running
  system does refuse to *assign* a tier in a module declared platform-only, but nothing at
  runtime can know that a module administers authority in the first place — that is a
  judgement about what the source does.

  **`backend/module_role_writes_go_through_the_capability`** — the assignment table is
  reached through its service, never directly. The service is where the audit entry is
  emitted and where an assignment is refused when the declarations cannot support it: a
  module that administers authority, a module that never opted in, a tier the application's
  ladder does not declare. A row written around it is not a more permissive assignment; it
  is one that can never take effect, and whoever wrote it will believe the person is
  authorized until the moment they are not. A plain *read* is refused too, on the same
  footing as hand-rolled row ownership and for the same reason — a read is the first half of
  a per-module gate written by hand — and what a subject holds already has an answer that
  carries its provenance with it.

  All three are `static-bespoke`: they name platform types, so they are not portable to a
  second stack the way a shape rule is. Six corpus cases contract them, and the pair for the
  escalation guard puts the service and the declaration in *different files of the same
  module*, which is the shape a real one has — a check that looked only at the manifest
  would be blind to every application that keeps its service where it belongs.

## 0.31.0

### Added

- **`backend/errors_use_the_typed_envelope` and `backend/no_exception_text_in_responses`
  — the error path is the one place an application improvises a message for a client,
  and it was the one place nothing looked.** Two rules, added together because each
  covers a hole the other leaves open: one is about which exception is raised, the other
  about what is put inside it.

  `errors_use_the_typed_envelope` refuses the web framework's own HTTP error type in an
  application module. A platform that promises one error envelope has to be the only
  thing that builds it, and a module that names a status code and a message directly is
  a second, undocumented error contract for that one response. Each instance is
  defensible; the set of them is a shape no schema describes and no client can dispatch
  on. Two compliant cases pin the other side of the boundary, so the rule cannot be
  satisfied by over-flagging: naming the framework's error is not raising it (an adapter
  that catches one and re-raises it stays silent), and raising a non-HTTP exception of
  the language's own is not this rule's business.

  `no_exception_text_in_responses` refuses a caught exception's own text in the message
  the client receives. A driver names the table and the statement, a filesystem error
  names an absolute path and therefore the deployment layout, a connection error names
  an internal host. None of it is chosen, reviewed or versioned — it is a diagnostic
  string written for an operator reading a log, forwarded verbatim to whoever made the
  request. The rule that keeps declared fields out of a serialized response
  (`schemas_exclude_sensitive_fields`) cannot see this, because an error path builds its
  message on the spot rather than from a declared schema.

  **The compliant path is a split, not a prohibition, and the corpus says so.** The
  exception belongs in the log half of the envelope and the written message in the body
  half, so a case pins the log-context spelling as compliant: a detector that refused
  every mention of the caught exception would take the diagnosis away from the operator
  to protect the client, which is not the trade the rule is making. A second compliant
  case pins interpolation of a value the *caller* submitted, which is ordinary message
  writing and would be refused by any detector that matched f-strings inside a handler.

  Both are `static-portable` and `not-applicable` at runtime for the same reason, stated
  per rule: by the time a request is being served, the distinction each rule turns on
  — which type the author raised, and where a string came from — has been erased.
  Two detector residuals are recorded rather than claimed.

  This raises the bar: an application that passed 0.30.x can fail 0.31.0. No rule was
  changed or removed.

- **`backend/no_manual_actor_stamping` narrows to writes and gates; reading a stamp is no
  longer refused.** The rule's own prose said "only attribute access (set / compare) is
  policed", which is a sentence that contradicts itself — attribute access is the broad
  thing and set-or-compare is the narrow one — and the detector did the broad thing. So
  `if row.created_by_id is None` was refused by a rule whose stated justification is
  forgery, and a careful reader concluded from that they could not read provenance at all.

  The scope is now stated instead of implied, and it follows the harm. **Assigning** or
  deleting a stamp forges the trail. **Comparing** it against a principal is object-level
  authorization written inline, which belongs to the ownership seam. **Reading** it does
  neither, and the ordinary uses — a read DTO, a rendered "created by", a log line, a
  presence test — are exactly what a provenance trail is kept for. A comparison against a
  literal is a presence test and is not a decision; a comparison against anything else is.

  Three corpus cases contract the new boundary in both directions: a violation for the
  inline gate, and two compliant cases for the plain read and the presence test. The two
  existing violations were already assignments, so nothing that failed for the right
  reason starts passing.

  **The two sibling rules keep the broad reading, and that asymmetry is the decision.**
  For the managed scope and ownership columns a read is the first half of a hand-rolled
  scope filter or a hand-rolled per-row gate, and no static check can tell it from a
  display read. An actor stamp has no corresponding harm on the read side. Both sibling
  entries now say so in one sentence, so the breadth is recorded rather than inferred from
  a detector. Two residuals are recorded for the narrowed rule.

  This is a contract change in the permissive direction: an application that failed 0.30.x
  on a stamp read passes 0.31.0.

## 0.30.0

### Changed

- **`backend/no_manual_ownership_checks` requires reach, not co-location.** Two of the
  three residuals recorded for this rule in 0.29.1 stop being permitted limits and become
  required behaviour, each contracted by a corpus case. The reference implementation closed
  them in terp-framework 0.14.0; this raises the bar for every implementation, so a checker
  certified against 0.29.x can pass an app that 0.30.0 refuses.

  A **jobs declaration bound to a name** (`ModuleSpec(jobs=MODULE_JOBS)`) must now be seen
  as declaring background work. `spec.jobs` is a sequence by the time the composition-time
  twin reads it, so a detector that matches only a list-or-tuple LITERAL passes an app that
  then cannot start — the cheap check green and the expensive one refusing, which is the
  worst of the two orderings.

  **Reach follows a declared edge.** Modules are independent by default, so splitting a job
  away from an unowned service severs the reach, and `requires` restores it in one line. A
  detector keyed on the module a service is *declared in* never sees that, which made the
  advice both refusals give — put them in different modules — also the way through the
  gate.

  Two compliant cases pin the other side of the boundary, so the raised bar cannot be met
  by over-flagging: the same two modules with **no** declared edge must stay silent, and
  `OwnedMixin` reached through an intermediate base is ownership, so a detector matching a
  direct base name must not fire on an owned model.

  The rule's third residual — a `ModuleSpec` that omits `services=` — is untouched and
  stays recorded. No rule was added or removed.

## 0.29.1

### Changed

- **Two rules record their detector residuals** (`corpus/RESIDUALS.json`), which is data
  rather than a contract change: no rule requires more or less than it did.
  `backend/no_manual_lease_columns` matches a fixed set of lease column spellings on a
  table model, not the custody shape, so a holder/heartbeat pair under other names passes
  clean. `backend/no_manual_ownership_checks` carries three: its build-time background-work
  clause matches a `jobs=` list or tuple LITERAL (a declaration bound to a name is not
  seen), it matches `OwnedMixin` as a direct base name within the same module directory
  (an indirectly inherited or externally declared trait is not seen), and its
  composition-time twin iterates a ModuleSpec's declared services (a spec that omits
  `services=` is not reached).

  Both were recorded because a careful reader concluded from each that the rule refused a
  design it does not actually look at. That is what the ratchet is for: a known limit of
  precise detection belongs in data, so a second implementation neither over-fits nor
  over-claims, and so the limit is not rediscovered as folklore.

## 0.29.0

### Added

- **`backend/operations_reference_catalog`** — a route's declared operation (what it
  does for the person calling it, ADR 0102 in the reference framework) is a typed
  catalog constant, never a bare string or a value built inline at the call site.
  Mirrors the event bus's own no-drift rule (`backend/events_reference_catalog`):
  the guarantee is that an operation's stated id and wording can never drift from
  what the catalog documents.
- **`backend/routes_declare_operation`** — every route declares the operation it
  performs, once an app's operations catalog opts into strict coverage. The
  coverage choice is the app's own — an app that has not opted in is unaffected —
  but a route mounted under strict coverage with no declared operation fails the
  gate. Both rules share one runtime enforcement seam: the same boot check resolves
  every declared operation against the catalog by value (the no-drift half,
  unconditional) and, only under strict coverage, refuses a route that declares
  none (the coverage half).

88 rules: 73 backend, 15 frontend.

## 0.28.0

### Added

- **`frontend/no-untranslated-ui`** — static user-facing copy anywhere in app-authored
  frontend source must use `UiText` descriptors or `Trans`; bare JSX copy, rendered
  expression branches, accessibility text, literal UI labels and standard toast feedback
  are rejected.
- **`frontend/locale-catalogs-complete`** — every authored message must be translated in
  every declared target locale. Missing/malformed catalogs, empty or silently copied
  translations fail the gate, and the runtime resolver refuses incomplete target-locale
  entries as a second line of defence.

86 rules: 71 backend, 15 frontend.

## 0.27.0

### Added

- **`backend/declared_read_controls_are_forwarded`** — a declared filter or sort must be
  reachable from an endpoint that forwards it. The catalogue already refused a forwarded
  name that matches no declaration; this is the other direction, and it is the one that
  fails quietly. A declaration no endpoint forwards is inert: the capability is described in
  the source, absent from the API, and silent about the difference. It presents as an
  implemented feature — a client generated from the contract offers no way to sort, a screen
  built against it ships with every column's sorting disabled, and nothing in the read layer
  is wrong.

  **Judged by PRESENCE, per module and per control kind, never by name**, and that is the
  design rather than a shortcut. A per-name comparison cannot be sound here: the counterpart
  rule reads literal mapping keys and says so, because a filters mapping built elsewhere
  hides its names — and in this direction that blind spot flips from a missed detection to a
  FALSE one, rejecting a filter that is forwarded through a computed mapping. The keyword is
  visible in the source even when its value is not, so requiring a module that declares a
  filter to forward *a* filters mapping is decidable where requiring a specific name is not.
  The module is the unit because pairing one declaration to one endpoint is not statically
  knowable either.

  This is a **build-time-only** rule, and the runtime entry records why rather than
  deferring: the defect is the absence of a call. A request carrying that filter never
  arrives, because the endpoint exposes no parameter for it, so no code path runs and no
  fail-closed control can fire. Its counterpart is enforced at runtime precisely because
  there a request does reach the read layer.

- **`backend/frozen_values_hold_no_mutable_collection`** — a frozen value object must not
  hold a list, dict or set. Freezing binds the attributes, not what they point at, so a
  frozen object holding a mutable collection is immutable exactly one level deep — the level
  nobody checks. Callers rely on the declaration: they share the value between requests,
  cache it, use it as a registry key and skip defensive copies because the type says none
  are needed. `plan.columns.append(...)` succeeds on a frozen dataclass, and the mutation
  arrives somewhere else entirely as state that changed with no assignment near it.

  Recognised by declaration rather than convention — a dataclass frozen at the decorator, a
  NamedTuple, a model configured immutable — and the message names the immutable counterpart
  (a tuple, a Mapping, a frozenset) rather than only refusing. A NamedTuple is the sharper
  case in practice: it is the shape people reach for *because* it is safe to share, so the
  false guarantee travels further.

  Also build-time-only by nature. A runtime control would have to intercept mutation of an
  object the frozen value merely references — the list belongs to whoever else holds it, its
  mutating methods are not the frozen object's to override, and deep-freezing on
  construction would change the value's semantics rather than check them.

84 rules: 71 backend, 13 frontend.

## 0.26.1

No change to the standard's content. 0.26.0 announced
`layout-declaration.schema.json` and shipped it in neither artifact: the file was
added to the repository and to no packaging manifest, so the wheel's
`force-include` table and `package.json`'s `files` list both omitted it. The
consequence is the one that matters for a standard consumed as a distribution
(ADR 0086) — the schema described as normative and stack-neutral was unreadable
by every consumer, and the reference implementation's parity test for it skipped
rather than failed, because a schema that is absent and a schema that is
satisfied are the same silence. **Pin `0.26.1`, not `0.26.0`** — the catalog
content of the two is identical.

Also adds the gate that would have caught it:
`test_every_shipped_artifact_is_in_both_packaging_manifests` holds every
root-level data artifact to both manifests in both directions, so a schema added
without a manifest entry now fails here rather than in a consumer's skip.

## 0.26.0

### Added

- **`layout-declaration.schema.json`** — the normative, stack-neutral schema for the
  document an app checks in to declare its layout. It promotes into the standard what
  was previously only a convention in one stack's template, and it exists because that
  convention was carrying a defect: the document declared which page contract the app
  opted into, the running app was told the same thing a second time in its own code,
  and the template instructed the reader to "keep the two in sync". An unenforced
  invariant with a human assigned to it. Delete either side and the app keeps a
  build-time rule with no runtime check, or a runtime check no checker agrees with,
  and nothing anywhere says which.

  So the schema states the document as the single source, and widens it past the
  contract to the shell's own shape — `contentWidth`, `density`, `navPlacement`. Those
  three were reachable only by editing code, which put them out of reach of anything
  that edits files. Declaring them here is what lets a tool read and rewrite how an
  app's shell is shaped without writing that app's TypeScript.

  The portable/per-stack split follows `restricted-surface.json`'s precedent exactly.
  `contract` is a plain string: which contracts exist, and which components each of
  their page slots admits, is per-stack configuration and stays in the catalog entry's
  non-normative `reference` field. The shell's vocabulary is fixed here, because a
  density or a navigation placement means the same thing on any stack.

  **`defaultTheme` joins them, and is the clearest case of the same reason.** Which
  palette an app opens on is among the most visible choices its operator makes, and it too
  was reachable only by editing the app's own code. It sits at the top level rather than
  under `shell` because a palette paints the frame and the page alike, while `shell` is
  where the frame's *geometry* is declared — and because the two halves of the split fall
  differently: shell vocabulary is fixed normatively, palette names are a stack's own to
  publish. So it follows `contract`'s half rather than the shell's — a plain string, with
  the values recorded non-normatively in the catalog entry's `reference` field. The one
  reserved portable name is `system`: the app opens on whatever light or dark preference
  the viewer's own platform reports. A consumer must refuse a name its stack does not ship
  rather than fall back to one it does, because falling back is precisely how a declaration
  ends up doing nothing while looking like it works.

  **`shell.navGroups` joins it too, and it is the first nested shape in the document.** A
  navigation group spans modules, so no module can own one — which left the app's own code
  as the only place a group could be declared, and therefore left the order of an app's
  navigation out of reach of anything that edits files. This one goes UNDER `shell`, unlike
  the palette, and the split is the same test applied honestly: what a group's entries are
  called and what their fields mean is fixed here for every stack, so it belongs with the
  keys whose vocabulary this schema fixes. Only the values are the app's.

  An entry is `id`, `label` and an optional integer `order`. Three of those carry a decision.
  `id` is non-empty, because a consumer may reasonably treat the empty string as a usable key
  at render time — where being total matters more than being strict — while declaring one is
  an authoring error with no legitimate transient form. `label` is REQUIRED and the empty
  string is its declared way to say "render no label at all", so a positioning-only group is
  something the document states rather than a key someone forgot. And `order` is an integer
  with absent meaning zero over a stable sort, so an app that only wants a sequence writes the
  groups in that sequence and sets it on none of them.

  Six mutations, all red: a group entry that accepts an unknown field, `label` no longer
  required, an empty id made legal, a sort key that is not an ordinal, an empty label refused
  (which would remove the only way to declare a positioning-only group), and `navGroups`
  stopped being a list.

  **`shell.brand` is the third thing an app could only say in code.** A mark is among the
  most visible things about an app, and declaring one meant editing that app's source — so
  a tool that puts a logo in front of an operator had nowhere to put the answer. It is two
  optional paths, `logo` and `logoDark`, and the second is declared rather than derived
  because a mark with fixed colours cannot survive a dark background and no consumer can
  tell whether this one can. An app with one mark declares one; requiring the counterpart
  would force every app to claim a second asset it may not have.

  A consumer holding both must choose by the appearance of the palette actually in force,
  not by the viewer's platform preference. The distinction is not pedantry now that an app
  can pin a palette: an app that opens on a dark palette on a light platform would otherwise
  be handed the light mark on a dark background.

  The well-formedness gate stopped being about one key while this landed. It held the
  navigation group's entry to refusing unknown fields, describing every field and declaring
  a type for each, and it did that by naming `navGroups` — so `brand` arrived unchecked. It
  now runs over every shell key that is a shape rather than a choice, which is how the third
  one will be checked without anyone remembering to. Six mutations, all red.

  Three properties of the schema are load-bearing rather than stylistic.
  `additionalProperties: false` at both levels, so a consumer refuses a key it does not
  recognise instead of ignoring it — a declaration that does nothing must not look like
  one that works. Every key is optional, and an absent key is not a default: it is the
  app declining to declare, and a consumer leaves whatever was already in force alone.
  And the schema stays inside the minimal validator subset this spec ships, because the
  smallest consumer available is that validator, and a schema reaching for a keyword it
  cannot honour is unusable by exactly the audience it was written for.

### Changed

- **`frontend/layout-contract`** now states that the declaration is the single source
  for both halves of the rule, and cites the schema. The rule itself is unchanged — an
  opted-in app's archetype body slots still admit only the contract's components. What
  changed is that where the opt-in is declared is now normative, and that a key declared
  both in the document and in the app's own code is refused rather than resolved by an
  invisible precedence.

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
