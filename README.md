<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/assets/terp-logo-dark.svg" />
  <img src="docs/assets/terp-logo.svg" alt="Terp" width="264" height="106" />
</picture>

# terp-spec — the contracts Terp's programs read

This repository holds the documents more than one Terp program reads: the
declarations an app checks in, the formats a checker reports in, the assurance
profile a release states, and the event stream a conversation produces. Each is a
JSON Schema, and where readers must agree on how a file reads, a set of fixtures
every reader runs. The repository is deliberately self-contained (no `terp.*`
imports, plain JSON) and consumed as a **package**, never a repo path (ADR 0082).

**The rules are not here.** The rule catalog, its corpus, the refused surface, the
rule pages and the runtime security cases are the framework's own, and live in
[terp-framework](https://github.com/AITT-NL/terp-framework) beside the checkers
that enforce them (framework ADR 0203): the backend half ships with `terp-arch`,
the frontend half with `@terpjs/eslint-boundaries`. Terp is a Python and React
framework, and no stack-neutral standard or certification is offered. Up to 0.43.0
this package also carried the rules; their history is in this repository's git log
and in [CHANGELOG.md](CHANGELOG.md).

## The package seam (ADR 0082)

The directory doubles as two thin distributions over one data set:

- **`terp-spec`** (Python, `pyproject.toml`): a dependency-free `terp_spec`
  accessor — `spec_dir()` returns the on-disk root, `spec_version()` the `VERSION`
  semver.
- **`@terpjs/spec`** (npm, `package.json`): data only; consumers resolve the root
  via `require.resolve("@terpjs/spec/package.json")`.

Both are **published from the tag workflow** (ADR 0086) — `terp-spec` on PyPI,
`@terpjs/spec` on npm, via Trusted Publishing (OIDC), so a reader pins an ordinary
version. Both manifests carry `VERSION`, which is independent of the framework's
lockstep release version: Studio and the runner read these contracts without
depending on the framework. The suite here (`python -m pytest`) holds the three
version declarations equal and both manifests to exactly the artifacts on disk,
and no CI job checks out another repository.

The readers: the framework (its checks, its generator and its CLI), Studio, and the
runner. Each pins a published release and moves its pin on its own.

The artifacts:

1. **`VERSION`** — the semver of the contracts.
2. **The finding format** (`findings.schema.json`) — what a checker emits per
   finding, attributed to a rule id from the framework's catalog.
3. **The check-report format** (`app-check-report.schema.json`) — the complete
   result of one checker invocation over one application tree: the finding format
   plus the run's own evaluated-rule inventory, format version, checker identity
   and verdict, so a driving tool can join per-rule verdicts to the catalog
   fail-closed.
4. **The layout declaration** (`layout-declaration.schema.json`) — the schema for
   the document an app checks in to declare which slot-typed page contract it opts
   into, which palette it starts on, and how its application shell is shaped
   (content measure, density, navigation placement, the navigation groups a
   module's items name by id, and the mark the app is recognised by). One
   document, so a build-time check and the running app read the same bytes and
   neither can hold a different answer — and so a tool that edits files rather
   than code can read and rewrite those choices.
5. **The deployment declaration** (`deployment-declaration.schema.json`, with
   `deployment-declaration.fixtures.json`) — the schema for the `deployment.json`
   an app checks in at its project root to declare its deployable units, and the
   fixtures every reader of it runs. See "Deployment declaration" below.
6. **The development-loop declaration** (`workbench-declaration.schema.json`, with
   `workbench-declaration.fixtures.json`) — the vocabulary of the `workbench.json`
   an app checks in to say which parts of its development loop a tool that drives
   it relies on, and the fixtures every reader of it runs. See "Development-loop
   declaration" below.
7. **The conversation event stream** (`conversation-events.schema.json`, with
   `conversation-events.fixtures.json`) — the vocabulary of the events one run of a
   conversation streams to the people following it: a profile of AG-UI 1.0 and the
   names Terp adds where AG-UI leaves a name open, with recorded runs every
   producer and reader runs. See "Conversation event stream" below.
8. **The assurance profile** (`assurance-profile.schema.json`) — the
   machine-readable release-assurance claim a toolchain emits from its release
   verification profile. See "Assurance profile" below.
9. **The changelog** (`CHANGELOG.md`) — the change history keyed to `VERSION` (the
   top entry must match), so a reader pinned to an earlier version can see exactly
   what changed since.

## Finding format

A conformant checker emits an array of findings per checked tree, shaped by
`findings.schema.json`: each finding names the **catalog rule id** it realises
(`rule`), the file `path` relative to the checked tree's root, and optionally a
`line`, a directive `message`, a `fix_hint` (the compliant construct, for agent
consumers acting on findings without re-reading the catalog), and a
`fingerprint` (a stable, checker-chosen per-instance identifier so a finding
can be tracked across line-shifting edits). Attribution is always to the
catalog id — the framework's ESLint adapter, whose core rule ids are shared
between several catalog rules, publishes this mapping as `catalogRuleId()` in
`@terpjs/eslint-boundaries`.

## Check-report format

Findings alone cannot support a per-rule verdict: a rule with zero findings is
only *passing* if the run actually evaluated it, and the consumer must never
supply that knowledge itself — its own catalog copy can be newer or older than
the checked app's pinned toolchain (version skew), and some enforcement is
conditional (an escape-hatch budget only when one is checked in, a layout
contract only when the app opts in). So a conformant checker reports a whole
run as one **application check report** (`app-check-report.schema.json`): a
format marker (`terp_check_report: 1`), the **spec version** — the release of this
package whose check-report format it follows; its rule ids resolve against the
catalog the checker ships — the **checker identity**, the run **verdict** (`ok`,
or an explicit `error` for a run that failed to complete — an erroring run never
claims ok and never claims rules it did not finish evaluating), the
**evaluated-rule inventory** (`rules`), the opt-in rules published as
**`not_applicable`** (their own state — never passing, never unknown), the
**findings** (exactly the finding format's item shape — the suite holds the two
identical), and **`unattributed`** messages (diagnostics outside the catalog,
surfaced rather than dropped). A consumer joins per-rule verdicts to the catalog exclusively
through the report's inventory, fail closed: pass = evaluated with no
attributed finding; a rule the run did not publish renders unknown, never
green. A multi-surface toolchain emits one report per checker run and a
consumer merges reports through their inventories.

## Assurance profile

The framework's rule checks prove the *Terp-specific* half of release readiness.
The **assurance profile** (`assurance-profile.schema.json`) is the
machine-readable composition of that with the generic evidence lanes a release
also stands on — one document a toolchain emits from its release verification
profile, so "this build is releasable" becomes a checkable artifact instead of
a habit.

The lane vocabulary and each lane's requirement level are **normative** and
fixed here — an emitter cannot demote a required lane, which is why the
requirement level is deliberately not a field of the document:

| Lane | Requirement | Evidence |
|---|---|---|
| `terp-standard` | **required** | The rule catalog's enforcement surfaces ran and passed: the architecture gate and the frontend boundary lint, publishing their evaluated-rule inventories (check reports). |
| `appsec-baseline` | **required** | The delegated generic AppSec baseline passed (the reference realisation: `ruff` with the flake8-bandit `S` rules). |
| `dependency-audit` | **required** | Dependency trees were audited against known-vulnerability databases (the reference realisation: `pip-audit` and `npm audit`). |
| `secret-scanning` | **required** | The repository was scanned for committed credentials, **including its history** (the reference realisation: `gitleaks detect`). A source rule can only see the working tree, so this is the only lane that answers for a secret that was committed and then removed — which is still a leak, and is the common shape. |
| `a11y` | recommended | Automated accessibility checks over the running app (e.g. axe). |
| `blackbox-conformance` | recommended | The black-box behavioural conformance suite over the running workbench. |
| `test-adequacy` | recommended | The test suite was shown able to *fail*: a deliberate change to the code under test is caught by it (the reference realisation: diff-scoped mutation testing). Coverage does not evidence this lane — it reports which lines ran, not whether anything would have noticed them changing. |

`test-adequacy` is the lane that asks a question none of the others do:
**could this suite have failed?** Every other lane runs checks and reports their
verdicts; all six can be green over a suite that asserts nothing meaningful.
The catalog reaches the *syntactic* form of that — `no_empty_tests` refuses an
empty body, a bare `pass`, a constant assertion — and by construction cannot
reach the semantic form, a test whose assertion is trivially satisfied by the
path it exercises. A boundary test goes vacuous the moment the boundary it was
named for moves, and stays green while it does.

Only a deliberate change to the code under test settles it, which is why this is
a lane and not a rule: it is a different *kind* of enforcement from the
build-time/runtime pair every catalog rule declares. **Coverage is not this
lane.** Coverage reports which lines ran; adequacy asks whether anything would
have noticed them changing, and a line can be covered by a test that would pass
however it behaved.

The claim (`ok`) is true exactly when every **required** lane passed;
recommended lanes inform the reader but never carry the claim. Every lane of
the vocabulary appears exactly once — a lane the toolchain does not realise is
reported `not-run` (with no composing checks), never dropped and never counted
as passed. Each realised lane names the verification-check ids whose verdicts
compose it, so a consumer can trace the claim into the toolchain's own
verification envelope.

## Deployment declaration

A tool that deploys an app has to know which units exist, which one serves the
API, how to tell each is healthy, which migration histories each owns, what
holds state and how it is backed up, and what a rollback is. A tool that
assumes one template's service names is guessing, and the guess fails silently
the first day an app adds a worker, a shared store or a second deployable. So
the app says so, in `deployment.json` at its project root, written in the
vocabulary `deployment-declaration.schema.json` fixes. Nothing in it is read by
the running app; its readers are the app's own gate and the tools that drive a
deploy, which read it as data and never import the app.

A file sits in exactly one of four states:

| State | The file | The check | A deploy tool |
|---|---|---|---|
| Undeclared | absent | passes | may decline to drive the app, and says so |
| Own | `"build": "own"` | runs | drives units built from the committed profile and build files |
| Generated | `"build": "generated"` | runs | drives units whose build files a generator of the stack renders |
| Opted out | `{"unmanaged": true, "reason": "..."}` | off; a blank reason is refused | does not drive the app, and shows the reason |

It is a **partial** description: a service it does not name is not its
business, a role nobody has heard of is information, and no rule asks whether a
topology is approved. Every fact another file owns stays there — the profile
owns commands, start order, images and volumes; the variable manifest owns
variables; the code owns jobs and schedules; the environment's record owns
domains, TLS, the backup destination and its credentials, sizes and instance
counts per environment, and the image-digest allowlist. Where the declaration
restates such a fact, the owner wins and a disagreement is refused.

Three rules check it, and the schema is what the first one reads:

- **`backend/deployment_declaration_is_readable`** — every reader reads the
  file the same way, or refuses it: valid against the schema, in exactly one
  state, with no key the vocabulary lacks (a `$`-prefixed annotation excepted),
  no free image field, no shell-string command, no control character and no
  string past its cap, no path that resolves outside the checkout, never the
  development profile, and coherent with itself. A key for **deploy policy** —
  who may publish, how many approvals a deploy needs, who may reach a deployed
  app, which gate policy applies — is refused with its own message, because
  anyone who can commit to the app could lower a policy kept there; the schema
  names those keys (`$defs.deployPolicyKeys`) so every reader gives that message.
- **`backend/deployment_declaration_tells_the_truth`** — what the declaration
  says is true of the deployment profile it names (read with its overrides as
  one resolved profile) and of the app: units, volumes, variables passed,
  restated commands and start order, datastore images pinned to the stack's
  published digest, every other unit built from the checkout, migration
  histories and health paths, and a volume's restated mount. The app-side half
  needs the composed app and skips with a named note where none can be loaded.
- **`backend/deployment_generated_files_match_their_render`** — in the generated
  state, every build file the stack's generator owns is byte for byte what it
  renders from the declaration, the project's name and the framework release's
  tables, a path it owns but does not render is absent, the environment files a
  generated unit loads stay out of version control and the build context, the
  project's name is one the container tooling accepts, and the build the app's
  template recorded agrees. A declaration the generator cannot render is red here,
  naming the refusal and `own` as the way out. Silent in every other state.

**The generator's words.** Two words exist for the generated state. `generator`
holds what only a generator reads, and is valid nowhere else: beside `own` it is
refused, because nothing would honour it. It has two words.
`generator.systemPackages` names operating-system packages from a closed
system-package table the stack publishes, one pinned source per entry, as the
datastore table does for images; a reader refuses a name its table does not carry
and names the ones it does, so a stack whose table is empty refuses every name,
and the pattern refuses a name that could be read as an option.
`generator.recipes` (`{"site": "static-site"}`) maps a web unit's id to the
recipe its image is built from. A recipe is a name and nothing else: what its
build takes and how its image serves the result is the stack's to fix, so two
apps that name one recipe get one build. `static-site` is the only recipe, and a
reader refuses a key that names no declared web unit, naming the web units the
file declares. A web unit with no entry is built as the app's own web tier is.
`volumes[].mount`
(`{"path": "var/files", "units": ["api", "worker"]}`) says where a volume is
mounted and on which declared units, always inside the app's `var/` directory
with no segment that begins with a dot. Under `own` it restates the profile,
which the truth rule holds it to; under `generated` it is what the generator
renders, and required. Which mount paths a stack's generator can render is that
stack's to say.

The schema also names, as data rather than prose, the role words it knows
(`$defs.knownRoles`) and the unit fields a reader resolves by role
(`$defs.roleResolvedFields`): under a role the vocabulary does not know, such a
field has no reader, and declaring it is refused. Every pattern ends in
`(?![\s\S])` rather than `$`, because in some regular-expression engines `$`
also matches before a final newline — which would let a newline through the very
patterns that exist to refuse control characters.

**Which datastore kinds, versions and digests exist is per stack**: each
framework release publishes a closed table, one digest per kind and version, and
a reader refuses a kind or version its table does not carry. The table states
which digests a framework version accepts; whether an environment accepts them
is that environment's own allowlist, outside the file.

`deployment-declaration.fixtures.json` holds what every reader runs beside the
framework's corpus: for each violation case of the three rules, the **field** the
refusal is about and the **values that field allows**, so a reader's test asserts
its message names both; and the path escapes a corpus case cannot carry — a symbolic
link out of the checkout, and a build context that is inside a version-control
work tree but outside the project root — as trees a reader's own test builds on
disk, because a wheel or a tarball carries no link and a corpus case is no work
tree.

A reader parses `deployment.json` strictly. A key written twice in one object and
a number that is no JSON number (`NaN`, an infinity) are each read by a lenient
parser, so the same bytes would be two documents to two readers; the fixtures
refuse both at `$`, the file itself, and a case that carries one holds a file that
is deliberately not strict JSON.

## Development-loop declaration

A tool that drives an app's development loop has to know which compose file
describes it, which service serves the interface and which the API, through
which variable each host port arrives, where the API says it is ready, and
through which variables the source root and the framing grant reach the
containers. A tool that assumes one template's names is guessing, and the guess
fails silently the first time an app renames a variable. So the app says so, in
`workbench.json` at its project root, in the vocabulary
`workbench-declaration.schema.json` fixes. An app whose loop is not the compose
shape a tool assumes names its own commands there instead.

| State | The file | A reader |
|---|---|---|
| Undeclared | absent | assumes the conventions of the template the app came from |
| Declared | `schemaVersion` and `services` | reads it, and refuses what it would act on wrongly |
| Opted out | `{"unmanaged": true, "reason": "..."}` | does not interpret the loop, and shows the reason |

It is a **partial** description, and unlike the deployment declaration its
objects are open: a service it does not name, a role nobody has heard of and a
key the vocabulary lacks (an app's own note, a key another tool invented) are
never refused. What is refused is a value a reader would act on wrongly. Four of
those the schema's keyword subset cannot state, so it names their lists in
`$defs` and every reader applies them: a field resolved by role
(`roleResolvedFields`) under a role no reader looks up (`knownRoles`); a
variable a reader would set whose name the container toolchain or the process
environment reads for itself (`reservedEnvironmentPrefixes`,
`reservedEnvironmentNames`), because a reader puts every declared name into the
environment of the commands it runs; and a compose file named as a deployment
profile (`deploymentProfileMarkers`). The command slots are the `commands`
block's properties, and any command declared means a `start` is declared.

**An unreadable declaration is not an absent one.** A reader that meets a
`schemaVersion` it does not know, or a file it cannot read, refuses it and says
why; it never falls back to the conventions it would assume for an absent file,
because an app that renamed a variable and then broke its JSON would get the old
name set, and a stack started on a guess. The template seeds the file once and
the app owns it afterwards, so a later version reaches an existing app only
through an adoption step the app runs, never by an upgrade overwriting it.

**A vocabulary, not a rule.** No catalog entry realises it. What the framework's
own gate does with the file - hold it to the compose file it names - is a check
of its development loop, which another reader need not have in this shape; what every reader must agree on is how the file itself reads, and
`workbench-declaration.fixtures.json` fixes that: valid documents with what a
reader resolves from them (`reads`), invalid ones with the field the refusal is
about and the values it allows, and texts that are not one JSON document. The
suite reads every fixture with a reference reader of the `$defs` lists, and holds
the list of vocabularies read by fixtures by name.

## Conversation event stream

An application that lets a person talk to an assistant streams each run of the
assistant to the people following it: the reply as it is written, each tool
call as a row on a timeline, a question the assistant asks before it can go on,
and how the run ended. The producer that runs the assistant and the client that
shows it are separate programs, often in separate stacks, and each wrote its own
idea of the frames once; the words now live here, in
`conversation-events.schema.json`.

**It is a profile of AG-UI 1.0** (the Agent-User Interaction Protocol), not a
protocol of its own: every event is an AG-UI event, so a client written for
AG-UI reads a Terp stream unchanged, and an agent that speaks AG-UI can sit
behind a Terp producer. The profile says three things AG-UI leaves open:

- **Which events a Terp stream carries** — twelve, closed: `RUN_STARTED`, the
  text message trio, the tool call quartet (start, args, end, result),
  `ACTIVITY_SNAPSHOT`, `CUSTOM`, `RUN_FINISHED` and `RUN_ERROR`. Raw provider
  events, state snapshots, reasoning, subagents and the convenience chunks are
  not in version 1.
- **What every event must carry, and how long it may be** — every object is
  closed but three, which AG-UI carries opaquely and the event rules reach
  inside (an interrupt's `responseSchema`, a producer's own activity `content`
  and a `CUSTOM` event's `value`), every string is capped and refuses control
  characters (prose keeps its tabs and line breaks), an outcome is always
  stated, an interrupt outcome carries exactly one interrupt because a
  conversation has at most one open question, and an event is at most
  `maxEventBytes` of compact UTF-8 JSON and `maxEventDepth` levels of objects
  and arrays.
- **What Terp adds where AG-UI leaves a name open** — `terp.compaction` as an
  activity type; `terp.context` (how full the assistant's memory is) and
  `terp.handoff` (another run follows, and which one when the producer knows)
  as custom events; `terp.question` as an interrupt reason, answered by
  buttons, a choice, several choices or a text; and a `metadata.terp` key where
  an event needs one: the vocabulary version on `RUN_STARTED`, the assistant's
  own sentence about a tool call, a tool result's status, and `steered` on a
  run cancelled for the next message.

| Name | A reader |
|---|---|
| under `terp.` | reads it as this vocabulary says, and refuses one the vocabulary does not define: the namespace is closed |
| any other | is the producer's own; a reader that does not know it shows nothing for it and acts on nothing |

**One event, one schema and four rules; a run, ten rules.** The schema validates
one event. What one event keeps that a schema cannot state is named in
`$defs.eventRules`: an interrupt's expiry names a day that exists, which a reader
checks itself because date parsers disagree, an event nests no deeper than
`maxEventDepth`, measured without recursion before anything walks it, no two
options of a question carry one value, and no string anywhere in the event, its
object keys and the open objects included, holds a control character.
The order a run keeps — opened by `RUN_STARTED`, closed by exactly one terminal
event, every text message and tool call opened before it is used and closed
before the run finishes, every reference to a message or a call known, a
message id and a tool call id one id space as they are to an AG-UI client, an
activity keeping its type — is named in `$defs.streamRules`, which every reader
applies because a schema cannot state it. A reader that meets an event it cannot
validate, or a run that breaks a rule, stops interpreting the run there: it keeps
what it read before, reads the run as failed, and says so. It never guesses past
a broken stream. Where one event breaks several rules, a reader reports the
first of them in the list's order, so every reader names the same one.

**An unreadable version is not an empty one.** `RUN_STARTED` carries
`metadata.terp.schemaVersion`. A reader that does not know the version reads
nothing from the run and says the stream is from a newer version; a producer
writes a version only once the readers it serves read it — readers first,
writers last, as for the declarations above.

**A vocabulary, not a rule.** No catalog entry realises it: what a producer
stores or how a client lays a conversation out is each stack's own. What every
producer and reader must agree on is how a stream reads, and
`conversation-events.fixtures.json` fixes that: single events, valid or refused
at a named field (by the schema, or by the event rule the fixture names), and
recorded runs, each valid one with what a reader resolves
from it (`reads`: the transcript items in order, the outcome, the open
question, the memory fill, the usage, the run that follows, the failure), each
invalid one with the one rule it breaks and the event where it breaks it. The
suite reads every fixture with a reference reader of the stream rules.

## Changing a contract

- **A contract changes for its readers.** A field joins when a reader needs it,
  with fixtures that state what is valid and what each refusal names, so every
  reader runs the same cases. A reader adopts a new release by moving its own pin;
  a producer writes a new value only once the readers it serves read it — readers
  first, writers last.
- **The schemas stay inside the validator subset** (`tests/schema_subset.py`), so
  the smallest consumer available can apply them.
- **Every change bumps `VERSION`** and adds the matching `CHANGELOG.md` entry (the
  suite holds the top entry to the version). Pre-1.0, a **changed contract** — a
  new mandatory field, a changed finding shape, a removed artifact — bumps the
  **minor** (the strongest signal 0.x semver carries); purely additive fields also
  bump the minor; prose bumps the patch. From 1.0.0 a changed contract bumps the
  **major**.
- **A rule never lands here.** A new rule lands in terp-framework, in one pull
  request with its check, its catalog entry, its corpus cases and its page.
