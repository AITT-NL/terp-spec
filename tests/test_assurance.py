"""The assurance-profile format is well-formed and its claim semantics hold.

``assurance-profile.schema.json`` is the machine-readable release-assurance
claim a toolchain emits from its release verification profile (see the
README's assurance-profile section — the lane vocabulary and each lane's
requirement level are normative and live in the spec, never in the document).
These assertions hold the checked-in schema to its own contract with the same
minimal validator every contract suite uses, and pin the normative vocabulary so
it cannot drift silently between the schema and the README.
"""

from __future__ import annotations

import json

import pytest

from terp_spec import spec_dir

from schema_subset import _validate

_SPEC = spec_dir()

#: The normative lane vocabulary with its requirement mapping (the README table).
REQUIRED_LANES = (
    "terp-standard",
    "appsec-baseline",
    "dependency-audit",
    "secret-scanning",
)
RECOMMENDED_LANES = ("a11y", "blackbox-conformance", "test-adequacy")


def _schema() -> dict:
    return json.loads(
        (_SPEC / "assurance-profile.schema.json").read_text(encoding="utf-8")
    )


def _sample() -> dict:
    return json.loads((_SPEC / "assurance-profile.fixtures.json").read_text(encoding="utf-8"))["valid"]


def test_a_representative_assurance_profile_validates() -> None:
    assert _validate(_sample(), _schema(), "assurance") == []


def test_malformed_assurance_profiles_are_rejected() -> None:
    schema = _schema()
    bad_version = _sample() | {"spec_version": "not-semver"}
    assert _validate(bad_version, schema, "assurance")
    no_lanes = {k: v for k, v in _sample().items() if k != "lanes"}
    assert _validate(no_lanes, schema, "assurance")
    unknown_lane = _sample()
    unknown_lane["lanes"][0]["id"] = "vibes"
    assert _validate(unknown_lane, schema, "assurance")
    bad_status = _sample()
    bad_status["lanes"][0]["status"] = "skipped"
    assert _validate(bad_status, schema, "assurance")
    # Requirement levels are the spec's, never the emitter's: a document
    # cannot carry (and thereby demote/promote) a per-lane requirement field.
    demoted = _sample()
    demoted["lanes"][0] = demoted["lanes"][0] | {"requirement": "recommended"}
    assert _validate(demoted, schema, "assurance")
    extra_field = _sample() | {"vendor_extension": {}}
    assert _validate(extra_field, schema, "assurance")


def test_the_lane_vocabulary_is_the_normative_mapping() -> None:
    """The schema's lane enum must equal the README's normative table (the
    requirement mapping this suite pins) — one vocabulary, stated twice,
    held equal here so neither can drift silently."""
    schema = _schema()
    enum = schema["properties"]["lanes"]["items"]["properties"]["id"]["enum"]
    assert tuple(enum) == REQUIRED_LANES + RECOMMENDED_LANES
    readme = (_SPEC / "README.md").read_text(encoding="utf-8")
    for lane in REQUIRED_LANES:
        assert f"| `{lane}` | **required** |" in readme, (
            f"README assurance table must state {lane!r} as required"
        )
    for lane in RECOMMENDED_LANES:
        assert f"| `{lane}` | recommended |" in readme, (
            f"README assurance table must state {lane!r} as recommended"
        )


@pytest.mark.parametrize("lane_id", REQUIRED_LANES + RECOMMENDED_LANES)
def test_every_lane_is_required_exactly_once(lane_id: str) -> None:
    doc = _sample()
    others = [lane for lane in doc["lanes"] if lane["id"] != lane_id]
    assert _validate(doc | {"lanes": others}, _schema(), "assurance")
    duplicate = others[0] | {"checks": ["another-check"], "status": "passed"}
    assert _validate(doc | {"lanes": [*others, duplicate]}, _schema(), "assurance")
    assert not _validate(doc | {"lanes": list(reversed(doc["lanes"]))}, _schema(), "assurance")


@pytest.mark.parametrize("lane_id", REQUIRED_LANES + RECOMMENDED_LANES)
@pytest.mark.parametrize("status", ["passed", "failed", "not-run"])
def test_claim_and_evidence_match_the_verdict(lane_id: str, status: str) -> None:
    doc = _sample()
    lane = next(row for row in doc["lanes"] if row["id"] == lane_id)
    lane.update(status=status, checks=[] if status == "not-run" else ["example-check"])
    doc["ok"] = status == "passed" or lane_id in RECOMMENDED_LANES
    assert not _validate(doc, _schema(), "assurance")
    assert _validate(doc | {"ok": not doc["ok"]}, _schema(), "assurance")
    lane["checks"] = ["example-check"] if status == "not-run" else []
    assert _validate(doc, _schema(), "assurance")
