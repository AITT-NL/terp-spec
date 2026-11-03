"""Behavioral security cases are complete, stack-neutral and shipped as data."""
from __future__ import annotations

import copy
import json

import pytest

from terp_spec import spec_dir
from test_standard import _validate

ROOT = spec_dir()


def _artifacts() -> tuple[dict, dict]:
    return (
        json.loads((ROOT / "runtime-security.fixtures.json").read_text()),
        json.loads((ROOT / "runtime-security.schema.json").read_text()),
    )


def test_runtime_scenarios_validate_and_identify_real_catalog_rules() -> None:
    fixtures, schema = _artifacts()
    assert _validate(fixtures, schema, "runtime-security") == []
    ids = [case["id"] for case in fixtures["cases"]]
    assert len(ids) == len(set(ids)), "a repeated id makes evidence ambiguous"
    for case in fixtures["cases"]:
        for rule in case["rules"]:
            catalog = json.loads((ROOT / "catalog" / f"{rule}.json").read_text())
            assert catalog["id"] == rule


@pytest.mark.parametrize("field", ["setup", "exercise", "expected", "controls"])
def test_a_case_without_actions_outcomes_or_controls_is_not_a_contract(field: str) -> None:
    fixtures, schema = _artifacts()
    invalid = copy.deepcopy(fixtures)
    invalid["cases"][0][field] = []
    assert _validate(invalid, schema, "runtime-security")
    del invalid["cases"][0][field]
    assert _validate(invalid, schema, "runtime-security")


@pytest.mark.parametrize("field", ["id", "capability"])
def test_case_identifiers_cannot_end_in_a_newline(field: str) -> None:
    fixtures, schema = _artifacts()
    invalid = copy.deepcopy(fixtures)
    invalid["cases"][0][field] += "\n"
    assert _validate(invalid, schema, "runtime-security")


def test_an_empty_or_wrong_version_contract_is_rejected() -> None:
    fixtures, schema = _artifacts()
    assert _validate(fixtures | {"cases": []}, schema, "runtime-security")
    assert _validate(fixtures | {"runtime_security": True}, schema, "runtime-security")
    assert _validate(fixtures | {"runtime_security": 2}, schema, "runtime-security")


def test_the_contract_covers_the_security_boundaries_it_claims() -> None:
    fixtures, _ = _artifacts()
    # These stable identifiers are the minimum contract, not a count a newly
    # added case can preserve while accidentally removing another boundary.
    assert {case["id"] for case in fixtures["cases"]} >= {
        "scope.relationships", "writes.denial", "tokens.snapshot",
        "oidc.browser-binding", "sessions.logout", "outbox.finalize",
        "egress.budgets", "logs.redaction", "config.transport",
        "webhooks.envelope", "jobs.atomicity", "files.binding",
        "permissions.floor-and-grant", "replay.current-authority",
        "streams.current-grants", "leases.protected-effects",
        "sessions.rotation", "native.browser-refused",
        "accounts.enumeration", "accounts.proof-of-address", "accounts.single-use",
        "accounts.sealed-tokens", "accounts.expiry", "accounts.backoff",
        "accounts.lowest-rank", "accounts.close",
    }
    readme = (ROOT / "README.md").read_text()
    assert "runtime-security.fixtures.json" in readme
    assert "runtime-security.schema.json" in readme
