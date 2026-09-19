"""Typed motion transcript validation; fixtures are synthetic, not browser proof."""
import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from motion_evidence import motion_findings


class MotionEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.expected = dict(intent="MM-001", scope="UI-001 / hero", mode="normal",
                             states=["ready"], targets=["390"], assetRequired=False)
        self.value = dict(intent="MM-001", scope="UI-001 / hero", mode="normal",
                          reducedMotion=False, asset=None, observations=[{
                              "target": "390", "state": "ready", "trigger": "entry",
                              "endState": "hero visible", "fallbackObserved": False,
                              "samples": [{"atMs": t, "values": {"opacity": v}}
                                          for t, v in [(0, "0"), (100, "0.5"), (200, "1")]]}])

    def test_normal_and_reduced_observations(self):
        self.assertEqual(motion_findings(self.value, self.expected), [])

        self.expected["mode"] = self.value["mode"] = "reduced"
        self.value["reducedMotion"] = True
        row = self.value["observations"][0]
        row["fallbackObserved"] = True
        for sample in row["samples"]:
            sample["values"]["opacity"] = "1"
        self.assertEqual(motion_findings(self.value, self.expected), [])
        row["fallbackObserved"] = False
        self.assertTrue(motion_findings(self.value, self.expected))

    def test_authorization_is_an_explicit_asset_bound_record(self):
        self.expected["assetRequired"] = True
        for authorization in ("pending owner approval", "not authorized by owner", {},
                              {"decision": "approved"}):
            with self.subTest(authorization=authorization):
                self.value["asset"] = dict(path="docs/hero.mp4", sha256="a" * 64,
                                           authorization=authorization, review="approved")
                self.assertTrue(motion_findings(self.value, self.expected))

    def test_identity_and_actual_preference_cannot_be_reused(self):
        for key, value in [("intent", "MM-002"), ("scope", "UI-001 / footer"),
                           ("mode", "reduced"), ("reducedMotion", True)]:
            with self.subTest(key=key):
                wrong = copy.deepcopy(self.value)
                wrong[key] = value
                self.assertTrue(motion_findings(wrong, self.expected))

    def test_generic_static_and_incomplete_evidence_fail(self):
        self.assertTrue(motion_findings({"result": "PASS"}, self.expected))
        for field, value in [("state", "invented"), ("target", "768"),
                             ("trigger", "placeholder"), ("samples", []),
                             ("samples", [{"atMs": t, "values": {"opacity": "1"}}
                                          for t in (0, 100, 200)])]:
            with self.subTest(field=field):
                wrong = copy.deepcopy(self.value)
                wrong["observations"][0][field] = value
                self.assertTrue(motion_findings(wrong, self.expected))

    def test_duplicate_targets_and_unordered_samples_fail(self):
        self.value["observations"].append(copy.deepcopy(self.value["observations"][0]))
        self.assertTrue(motion_findings(self.value, self.expected))
        self.value["observations"].pop()
        self.value["observations"][0]["samples"][1]["atMs"] = 0
        self.assertTrue(motion_findings(self.value, self.expected))

    def test_required_media_needs_completed_authorization_and_review(self):
        self.expected["assetRequired"] = True
        self.assertTrue(motion_findings(self.value, self.expected))
        self.value["asset"] = dict(path="docs/hero.mp4", sha256="a" * 64,
                                   authorization="pending", review="approved")
        self.assertTrue(motion_findings(self.value, self.expected))
        self.value["asset"]["authorization"] = dict(decision="approved", owner="Product owner",
            provider="Example provider", action="generate", path="docs/hero.mp4", sha256="a" * 64)
        self.expected["provider"] = "Example provider"
        self.assertEqual(motion_findings(self.value, self.expected), [])
        for key, value in (("decision", "pending"), ("provider", "Other provider"),
                           ("provider", "authorized provider"),
                           ("path", "docs/other.mp4"), ("sha256", "b" * 64)):
            with self.subTest(key=key):
                wrong = copy.deepcopy(self.value)
                wrong["asset"]["authorization"][key] = value
                self.assertTrue(motion_findings(wrong, self.expected))


if __name__ == "__main__":
    unittest.main()
