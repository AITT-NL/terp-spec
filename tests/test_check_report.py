"""The application check-report format is well-formed and its contract is checkable.

``app-check-report.schema.json`` is the complete result of one checker
invocation over one application tree: the evaluated-rule inventory, the spec
version the rule ids resolve against, the checker's identity, and the findings
— everything a driving tool needs to join per-rule verdicts to the catalog
fail-closed (a rule the run did not publish as evaluated can never render as
passing). These assertions hold the checked-in schema to its own contract (it
validates representative reports, rejects malformed ones, and its embedded
finding shape is exactly the finding format), using the same minimal validator
the catalog suite uses.
"""

from __future__ import annotations

import json

from terp_spec import spec_dir, spec_version

from test_standard import _validate

_SPEC = spec_dir()


def _schema() -> dict:
    return json.loads(
        (_SPEC / "app-check-report.schema.json").read_text(encoding="utf-8")
    )


def _sample() -> dict:
    return {
        "terp_check_report": 1,
        "spec_version": spec_version(),
        "checker": {"tool": "example-checker", "version": "1.0.0"},
        "ok": False,
        "rules": ["backend/no_dynamic_sql", "backend/escape_hatch_budget"],
        "not_applicable": ["frontend/layout-contract"],
        "findings": [
            {
                "rule": "backend/no_dynamic_sql",
                "path": "modules/notes/service.py",
                "line": 12,
                "message": "SQL is built from a dynamic string; bind parameters instead.",
                "fix_hint": "session.exec(select(Model).where(...)) with bound parameters",
                "fingerprint": "b9c1e2",
            }
        ],
        "unattributed": [
            {
                "path": "modules/notes/service.py",
                "line": 3,
                "message": "an unrelated configured tool's diagnostic",
                "reported_as": "some-other-rule",
            }
        ],
    }


def _sample_error() -> dict:
    return {
        "terp_check_report": 1,
        "spec_version": spec_version(),
        "checker": {"tool": "example-checker", "version": "1.0.0"},
        "ok": False,
        "error": "the checked tree could not be parsed",
        "rules": [],
        "findings": [],
    }


def test_a_representative_report_validates() -> None:
    assert _validate(_sample(), _schema(), "check-report") == []


def test_a_minimal_and_an_erroring_report_validate() -> None:
    schema = _schema()
    minimal = {
        "terp_check_report": 1,
        "spec_version": spec_version(),
        "checker": {"tool": "example-checker", "version": "1.0.0"},
        "ok": True,
        "rules": ["backend/no_dynamic_sql"],
        "findings": [],
    }
    assert _validate(minimal, schema, "check-report") == []
    erroring = _sample_error()
    assert _validate(erroring, schema, "check-report") == []
    # The semantic half the schema subset cannot express, held on the
    # documented samples: an erroring run never claims ok, and it claims no
    # evaluated rules it did not finish holding the tree to.
    assert erroring["ok"] is False
    assert erroring["rules"] == []


def test_malformed_reports_are_rejected() -> None:
    schema = _schema()
    unknown_marker = _sample() | {"terp_check_report": 2}
    assert _validate(unknown_marker, schema, "check-report")
    bad_version = _sample() | {"spec_version": "not-semver"}
    assert _validate(bad_version, schema, "check-report")
    no_checker = {k: v for k, v in _sample().items() if k != "checker"}
    assert _validate(no_checker, schema, "check-report")
    no_inventory = {k: v for k, v in _sample().items() if k != "rules"}
    assert _validate(no_inventory, schema, "check-report")
    bad_rule_id = _sample() | {"rules": ["Backend/No Dynamic SQL"]}
    assert _validate(bad_rule_id, schema, "check-report")
    unattributed_finding = _sample()
    del unattributed_finding["findings"][0]["rule"]
    assert _validate(unattributed_finding, schema, "check-report")
    pathless_message = _sample()
    del pathless_message["unattributed"][0]["path"]
    assert _validate(pathless_message, schema, "check-report")
    extra_field = _sample() | {"vendor_extension": {}}
    assert _validate(extra_field, schema, "check-report")


def test_the_embedded_finding_shape_is_the_finding_format() -> None:
    """The report's `findings` items are EXACTLY findings.schema.json's items
    (inlined because the suite's dependency-free validator resolves no $ref) —
    held identical here so the two artifacts can never drift apart."""
    findings_schema = json.loads(
        (_SPEC / "findings.schema.json").read_text(encoding="utf-8")
    )
    assert _schema()["properties"]["findings"]["items"] == findings_schema["items"], (
        "app-check-report.schema.json findings items must equal "
        "findings.schema.json items verbatim"
    )


def test_sample_rule_ids_resolve_against_the_catalog() -> None:
    """The documented samples name real catalog rules, so the reference shape
    a checker implements from this suite is itself coherent."""
    catalog = {
        f"{surface}/{path.stem}"
        for surface in ("backend", "frontend")
        for path in (_SPEC / "catalog" / surface).glob("*.json")
    }
    sample = _sample()
    for rule_id in (
        *sample["rules"],
        *sample["not_applicable"],
        *(finding["rule"] for finding in sample["findings"]),
    ):
        assert rule_id in catalog, f"sample names an uncatalogued rule: {rule_id}"
