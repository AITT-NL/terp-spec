# Contributing to the Terp Standard

This repository is the stack-neutral **specification** of Terp's
secure-by-default rules. `terp-framework` is the reference implementation; this
is what any other stack would implement and be verified against. It is
deliberately self-contained — plain JSON and sample files, no `terp.*` imports.

## This repository is public

`terp-spec` is public on GitHub and publishes to PyPI (`terp-spec`) and npm
(`@terpjs/spec`).

**Never name an application built on Terp, its owner, or its client** — not in a
catalog entry, a corpus sample, a rule's `intent` or `reference` prose, the
CHANGELOG, a commit subject or body, or a pull request title or description. A
rule's rationale is about the failure it prevents — "a worker that reclaims a row
another worker still holds" — not about who hit it. The evidence travels just as
well anonymous, and usually reads better.

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

## The ratchets — every one of them only shrinks

A change here is judged against these, and they are the whole review:

- **`catalog/<surface>/<rule>.json`** declares a rule. A new rule ships its
  catalog entry; ids are `backend/<name>` or `frontend/<name>`.
- **`corpus/<surface>/<rule>/`** holds violation and compliant samples. Adding
  cases flips the entry's `corpus` flag and drops the rule from the ratchet.
  A compliant sample is not decoration: it contracts what a checker must *not*
  flag, which is how a second implementation avoids over-fitting.
- **`corpus/PENDING.json`** — rules with no corpus yet. It only shrinks.
- **`corpus/RESIDUALS.json`** — the forms a precise checker deliberately does not
  catch, recorded as data. Closing one means seeding the corpus case that
  contracts it and deleting the entry, never silently.

## Versioning and the release order

`VERSION` is the semver of the standard and the top `CHANGELOG.md` entry must
equal it. Pre-1.0: a changed contract bumps the minor, additive fields and new
rules bump the minor, prose bumps the patch.

```bash
python -m pytest tests/ -q
```

The two repositories' CIs are **circularly coupled**: this repository certifies
against a pinned commit of the reference implementation (`REFERENCE_SHA`), while
the framework's gate installs the *published* `terp-spec`. So a new rule is red
here until the reference implementation carries the check, and red there until
the spec version is released. The order is: land the implementation, bump
`REFERENCE_SHA`, re-run CI here, release, then move the framework's two pins
together.

`reference-drift.yml` watches the reference's default branch on its own
schedule, so drift surfaces as its own build rather than inside an unrelated
pull request.

## Reporting a vulnerability

Do not open a public issue for a security problem. Report it privately through
GitHub's security advisories for this repository.
