"""Tests for parity_capture.py --hifi-package reference mode."""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
for _directory in (SCRIPTS_DIR, TESTS_DIR):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import parity_capture  # noqa: E402
from test_harness_design_coverage import surface as design_surface  # noqa: E402
from test_parity_capture import STUB_BAT, STUB_ENV, STUB_PY, STUB_SH, plan_markdown  # noqa: E402


class ParityCaptureHifiPackageTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

        stub_dir = self.root / "bin"
        stub_dir.mkdir()
        self.stub_py = stub_dir / "_stub_browser.py"
        self.stub_py.write_text(STUB_PY, encoding="utf-8")
        stub_sh = stub_dir / "agent-browser"
        stub_sh.write_text(STUB_SH, encoding="utf-8")
        stub_sh.chmod(0o755)
        (stub_dir / "agent-browser.bat").write_text(STUB_BAT, encoding="utf-8")
        self._old_resolve_cli = parity_capture._resolve_cli
        parity_capture._resolve_cli = lambda: [sys.executable, str(self.stub_py)]
        self.addCleanup(self._restore_resolve_cli)
        self.log_path = self.root / "calls.jsonl"
        self._old_env = {name: os.environ.get(name) for name in STUB_ENV}
        os.environ["PATH"] = str(stub_dir) + os.pathsep + (self._old_env["PATH"] or "")
        os.environ["STUB_LOG"] = str(self.log_path)
        os.environ["STUB_STATE"] = str(self.root / "stub-state.json")
        for name in STUB_ENV:
            if name.startswith("STUB_") and name not in ("STUB_LOG", "STUB_STATE"):
                os.environ.pop(name, None)
        self.addCleanup(self._restore_env)

        self.package = self.root / "hifi"
        self.package.mkdir()
        manifest = {
            "schema": "ui-hifi/2",
            "surfaces": [
                {"id": "UI-001", "page": "index.html", "route": "/home"},
                {"id": "UI-002", "page": "details.html", "route": "/details/:id"},
            ],
            "pages": [{"path": "details.html", "sha256": "0" * 64}],
            "interactions": [],
        }
        script = (
            '<script id="ui-hifi-manifest" type="application/json">'
            + json.dumps(manifest)
            + "</script>"
        )
        (self.package / "index.html").write_text(
            f"<html><body>{script}</body></html>", encoding="utf-8"
        )
        (self.package / "details.html").write_text(
            "<html><body>details</body></html>", encoding="utf-8"
        )

        self.plan = self.root / "PLAN.md"
        self.plan.write_text(
            plan_markdown(
                [
                    {"id": "UI-001", "trace_ids": ["REQ-001"], "route": "/home",
                     "breakpoints": ["390", "768"], "states": ["ready", "empty"],
                     "evidence_gate": "required"},
                    {"id": "UI-002", "trace_ids": ["REQ-002"], "route": "/details/:id",
                     "breakpoints": ["390"], "states": ["ready"],
                     "evidence_gate": "required"},
                ]
            ),
            encoding="utf-8",
        )
        self.out = self.root / "docs" / "goal" / "evidence" / "parity"

    def _restore_env(self) -> None:
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _restore_resolve_cli(self) -> None:
        parity_capture._resolve_cli = self._old_resolve_cli

    def run_main(self, *extra: str) -> tuple[int, str]:
        argv = [
            "--plan", str(self.plan),
            "--hifi-package", str(self.package),
            "--base-url", "http://localhost:3000",
            "--out", str(self.out),
            *extra,
        ]
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = parity_capture.main(argv)
        return code, stdout.getvalue()

    def calls(self) -> list[list[str]]:
        if not self.log_path.exists():
            return []
        return [json.loads(line) for line in self.log_path.read_text().splitlines()]

    def work_calls(self) -> list[list[str]]:
        """Browser calls after the preflight."""

        return [
            argv for argv in self.calls() if argv[:1] not in (["--version"], ["close"])
        ]

    def opens(self) -> list[str]:
        return [argv[1] for argv in self.work_calls() if argv[:1] == ["open"]]

    def page_uri(self, page: str) -> str:
        return self.package.joinpath(page).resolve().as_uri()

    def write_route_map(self, payload: dict[str, object]) -> Path:
        route_map = self.root / "route-map.json"
        route_map.write_text(json.dumps(payload), encoding="utf-8")
        return route_map

    def default_route_map(self) -> Path:
        return self.write_route_map({
            "/home": {"states": {"empty": {"app_eval": "window.__setEmpty()"}}},
            "/details/:id": {"app_path": "/products/42"},
        })

    def write_plan(self, surface: dict[str, object]) -> None:
        self.plan.write_text(plan_markdown([surface]), encoding="utf-8")

    @staticmethod
    def plain_surface(surface_id: str, route: str, breakpoints: list[str],
                      states: list[str]) -> dict[str, object]:
        return {"id": surface_id, "trace_ids": ["REQ-001"], "route": route,
                "breakpoints": breakpoints, "states": states, "evidence_gate": "required"}

    def manifest(self) -> dict[str, object]:
        return json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))

    def test_hifi_mode_drives_package_pages_and_captures_only_the_canvas(self) -> None:
        code, out = self.run_main("--route-map", str(self.default_route_map()))
        self.assertEqual(0, code, out)
        manifest = self.manifest()
        self.assertEqual("PASS", manifest["status"])
        self.assertEqual("hifi-package", manifest["reference_mode"])
        self.assertEqual(self.package.as_posix(), manifest["hifi_package"])
        self.assertIsNone(manifest["reference"])
        # UI-001: 2 breakpoints x 2 states; UI-002: 1 breakpoint x 1 state.
        self.assertEqual(5, len(manifest["captured"]))
        # Routes sort first, then the package pages; the empty state reloads /home.
        self.assertEqual(
            [
                "http://localhost:3000/products/42",
                "http://localhost:3000/home",
                "http://localhost:3000/home",
                self.page_uri("details.html"),
                self.page_uri("index.html"),
            ],
            self.opens(),
        )
        screenshots = [argv for argv in self.work_calls() if argv[:1] == ["screenshot"]]
        for argv in screenshots:
            if argv[-1].endswith("-target.png"):
                self.assertEqual("[data-hifi-canvas]", argv[1])
            else:
                self.assertEqual(["screenshot", "--full"], argv[:2])
        self.assertEqual(5, sum(1 for argv in screenshots if argv[-1].endswith("-target.png")))

    def test_hifi_reference_page_is_opened_once_per_package_page(self) -> None:
        self.write_plan(self.plain_surface("UI-001", "/home", ["390", "768"], ["ready"]))
        code, out = self.run_main()
        self.assertEqual(0, code, out)
        self.assertEqual(
            ["http://localhost:3000/home", self.page_uri("index.html")], self.opens()
        )

    def test_hifi_mode_ignores_reference_selectors_and_reference_eval(self) -> None:
        self.write_plan(self.plain_surface("UI-001", "/home", ["390"], ["ready", "empty"]))
        route_map = self.write_route_map({"/home": {
            "reference": {"selector": "#nav"},
            "states": {"empty": {"app_eval": "window.__setEmpty()",
                                 "reference_eval": "window.__refEmpty()"}},
        }})
        code, out = self.run_main("--route-map", str(route_map))
        self.assertEqual(0, code, out)
        for argv in self.work_calls():
            if argv[:1] == ["eval"]:
                self.assertEqual(["eval", "--stdin"], argv[:2])
        # One load serves both states even though each carries a reference_eval.
        self.assertEqual(
            ["http://localhost:3000/home", self.page_uri("index.html")], self.opens()
        )

    def test_a_missing_target_control_skips_the_pair_and_keeps_the_page(self) -> None:
        os.environ["STUB_HIFI_TARGET"] = "missing"
        self.addCleanup(os.environ.pop, "STUB_HIFI_TARGET", None)
        self.write_plan(self.plain_surface("UI-001", "/home", ["390", "768"], ["ready"]))
        code, out = self.run_main()
        self.assertEqual(1, code, out)
        manifest = self.manifest()
        self.assertEqual("FAIL", manifest["status"])
        self.assertEqual([], manifest["captured"])
        self.assertIn(
            "target control missing", manifest["skipped"][0]["reason"], manifest["skipped"]
        )
        # The untouched page still served the second tuple's attempt.
        self.assertEqual(1, self.opens().count(self.page_uri("index.html")))

    def test_a_missing_state_control_skips_the_pair(self) -> None:
        os.environ["STUB_HIFI_STATE"] = "missing"
        self.addCleanup(os.environ.pop, "STUB_HIFI_STATE", None)
        self.write_plan(self.plain_surface("UI-001", "/home", ["390"], ["ready"]))
        code, out = self.run_main()
        self.assertEqual(1, code, out)
        manifest = self.manifest()
        self.assertEqual([], manifest["captured"])
        self.assertIn("state control missing", manifest["skipped"][0]["reason"])

    def test_an_unapplied_control_click_forces_a_fresh_reference_page(self) -> None:
        os.environ["STUB_HIFI_STATE"] = "notapplied"
        self.addCleanup(os.environ.pop, "STUB_HIFI_STATE", None)
        self.write_plan(self.plain_surface("UI-001", "/home", ["390", "768"], ["ready"]))
        code, out = self.run_main()
        self.assertEqual(1, code, out)
        manifest = self.manifest()
        self.assertEqual([], manifest["captured"])
        self.assertIn("state did not apply", manifest["skipped"][0]["reason"])
        # The unknown page state made the second tuple reload before its attempt.
        self.assertEqual(2, self.opens().count(self.page_uri("index.html")))

    def test_a_plan_surface_missing_from_the_manifest_is_skipped(self) -> None:
        self.write_plan(self.plain_surface("UI-999", "/home", ["390"], ["ready"]))
        code, out = self.run_main()
        self.assertEqual(1, code, out)
        manifest = self.manifest()
        self.assertIn(
            "no ui-hifi-manifest surface for surface_id 'UI-999'",
            manifest["skipped"][0]["reason"],
        )

    def test_long_content_needs_only_app_eval_in_hifi_mode(self) -> None:
        self.write_plan(design_surface("UI-001", ["ready"], "ready"))
        route_map = self.write_route_map({"/ui-001": {
            "conditions": {"long-content": {"app_eval": "window.__app()"}},
        }})
        code, out = self.run_main("--route-map", str(route_map))
        self.assertEqual(0, code, out)
        manifest = self.manifest()
        self.assertEqual("PASS", manifest["status"])
        states = {row["state"] for row in manifest["captured"]}
        self.assertIn("long-content", states)
        self.assertEqual(8, len(manifest["captured"]))

    def test_long_content_without_app_eval_is_skipped_in_hifi_mode(self) -> None:
        self.write_plan(design_surface("UI-001", ["ready"], "ready"))
        route_map = self.write_route_map({"/ui-001": {
            "conditions": {"long-content": {"reference_eval": "window.__ref()"}},
        }})
        code, out = self.run_main("--route-map", str(route_map))
        self.assertEqual(1, code, out)
        manifest = self.manifest()
        self.assertIn(
            "long-content requires app_eval in the route-map conditions",
            json.dumps(manifest["skipped"]),
        )
        self.assertNotIn("reference_eval and", json.dumps(manifest["skipped"]))

    def test_the_app_side_is_captured_full_page_at_the_breakpoint_width(self) -> None:
        self.write_plan(self.plain_surface("UI-001", "/home", ["390"], ["ready"]))
        code, out = self.run_main()
        self.assertEqual(0, code, out)
        viewports = [argv for argv in self.work_calls() if argv[:2] == ["set", "viewport"]]
        self.assertEqual([["set", "viewport", "390", "1000"], ["set", "viewport", "390", "1000"]],
                         viewports)
        actual = [argv for argv in self.work_calls()
                  if argv[:1] == ["screenshot"] and argv[-1].endswith("-actual.png")]
        self.assertEqual([["screenshot", "--full"]], [argv[:2] for argv in actual])

    def test_a_missing_package_directory_is_refused_before_any_browser_work(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = parity_capture.main(
                ["--plan", str(self.plan), "--hifi-package", str(self.root / "ghost"),
                 "--base-url", "http://localhost:3000", "--out", str(self.out)]
            )
        self.assertEqual(1, code)
        self.assertIn("hifi package directory not found", stderr.getvalue())
        self.assertEqual([], self.calls())

    def test_a_package_without_an_entry_is_refused(self) -> None:
        empty = self.root / "empty-package"
        empty.mkdir()
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = parity_capture.main(
                ["--plan", str(self.plan), "--hifi-package", str(empty),
                 "--base-url", "http://localhost:3000", "--out", str(self.out)]
            )
        self.assertEqual(1, code)
        self.assertIn("has no index.html entry", stderr.getvalue())
        self.assertEqual([], self.calls())

    def test_an_entry_without_a_manifest_script_is_refused(self) -> None:
        bare = self.root / "bare-package"
        bare.mkdir()
        (bare / "index.html").write_text("<html><body>no manifest</body></html>", encoding="utf-8")
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = parity_capture.main(
                ["--plan", str(self.plan), "--hifi-package", str(bare),
                 "--base-url", "http://localhost:3000", "--out", str(self.out)]
            )
        self.assertEqual(1, code)
        self.assertIn("has no ui-hifi-manifest script", stderr.getvalue())
        self.assertEqual([], self.calls())

    def test_a_manifest_with_the_wrong_schema_is_refused(self) -> None:
        stale = self.root / "stale-package"
        stale.mkdir()
        manifest = {"schema": "ui-hifi/1", "surfaces": [{"id": "UI-001", "page": "index.html"}]}
        (stale / "index.html").write_text(
            '<script id="ui-hifi-manifest" type="application/json">'
            + json.dumps(manifest)
            + "</script>",
            encoding="utf-8",
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = parity_capture.main(
                ["--plan", str(self.plan), "--hifi-package", str(stale),
                 "--base-url", "http://localhost:3000", "--out", str(self.out)]
            )
        self.assertEqual(1, code)
        self.assertIn("must be schema ui-hifi/2", stderr.getvalue())
        self.assertEqual([], self.calls())

    def test_a_manifest_page_missing_on_disk_is_refused(self) -> None:
        ghosted = self.root / "ghost-package"
        ghosted.mkdir()
        manifest = {"schema": "ui-hifi/2", "surfaces": [{"id": "UI-001", "page": "ghost.html"}]}
        (ghosted / "index.html").write_text(
            '<script id="ui-hifi-manifest" type="application/json">'
            + json.dumps(manifest)
            + "</script>",
            encoding="utf-8",
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = parity_capture.main(
                ["--plan", str(self.plan), "--hifi-package", str(ghosted),
                 "--base-url", "http://localhost:3000", "--out", str(self.out)]
            )
        self.assertEqual(1, code)
        self.assertIn("hifi package page is missing: ghost.html", stderr.getvalue())
        self.assertEqual([], self.calls())

    def test_reference_and_hifi_package_are_mutually_exclusive(self) -> None:
        stderr = io.StringIO()
        with self.assertRaises(SystemExit) as raised, contextlib.redirect_stderr(stderr):
            parity_capture.main(
                ["--plan", str(self.plan), "--reference", str(self.root / "ref.html"),
                 "--hifi-package", str(self.package), "--out", str(self.out)]
            )
        self.assertEqual(2, raised.exception.code)
        self.assertIn("choose exactly one reference mode", stderr.getvalue())

    def test_a_reference_mode_is_required(self) -> None:
        stderr = io.StringIO()
        with self.assertRaises(SystemExit) as raised, contextlib.redirect_stderr(stderr):
            parity_capture.main(
                ["--plan", str(self.plan), "--base-url", "http://localhost:3000",
                 "--out", str(self.out)]
            )
        self.assertEqual(2, raised.exception.code)
        self.assertIn("choose exactly one reference mode", stderr.getvalue())

    def test_unchanged_package_bytes_carry_and_skip_the_reference_side(self) -> None:
        code, out = self.run_main("--route-map", str(self.default_route_map()))
        self.assertEqual(0, code, out)
        self.log_path.unlink()
        code, out = self.run_main("--route-map", str(self.default_route_map()),
                                  "--carry-from", str(self.out / "manifest.json"))
        self.assertEqual(0, code, out)
        manifest = self.manifest()
        self.assertEqual("PASS", manifest["status"])
        classifications = {row["classification"] for row in manifest["captured"]}
        self.assertEqual({"carried"}, classifications)
        # Every open belongs to the app side; the carried pairs skip the package.
        self.assertTrue(self.opens())
        self.assertFalse([uri for uri in self.opens() if uri.startswith("file:")])

    def test_changed_package_bytes_are_recaptured_not_carried(self) -> None:
        code, out = self.run_main("--route-map", str(self.default_route_map()))
        self.assertEqual(0, code, out)
        details = self.package / "details.html"
        details.write_text(details.read_text(encoding="utf-8") + "<!-- edited -->",
                           encoding="utf-8")
        self.log_path.unlink()
        code, out = self.run_main("--route-map", str(self.default_route_map()),
                                  "--carry-from", str(self.out / "manifest.json"))
        self.assertEqual(0, code, out)
        manifest = self.manifest()
        classifications = {row["classification"] for row in manifest["captured"]}
        self.assertEqual({"identical"}, classifications)
        self.assertEqual(1, self.opens().count(self.page_uri("details.html")))
