"""Publication checkout paths retain approval identities and upstream history."""
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_ui_design_contract import materialize_publication
import check_ui_publication as publication
from ui_approval_digest import canonical_ui_approval_sha256


# After the 0.55.0 cutover instant, and still on 2026-09-27 under the UTC-12
# receipt date that the "Decided on predates" check uses.
POST_CUTOVER_RECEIPT = "2026-09-27T20:00:00Z"
# After the cutover instant, but 2026-09-26 under the UTC-12 receipt date.
RELEASE_DAY_RECEIPT = "2026-09-27T08:00:00Z"
PRE_CUTOVER_RECEIPT = "2020-01-01T00:00:00Z"
DATED_CASES = (
    # (Visual Approval Decided on, HiFi receipt executedAt, historical)
    ("2026-09-26", PRE_CUTOVER_RECEIPT, True),
    ("2026-09-27", PRE_CUTOVER_RECEIPT, False),
    # A backdated approval cannot hide post-cutover HiFi evidence.
    ("2026-09-26", POST_CUTOVER_RECEIPT, False),
    # Time-zone rounding cannot move a release-day receipt before the cutover.
    ("2026-09-26", RELEASE_DAY_RECEIPT, False),
)


def assert_current_hifi_findings(test, findings, backdated):
    joined = "\n".join(findings)
    test.assertIn("requires ui-evidence/3 machine observation", joined)
    test.assertIn("reviewer shell version 3", joined)
    test.assertIn("Frontend Design Usage", joined)
    if backdated:
        test.assertIn("Decided on predates the newest HiFi review evidence", joined)


class PublicationTests(unittest.TestCase):
    def test_publication_and_drift(self):
        for required in (False, True):
            with self.subTest(required=required), tempfile.TemporaryDirectory() as temp:
                source, candidate = Path(temp) / "source", Path(temp) / "candidate"
                source.mkdir()
                materialize_publication(source, required=required)
                if required:
                    design = source / "docs/design"
                    (design / "design-system-preview.html").write_bytes(publication.render_view(
                        (design / "design-system.json").read_bytes(),
                        (design / "design-system.md").read_bytes(),
                        source,
                    ).encode("utf-8"))
                    renderer = publication.COMPILER / "render_design_system_preview.py"
                    result = subprocess.run([sys.executable, str(renderer), "--repo-root", str(source),
                                             "--registry", str(design / "design-system.json"),
                                             "--markdown", str(design / "design-system.md"),
                                             "--check", str(design / "design-system-preview.html")],
                                            capture_output=True, text=True, encoding="utf-8")
                    self.assertEqual(0, result.returncode, result.stderr)
                def git(*args):
                    subprocess.run(["git", "-C", str(source), *args], check=True, capture_output=True)
                git("init", "-q")
                git("add", ".")
                git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                    "-c", "commit.gpgsign=false", "commit", "-qm", "fixture")
                shutil.copytree(source, candidate)
                hifi = Path("docs/design/ui-references/run-1/index.html")
                def check(published=False):
                    return publication.validate(source, candidate, hifi=hifi, required=required, published=published)
                self.assertEqual([], check())
                self.assertEqual([], check(published=True))
                if required:
                    view = candidate / "docs/design/design-system-preview.html"
                    original_view = view.read_bytes()
                    view.write_bytes(original_view + b"edited")
                    self.assertIn("preview is stale", " ".join(check()))
                    view.unlink()
                    self.assertTrue(check())  # Tracked-file inventory also rejects removal.
                    view.write_bytes(original_view)
                    self.assertEqual([], check())
                upstream = candidate / "docs/product/PRD.md"
                original = upstream.read_bytes()
                upstream.write_bytes(original + b"\ndrift")
                self.assertIn("upstream/source", " ".join(check()))
                upstream.write_bytes(original)
                page = candidate / hifi
                original_page = page.read_bytes()
                page.write_bytes(original_page + b"tamper")
                self.assertTrue(check())
                page.unlink()
                self.assertTrue(check())
                page.write_bytes(original_page)
                hidden = candidate / "docs/design/hidden.html"
                hidden.write_text("ignored candidate", encoding="utf-8")
                (candidate / ".git/info/exclude").write_text("docs/design/hidden.html\n", encoding="utf-8")
                self.assertIn("must not be ignored", " ".join(check()))
                hidden.unlink()
                git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                    "-c", "commit.gpgsign=false", "commit", "--allow-empty", "-qm", "drift")
                self.assertIn("HEAD differs", " ".join(check()))

    def test_new_or_changed_legacy_approval_needs_current_hifi_evidence(self):
        for committed in ("absent", "other-target"):
            with self.subTest(committed=committed), tempfile.TemporaryDirectory() as temp:
                source, candidate = Path(temp) / "source", Path(temp) / "candidate"
                source.mkdir()
                materialize_publication(source, required=False)
                ui_path = source / "docs/design/ui-design.md"
                text = ui_path.read_text(encoding="utf-8")
                def git(*args):
                    subprocess.run(["git", "-C", str(source), *args], check=True, capture_output=True)
                git("init", "-q")
                git("add", ".")
                if committed == "absent":
                    git("rm", "-q", "--cached", "docs/design/ui-design.md")
                else:
                    target = publication.ui.parse_ui_contract_view(text)[0]["approved_target"]
                    ui_path.write_text(text.replace("Approved target: " + target["path"] + " @ sha256:" + target["sha256"],
                                                    "Approved target: " + target["path"] + " @ sha256:" + "0" * 64), encoding="utf-8")
                    git("add", "docs/design/ui-design.md")
                git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                    "-c", "commit.gpgsign=false", "commit", "-qm", "fixture")
                ui_path.write_text(text, encoding="utf-8")
                shutil.copytree(source, candidate)
                findings = "\n".join(publication.validate(
                    source, candidate, hifi=Path("docs/design/ui-references/run-1/index.html")))
                self.assertIn("requires ui-evidence/3 machine observation", findings)
                self.assertIn("reviewer shell version 3", findings)
                self.assertIn("Frontend Design Usage", findings)

    def test_dated_legacy_approval_needs_current_hifi_even_when_committed(self):
        # The approval is committed at HEAD unchanged; only its decision and
        # HiFi receipt dates decide whether ui-evidence/2 HiFi receipts may stay.
        for decided_on, executed_at, historical in DATED_CASES:
            with self.subTest(decided_on=decided_on, executed_at=executed_at), \
                    tempfile.TemporaryDirectory() as temp:
                source, candidate = Path(temp) / "source", Path(temp) / "candidate"
                source.mkdir()
                materialize_publication(source, required=False, visual_decided_on=decided_on,
                                        hifi_executed_at=executed_at)
                def git(*args):
                    subprocess.run(["git", "-C", str(source), *args], check=True, capture_output=True)
                git("init", "-q")
                git("add", ".")
                git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                    "-c", "commit.gpgsign=false", "commit", "-qm", "fixture")
                shutil.copytree(source, candidate)
                findings = publication.validate(
                    source, candidate, hifi=Path("docs/design/ui-references/run-1/index.html"))
                if historical:
                    self.assertEqual([], findings)
                else:
                    assert_current_hifi_findings(self, findings, executed_at == POST_CUTOVER_RECEIPT)

    def test_compiler_preflight_applies_the_dated_current_hifi_rule(self):
        import check_design_system_pair
        for decided_on, executed_at, historical in DATED_CASES:
            with self.subTest(decided_on=decided_on, executed_at=executed_at), \
                    tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                _, _, _, _, _, pair = materialize_publication(
                    root, required=True, visual_decided_on=decided_on, hifi_executed_at=executed_at)
                problems = check_design_system_pair.compare(
                    pair[0].read_text(encoding="utf-8"),
                    json.loads(pair[1].read_text(encoding="utf-8")),
                    require_filled=True, repo_root=root)
                if historical:
                    self.assertEqual([], problems)
                else:
                    self.assertIn("ui-design: ", "\n".join(problems))
                    assert_current_hifi_findings(self, problems, executed_at == POST_CUTOVER_RECEIPT)
                    # A Harness join for an older RUN turns the dated rule off.
                    self.assertEqual([], check_design_system_pair.compare(
                        pair[0].read_text(encoding="utf-8"),
                        json.loads(pair[1].read_text(encoding="utf-8")),
                        require_filled=True, repo_root=root, apply_current_hifi_cutover=False))

    def test_current_hifi_cutover_boundaries(self):
        from datetime import datetime, timezone
        applies = publication.ui.current_hifi_cutover_applies
        def utc(*parts):
            return datetime(*parts, tzinfo=timezone.utc)
        self.assertFalse(applies("2026-09-26", []))
        self.assertFalse(applies("2026-09-26", [utc(2026, 9, 26, 23, 59, 59)]))
        self.assertTrue(applies("2026-09-26", [utc(2026, 9, 1), utc(2026, 9, 27)]))
        self.assertTrue(applies("2026-09-26", [utc(2026, 9, 27, 8)]))
        self.assertTrue(applies("2026-09-27", []))
        self.assertTrue(applies("later", []))
        self.assertTrue(applies(None, []))

    def test_digest_cli_is_stable_across_derived_linkage(self):
        text = "# UI\n\nApproved direction\nCompiled design system pair: pending\n"
        linked = text.replace("pending", "docs/design/pair @ sha256:" + "a" * 64)
        self.assertEqual(canonical_ui_approval_sha256(text), canonical_ui_approval_sha256(linked))
        self.assertNotEqual(hashlib.sha256(linked.encode()).hexdigest(), canonical_ui_approval_sha256(linked))
        with tempfile.TemporaryDirectory(prefix="digest path with spaces ") as temp:
            path = Path(temp) / "ui design.md"
            path.write_text(linked, encoding="utf-8")
            script = Path(publication.__file__).with_name("ui_approval_digest.py")
            result = subprocess.run([sys.executable, str(script), str(path)], capture_output=True, text=True, encoding="utf-8")
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(canonical_ui_approval_sha256(linked), result.stdout.strip())


if __name__ == "__main__":
    unittest.main()
