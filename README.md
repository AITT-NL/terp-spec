# The Terp Standard — rule catalog + violation corpus

This repository is the **stack-neutral specification** of Terp's
secure-by-default rules (ADR 0080, made consumable by ADR 0081). The framework
([terp-framework](https://github.com/AITT-NL/terp-framework)) is the
**reference implementation**; this spec is what any other stack would
implement and be verified against. It is deliberately self-contained (no
`terp.*` imports, plain JSON + sample files) and consumed as a **package**,
never a repo path (ADR 0082).

## The package seam (ADR 0082)

The directory doubles as two thin distributions over one data set:

- **`terp-spec`** (Python, `pyproject.toml`): a dependency-free `terp_spec`
  accessor — `spec_dir()` returns the on-disk spec root, `spec_version()` the
  `VERSION` semver. A uv workspace member; the framework's certification tests
  locate the spec only through it.
- **`@terp/spec`** (npm, `package.json`): data only; consumers resolve the spec
  root via `require.resolve("@terp/spec/package.json")`. An npm workspace
  member; the ESLint adapter's corpus/surface tests depend on it.

Both manifests carry the **spec version** (`VERSION`) — independent of the
platform's lockstep release version, per ADR 0081's certification model; the
standalone suite holds the three declarations equal.

The spec-only validations (versioning, schema validity, the refused surface's
shape, the corpus ratchet and directory discipline) live in `spec/tests/` and
run standalone (`python -m pytest` from `spec/`; CI: the path-filtered
`spec.yml` workflow). The framework gate keeps the *parity* half — everything
that needs the live implementations. Because the framework consumes a **pinned
release**, this repository's CI additionally runs `certify-against-reference`:
it checks out the reference framework, substitutes the candidate spec for the
pinned `terp-spec` / `@terp/spec`, and runs the framework's parity + corpus
certification — so a catalog or corpus change is proven against the live
implementations *before* release, and the framework's later pin bump re-proves
it in the framework's own gate. Splitting the spec out is then purely a
manifest change: move `spec/` + `spec.yml`, repin `terp-spec` / `@terp/spec`
from workspace sources to a git tag or registry release
(`tests/architecture/test_repo_split_readiness.py` fails the build if code
re-couples the units by path).

The artifacts:

1. **`VERSION`** — the semver of the standard. A checker certified against the
   corpus records the spec version it was certified for.
2. **The catalog** (`catalog/`) — one JSON document per rule (validated by
   `catalog/schema.json`): what the rule is, why it exists, and how it is
   enforced today.
3. **The corpus** (`corpus/`) — violating and compliant code samples per rule:
   the executable meaning of the rule. `corpus/PENDING.json` is the coverage
   ratchet — the explicit list of rules still without cases, which only shrinks.
4. **The finding format** (`findings.schema.json`) — what a conformant checker
   emits, so checkers are interoperable and a corpus harness can be generic.
5. **The check-report format** (`app-check-report.schema.json`) — the complete
   result of one checker invocation over one application tree: the finding
   format plus the run's own evaluated-rule inventory, spec version, checker
   identity and verdict, so a driving tool can join per-rule verdicts to the
   catalog fail-closed.
6. **The refused surface** (`restricted-surface.json`) — the stack-neutral,
   normative declaration of the raw frontend primitives an app module must not
   author (elements, attributes, egress globals/member calls, stylesheet
   extensions, deep-import segments). The portable prohibition rules cite it
   structurally (the `restricted_surface` catalog field); which sanctioned
   component answers each primitive is per-stack configuration.
7. **The residual ratchet** (`corpus/RESIDUALS.json`) — the statically-erased
   or renamed forms deliberately outside the corpus contract, per rule, as
   shrink-only data (see "Detector boundaries" below).
8. **The scorecard format** (`scorecard.schema.json`) — the machine-readable
   certification summary a conformant checker emits (spec version, per-rule
   verdicts over the corpus, residuals claimed), so "certified against spec
   X.Y.Z" is a verifiable artifact instead of a claim.
9. **The changelog** (`CHANGELOG.md`) — the change history keyed to `VERSION`
   (the top entry must match, held by the spec suite), so a checker certified
   against an earlier version can see exactly what changed since.
10. **The rule pages** (`docs/rules/`) — plain-language documentation generated
    from the catalog (`tools/generate_rule_docs.py`; regenerate-and-compare
    parity in the spec suite, so the pages cannot drift from the data).

Everything is locked to the live implementations by build-time parity tests
(`tests/architecture/test_spec_catalog.py`, `tests/architecture/test_spec_corpus.py`,
`packages/frontend/eslint-boundaries/src/corpus.test.js` and
`packages/frontend/eslint-boundaries/src/surface.test.js` — the latter holds the
reference adapter to `restricted-surface.json` both structurally and
behaviourally), following the
same "docs can't lie" discipline as the rest of the gate: a rule cannot ship
without a catalog entry, a catalog entry cannot outlive its rule, and every
enforcement reference must resolve to real code.

## Scope: what the standard claims — and delegates

The catalog is **Terp-specific secure architecture, not complete application
security**. A rule is admitted only when Terp provides a *privileged seam* or
a *more precise invariant* than a generic analyzer can state — a framework
chokepoint to pair with (`runtime.applicability: required`), a
refused-surface entry, a trait/registry the rule holds code to. Generic
vulnerability classes that stock security analyzers already detect well
(command injection, unsafe deserialization, weak security randomness, …) are
**delegated, never duplicated**: a conformant toolchain
runs a generic security baseline for its language *next to* the Terp rules
(the reference stack pins ruff's bandit-derived `S` rules, wired into the
platform repo, the client template, and each generated project's own gate —
platform ADR 0085). Classes no stock analyzer detects well — path traversal,
secrets in logs, browser-storage auth material — are addressed
**constructively** by the reference framework (streamed storage behind
declared references, central log redaction, the session/refresh model) and
earn a detective catalog rule only through the same admission bar, never as a
checkbox. Baseline findings are **not** Terp findings: the finding
format's `rule` pattern admits only catalog ids, so a generic finding can
never masquerade as (or dilute) a Terp verdict — it travels as the baseline
tool's own output (or the envelope's `unattributed` bucket, ADR 0083).

Catalog entries deliberately carry **no CWE/OWASP mappings**: no governance
consumer exists for them, and the delegated baseline's own documentation
already maps the generic classes. Metadata joins the catalog when something
machine-consumes it, not before.

## Catalog format

`catalog/<surface>/<rule>.json`, validated against `catalog/schema.json` (the
schema is normative and travels with the spec). The normative statement of a
rule is its `title` + `intent`, and that prose is **stack-neutral by
construction**: plain prose, no docstring markup, no reference-implementation
symbols, package paths, marker spellings, or repo-internal pointers (sibling
rules are cited by catalog rule name). The reference realisation lives in the
non-normative fields (`enforcement`, `reference`, `opt_out`, `guide_topic`).
The standalone suite enforces the split
(`test_normative_prose_is_stack_neutral`).

| Field | Meaning |
|---|---|
| `id` | `<surface>/<rule>` — `backend/<snake_case>` (a `terp.arch` rule) or `frontend/<kebab-case>` (a boundary rule). **Findings are attributed to this id**, never to a tool-internal rule id. |
| `surface` | `backend` or `frontend`. |
| `title` | One-line statement of the invariant. |
| `intent` | Why the rule exists — the drift or threat it prevents. |
| `layer` | Cheapest faithful verification for a *new* stack: see below. |
| `enforcement` | How the reference implementation enforces it (first entry: the `build-time` check). A `runtime` entry names the fail-closed runtime control pairing with it (the two-layer discipline a Level 3 stack must reproduce for the rules that require it); a `black-box` entry names the `@terp/conformance` probe title. For frontend rules, `reported_as` is the ESLint rule id violations surface as — several catalog rules share one core rule id, so the adapter publishes a `catalogRuleId()` mapping and findings are attributed through it. |
| `runtime` | **Mandatory.** The rule's runtime-applicability classification (`required` / `not-applicable` / `deferred`) plus a `rationale` (mandatory for exemptions) and, for `deferred`, a `tracking` reference naming where the deferral is tracked — see “Runtime applicability” below. |
| `restricted_surface` | Frontend prohibition rules only: the `restricted-surface.json` keys the rule realises — the structural citation the spec suite resolves (every key must be claimed by some rule; a prose mention in `intent` must agree with the field). |
| `opt_out` | The *reference realisation* of the abstract escape-hatch contract (see below). |
| `reference` | Optional reference-implementation metadata: the compliant realisation the reference stack offers (component / helper names). **Not normative** — the `title` and `intent` state the stack-neutral invariant; another stack ships its own realisation. |
| `guide_topic` | Reference-implementation metadata (backend only): the `terp guide` topic teaching the compliant pattern. Not normative for other stacks. |
| `corpus` | Whether `corpus/<id>/` cases exist yet (the parity test holds this flag to the directory truth; a covered rule needs at least one `violation-*` **and** one `compliant-*` case). |

### Enforcement layers

- **`black-box`** — the invariant is observable by probing a *running* app
  (no source access needed). Portable to any stack via a conformance suite;
  each such rule names its probe in a `black-box` enforcement entry
  (`packages/frontend/conformance/tests/standard.spec.ts`).
- **`static-portable`** — expressible as source patterns a generic engine
  (Semgrep/ast-grep-class) can realise per language from this spec.
- **`static-bespoke`** — needs deep framework knowledge (traits, `ModuleSpec`,
  archetype slots); built per officially certified stack only.

The classification is a judgment about *porting cost*, not a limit on the
reference implementation — today every rule is enforced by `terp.arch` or
`@terp/eslint-boundaries` regardless of layer.

### Runtime applicability (the two-layer discipline, per rule)

Whether a rule *additionally* pairs with a fail-closed runtime control is not a
blanket claim — it is recorded per rule in the mandatory `runtime` block and
held coherent by the spec suite:

- **`required`** — the invariant is observable in the running system and the
  reference implementation owns a fail-closed control for it; the entry **must**
  declare that control as a `kind: "runtime"` enforcement entry (whose `ref`
  must resolve to a real symbol — the framework's parity test fails otherwise).
- **`not-applicable`** — the invariant is a property of the authored artifact
  (source form, imports, justification markers, checked-in files) that is
  erased or already materialised by the time the app runs, so no runtime seam
  can enforce it. The mandatory `rationale` states why; the build-time check is
  the control, by recorded decision.
- **`deferred`** — a runtime control would add independent fidelity on a seam
  the reference framework owns, but has not shipped yet: an explicit, reviewed
  gap, never a silent one. The mandatory `rationale` names the seam, and the
  mandatory `tracking` reference names where the deferral is tracked (an issue
  URL or the reference implementation's tracker document plus the seam) — so a
  deferral has a lifecycle instead of being open-ended.

Fail-closed consistency (spec suite): `required` iff a `runtime` enforcement
entry exists; an exemption always carries a non-empty rationale; a deferral
always carries a tracking reference.

### The escape-hatch contract

Every rule has **at most one** governed opt-out, and its *semantics* are the
normative part: a **justified inline marker** on (or immediately above) the
violating line that names the **catalog rule name** (the `<rule>` half of the
id — never a tool-internal rule id, mirroring findings attribution) and states
a reason; an unjustified marker is itself a violation; marker counts must
exactly match a checked-in per-app budget that can only shrink (the ratchet).
The `opt_out` field records the reference realisation's concrete spelling
(`# arch-allow-<rule>: <reason>` in Python, `// terp-allow-<rule>: <reason>`
in TypeScript) — the spelling is derived from the rule id, and the spec suite
holds the derivation. The escape-hatch **governance rules themselves** (the
budget ratchet, the ungoverned-marker condition) carry no `opt_out`:
governance cannot be waived by the mechanism it governs. Another stack
implements the same contract with its own comment syntax.

The `<reason>` is free text, and MAY carry structured metadata tokens so a
long-lived exception stays visible and auditable rather than eternal:
`owner:<who>` (who answers for the exception), `ticket:<ref>` (where its
removal is tracked), and `review-by:<YYYY-MM-DD>` (when it must be re-justified).
The tokens are a convention, not a gate — the marker's semantics are unchanged,
and a checker MUST NOT reject a reason without them — but a toolchain SHOULD
surface expired `review-by:` dates in its reporting.

## Finding format

A conformant checker emits an array of findings per checked tree, shaped by
`findings.schema.json`: each finding names the **catalog rule id** it realises
(`rule`), the file `path` relative to the checked tree's root, and optionally a
`line`, a directive `message`, a `fix_hint` (the compliant construct, for agent
consumers acting on findings without re-reading the catalog), and a
`fingerprint` (a stable, checker-chosen per-instance identifier so a finding
can be tracked across line-shifting edits). Attribution is always to the
stack-neutral catalog id — the reference ESLint adapter, whose core rule ids
are shared between several catalog rules, publishes this mapping as
`catalogRuleId()` in `@terp/eslint-boundaries`.

## Check-report format

Findings alone cannot support a per-rule verdict: a rule with zero findings is
only *passing* if the run actually evaluated it, and the consumer must never
supply that knowledge itself — its own catalog copy can be newer or older than
the checked app's pinned toolchain (version skew), and some enforcement is
conditional (an escape-hatch budget only when one is checked in, a layout
contract only when the app opts in). So a conformant checker reports a whole
run as one **application check report** (`app-check-report.schema.json`): a
format marker (`terp_check_report: 1`), the **spec version** its rule ids
resolve against, the **checker identity** (the same identity its certification
scorecard carries), the run **verdict** (`ok`, or an explicit `error` for a
run that failed to complete — an erroring run never claims ok and never claims
rules it did not finish evaluating), the **evaluated-rule inventory**
(`rules`), the opt-in rules published as **`not_applicable`** (their own
state — never passing, never unknown), the **findings** (exactly the finding
format's item shape — the spec suite holds the two identical), and
**`unattributed`** messages (diagnostics outside the standard, surfaced rather
than dropped). A consumer joins per-rule verdicts to the catalog exclusively
through the report's inventory, fail closed: pass = evaluated with no
attributed finding; a rule the run did not publish renders unknown, never
green. A multi-surface toolchain emits one report per checker run and a
consumer merges reports through their inventories.

## Scorecard format

A checker claiming certification emits a scorecard (`scorecard.schema.json`):
the spec version it certified against, the checker's identity, and one entry
per claimed rule with its pass/fail verdict over the corpus and the residuals
it relies on (which must be a subset of `corpus/RESIDUALS.json` for the rule —
claiming an unrecorded residual is a conformance failure). A consumer can
re-run the corpus and reproduce the scorecard, making the certification claim
verifiable.

## Corpus format

```text
corpus/backend/<rule>/violation-01/  # files rooted at the app package root
corpus/backend/<rule>/compliant-01/  #   e.g. modules/notes/service.py
corpus/frontend/<rule>/violation-01/ # files rooted at the frontend app root
corpus/frontend/<rule>/compliant-01/ #   e.g. src/modules/widgets/Widget.tsx
```

A case may ship an extra checker input at its root when the rule takes one:
the `backend/escape_hatch_budget` cases carry the `escape-hatch-budget.json`
the ratchet is verified against, and a frontend layout-contract case activates
via a `layout-contract.json` at its root.

A violation case MAY additionally ship an **`expected-findings.json`** at its
root: the exact findings (rule + path + line, shaped by
`findings.schema.json`) a maximally-precise checker emits for the rule under
test. A harness may assert the manifest exactly — hardening the per-case
contract from "flags something" to "flags the right line" — while the loose
contract below remains the floor for cases without one (and the ceiling a
checker must reach to conform). The spec suite holds every checked-in manifest
to the finding shape and to the case it sits in.

The contract for a checker claiming conformance for a rule is stated **per
rule**, over the finding format above:

- every `violation-*` case produces at least one finding attributed to that
  rule's catalog id, and
- every `compliant-*` case produces **no** findings for that rule.

A compliant case is minimal, not a full application — it may legitimately be
incomplete with respect to *other* rules, so a multi-rule checker scopes the
corpus run to the rule under test. (The reference frontend harness happens to
hold its compliant cases fully clean across all boundary rules — a stricter
bar than the contract requires.)

### Detector boundaries (what the corpus deliberately does not require)

The executable corpus **is** the interoperability contract: a checker is
conformant for a rule when it flags every `violation-*` case and stays silent
on every `compliant-*` case — nothing more. The violation cases include the
evasion shapes the rules are expected to see through (qualified/attribute
calls, multiline constructs, values routed through a local variable or
`.format()`/`%` building, aliased and parenthesized imports, computed
`window["fetch"]`-style member access for the egress family), and the
compliant cases pin the near-misses that must **not** fire (adjacent-literal
SQL that merely looks concatenated, credential-shaped names with dynamic
values, `*_mock`/`socketserver`-style name cousins, member calls like
`repo.fetch(...)` / `interpreter.eval(...)` on local objects, forbidden syntax
quoted inside comments and strings).

Some statically-erased or renamed forms are **deliberately outside** the
contract — known limits of precise, low-false-positive detection, kept out of
the corpus so a second implementation neither over-fits nor under-claims.
These residuals are recorded per rule in **`corpus/RESIDUALS.json`** — a
machine-readable ratchet governed like `corpus/PENDING.json`: the list only
shrinks, and closing a residual means seeding the corpus case that contracts
it and deleting the entry, never silently. Today it records:

- an alias-renamed symbol import (`from sqlalchemy import text as sql_text`)
  is not required to be resolved to `text`;
- dynamic import (`importlib.import_module("httpx")`) is not required to be
  seen as an import;
- a computed sink or global (`el["innerHTML"] = …`, `window["eval"]`) is not
  required to be recognised for the *eval/DOM-sink* rules (the egress family
  **does** contract the computed forms — its cases include them);
- `Function("…")` called without `new`, and egress through receivers other
  than `window`/`globalThis` (`self.fetch`), are not required.

These residuals are governed the usual way: the escape-hatch contract makes
sanctioned exceptions visible, and the paired runtime controls (where
`runtime.applicability` is `required`) hold the invariant regardless of
spelling. Widening a detector past the contract is always allowed — the
corpus states the floor, not the ceiling.

The reference implementations are themselves held to this contract in CI:
`test_spec_corpus.py` runs each catalogued `terp.arch` rule over the backend
corpus, and `corpus.test.js` runs the ESLint adapter over the frontend corpus,
attributing findings via `catalogRuleId()`. Corpus sample files are
intentionally violating code — they are excluded from repo-wide lint
(`ruff` `extend-exclude`) and are never imported or executed.

Coverage is governed by **`corpus/PENDING.json`**: the exact list of rules
still without cases. Seeding a rule's corpus removes it from the list; a new
rule shipped without corpus must be listed there explicitly — so uncovered
rules stay visible and the list only shrinks. Every `static-portable` backend
rule must have cases (enforced by the parity test); today every backend and
frontend rule has cases and the pending list is empty — it exists so a *new*
rule can ship with its gap explicit and reviewed.

## Conformance levels

- **Level 1 — black-box:** the app passes the runnable conformance suite
  (`@terp/conformance`) for the capabilities it claims, including the
  `standard:` probes the `black-box` catalog entries name.
- **Level 2 — static rule pack:** additionally, a checker validated against
  this corpus enforces the `static-portable` rules for the app's language(s),
  emitting findings per `findings.schema.json`.
- **Level 3 — full harness:** additionally, the `static-bespoke` rules, the
  paired `runtime` controls of every rule whose `runtime.applicability` is
  `required`, and the governed escape-hatch budget ratchet are enforced (today:
  the `terp.arch` + `@terp/eslint-boundaries` reference harness on top of
  `terp.core` / `@terp/react-core`).

## Growing the spec

- **New rule** → ship the rule and its catalog entry together (the parity test
  fails otherwise); classify its runtime applicability deliberately (`required`
  with the declared control, or an exemption with its rationale — a deferral
  also names its `tracking` reference); seed corpus cases when the rule is
  portable, or list it in `corpus/PENDING.json` explicitly; regenerate the
  rule pages (`python tools/generate_rule_docs.py`).
- **New corpus cases** → add `violation-*`/`compliant-*` directories, flip the
  entry's `corpus` flag to `true`, and drop the rule from `corpus/PENDING.json`;
  the harness picks the cases up by convention. Ship an `expected-findings.json`
  when the violating lines are pinned. Closing a documented detector residual
  also deletes its `corpus/RESIDUALS.json` entry.
- **New stack** → implement the `static-portable` rules however you like; the
  corpus is the acceptance test, findings must attribute to catalog ids, and
  the certification summary is a scorecard (`scorecard.schema.json`).
- **Format change** → bump `VERSION` and add the matching `CHANGELOG.md` entry
  (the suite holds the top entry to the version). Pre-1.0, a **changed
  contract** — a new mandatory catalog field (0.5.0's `runtime` block), a
  changed finding shape —
  bumps the **minor** (the strongest signal 0.x semver carries; a 0.x major
  would claim a stability this spec does not yet promise); purely additive
  fields and new rules also bump the minor; prose bumps the patch. From 1.0.0
  a changed contract bumps the **major**.
