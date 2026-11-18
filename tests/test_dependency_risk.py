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
