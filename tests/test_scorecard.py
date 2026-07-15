"""The scorecard format is well-formed and its contract is checkable.

``scorecard.schema.json`` is the machine-readable certification summary a
conformant checker emits — the artifact that makes "certified against spec
X.Y.Z" verifiable. These assertions hold the checked-in schema to its own
contract (it validates a representative scorecard, rejects malformed ones,
and its residual-claim semantics resolve against ``corpus/RESIDUALS.json``),
using the same minimal validator the catalog suite uses.
"""

from __future__ import annotations

import json

from terp_spec import spec_dir, spec_version

from test_standard import _validate

_SPEC = spec_dir()


def _schema() -> dict:
    return json.loads((_SPEC / "scorecard.schema.json").read_text(encoding="utf-8"))


def _sample() -> dict:
    residuals = json.loads(
        (_SPEC / "corpus" / "RESIDUALS.json").read_text(encoding="utf-8")
    )["residuals"]
    rule, claimed = next(iter(residuals.items()))
    return {
        "spec_version": spec_version(),
        "checker": {"tool": "example-checker", "version": "1.0.0"},
        "rules": [
            {"rule": "backend/no_dynamic_sql", "pass": True},
            {"rule": rule, "pass": True, "residuals_claimed": list(claimed)},
        ],
    }


def test_a_representative_scorecard_validates() -> None:
    assert _validate(_sample(), _schema(), "scorecard") == []


def test_malformed_scorecards_are_rejected() -> None:
    schema = _schema()
    bad_version = _sample() | {"spec_version": "not-semver"}
    assert _validate(bad_version, schema, "scorecard")
    no_rules = {k: v for k, v in _sample().items() if k != "rules"}
    assert _validate(no_rules, schema, "scorecard")
    bad_rule_id = _sample()
    bad_rule_id["rules"][0]["rule"] = "Backend/No Dynamic SQL"
    assert _validate(bad_rule_id, schema, "scorecard")
    extra_field = _sample() | {"vendor_extension": {}}
    assert _validate(extra_field, schema, "scorecard")


def test_sample_residual_claims_resolve_against_the_ratchet() -> None:
    """The semantic half the schema cannot express: residuals_claimed must be a
    subset of corpus/RESIDUALS.json for the rule — claiming a residual the spec
    does not record is a conformance failure, and this proves the reference
    sample (and thus the documented contract) is itself coherent."""
    residuals = json.loads(
        (_SPEC / "corpus" / "RESIDUALS.json").read_text(encoding="utf-8")
    )["residuals"]
    for entry in _sample()["rules"]:
        for claim in entry.get("residuals_claimed", []):
            assert claim in residuals.get(entry["rule"], []), (
                f"{entry['rule']}: claimed residual is not recorded in RESIDUALS.json: "
                f"{claim!r}"
            )
