# Dependency risk acceptance

The dependency audit document describes scanner evidence, not release permission.
`complete: false` is never a clean scan and cannot be accepted. npm blocks high and
critical findings; the Python scanner blocks every advisory. Dependency scope is
installation metadata, never evidence of exploitability.

An acceptance describes one occurrence of one vulnerability in an exact project,
commit, lock set and environment. It requires an authenticated human decision,
recorded outside the application checkout. The shape alone grants no authority:
readers must verify the issuer against operator-controlled trust, check current
revocation status, and enforce approval and expiry times. Maximum lifetime is 30
days; the default is seven. Expiry blocks new releases and promotions, not an
already running process.

A renewal supersedes the earlier decision for the same finding, project, commit
and target environment. Select the latest decision before checking its expiry or
revocation: withdrawing or expiring a renewal must not revive an older acceptance.

Fingerprints are SHA-256 of ASCII JSON with sorted keys and compact separators,
over `advisories`, `ecosystem`, `package`, `version`, `lockfile` and
`dependency_paths`. Arrays in this identity are sorted and deduplicated. npm
transitive advisory references must be resolved; every installed occurrence
remains explicit. A supplied fingerprint must be recomputed before matching.

Release permission is separate from assurance. An accepted vulnerability remains
a failed dependency check and a failed assurance lane. Consumers must not turn
that raw verdict green. Other failed checks and incomplete scanner evidence
cannot be covered by this contract. Old readers must refuse any release format
that introduces exception-based permission.
