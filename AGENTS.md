# AGENTS.md — terp-spec, the contracts Terp's programs read

Instructions for **all** AI coding agents (Copilot, Claude, Cursor, Codex, …)
working in this repository. Read this before any non-trivial change.

## This repository is public

`terp-spec` is public on GitHub, and it publishes to PyPI (`terp-spec`) and npm
(`@terpjs/spec`).

**Never name a downstream application, its owner, or its client in anything that
lands here.** Not in a schema description, a fixture, the CHANGELOG, a commit
subject or body, or a PR title or description. The apps built on Terp belong to
someone, and their names are not ours to publish.

Write the *friction* and the *evidence*, never the reporter. A contract's
rationale is about the failure it prevents — "a deploy tool that reads a field the
app never declared" — not about who hit it. The evidence travels just as well
anonymous, and usually reads better, because it describes the mistake instead of
the person.

**When this actually happens.** Almost never from an outside contributor: they
have no application of ours to name. It happens when one person — or one agent
session — has a Terp repository and an application built on Terp open at the same
time, and a detail crosses over because it was on screen: a real variable name, a
real container, a real incident, quoted rather than invented. That is the moment
the rule exists for. If you are working both sides, write the example; do not
copy it.

**Get it right the first time; a later scrub is incomplete by construction.** Git
history keeps the original text, the commit list shows the original subject, and
a name that reaches a published package cannot be edited out of it at all — only
the whole release can be withdrawn.

The places it actually gets in: a schema `description`, a CHANGELOG entry
explaining why a field was added, a fixture copied from a real declaration, and
commit subjects and bodies (which no file scan will ever catch). If you need a
concrete example, invent a neutral one. If the point cannot be made without
naming someone, it is not general enough to belong in a shared contract.

## What this repository is

The contracts more than one Terp program reads: the deployment, workbench and
layout declarations, the finding and check-report formats, the assurance profile
and the conversation event stream, each a JSON Schema with the fixtures every
reader runs. It is deliberately self-contained — plain JSON, no `terp.*` imports —
and is consumed as a **package**, never a repo path (ADR 0082).

The rule catalog, its corpus and the checks that hold them are the framework's
own: they live in `terp-framework`, beside the checkers that enforce them
(framework ADR 0203). A new rule never lands here. The owner kept this package's
name, `terp-spec` / `@terpjs/spec`, on 2026-11-07, rather than the
`terp-contracts` ADR 0203 proposed, which sits one letter from the framework's
`@terpjs/contract` design-token package.

## What a change is judged against

- **A contract changes only for its readers**, and a field joins with fixtures
  that state what is valid and what each refusal names, so every reader runs the
  same cases.
- **The schemas stay inside the validator subset** in `tests/schema_subset.py`.
- **Both packaging manifests ship exactly what is on disk**
  (`tests/test_contracts.py`).

## Versioning

`VERSION` is the semver of the contracts, and the **top `CHANGELOG.md` entry must
equal it** (`tests/test_changelog.py`). `pyproject.toml` and `package.json` carry
the same value. Pre-1.0: a changed contract bumps the minor, additive fields bump
the minor, prose bumps the patch.

The version is deliberately independent of the framework's lockstep release
version: Studio and the runner read these contracts without depending on the
framework.

## Run the gate

```bash
python -m pytest tests/ -q
```

No CI job here checks out another repository, and nothing here waits on one. A
release is a `vX.Y.Z` tag on merged history; each reader then moves its own pin:
the framework (`terp-spec` in `pyproject.toml` and `@terpjs/spec` in
`packages/frontend/eslint-boundaries`, together), Studio and the runner. The
runner refuses an app checked against a release it does not carry, so a release
reaches it before any app pins a framework that reads that release.
