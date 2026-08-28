# AGENTS.md — the Terp Standard

Instructions for **all** AI coding agents (Copilot, Claude, Cursor, Codex, …)
working in this repository. Read this before any non-trivial change.

## This repository is public

`terp-spec` is public on GitHub, and it publishes to PyPI (`terp-spec`) and npm
(`@terpjs/spec`).

**Never name a downstream application, its owner, or its client in anything that
lands here.** Not in a catalog entry, a corpus sample, a rule's `intent` or
`reference` prose, the CHANGELOG, a commit subject or body, or a PR title or
description. The apps built on Terp belong to someone, and their names are not
ours to publish.

Write the *friction* and the *evidence*, never the reporter. A rule's rationale
is about the failure it prevents — "a worker that reclaims a row another worker
still holds" — not about who hit it. The evidence travels just as well anonymous,
and usually reads better, because it describes the mistake instead of the person.

**Get it right the first time; a later scrub is incomplete by construction.** Git
history keeps the original text, the commit list shows the original subject, and
a name that reaches a published package cannot be edited out of it at all — only
the whole release can be withdrawn.

The places it actually gets in: a rule's narrative `intent`, a CHANGELOG entry
explaining why a rule was added, a corpus sample copied from real code, and
commit subjects and bodies (which no file scan will ever catch). If you need a
concrete example, invent a neutral one. If the point cannot be made without
naming someone, it is not general enough to belong in a specification.

## What this repository is

The **stack-neutral specification** of Terp's secure-by-default rules (ADR 0080,
made consumable by ADR 0081). `terp-framework` is the reference implementation;
this is what any other stack would implement and be verified against. It is
deliberately self-contained — plain JSON and sample files, no `terp.*` imports —
and is consumed as a **package**, never a repo path (ADR 0082).

## The ratchets — every one of them only shrinks

- **`catalog/<surface>/<rule>.json`** declares a rule. A new rule ships its
  catalog entry; ids are `backend/<name>` or `frontend/<name>`.
- **`corpus/<surface>/<rule>/`** holds violation and compliant samples. Adding
  cases flips the entry's `corpus` flag and drops the rule from the ratchet.
- **`corpus/PENDING.json`** — the coverage ratchet: rules with no corpus yet.
- **`corpus/RESIDUALS.json`** — the *detector*-residual ratchet: the forms a
  precise, low-false-positive checker deliberately does not catch, recorded as
  data so a second implementation neither over-fits nor over-claims. Closing one
  means seeding the corpus case that contracts it and deleting the entry, never
  silently. Every key must be a catalogued rule id, and the list is sorted.

## Versioning

`VERSION` is the semver of the standard, and the **top `CHANGELOG.md` entry must
equal it** (`tests/test_changelog.py`). `pyproject.toml` and `package.json` carry
the same value. Pre-1.0: a changed contract bumps the minor, additive fields and
new rules bump the minor, prose bumps the patch.

The spec version is deliberately independent of the framework's lockstep release
version, per ADR 0081's certification model.

## Run the gate

```bash
python -m pytest tests/ -q
```

Note the two repositories' CIs are **circularly coupled**: terp-spec's
`certify-against-reference` job checks out framework main and runs its parity
tests against this catalog, while the framework's gate installs the *pinned
published* terp-spec. So a new rule fails spec CI until framework main carries
the check, and fails framework CI until the spec version is released. Push spec
first, then the framework, then re-run spec CI.
