"""Tests for parity_capture.py --recapture: after a repair, capture only what it can affect."""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
for _directory in (SCRIPTS_DIR, TESTS_DIR):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import parity_capture  # noqa: E402
import test_parity_capture as single  # noqa: E402
import test_parity_capture_hifi as hifi  # noqa: E402

NEEDS_PILLOW = "pixel diff needs Pillow"


def rows_by(manifest: dict, key: str) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for row in manifest["captured"]:
        grouped.setdefault(row[key], []).append(row)
    return grouped


@unittest.skipIf(sys.platform == "darwin", single.DARWIN_FD_EXEC)
class SingleHtmlRecaptureTests(unittest.TestCase):
    """Two routes on one reference; a repair touches only /home."""

    base = single.ParityCaptureTests
    setUp = base.setUp
    _restore_env = base._restore_env
    _restore_resolve_cli = base._restore_resolve_cli
    run_main = base.run_main
    calls = base.calls
    work_calls = base.work_calls
    write_route_map = base.write_route_map
    set_surfaces = base.set_surfaces

    def run_routes(self, *extra: str, out: Path) -> tuple[int, str]:
        self.set_surfaces(["ready"], ["390"], routes=("/home", "/settings"))
        route_map = self.write_route_map({
            "/home": {"reference": {"selector": "#a"}},
            "/settings": {"reference": {"selector": "#b"}},
        })
        self.log_path.unlink(missing_ok=True)
        return self.run_main("--route-map", str(route_map), "--out", str(out), *extra)

    def before_repair(self) -> Path:
        first = self.root / "before"
        code, output = self.run_routes(out=first)
        self.assertEqual(0, code, output)
        return first / "manifest.json"

    def opens(self) -> list[str]:
        return [argv[1] for argv in self.work_calls() if argv[:1] == ["open"]]

    @unittest.skipUnless(parity_capture._load_pillow(), NEEDS_PILLOW)
    def test_only_the_repaired_route_is_captured(self) -> None:
        first = self.before_repair()
        before = rows_by(json.loads(first.read_text(encoding="utf-8")), "route")
        after = self.root / "after"
        # The repair changes the app; only /home is looked at again.
        with patch.dict(os.environ, {"STUB_SHOT_COLOR_ACTUAL": "ff0000"}):
            code, output = self.run_routes("--carry-from", str(first), "--recapture", "/home", out=after)
        self.assertEqual(0, code, output)
        self.assertEqual(["http://localhost:3000/home", self.reference.resolve().as_uri()], self.opens())
        manifest = json.loads((after / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("PASS", manifest["status"])
        self.assertTrue(manifest["gating_eligible"])
        self.assertEqual(["/home"], manifest["recapture_scope"])
        rows = rows_by(manifest, "route")
        self.assertEqual("changed", rows["/home"][0]["classification"])
        settings = rows["/settings"][0]
        self.assertEqual("carried", settings["classification"])
        self.assertEqual(
            {"manifest": first.as_posix(), "classification": "identical", "recapture_scope": ["/home"]},
            settings["carried_from"],
        )
        for key in ("target", "actual", "target_sha256", "actual_sha256", "geometry_fingerprint"):
            self.assertEqual(before["/settings"][0][key], settings[key], key)

    @unittest.skipUnless(parity_capture._load_pillow(), NEEDS_PILLOW)
    def test_a_surface_id_names_the_scope_too(self) -> None:
        first = self.before_repair()
        code, output = self.run_routes("--carry-from", str(first), "--recapture", "UI-002",
                                       out=self.root / "after")
        self.assertEqual(0, code, output)
        self.assertEqual(["http://localhost:3000/settings"], self.opens())

    @unittest.skipUnless(parity_capture._load_pillow(), NEEDS_PILLOW)
    def test_without_a_scope_every_entry_is_captured_again(self) -> None:
        first = self.before_repair()
        after = self.root / "after"
        with patch.dict(os.environ, {"STUB_SHOT_COLOR_ACTUAL": "ff0000"}):
            code, output = self.run_routes("--carry-from", str(first), out=after)
        self.assertEqual(0, code, output)
        self.assertEqual(
            ["http://localhost:3000/home", self.reference.resolve().as_uri(),
             "http://localhost:3000/settings", self.reference.resolve().as_uri()],
            self.opens(),
        )
        manifest = json.loads((after / "manifest.json").read_text(encoding="utf-8"))
        self.assertIsNone(manifest["recapture_scope"])
        self.assertEqual({"changed": 2}, manifest["classification_counts"])

    @unittest.skipUnless(parity_capture._load_pillow(), NEEDS_PILLOW)
    def test_an_out_of_scope_pair_whose_images_changed_on_disk_is_captured(self) -> None:
        first = self.before_repair()
        settings = rows_by(json.loads(first.read_text(encoding="utf-8")), "route")["/settings"][0]
        Path(settings["actual"]).write_bytes(b"edited after the review")
        code, output = self.run_routes("--carry-from", str(first), "--recapture", "/home",
                                       out=self.root / "after")
        self.assertEqual(0, code, output)
        self.assertIn("http://localhost:3000/settings", self.opens())

    def test_an_unknown_scope_id_is_refused_before_any_browser_work(self) -> None:
        first = self.before_repair()
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code, _ = self.run_routes("--carry-from", str(first), "--recapture", "/home,/nowhere",
                                      out=self.root / "after")
        self.assertEqual(1, code)
        self.assertIn("--recapture names no hosted PLAN route or surface: /nowhere", stderr.getvalue())
        self.assertEqual([], self.calls())

    def test_recapture_needs_a_carry_source_and_a_name(self) -> None:
        cases = {
            "no carry source": ["--recapture", "/home"],
            "with recapture-carried": ["--carry-from", "m.json", "--recapture", "/home", "--recapture-carried"],
            "empty list": ["--carry-from", "m.json", "--recapture", " , "],
        }
        for name, extra in cases.items():
            with self.subTest(name):
                with contextlib.redirect_stderr(io.StringIO()):
                    with self.assertRaises(SystemExit) as raised:
                        self.run_main(*extra)
                self.assertEqual(2, raised.exception.code)


@unittest.skipUnless(parity_capture._load_pillow(), NEEDS_PILLOW)
class HifiRecaptureTests(unittest.TestCase):
    """UI-001 on index.html (/home), UI-002 on details.html (/details/:id)."""

    base = hifi.ParityCaptureHifiPackageTests
    setUp = base.setUp
    _restore_env = base._restore_env
    _restore_resolve_cli = base._restore_resolve_cli
    run_main = base.run_main
    calls = base.calls
    work_calls = base.work_calls
    opens = base.opens
    page_uri = base.page_uri
    write_route_map = base.write_route_map
    default_route_map = base.default_route_map
    manifest = base.manifest

    def before_change(self) -> Path:
        kept = self.root / "before.json"
        code, output = self.run_main("--route-map", str(self.default_route_map()))
        self.assertEqual(0, code, output)
        kept.write_text((self.out / "manifest.json").read_text(encoding="utf-8"), encoding="utf-8")
        self.log_path.unlink()
        return kept

    def test_a_changed_target_page_outside_the_scope_is_captured(self) -> None:
        kept = self.before_change()
        details = self.package / "details.html"
        details.write_text("<html><body>corrected details</body></html>", encoding="utf-8")
        code, output = self.run_main("--route-map", str(self.default_route_map()),
                                     "--carry-from", str(kept), "--recapture", "/home")
        self.assertEqual(0, code, output)
        details_row = rows_by(self.manifest(), "surface_id")["UI-002"][0]
        self.assertEqual("identical", details_row["classification"])
        self.assertIn(self.page_uri("details.html"), self.opens())

    def test_a_one_page_correction_does_not_expire_the_other_page(self) -> None:
        kept = self.before_change()
        # Assembly rewrites the entry's manifest hash for the corrected child,
        # so the entry page's bytes change too.
        details = self.package / "details.html"
        details.write_text("<html><body>corrected details</body></html>", encoding="utf-8")
        entry = self.package / "index.html"
        entry.write_text(entry.read_text(encoding="utf-8").replace(
            "0" * 64, parity_capture._file_sha256(details)), encoding="utf-8")
        code, output = self.run_main("--route-map", str(self.default_route_map()),
                                     "--carry-from", str(kept))
        self.assertEqual(0, code, output)
        manifest = self.manifest()
        classes = {(row["surface_id"], row["classification"]) for row in manifest["captured"]}
        self.assertEqual({("UI-001", "carried"), ("UI-002", "identical")}, classes)
        self.assertEqual([self.page_uri("details.html")],
                         [uri for uri in self.opens() if uri.startswith("file:")])
        # The package identity stays on record and follows every page.
        before = json.loads(kept.read_text(encoding="utf-8"))["package_sha256"]
        self.assertRegex(manifest["package_sha256"], "^[0-9a-f]{64}$")
        self.assertNotEqual(before, manifest["package_sha256"])

    def test_an_entry_page_change_outside_the_manifest_expires_its_captures(self) -> None:
        kept = self.before_change()
        entry = self.package / "index.html"
        entry.write_text(entry.read_text(encoding="utf-8").replace(
            "<body>", "<body><p>new hero</p>"), encoding="utf-8")
        code, output = self.run_main("--route-map", str(self.default_route_map()),
                                     "--carry-from", str(kept))
        self.assertEqual(0, code, output)
        classes = {(row["surface_id"], row["classification"]) for row in self.manifest()["captured"]}
        self.assertEqual({("UI-001", "identical"), ("UI-002", "carried")}, classes)


if __name__ == "__main__":
    unittest.main()
