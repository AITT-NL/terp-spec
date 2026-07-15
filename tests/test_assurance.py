"""The assurance-profile format is well-formed and its claim semantics hold.

``assurance-profile.schema.json`` is the machine-readable release-assurance
claim a toolchain emits from its release verification profile (see the
README's assurance-profile section — the lane vocabulary and each lane's
requirement level are normative and live in the spec, never in the document).
These assertions hold the checked-in schema to its own contract with the same
minimal validator the catalog suite uses, and pin the normative vocabulary so
it cannot drift silently between the schema and the README.
"""

from __future__ import annotations

import json

from terp_spec import spec_dir, spec_version

from test_standard import _validate

_SPEC = spec_dir()

#: The normative lane vocabulary with its requirement mapping (the README table).
REQUIRED_LANES = ("terp-standard", "appsec-baseline", "dependency-audit")
RECOMMENDED_LANES = ("a11y", "blackbox-conformance")


def _schema() -> dict:
    return json.loads(
        (_SPEC / "assurance-profile.schema.json").read_text(encoding="utf-8")
    )


def _sample() -> dict:
    return {
        "terp_assurance": 1,
        "spec_version": spec_version(),
        "toolchain": {"tool": "example-toolchain", "version": "1.0.0"},
        "profile": "release",
        "ok": True,
        "lanes": [
            {"id": "terp-standard", "status": "passed", "checks": ["architecture", "frontend-boundaries"]},
            {"id": "appsec-baseline", "status": "passed", "checks": ["appsec-baseline"]},
            {"id": "dependency-audit", "status": "passed", "checks": ["dependency-audit-python", "dependency-audit-npm"]},
            {"id": "a11y", "status": "not-run", "checks": []},
            {"id": "blackbox-conformance", "status": "failed", "checks": ["conformance"]},
        ],
    }


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
