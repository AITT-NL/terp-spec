# Contributing to terp-spec

This repository holds the **contracts** Terp's programs read: the deployment,
workbench and layout declarations, the finding and check-report formats, the
assurance profile and the conversation event stream. A contract is here because
more than one program reads it. The rules, their corpus and the checks that hold
them are the framework's own and live in `terp-framework` (its ADR 0203). This
repository is deliberately self-contained — plain JSON, no `terp.*` imports.

## This repository is public

`terp-spec` is public on GitHub and publishes to PyPI (`terp-spec`) and npm
(`@terpjs/spec`).

**Never name an application built on Terp, its owner, or its client** — not in a
schema description, a fixture, the CHANGELOG, a commit subject or body, or a pull
request title or description. A contract's rationale is about the failure it
prevents — "a deploy tool that reads a field the app never declared" — not about
who hit it. The evidence travels just as well anonymous, and usually reads better.

Get it right the first time. Git history keeps the original text even after a
scrub, and a name that reaches a published package cannot be edited out of it —
only the whole release can be withdrawn. [`AGENTS.md`](AGENTS.md) carries the
full rule.

## Sign your work (Developer Certificate of Origin)

This project uses the
[Developer Certificate of Origin](https://developercertificate.org) rather than a
contributor licence agreement. The DCO is a statement that you have the right to
submit the change — it asks for no copyright assignment and grants nothing beyond
the Apache-2.0 licence this repository already carries, so your contribution is
under the same terms as the rest of the work (Apache-2.0 §5).

Add a `Signed-off-by` line to each commit (`git commit -s` writes it):

```
Signed-off-by: Your Name <your.email@example.com>
```

## What a change here is judged against

- **A contract changes only for its readers.** Each schema names the programs
  that read it; a field joins when a reader needs it, with fixtures that state
  what is valid and what each refusal names, so every reader runs the same cases.
- **The schemas stay inside the validator subset** in `tests/schema_subset.py`:
  the smallest consumer available must be able to apply them.
- **Both packaging manifests ship exactly what is on disk.**
  `tests/test_contracts.py` refuses an artifact either manifest misses, and an
  entry with nothing behind it.

A rule, its corpus cases and its catalog entry land in `terp-framework`, in one
pull request with the check that enforces it.

## Versioning and releasing

`VERSION` is the semver of the contracts and the top `CHANGELOG.md` entry must
equal it. Pre-1.0: a changed contract bumps the minor, additive fields bump the
minor, prose bumps the patch.

```bash
python -m pytest tests/ -q
```

No CI job here checks out another repository. A release is a `vX.Y.Z` tag on a
merged commit; `release.yml` verifies it and publishes both packages. Each reader
then moves its own pin: the framework (`terp-spec` and `@terpjs/spec` together),
Studio and the runner.

## Reporting a vulnerability

Do not open a public issue for a security problem. Report it privately through
GitHub's security advisories for this repository. [SECURITY.md](SECURITY.md) says
how, and how soon you hear back.
