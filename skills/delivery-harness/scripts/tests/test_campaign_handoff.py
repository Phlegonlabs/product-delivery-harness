"""Campaign handoff regressions through the document-sync public CLI."""

import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness_contract import contract_digest
from check_document_sync import main


SCRIPT = Path(__file__).resolve().parents[1] / "check_document_sync.py"
MESSAGING = "docs/gtm/MESSAGING.md"
CAMPAIGN = "docs/gtm/CAMPAIGN.md"
SOURCE = """# Messaging Record
Revision: MSG-1
Date: 2026-11-18
## Approved Public Claims
| Claim | Evidence | Check date |
| --- | --- | --- |
| C01: Three operators reconstructed enquiry status | RA-001 | 2026-11-18 |
Owner approval source and approved revision: fixture decision, MSG-1
## Claims Not Allowed
| Claim not allowed | Missing or conflicting evidence |
| --- | --- |
| C02: Instant booking | No evidence |
## Change Log
| MSG-0 | C01 withdrawn in an old revision |
"""
DRAFT = """# Campaign Review Package
## Brief
Source: docs/gtm/MESSAGING.md revision MSG-1; source piece SP-01; C01 / RA-001.
## Individual Drafts
hook-a: Three venue operators reconstructed enquiry status.
## Change Log
Historic source: MESSAGING.md revision MSG-0; C02 was removed.
"""


class CampaignHandoffTests(unittest.TestCase):
    process = False
    @classmethod
    def setUpClass(cls):
        cls.digest = contract_digest()

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name).resolve()
        self.write(MESSAGING, SOURCE)
        self.write(CAMPAIGN, DRAFT)

    def write(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def cli(self, baseline=None, paths=(MESSAGING, CAMPAIGN), identity=True):
        command = [sys.executable, "-B", str(SCRIPT), "--repo-root", str(self.root)]
        if identity:
            command += ["--loaded-digest", self.digest]
        if baseline is not None:
            self.write("baseline.json", json.dumps(baseline))
            command += ["--baseline", "baseline.json"]
        for name in paths:
            command += ["--path", name]
        if self.process:
            completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=20)
            self.assertIn(completed.returncode, (0, 1), completed.stdout + completed.stderr)
            return completed.returncode, json.loads(completed.stdout)
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch("check_document_sync.contract_digest", return_value=self.digest):
            code = main(command[3:])
        self.assertIn(code, (0, 1), output.getvalue())
        return code, json.loads(output.getvalue())

    def refreshed(self, **kwargs):
        _, first = self.cli(**kwargs)
        return self.cli(first["snapshot"], **kwargs)

    def test_current_binding_is_quiet_and_history_is_not_a_live_claim(self):
        code, report = self.refreshed()
        self.assertEqual(0, code, report)
        self.assertEqual([], report["findings"])
        self.assertEqual({"schema", "installed_digest", "documents"}, set(report["snapshot"]))

    def test_source_change_stays_stale_after_refresh_then_restoration_clears(self):
        _, first = self.cli()
        self.write(MESSAGING, SOURCE.replace("MSG-1", "MSG-2"))
        code, changed = self.cli(first["snapshot"])
        self.assertEqual(1, code)
        self.assertIn("campaign_messaging_stale", {row["kind"] for row in changed["findings"]})
        code, refreshed = self.cli(changed["snapshot"])
        self.assertEqual(1, code)
        self.assertEqual(["campaign_messaging_stale"], [row["kind"] for row in refreshed["findings"]])
        self.write(MESSAGING, SOURCE)
        self.assertEqual(0, self.refreshed()[0])

    def test_revision_only_edit_cannot_reapprove_withdrawn_claim(self):
        source = SOURCE.replace("Revision: MSG-1", "Revision: MSG-2").replace(
            "| C01: Three operators reconstructed enquiry status | RA-001 | 2026-11-18 |", ""
        ).replace("## Claims Not Allowed", "## Claims Not Allowed\nC01 withdrawn: evidence no longer supports it.")
        self.write(MESSAGING, source)
        self.write(CAMPAIGN, DRAFT.replace("MSG-1", "MSG-2"))
        code, report = self.refreshed()
        self.assertEqual(1, code)
        self.assertIn({"kind": "campaign_claim_not_approved", "path": CAMPAIGN, "source": MESSAGING,
                       "claim_id": "C01", "reason": "withdrawn"}, report["findings"])
        self.assertNotIn("campaign_messaging_stale", {row["kind"] for row in report["findings"]})
        self.write(CAMPAIGN, DRAFT.replace("MSG-1", "MSG-2").replace("C01 / RA-001", "RA-002").replace(
            "Three venue operators reconstructed enquiry status.", "Review the revised concept."))
        self.assertEqual(0, self.refreshed()[0])

    def test_unknown_claim_and_old_approval_are_not_approved(self):
        self.write(CAMPAIGN, DRAFT.replace("C01 /", "CLAIM-999 /"))
        _, report = self.refreshed()
        self.assertIn("campaign_claim_not_approved", {row["kind"] for row in report["findings"]})
        self.write(CAMPAIGN, DRAFT)
        self.write(MESSAGING, SOURCE.replace("fixture decision, MSG-1", "fixture decision, MSG-0"))
        _, report = self.refreshed()
        self.assertIn("claim_approval_revision_unverified", {row.get("reason") for row in report["findings"]})

    def test_real_template_fields_and_revision_formats(self):
        for revision in ("r1", "1", "v1.2.3", "2026-11-18.1", "MSG-2", "abc1234"):
            with self.subTest(revision=revision):
                self.write(MESSAGING, SOURCE.replace("MSG-1", revision).replace("Revision:", "**Revision:**"))
                self.write(CAMPAIGN, DRAFT.replace("Source: docs/gtm/MESSAGING.md revision MSG-1; source piece SP-01; C01 / RA-001.",
                    f"Messaging record: [Messaging](MESSAGING.md)\nMessaging revision: `{revision}`\nClaims: C01"))
                self.assertEqual(0, self.refreshed()[0])

    def test_unreadable_or_conflicting_references_require_persistent_review(self):
        for brief in ("Use MESSAGING.md, latest revision.", "Messaging revision: [unknown]",
                      "Source: MESSAGING.md revision MSG-1\nSource: MESSAGING.md revision MSG-0",
                      "Source: other/MESSAGING.md revision MSG-1",
                      "Source: MESSAGING.md revision MSG-1; MESSAGING.md revision MSG-0",
                      "Source: MESSAGING.md revision MSG-1; MESSAGING.md unknown",
                      "Source: MESSAGING.md revision MSG-1\nAlso follow MESSAGING.md when drafting."):
            with self.subTest(brief=brief):
                self.write(CAMPAIGN, "# Campaign\n## Brief\n" + brief)
                self.assertEqual(1, self.refreshed()[0])

    def test_migration_requires_a_binding_without_changing_snapshot_schema(self):
        self.write(CAMPAIGN, "# Existing campaign\nCopy awaiting source reconciliation.\n")
        code, report = self.refreshed()
        self.assertEqual(1, code)
        self.assertIn("campaign_handoff_unverified", {row["kind"] for row in report["findings"]})
        self.write(CAMPAIGN, "# Campaign\nMessaging revision: MSG-1\nCopy: A prose claim has no machine identity.\n")
        self.assertEqual(0, self.refreshed()[0])

    def test_explicit_scope_and_first_child_observation_are_preserved(self):
        self.write("notes.md", "A historical mention of MESSAGING.md MSG-0 and C02.\n")
        self.assertEqual(0, self.refreshed(paths=("notes.md",))[0])
        self.assertEqual(0, self.refreshed(paths=(MESSAGING,))[0])
        _, report = self.refreshed(paths=(CAMPAIGN,))
        self.assertIn("messaging_source_not_in_inventory_or_missing", {row.get("reason") for row in report["findings"]})
        code, report = self.cli(identity=False)
        self.assertEqual(1, code)
        self.assertEqual({"baseline_review_required", "loaded_identity_unobserved"},
                         {row["kind"] for row in report["findings"]})

    def test_missing_source_is_not_silently_verified(self):
        # Start without a source, rather than removing a user document.
        with tempfile.TemporaryDirectory() as empty:
            self.root = Path(empty).resolve()
            self.write(CAMPAIGN, DRAFT)
            code, report = self.refreshed()
            self.assertEqual(1, code)
            self.assertIn("messaging_source_not_in_inventory_or_missing", {row.get("reason") for row in report["findings"]})

    def test_template_id_column_and_scoped_campaign_folder(self):
        source = SOURCE.replace("| Claim | Evidence | Check date |", "| Claim ID | Claim | Evidence | Check date |")
        source = source.replace("| C01: Three operators", "| C01 | Three operators")
        self.write(MESSAGING, source)
        alternate = "docs/gtm/campaigns/launch.md"
        self.write(alternate, DRAFT)
        self.assertEqual(0, self.refreshed(paths=(MESSAGING, alternate))[0])
        self.write(alternate, DRAFT.replace("MSG-1", "MSG-0"))
        code, report = self.refreshed(paths=(MESSAGING, alternate))
        self.assertEqual(1, code)
        self.assertEqual(alternate, report["findings"][0]["path"])

    def test_missing_or_ambiguous_source_revision_cannot_be_baselined_away(self):
        for source in (SOURCE.replace("Revision: MSG-1", "Revision:"),
                       SOURCE.replace("Revision: MSG-1", "Revision: MSG-1\nRevision: MSG-2")):
            with self.subTest(source=source[:80]):
                self.write(MESSAGING, source)
                code, report = self.refreshed()
                self.assertEqual(1, code)
                self.assertIn("missing_or_unreadable_source_revision", {row.get("reason") for row in report["findings"]})

    def test_fenced_public_copy_cannot_hide_a_withdrawn_id_or_fake_metadata(self):
        self.write(CAMPAIGN, DRAFT.replace("## Individual Drafts", "## Individual Drafts\n```text\nC02: Instant booking\n## History\n```"))
        code, report = self.refreshed()
        self.assertEqual(1, code)
        self.assertIn("C02", {row.get("claim_id") for row in report["findings"]})
        self.write(CAMPAIGN, "# Campaign\n```text\nMessaging revision: MSG-1\n```\n")
        self.assertEqual(1, self.refreshed()[0])


def replay_live_cases(case_root):
    """Copy only the named live handoff inputs into disposable CLI fixtures."""
    suite = CampaignHandoffTests()
    suite.process = True
    suite.digest = contract_digest()
    for name, expected in (("01-positive", 0), ("02-unchanged", 0),
                           ("05-messaging-withdrawal", 1), ("06-refreshed-inventory-stale-consumers", 1)):
        with tempfile.TemporaryDirectory() as temporary:
            suite.root = Path(temporary).resolve()
            for doc in (MESSAGING, CAMPAIGN):
                suite.write(doc, (case_root / name / doc).read_text(encoding="utf-8-sig"))
            code, report = suite.refreshed()
            assert code == expected, (name, report)
            print(name, code, [row["kind"] for row in report["findings"]])
            if name == "05-messaging-withdrawal":
                suite.write(CAMPAIGN, (case_root / name / CAMPAIGN).read_text(encoding="utf-8-sig").replace("MSG-1", "MSG-2"))
                code, report = suite.refreshed()
                assert code == 1 and any(row["kind"] == "campaign_claim_not_approved" for row in report["findings"])
                print("revision-only-edit", code, [row["kind"] for row in report["findings"]])
                for doc in (MESSAGING, CAMPAIGN):
                    suite.write(doc, (case_root / "01-positive" / doc).read_text(encoding="utf-8-sig"))
                assert suite.refreshed()[0] == 0
                print("restored", 0)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--live-cases":
        replay_live_cases(Path(sys.argv[2]))
    else:
        unittest.main()
