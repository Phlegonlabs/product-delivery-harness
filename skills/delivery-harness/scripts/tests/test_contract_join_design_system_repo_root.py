"""The strict frozen join checks pair bindings against the real repository."""

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_contract_join import validate_frozen_contract_joins  # noqa: E402
import test_harness_strict_authority as authority  # noqa: E402


class SchemaTwoRepoRootJoinTests(unittest.TestCase):
    def test_schema_two_pair_is_checked_against_repo_root(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run, _ = authority.StrictAuthorityJoinTests._ui_fixture(root, required=True)
            self.assertEqual([], validate_frozen_contract_joins(plan, root, run=run))

    def test_stale_schema_two_binding_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            plan, run, paths = authority.StrictAuthorityJoinTests._ui_fixture(root, required=True)
            self.assertEqual([], validate_frozen_contract_joins(plan, root, run=run))
            registry = json.loads(paths["design_json"].read_text(encoding="utf-8"))
            registry["sourceBindings"]["prd"]["sha256"] = "0" * 64
            authority.StrictAuthorityJoinTests._refresh_pair(root, paths, registry)
            for source in plan["sources"]:
                source["content_sha256"] = hashlib.sha256((root / source["location"]).read_bytes()).hexdigest()
            errors = validate_frozen_contract_joins(plan, root, run=run)
            self.assertFalse(any("require repo_root" in item for item in errors), errors)
            self.assertTrue(
                any("sourceBindings.prd sha256 does not match current bytes" in item for item in errors), errors,
            )


if __name__ == "__main__":
    unittest.main()
