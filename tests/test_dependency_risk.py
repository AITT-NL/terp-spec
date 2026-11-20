"""Shared scanner and acceptance shapes are held to the portable schema subset."""

import hashlib
import json

import pytest

from schema_subset import _validate
from terp_spec import spec_dir


@pytest.mark.parametrize("name", ["dependency-audit", "dependency-risk-acceptance"])
def test_contract_fixtures(name):
    root = spec_dir()
    schema = json.loads((root / f"{name}.schema.json").read_text())
    for case in json.loads((root / f"{name}.fixtures.json").read_text()):
        errors = _validate(case["document"], schema, "root")
        assert (not errors) == case["valid"], (case["name"], errors)
        if case["valid"]:
            items = case["document"].get("findings", [case["document"].get("finding")])
            for item in items:
                identity = {key: item[key] for key in ("advisories", "ecosystem", "package", "version", "lockfile", "dependency_paths")}
                encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
                assert item["fingerprint"] == "sha256:" + hashlib.sha256(encoded).hexdigest()


@pytest.mark.parametrize("field", ["id", "project_id", "reason", "approved_by", "environments", "evidence"])
@pytest.mark.parametrize("blank", [" ", "\t", "\u00a0", "\ufeff"])
def test_acceptance_requires_content_in_authority_fields(field, blank):
    root = spec_dir()
    schema = json.loads((root / "dependency-risk-acceptance.schema.json").read_text())
    record = json.loads((root / "dependency-risk-acceptance.fixtures.json").read_text())[0]["document"]
    record[field] = [blank] if isinstance(record[field], list) else blank
    assert _validate(record, schema, "root")


@pytest.mark.parametrize("name", ["dependency-audit", "dependency-risk-acceptance"])
def test_lock_digest_covers_the_entire_string(name):
    root = spec_dir()
    schema = json.loads((root / f"{name}.schema.json").read_text())
    doc = json.loads((root / f"{name}.fixtures.json").read_text())[0]["document"]
    lock = next(iter(doc["locks"]))
    doc["locks"][lock] += "\n"
    assert _validate(doc, schema, "root")
