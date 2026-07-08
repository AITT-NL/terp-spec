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
that needs the live implementations. Splitting the spec out is then purely a
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
5. **The refused surface** (`restricted-surface.json`) — the stack-neutral,
   normative declaration of the raw frontend primitives an app module must not
   author (elements, attributes, egress globals/member calls, stylesheet
   extensions, deep-import segments). The portable prohibition rules cite it;
   which sanctioned component answers each primitive is per-stack configuration.

Everything is locked to the live implementations by build-time parity tests
(`tests/architecture/test_spec_catalog.py`, `tests/architecture/test_spec_corpus.py`,
`packages/frontend/eslint-boundaries/src/corpus.test.js` and
`packages/frontend/eslint-boundaries/src/surface.test.js` — the latter holds the
reference adapter to `restricted-surface.json` both structurally and
behaviourally), following the
same "docs can't lie" discipline as the rest of the gate: a rule cannot ship
without a catalog entry, a catalog entry cannot outlive its rule, and every
enforcement reference must resolve to real code.

## Catalog format

`catalog/<surface>/<rule>.json`, validated against `catalog/schema.json` (the
schema is normative and travels with the spec):

| Field | Meaning |
|---|---|
| `id` | `<surface>/<rule>` — `backend/<snake_case>` (a `terp.arch` rule) or `frontend/<kebab-case>` (a boundary rule). **Findings are attributed to this id**, never to a tool-internal rule id. |
| `surface` | `backend` or `frontend`. |
| `title` | One-line statement of the invariant. |
| `intent` | Why the rule exists — the drift or threat it prevents. |
| `layer` | Cheapest faithful verification for a *new* stack: see below. |
| `enforcement` | How the reference implementation enforces it (first entry: the `build-time` check). A `runtime` entry names the fail-closed runtime control pairing with it (the two-layer discipline a Level 3 stack must reproduce); a `black-box` entry names the `@terp/conformance` probe title. For frontend rules, `reported_as` is the ESLint rule id violations surface as — several catalog rules share one core rule id, so the adapter publishes a `catalogRuleId()` mapping and findings are attributed through it. |
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
`@terp/eslint-boundaries` regardless of layer, and each pairs with a
fail-closed runtime control per the two-layer discipline (recorded as a
`runtime` enforcement entry where the control is a distinct named seam).

### The escape-hatch contract

Every rule has exactly one governed opt-out, and its *semantics* are the
normative part: a **justified inline marker** on (or immediately above) the
violating line that names the rule and states a reason; an unjustified marker
is itself a violation; marker counts must exactly match a checked-in
per-app budget that can only shrink (the ratchet). The `opt_out` field records
the reference realisation's concrete spelling (`# arch-allow-<rule>: <reason>`
in Python, `// terp-allow-<rule>: <reason>` in TypeScript); another stack
implements the same contract with its own comment syntax.

## Finding format

A conformant checker emits an array of findings per checked tree, shaped by
`findings.schema.json`: each finding names the **catalog rule id** it realises
(`rule`), the file `path` relative to the checked tree's root, and optionally a
`line` and a directive `message`. Attribution is always to the stack-neutral
catalog id — the reference ESLint adapter, whose core rule ids are shared
between several catalog rules, publishes this mapping as `catalogRuleId()` in
`@terp/eslint-boundaries`.

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
  paired `runtime` controls, and the governed escape-hatch budget ratchet are
  enforced (today: the `terp.arch` + `@terp/eslint-boundaries` reference
  harness on top of `terp.core` / `@terp/react-core`).

## Growing the spec

- **New rule** → ship the rule and its catalog entry together (the parity test
  fails otherwise); seed corpus cases when the rule is portable, or list it in
  `corpus/PENDING.json` explicitly.
- **New corpus cases** → add `violation-*`/`compliant-*` directories, flip the
  entry's `corpus` flag to `true`, and drop the rule from `corpus/PENDING.json`;
  the harness picks the cases up by convention.
- **New stack** → implement the `static-portable` rules however you like; the
  corpus is the acceptance test, and findings must attribute to catalog ids.
- **Breaking format change** → bump `VERSION` (major for a changed contract,
  minor for new fields/rules, patch for prose).
