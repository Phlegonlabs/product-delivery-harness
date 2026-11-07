"""Tests for parity_capture.py using a stubbed agent-browser CLI."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
for _directory in (SCRIPTS_DIR, TESTS_DIR):
    if str(_directory) not in sys.path:
        sys.path.insert(0, str(_directory))

import parity_capture  # noqa: E402
from test_harness_design_coverage import surface as design_surface  # noqa: E402

STUB_PY = r"""
import json, os, struct, sys, zlib
argv = sys.argv[1:]
log = os.environ.get("STUB_LOG")
if log:
    with open(log, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(argv) + "\n")
state_path = os.environ.get("STUB_STATE")
state = {}
if state_path and os.path.exists(state_path):
    with open(state_path, encoding="utf-8") as handle:
        state = json.load(handle)


def save_state():
    if state_path:
        with open(state_path, "w", encoding="utf-8") as handle:
            json.dump(state, handle)


def hifi_control(env):
    # Result of parity_capture's package target/state control evals.
    mode = os.environ.get(env, "ok")
    if mode == "missing":
        if env == "STUB_HIFI_TARGET":
            return {"applied": False, "clean": True, "reason": "target control missing: 390"}
        return {"applied": False, "clean": True, "reason": "state control missing: UI-001 ready"}
    if mode == "notapplied":
        if env == "STUB_HIFI_TARGET":
            return {"applied": False, "clean": False, "reason": "target did not apply: 768"}
        return {"applied": False, "clean": False, "reason": "state did not apply: UI-001 ready"}
    return {"applied": True, "clean": True, "reason": None}


def solid_png(size, color, patch=None):
    # A tiny truecolor PNG; an optional (w, h) patch at the top left is red.
    width, height = (int(part) for part in size.split("x"))
    red = (255, 0, 0)
    rows = b""
    for y in range(height):
        row = b"\x00"
        for x in range(width):
            inside = patch and x < patch[0] and y < patch[1]
            row += bytes(red if inside else color)
        rows += row

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


if argv[:1] == ["--version"]:
    print("agent-browser 0.36.0-stub")
    raise SystemExit(0)
if argv[:1] == ["open"]:
    state["url"] = argv[1]
    save_state()
    print("stub ok")
    raise SystemExit(0)
if argv[:2] == ["set", "media"]:
    state["scheme"] = argv[2]
    state["reduced"] = "reduced-motion" in argv[3:]
    save_state()
    print("stub ok")
    raise SystemExit(0)
if argv[:1] == ["screenshot"]:
    path = argv[-1]
    side = "TARGET" if state.get("url", "").startswith("file:") else "ACTUAL"
    if os.environ.get("STUB_SHOT_MODE") == "garbage":
        data = b"\x89PNG\r\n\x1a\nstub"
    else:
        color = bytes.fromhex(os.environ.get("STUB_SHOT_COLOR_" + side, "204060"))
        patch = os.environ.get("STUB_SHOT_PATCH_" + side)
        data = solid_png(
            os.environ.get("STUB_SHOT_SIZE_" + side, "10x10"),
            color,
            tuple(int(part) for part in patch.split("x")) if patch else None,
        )
    with open(path, "wb") as handle:
        handle.write(data)
    raise SystemExit(0)
if argv[:1] == ["eval"]:
    body = sys.stdin.read() if "--stdin" in argv else " ".join(argv)
    if "overflowX" in body:
        mode = os.environ.get("STUB_GEOMETRY_MODE", "pass")
        if mode == "exit":
            print("geometry unavailable", file=sys.stderr)
            raise SystemExit(3)
        if mode == "malformed":
            print("not json")
        else:
            scanned = os.environ.get("STUB_GEOMETRY_SCANNED", "5")
            print('{"overflowX": 0, "scanned": ' + scanned + ', "overlaps": []}')
    elif "a[href=" in body:
        print(os.environ.get("STUB_PROBE_RESULT", "false"))
    elif "prefers-reduced-motion" in body:
        print(json.dumps({"scheme": state.get("scheme", "light"),
                          "reduced": state.get("reduced", False)}))
    elif "data-hifi-state-control" in body:
        print(json.dumps(hifi_control("STUB_HIFI_STATE")))
    elif "data-hifi-target-control" in body:
        print(json.dumps(hifi_control("STUB_HIFI_TARGET")))
    else:
        print("undefined")
    raise SystemExit(0)
print("stub ok")
"""

STUB_ENV = (
    "PATH", "STUB_LOG", "STUB_STATE", "STUB_PROBE_RESULT", "STUB_GEOMETRY_MODE",
    "STUB_GEOMETRY_SCANNED", "STUB_SHOT_MODE", "STUB_HIFI_TARGET", "STUB_HIFI_STATE",
    "STUB_SHOT_SIZE_TARGET", "STUB_SHOT_SIZE_ACTUAL",
    "STUB_SHOT_COLOR_TARGET", "STUB_SHOT_COLOR_ACTUAL",
    "STUB_SHOT_PATCH_TARGET", "STUB_SHOT_PATCH_ACTUAL",
)

STUB_SH = """#!/bin/sh
exec python3 "$(dirname "$0")/_stub_browser.py" "$@"
"""

STUB_BAT = '@python "%~dp0_stub_browser.py" %*\n'


def plan_markdown(ui_surfaces: list[dict[str, object]]) -> str:
    return (
        "# Plan\n\n## Harness Plan Manifest\n\n```json\n"
        + json.dumps({"harness_plan": {"plan_id": "PLAN-T", "ui_surfaces": ui_surfaces}}, indent=2)
        + "\n```\n"
    )


DARWIN_FD_EXEC = "macOS cannot execute /dev/fd/N, so descriptor-bound launch fails closed there"

class ParityCaptureTests(unittest.TestCase):
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
        # shutil.which on POSIX requires the executable bit.
        stub_sh.chmod(0o755)
        (stub_dir / "agent-browser.bat").write_text(STUB_BAT, encoding="utf-8")
        self._old_resolve_cli = parity_capture._resolve_cli
        parity_capture._resolve_cli = lambda: [
            sys.executable,
            str(self.stub_py),
        ]
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

        self.plan = self.root / "PLAN.md"
        self.plan.write_text(
            plan_markdown(
                [
                    {
                        "id": "UI-001",
                        "trace_ids": ["REQ-001"],
                        "route": "/home",
                        "breakpoints": ["390", "768", "1200"],
                        "states": ["ready", "empty", "loading:n/a — deferred"],
                        "evidence_gate": "required",
                    }
                ]
            ),
            encoding="utf-8",
        )
        self.reference = self.root / "reference.html"
        self.reference.write_text("<html><body>ref</body></html>", encoding="utf-8")
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
            "--reference", str(self.reference),
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
        """Browser calls after the preflight, with screenshot paths named by side."""

        work = []
        for argv in self.calls():
            if argv[:1] in (["--version"], ["close"]):
                continue
            if argv[:1] == ["screenshot"]:
                argv = ["screenshot", "target" if argv[-1].endswith("-target.png") else "actual"]
            work.append(argv)
        return work

    def write_route_map(self, payload: dict[str, object]) -> Path:
        route_map = self.root / "route-map.json"
        route_map.write_text(json.dumps(payload), encoding="utf-8")
        return route_map

    def set_surfaces(self, states: list[str], breakpoints: list[str], routes=("/home",)) -> None:
        self.plan.write_text(plan_markdown([
            {"id": f"UI-{index:03}", "trace_ids": ["REQ-001"], "route": route,
             "breakpoints": breakpoints, "states": states, "evidence_gate": "required"}
            for index, route in enumerate(routes, 1)
        ]), encoding="utf-8")

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    def test_trigger_free_tuples_load_each_side_once_per_route(self) -> None:
        self.set_surfaces(["ready"], ["390", "768", "1200"])
        route_map = self.write_route_map({"/home": {"reference": {"selector": "#nav"}}})
        code, out = self.run_main("--route-map", str(route_map))
        self.assertEqual(0, code, out)
        app_pass = [["open", "http://localhost:3000/home"], ["wait", "--load", "networkidle"]]
        reference_pass = [["open", self.reference.resolve().as_uri()],
                          ["eval", 'document.querySelector("#nav")?.click()']]
        for width in ("390", "768", "1200"):
            app_pass += [["set", "viewport", width, "1000"], ["screenshot", "actual"], ["eval", "--stdin"]]
            reference_pass += [["set", "viewport", width, "1000"], ["screenshot", "target"]]
        self.assertEqual(app_pass + reference_pass, self.work_calls())

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    def test_each_route_loads_both_sides_again(self) -> None:
        self.set_surfaces(["ready"], ["390", "768"], routes=("/home", "/settings"))
        route_map = self.write_route_map({
            "/home": {"reference": {"selector": "#a"}},
            "/settings": {"reference": {"selector": "#b"}},
        })
        code, out = self.run_main("--route-map", str(route_map))
        self.assertEqual(0, code, out)
        opens = [argv[1] for argv in self.work_calls() if argv[:1] == ["open"]]
        self.assertEqual(
            ["http://localhost:3000/home", self.reference.resolve().as_uri(),
             "http://localhost:3000/settings", self.reference.resolve().as_uri()],
            opens,
        )

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    def test_state_triggers_get_a_fresh_app_page_after_the_first(self) -> None:
        self.set_surfaces(["ready", "empty"], ["390", "768"])
        route_map = self.write_route_map({"/home": {
            "reference": {"selector": "#nav"},
            "states": {"empty": {"app_eval": "window.__setEmpty()"}},
        }})
        code, out = self.run_main("--route-map", str(route_map))
        self.assertEqual(0, code, out)
        app_url = "http://localhost:3000/home"
        load = [["open", app_url], ["wait", "--load", "networkidle"]]
        # Trigger-free tuples run first on one load. The first triggered tuple
        # still finds that page untouched; the second needs a fresh load.
        app_pass = (
            load
            + [["set", "viewport", "390", "1000"], ["screenshot", "actual"], ["eval", "--stdin"]]
            + [["set", "viewport", "768", "1000"], ["screenshot", "actual"], ["eval", "--stdin"]]
            + [["set", "viewport", "390", "1000"], ["eval", "--stdin"],
               ["screenshot", "actual"], ["eval", "--stdin"]]
            + load
            + [["set", "viewport", "768", "1000"], ["eval", "--stdin"],
               ["screenshot", "actual"], ["eval", "--stdin"]]
        )
        # The reference side has no trigger, so one load serves all four tuples.
        reference_pass = [["open", self.reference.resolve().as_uri()],
                          ["eval", 'document.querySelector("#nav")?.click()']]
        for width in ("390", "390", "768", "768"):
            reference_pass += [["set", "viewport", width, "1000"], ["screenshot", "target"]]
        self.assertEqual(app_pass + reference_pass, self.work_calls())

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    def test_reference_triggers_get_a_fresh_reference_page_after_the_first(self) -> None:
        self.set_surfaces(["ready", "empty"], ["390", "768"])
        route_map = self.write_route_map({"/home": {
            "reference": {"selector": "#nav"},
            "states": {"empty": {"app_eval": "window.__setEmpty()",
                                 "reference_eval": "window.__refEmpty()"}},
        }})
        code, out = self.run_main("--route-map", str(route_map))
        self.assertEqual(0, code, out)
        reference_url = self.reference.resolve().as_uri()
        self.assertEqual(2, sum(1 for argv in self.work_calls() if argv == ["open", reference_url]))
        manifest = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(4, len(manifest["captured"]))

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    def test_spawn_count_per_pair_drops_for_the_trigger_free_matrix(self) -> None:
        self.set_surfaces(["ready"], ["390", "768", "1200"])
        route_map = self.write_route_map({"/home": {"reference": {"selector": "#nav"}}})
        code, out = self.run_main("--route-map", str(route_map))
        self.assertEqual(0, code, out)
        # The per-tuple order spent 9 spawns per pair (27 for these three pairs).
        self.assertEqual(19, len(self.work_calls()))

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    def test_unreachable_reference_route_is_tried_once(self) -> None:
        os.environ["STUB_PROBE_RESULT"] = "false"
        code, out = self.run_main()
        self.assertEqual(1, code, out)
        reference_url = self.reference.resolve().as_uri()
        self.assertEqual(1, sum(1 for argv in self.work_calls() if argv == ["open", reference_url]))

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    def test_motion_preference_is_set_once_per_scope_group(self) -> None:
        self.plan.write_text(plan_markdown([design_surface("UI-004", ["ready"], "ready")]), encoding="utf-8")
        route_map = self.write_route_map({"/ui-004": {
            "reference": {"selector": "#nav"},
            "conditions": {
                "long-content": {"reference_eval": "window.__ref()", "app_eval": "window.__app()"},
            },
        }})
        code, out = self.run_main("--route-map", str(route_map))
        self.assertEqual(0, code, out)
        manifest = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(8, len(manifest["captured"]))
        media = [argv for argv in self.work_calls() if argv[:2] == ["set", "media"]]
        # Two scope groups (normal, reduced): one apply and one restore each,
        # not one pair per tuple.
        self.assertEqual(
            [["set", "media", "light"], ["set", "media", "light"],
             ["set", "media", "light", "reduced-motion"], ["set", "media", "light"]],
            media,
        )

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    def test_board_images_resolve_from_the_board_directory(self) -> None:
        self.assertEqual(
            "x.png", parity_capture._board_src("docs/goal/evidence/parity/x.png", Path("docs/goal/evidence/parity"))
        )
        self.assertEqual(
            "../old/x.png", parity_capture._board_src("docs/goal/evidence/old/x.png", Path("docs/goal/evidence/parity"))
        )
        self.assertEqual(
            "../parity%23baseline/x%20y.png",
            parity_capture._board_src("docs/goal/evidence/parity#baseline/x y.png", Path("docs/goal/evidence/parity")),
        )
        self.set_surfaces(["ready"], ["390"])
        route_map = self.write_route_map({"/home": {"reference": {"selector": "#nav"}}})
        old_cwd = os.getcwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, old_cwd)
        relative_out = Path("docs/goal/evidence/parity")
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = parity_capture.main([
                "--plan", str(self.plan), "--reference", str(self.reference),
                "--base-url", "http://localhost:3000", "--route-map", str(route_map),
                "--out", str(relative_out),
            ])
        self.assertEqual(0, code, stdout.getvalue())
        manifest = json.loads((relative_out / "manifest.json").read_text(encoding="utf-8"))
        row = manifest["captured"][0]
        self.assertTrue(row["target"].startswith("docs/goal/evidence/parity/"))
        board = (relative_out / "parity-board.html").read_text(encoding="utf-8")
        self.assertIn(f'src="{Path(row["target"]).name}"', board)
        self.assertNotIn("docs/goal/evidence/parity/", board)

    def read_manifest(self) -> dict[str, object]:
        return json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))

    def run_ready_matrix(self, *extra: str) -> tuple[int, str]:
        self.set_surfaces(["ready"], ["390", "768", "1200"])
        route_map = self.write_route_map({"/home": {"reference": {"selector": "#nav"}}})
        return self.run_main("--route-map", str(route_map), *extra)

    @unittest.skipUnless(parity_capture._load_pillow(), "pixel diff needs Pillow")
    def test_a_small_missing_element_is_changed_even_under_the_tolerance(self) -> None:
        image_module, _ = parity_capture._load_pillow()
        target, actual = self.root / "t.png", self.root / "a.png"
        base = image_module.new("RGBA", (100, 100), (255, 255, 255, 255))
        base.save(target)
        missing = base.copy()
        for x in range(40, 50):          # a 10 x 5 element dropped: 50 px = 0.5 %
            for y in range(40, 45):
                missing.putpixel((x, y), (0, 0, 0, 255))
        missing.save(actual)
        diff, reason = parity_capture._pixel_diff(target, actual)
        self.assertIsNone(reason)
        self.assertEqual([40, 40, 50, 45], diff["diff_box"])
        self.assertEqual("changed", parity_capture._classify(diff, 0.01))
        noise = base.copy()
        for y in range(10, 40):          # a one-pixel-wide seam: 30 px = 0.3 %
            noise.putpixel((20, y), (254, 255, 255, 255))
        noise.save(actual)
        diff, _ = parity_capture._pixel_diff(target, actual)
        self.assertEqual("identical", parity_capture._classify(diff, 0.01))
        self.assertEqual("changed", parity_capture._classify(diff, 0.0))

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    @unittest.skipUnless(parity_capture._load_pillow(), "pixel diff needs Pillow")
    def test_identical_pairs_are_classified_and_fingerprinted(self) -> None:
        code, out = self.run_ready_matrix()
        self.assertEqual(0, code, out)
        manifest = self.read_manifest()
        # Classification is reviewer input; the manifest verdict is unchanged.
        self.assertEqual("PASS", manifest["status"])
        self.assertTrue(manifest["gating_eligible"])
        self.assertEqual({"identical": 3}, manifest["classification_counts"])
        self.assertEqual(0.0, manifest["tolerance"])
        for row in manifest["captured"]:
            self.assertEqual("identical", row["classification"])
            self.assertEqual(
                {"ratio": 0.0, "differing_pixels": 0, "total_pixels": 100, "sizes_matched": True,
                 "target_size": [10, 10], "actual_size": [10, 10], "diff_box": None},
                row["pixel_diff"],
            )
            self.assertIsNone(row["pixel_diff_reason"])
            canonical = json.dumps(row["geometry"], sort_keys=True, separators=(",", ":"))
            self.assertEqual(hashlib.sha256(canonical.encode("utf-8")).hexdigest(), row["geometry_fingerprint"])

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    @unittest.skipUnless(parity_capture._load_pillow(), "pixel diff needs Pillow")
    def test_differing_pixels_make_the_pair_changed(self) -> None:
        os.environ["STUB_SHOT_PATCH_ACTUAL"] = "1x1"
        code, out = self.run_ready_matrix()
        self.assertEqual(0, code, out)
        manifest = self.read_manifest()
        self.assertEqual({"changed": 3}, manifest["classification_counts"])
        for row in manifest["captured"]:
            self.assertEqual("changed", row["classification"])
            self.assertEqual(1, row["pixel_diff"]["differing_pixels"])
            self.assertEqual(0.01, row["pixel_diff"]["ratio"])

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    @unittest.skipUnless(parity_capture._load_pillow(), "pixel diff needs Pillow")
    def test_tolerance_sets_the_identical_threshold(self) -> None:
        os.environ["STUB_SHOT_PATCH_ACTUAL"] = "1x1"
        code, out = self.run_ready_matrix("--tolerance", "0.02")
        self.assertEqual(0, code, out)
        manifest = self.read_manifest()
        self.assertEqual(0.02, manifest["tolerance"])
        self.assertEqual({"identical": 3}, manifest["classification_counts"])
        code, out = self.run_ready_matrix("--tolerance", "0.005")
        self.assertEqual(0, code, out)
        self.assertEqual({"changed": 3}, self.read_manifest()["classification_counts"])

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    @unittest.skipUnless(parity_capture._load_pillow(), "pixel diff needs Pillow")
    def test_a_size_mismatch_is_never_identical(self) -> None:
        os.environ["STUB_SHOT_SIZE_ACTUAL"] = "10x12"
        code, out = self.run_ready_matrix("--tolerance", "1.0")
        self.assertEqual(0, code, out)
        row = self.read_manifest()["captured"][0]
        self.assertEqual("changed", row["classification"])
        diff = row["pixel_diff"]
        self.assertFalse(diff["sizes_matched"])
        self.assertEqual([10, 10], diff["target_size"])
        self.assertEqual([10, 12], diff["actual_size"])
        # The two extra rows exist only on one side, so they count as differing.
        self.assertEqual(20, diff["differing_pixels"])
        self.assertEqual(120, diff["total_pixels"])
        board = (self.out / "parity-board.html").read_text(encoding="utf-8")
        self.assertIn("size mismatch: target 10\u00d710, actual 10\u00d712", board)

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    def test_without_pillow_the_diff_is_recorded_as_unavailable(self) -> None:
        with patch.object(parity_capture, "_load_pillow", return_value=None):
            code, out = self.run_ready_matrix()
        self.assertEqual(0, code, out)
        manifest = self.read_manifest()
        self.assertEqual("PASS", manifest["status"])
        for row in manifest["captured"]:
            self.assertIsNone(row["pixel_diff"])
            self.assertEqual("Pillow is not installed", row["pixel_diff_reason"])
            self.assertEqual("changed", row["classification"])
            self.assertIsNotNone(row["geometry_fingerprint"])
        board = (self.out / "parity-board.html").read_text(encoding="utf-8")
        self.assertIn("pixel diff unavailable: Pillow is not installed", board)

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    @unittest.skipUnless(parity_capture._load_pillow(), "pixel diff needs Pillow")
    def test_undecodable_images_never_fail_the_capture(self) -> None:
        os.environ["STUB_SHOT_MODE"] = "garbage"
        code, out = self.run_ready_matrix()
        self.assertEqual(0, code, out)
        for row in self.read_manifest()["captured"]:
            self.assertIsNone(row["pixel_diff"])
            self.assertTrue(row["pixel_diff_reason"].startswith("cannot decode the pair"))
            self.assertEqual("changed", row["classification"])

    def test_tolerance_must_be_a_fraction(self) -> None:
        for bad in ("1.5", "-0.1", "abc"):
            with self.subTest(bad=bad), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    self.run_main("--tolerance", bad)
                self.assertEqual(2, raised.exception.code)

    def board_row(self, name: str, classification: str, ratio: float | None) -> dict[str, object]:
        diff = None if ratio is None else {
            "ratio": ratio, "differing_pixels": int(ratio * 100), "total_pixels": 100,
            "sizes_matched": True, "target_size": [10, 10], "actual_size": [10, 10],
        }
        return {
            "surface_id": "UI-001", "route": f"/{name}", "breakpoint": "390", "state": "ready",
            "target": (self.out / f"{name}-target.png").as_posix(),
            "actual": (self.out / f"{name}-actual.png").as_posix(),
            "geometry": {"overflowX": 0, "scanned": 5, "overlaps": []}, "geometry_error": None,
            "classification": classification, "pixel_diff": diff,
            "pixel_diff_reason": None if diff else "Pillow is not installed",
        }

    def test_board_lists_changed_pairs_first_and_folds_identical_ones(self) -> None:
        self.out.mkdir(parents=True)
        captured = [
            self.board_row("same-a", "identical", 0.0),
            self.board_row("small", "changed", 0.02),
            self.board_row("unknown", "changed", None),
            self.board_row("same-b", "identical", 0.0),
            self.board_row("large", "changed", 0.30),
        ]
        skipped = [{"route": "/skipped", "breakpoint": "390", "state": "empty", "reason": "no trigger"}]
        board = parity_capture._board(self.out, captured, skipped).read_text(encoding="utf-8")
        order = [board.index(marker) for marker in
                 ("/unknown", "/large", "/small", "<details", "/same-a", "/same-b", "SKIPPED")]
        self.assertEqual(sorted(order), order)
        self.assertIn("2 identical pairs</summary>", board)
        self.assertIn("30.0000% of pixels differ (30 of 100)", board)
        # The folded section is collapsed by default (no `open` attribute).
        self.assertNotRegex(board, r"<details[^>]* open")
        self.assertEqual(1, board.count("<details"))

    def test_board_with_one_identical_pair_uses_the_singular(self) -> None:
        self.out.mkdir(parents=True)
        board = parity_capture._board(
            self.out, [self.board_row("only", "identical", 0.0)], []
        ).read_text(encoding="utf-8")
        self.assertIn("1 identical pair</summary>", board)

    def carry_run(self, *extra: str, out: Path | None = None) -> tuple[int, str]:
        """One-pair run; the log is cleared first so calls() covers this run only."""

        self.set_surfaces(["ready"], ["390"])
        route_map = self.write_route_map({"/home": {"reference": {"selector": "#nav"}}})
        self.log_path.unlink(missing_ok=True)
        args = ["--route-map", str(route_map), *extra]
        if out is not None:
            args += ["--out", str(out)]
        return self.run_main(*args)

    def first_run(self, *extra: str) -> Path:
        code, output = self.carry_run(*extra)
        self.assertEqual(0, code, output)
        return self.out / "manifest.json"

    def reference_opens(self) -> int:
        return sum(1 for argv in self.work_calls() if argv == ["open", self.reference.resolve().as_uri()])

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    @unittest.skipUnless(parity_capture._load_pillow(), "pixel diff needs Pillow")
    def test_carry_from_skips_the_reference_for_an_unchanged_pair(self) -> None:
        first = self.first_run()
        before = json.loads(first.read_text(encoding="utf-8"))["captured"][0]
        code, output = self.carry_run("--carry-from", str(first))
        self.assertEqual(0, code, output)
        manifest = self.read_manifest()
        self.assertEqual("PASS", manifest["status"])
        self.assertTrue(manifest["gating_eligible"])
        self.assertEqual({"carried": 1}, manifest["classification_counts"])
        self.assertEqual(first.as_posix(), manifest["carry_from"])
        row = manifest["captured"][0]
        self.assertEqual("carried", row["classification"])
        self.assertEqual({"manifest": first.as_posix(), "classification": "identical"}, row["carried_from"])
        for key in ("target", "actual", "target_sha256", "actual_sha256", "pixel_diff", "tuple_sha256"):
            self.assertEqual(before[key], row[key], key)
        # The geometry is probed again, so layout_check keeps a fresh trace.
        self.assertEqual(before["geometry_fingerprint"], row["geometry_fingerprint"])
        self.assertEqual(
            [["open", "http://localhost:3000/home"], ["wait", "--load", "networkidle"],
             ["set", "viewport", "390", "1000"], ["screenshot", "actual"], ["eval", "--stdin"]],
            self.work_calls(),
        )
        board = (self.out / "parity-board.html").read_text(encoding="utf-8")
        self.assertIn("1 carried pair</summary>", board)

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    @unittest.skipUnless(parity_capture._load_pillow(), "pixel diff needs Pillow")
    def test_carried_rows_keep_the_previous_paths_in_another_out_dir(self) -> None:
        first = self.first_run()
        before = json.loads(first.read_text(encoding="utf-8"))["captured"][0]
        other = self.root / "next-run"
        code, output = self.carry_run("--carry-from", str(first), out=other)
        self.assertEqual(0, code, output)
        row = json.loads((other / "manifest.json").read_text(encoding="utf-8"))["captured"][0]
        self.assertEqual("carried", row["classification"])
        self.assertEqual(before["target"], row["target"])
        self.assertTrue(Path(row["target"]).is_file())
        self.assertTrue(str(row["target"]).startswith(self.out.as_posix()))
        board = (other / "parity-board.html").read_text(encoding="utf-8")
        self.assertIn("../docs/goal/evidence/parity/", board)

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    @unittest.skipUnless(parity_capture._load_pillow(), "pixel diff needs Pillow")
    def test_a_carried_pair_can_be_carried_again(self) -> None:
        first = self.first_run()
        second_out = self.root / "second"
        self.assertEqual(0, self.carry_run("--carry-from", str(first), out=second_out)[0])
        third_out = self.root / "third"
        code, output = self.carry_run("--carry-from", str(second_out / "manifest.json"), out=third_out)
        self.assertEqual(0, code, output)
        row = json.loads((third_out / "manifest.json").read_text(encoding="utf-8"))["captured"][0]
        self.assertEqual("carried", row["classification"])
        self.assertEqual("carried", row["carried_from"]["classification"])
        self.assertEqual(0, self.reference_opens())

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    @unittest.skipUnless(parity_capture._load_pillow(), "pixel diff needs Pillow")
    def test_a_changed_page_is_recaptured_not_carried(self) -> None:
        # A new geometry changes the fingerprint. New pixels with the same
        # geometry are the case the fingerprint alone would miss.
        cases = {
            "geometry": ({"STUB_GEOMETRY_SCANNED": "6"}, "identical"),
            "pixels": ({"STUB_SHOT_COLOR_ACTUAL": "ff0000"}, "changed"),
        }
        for name, (env, expected) in cases.items():
            with self.subTest(name):
                previous_out = self.root / f"previous-{name}"
                self.assertEqual(0, self.carry_run(out=previous_out)[0])
                with patch.dict(os.environ, env):
                    code, output = self.carry_run(
                        "--carry-from", str(previous_out / "manifest.json"), out=self.out
                    )
                self.assertEqual(0, code, output)
                self.assertEqual(expected, self.read_manifest()["captured"][0]["classification"])
                self.assertEqual(1, self.reference_opens())

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    @unittest.skipUnless(parity_capture._load_pillow(), "pixel diff needs Pillow")
    def test_a_changed_reference_is_recaptured_not_carried(self) -> None:
        first = self.first_run()
        self.reference.write_text("<html><body>new design</body></html>", encoding="utf-8")
        code, output = self.carry_run("--carry-from", str(first))
        self.assertEqual(0, code, output)
        self.assertEqual("identical", self.read_manifest()["captured"][0]["classification"])
        self.assertEqual(1, self.reference_opens())

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    @unittest.skipUnless(parity_capture._load_pillow(), "pixel diff needs Pillow")
    def test_a_changed_linked_reference_asset_is_recaptured_not_carried(self) -> None:
        css = self.root / "theme.css"
        css.write_text("body{color:black}", encoding="utf-8")
        self.reference.write_text(
            '<html><head><link rel="stylesheet" href="theme.css"></head><body>ref</body></html>', encoding="utf-8"
        )
        first = self.first_run()
        css.write_text("body{color:red}", encoding="utf-8")   # the HTML bytes are unchanged
        code, output = self.carry_run("--carry-from", str(first))
        self.assertEqual(0, code, output)
        self.assertEqual("identical", self.read_manifest()["captured"][0]["classification"])
        self.assertEqual(1, self.reference_opens())

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    @unittest.skipUnless(parity_capture._load_pillow(), "pixel diff needs Pillow")
    def test_a_changed_asset_behind_the_stylesheet_is_recaptured_not_carried(self) -> None:
        (self.root / "theme.css").write_text("body{background:url(bg.svg)}", encoding="utf-8")
        (self.root / "bg.svg").write_text("<svg><rect fill='red'/></svg>", encoding="utf-8")
        self.reference.write_text(
            '<html><head><link rel="stylesheet" href="theme.css"></head><body>ref</body></html>', encoding="utf-8"
        )
        first = self.first_run()
        (self.root / "bg.svg").write_text("<svg><rect fill='blue'/></svg>", encoding="utf-8")   # two links away
        code, output = self.carry_run("--carry-from", str(first))
        self.assertEqual(0, code, output)
        self.assertEqual("identical", self.read_manifest()["captured"][0]["classification"])
        self.assertEqual(1, self.reference_opens())

    def test_reference_identity_follows_imports_and_inline_urls(self) -> None:
        (self.root / "base.css").write_text("@font-face{src:url(font.woff2)}", encoding="utf-8")
        (self.root / "theme.css").write_text('@import "base.css";', encoding="utf-8")
        (self.root / "font.woff2").write_bytes(b"font-a")
        (self.root / "hero.png").write_bytes(b"png-a")
        self.reference.write_text(
            '<html><head><link href="theme.css"><style>.hero{background:url("hero.png")}</style></head><body>ref</body></html>',
            encoding="utf-8",
        )
        before = parity_capture._reference_identity(self.reference)
        (self.root / "font.woff2").write_bytes(b"font-b")
        changed_font = parity_capture._reference_identity(self.reference)
        self.assertNotEqual(before, changed_font)
        (self.root / "hero.png").write_bytes(b"png-b")
        self.assertNotEqual(changed_font, parity_capture._reference_identity(self.reference))

    def test_reference_identity_tracks_linked_local_files_only(self) -> None:
        css = self.root / "theme.css"
        css.write_text("a{}", encoding="utf-8")
        self.reference.write_text(
            '<html><head><link href="theme.css"><script src="https://cdn.example/x.js"></script>'
            '<img src="data:image/png;base64,AA=="></head><body>ref</body></html>', encoding="utf-8"
        )
        before = parity_capture._reference_identity(self.reference)
        css.write_text("b{}", encoding="utf-8")
        self.assertNotEqual(before, parity_capture._reference_identity(self.reference))
        self.reference.write_text(
            '<html><head><link href="missing.css"></head><body>ref</body></html>', encoding="utf-8"
        )
        missing = parity_capture._reference_identity(self.reference)
        (self.root / "missing.css").write_text("c{}", encoding="utf-8")
        self.assertNotEqual(missing, parity_capture._reference_identity(self.reference))

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    @unittest.skipUnless(parity_capture._load_pillow(), "pixel diff needs Pillow")
    def test_a_changed_route_map_trigger_is_recaptured_not_carried(self) -> None:
        first = self.first_run()
        self.set_surfaces(["ready"], ["390"])
        route_map = self.write_route_map({"/home": {"reference": {"selector": "#other-nav"}}})
        self.log_path.unlink()
        code, output = self.run_main("--route-map", str(route_map), "--carry-from", str(first))
        self.assertEqual(0, code, output)
        self.assertEqual("identical", self.read_manifest()["captured"][0]["classification"])
        self.assertEqual(1, self.reference_opens())

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    @unittest.skipUnless(parity_capture._load_pillow(), "pixel diff needs Pillow")
    def test_only_an_identical_previous_pair_is_carried(self) -> None:
        os.environ["STUB_SHOT_PATCH_ACTUAL"] = "1x1"
        first = self.first_run()
        self.assertEqual("changed", self.read_manifest()["captured"][0]["classification"])
        code, output = self.carry_run("--carry-from", str(first))
        self.assertEqual(0, code, output)
        self.assertEqual("changed", self.read_manifest()["captured"][0]["classification"])
        self.assertEqual(1, self.reference_opens())

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    @unittest.skipUnless(parity_capture._load_pillow(), "pixel diff needs Pillow")
    def test_a_tighter_tolerance_stops_carrying(self) -> None:
        os.environ["STUB_SHOT_PATCH_ACTUAL"] = "1x1"
        first = self.first_run("--tolerance", "0.02")
        self.assertEqual("identical", self.read_manifest()["captured"][0]["classification"])
        kept = self.root / "kept-manifest.json"
        shutil.copy(first, kept)  # the next run rewrites manifest.json in the same directory
        code, output = self.carry_run("--carry-from", str(kept), "--tolerance", "0.0")
        self.assertEqual(0, code, output)
        self.assertEqual("changed", self.read_manifest()["captured"][0]["classification"])
        code, output = self.carry_run("--carry-from", str(kept), "--tolerance", "0.02")
        self.assertEqual(0, code, output)
        self.assertEqual("carried", self.read_manifest()["captured"][0]["classification"])

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    @unittest.skipUnless(parity_capture._load_pillow(), "pixel diff needs Pillow")
    def test_previous_images_that_changed_on_disk_are_not_carried(self) -> None:
        first = self.first_run()
        row = json.loads(first.read_text(encoding="utf-8"))["captured"][0]
        Path(row["target"]).write_bytes(b"edited after the review")
        code, output = self.carry_run("--carry-from", str(first))
        self.assertEqual(0, code, output)
        self.assertEqual("identical", self.read_manifest()["captured"][0]["classification"])
        self.assertEqual(1, self.reference_opens())

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    @unittest.skipUnless(parity_capture._load_pillow(), "pixel diff needs Pillow")
    def test_recapture_carried_captures_every_pair_again(self) -> None:
        first = self.first_run()
        code, output = self.carry_run("--carry-from", str(first), "--recapture-carried")
        self.assertEqual(0, code, output)
        manifest = self.read_manifest()
        self.assertEqual({"identical": 1}, manifest["classification_counts"])
        self.assertTrue(manifest["recapture_carried"])
        self.assertEqual(1, self.reference_opens())

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    def test_an_old_manifest_without_tuple_hashes_carries_nothing(self) -> None:
        first = self.first_run()
        data = json.loads(first.read_text(encoding="utf-8"))
        for row in data["captured"]:
            for key in ("tuple_sha256", "geometry_fingerprint", "actual_sha256"):
                row.pop(key)
        first.write_text(json.dumps(data), encoding="utf-8")
        code, output = self.carry_run("--carry-from", str(first))
        self.assertEqual(0, code, output)
        self.assertNotIn("carried", self.read_manifest()["classification_counts"])
        self.assertEqual(1, self.reference_opens())

    def test_an_unusable_carry_source_is_refused_before_any_browser_work(self) -> None:
        broken = self.root / "broken.json"
        broken.write_text("{not json", encoding="utf-8")
        no_rows = self.root / "no-rows.json"
        no_rows.write_text(json.dumps({"captured": 5}), encoding="utf-8")
        for source in (self.root / "missing.json", broken, no_rows):
            with self.subTest(source=source.name):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    code, _ = self.run_main("--carry-from", str(source))
                self.assertEqual(1, code)
                self.assertIn("--carry-from", stderr.getvalue())
        self.assertEqual([], self.calls())

    def test_recapture_carried_needs_a_carry_source(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as raised:
                self.run_main("--recapture-carried")
        self.assertEqual(2, raised.exception.code)

    def half_second_clock(self):
        """A clock that moves 0.5 s on every reading, so durations are exact."""

        readings = iter(range(10_000))
        return patch.object(parity_capture, "_clock", side_effect=lambda: next(readings) * 0.5)

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    def test_manifest_records_a_duration_per_pair_and_in_total(self) -> None:
        with self.half_second_clock():
            code, out = self.run_ready_matrix()
        self.assertEqual(0, code, out)
        manifest = self.read_manifest()
        # Each pair has one app block and one reference block (one reading
        # at each end), so 2 x 0.5 s each; the total runs from the first
        # reading to the last: 3 pairs x 4 readings + 1 more at each end.
        self.assertEqual([1000, 1000, 1000], [row["duration_ms"] for row in manifest["captured"]])
        self.assertEqual(6500, manifest["duration_ms"])
        self.assertIn("in 6.5s;", out)

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    @unittest.skipUnless(parity_capture._load_pillow(), "pixel diff needs Pillow")
    def test_a_carried_pair_only_spends_its_app_time(self) -> None:
        first = self.first_run()
        with self.half_second_clock():
            code, out = self.carry_run("--carry-from", str(first))
        self.assertEqual(0, code, out)
        manifest = self.read_manifest()
        self.assertEqual("carried", manifest["captured"][0]["classification"])
        self.assertEqual(500, manifest["captured"][0]["duration_ms"])
        self.assertEqual(1500, manifest["duration_ms"])

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    def test_real_durations_are_whole_milliseconds(self) -> None:
        code, out = self.run_ready_matrix()
        self.assertEqual(0, code, out)
        manifest = self.read_manifest()
        self.assertIsInstance(manifest["duration_ms"], int)
        for row in manifest["captured"]:
            self.assertIsInstance(row["duration_ms"], int)
            self.assertGreaterEqual(row["duration_ms"], 0)
        self.assertGreaterEqual(manifest["duration_ms"], max(row["duration_ms"] for row in manifest["captured"]))

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    def test_colliding_route_and_state_tokens_keep_distinct_evidence(self) -> None:
        routes = ["/foo/bar", "/foo-bar", "/FOO-BAR", "/" + "long-route-" * 21]
        states = ["ready", "error/value", "error-value"]
        self.plan.write_text(plan_markdown([
            {"id": f"UI-{index:03}", "route": route, "breakpoints": ["390"], "states": states}
            for index, route in enumerate(routes, 1)
        ]), encoding="utf-8")
        route_map = self.root / "route-map.json"
        route_map.write_text(json.dumps({route: {
            "reference": {"selector": "#nav"},
            "states": {state: {"app_eval": "window.fixtureState = true"} for state in states},
        } for route in routes}), encoding="utf-8")
        code, output = self.run_main("--route-map", str(route_map))
        self.assertEqual(0, code, output)
        manifest = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(manifest["gating_eligible"])
        rows = manifest["captured"]
        self.assertEqual(12, len(rows))
        paths = [row[kind] for row in rows for kind in ("target", "actual")]
        self.assertEqual(24, len({path.casefold() for path in paths}))
        self.assertTrue(all(Path(path).is_file() for path in paths))
        self.assertTrue(all(len(Path(path).name) <= 140 for path in paths))

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    def test_captures_the_full_non_na_matrix(self) -> None:
        route_map = self.root / "route-map.json"
        route_map.write_text(
            json.dumps(
                {
                    "/home": {
                        "reference": {"selector": "#nav-home"},
                        "states": {"empty": {"app_eval": "window.__setEmpty()"}},
                    }
                }
            ),
            encoding="utf-8",
        )
        code, out = self.run_main("--route-map", str(route_map))
        self.assertEqual(0, code, out)

        for width in ("390", "768", "1200"):
            self.assertEqual(1, len(list(self.out.glob(f"home-ready-{width}-*-target.png"))))
            self.assertEqual(1, len(list(self.out.glob(f"home-ready-{width}-*-actual.png"))))
        manifest = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(6, len(manifest["captured"]))
        self.assertEqual(0, len(manifest["skipped"]))
        self.assertEqual(6, manifest["required_combinations"])
        self.assertEqual(6, manifest["selected_combinations"])
        self.assertEqual("PASS", manifest["status"])
        self.assertTrue(manifest["gating_eligible"])
        self.assertNotIn("loading", {item["state"] for item in manifest["captured"] + manifest["skipped"]})
        self.assertEqual(
            "route-map selector #nav-home", manifest["reference_nav"]["/home"]
        )
        board = (self.out / "parity-board.html").read_text(encoding="utf-8")
        self.assertIn("target (design reference)", board)
        self.assertIn("actual (implementation)", board)
        self.assertIn("home-ready-390-", board)

        calls = self.calls()
        self.assertIn(["set", "viewport", "390", "1000"], calls)
        self.assertIn(["open", "http://localhost:3000/home"], calls)

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    def test_route_map_state_triggers_capture_non_ready_states(self) -> None:
        route_map = self.root / "route-map.json"
        route_map.write_text(
            json.dumps(
                {
                    "/home": {
                        "reference": {"selector": "#nav-home"},
                        "states": {
                            "empty": {"app_eval": "window.__setEmpty()"},
                        },
                    }
                }
            ),
            encoding="utf-8",
        )
        code, out = self.run_main("--route-map", str(route_map))
        self.assertEqual(0, code, out)
        self.assertEqual(1, len(list(self.out.glob("home-empty-768-*-actual.png"))))
        manifest = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(6, len(manifest["captured"]))
        self.assertEqual(0, len(manifest["skipped"]))
        self.assertIn(["eval", "--stdin"], self.calls())

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    def test_a_skipped_required_state_combination_fails(self) -> None:
        route_map = self.root / "route-map.json"
        route_map.write_text(
            json.dumps({"/home": {"reference": {"selector": "#nav-home"}}}),
            encoding="utf-8",
        )
        code, out = self.run_main("--route-map", str(route_map))
        self.assertEqual(1, code, out)
        manifest = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(3, len(manifest["captured"]))
        self.assertEqual(3, len(manifest["skipped"]))
        self.assertEqual("FAIL", manifest["status"])
        self.assertTrue(
            any(
                "no app_eval trigger for state 'empty'" in problem
                for problem in manifest["errors"]
            )
        )

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    def test_reference_probe_failure_skips_with_reason(self) -> None:
        os.environ["STUB_PROBE_RESULT"] = "false"
        code, out = self.run_main()
        self.assertEqual(1, code, out)
        manifest = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(0, len(manifest["captured"]))
        self.assertEqual(6, len(manifest["skipped"]))
        self.assertEqual("FAIL", manifest["status"])
        self.assertIn("no parity pairs were captured", manifest["errors"])
        # Ready reaches navigation and fails there; untriggered states are
        # skipped earlier for their missing app_eval trigger.
        reasons = [item["reason"] for item in manifest["skipped"]]
        self.assertEqual(
            3, sum(1 for reason in reasons if "reference nav" in reason)
        )
        self.assertEqual(
            3, sum(1 for reason in reasons if "no app_eval trigger" in reason)
        )

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    def test_only_filter_restricts_to_one_route(self) -> None:
        self.plan.write_text(
            plan_markdown(
                [
                    {
                        "id": "UI-001",
                        "trace_ids": ["REQ-001"],
                        "route": "/home",
                        "breakpoints": ["390"],
                        "states": ["ready"],
                        "evidence_gate": "required",
                    },
                    {
                        "id": "UI-002",
                        "trace_ids": ["REQ-002"],
                        "route": "/settings",
                        "breakpoints": ["390"],
                        "states": ["ready"],
                        "evidence_gate": "required",
                    },
                ]
            ),
            encoding="utf-8",
        )
        route_map = self.root / "route-map.json"
        route_map.write_text(
            json.dumps(
                {
                    "/home": {"reference": {"selector": "#a"}},
                    "/settings": {"reference": {"selector": "#b"}},
                }
            ),
            encoding="utf-8",
        )
        code, out = self.run_main("--route-map", str(route_map), "--only", "/settings")
        self.assertEqual(2, code, out)
        self.assertEqual(1, len(list(self.out.glob("settings-ready-390-*-target.png"))))
        self.assertEqual([], list(self.out.glob("home-ready-390-*-target.png")))
        manifest = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("PARTIAL", manifest["status"])
        self.assertFalse(manifest["gating_eligible"])
        self.assertEqual(2, manifest["required_combinations"])
        self.assertEqual(1, manifest["selected_combinations"])
        self.assertEqual(["/settings"], manifest["only_routes"])

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    def test_geometry_probe_nonzero_fails_the_capture(self) -> None:
        os.environ["STUB_GEOMETRY_MODE"] = "exit"
        route_map = self.root / "route-map.json"
        route_map.write_text(
            json.dumps(
                {
                    "/home": {
                        "reference": {"selector": "#nav-home"},
                        "states": {"empty": {"app_eval": "window.__setEmpty()"}},
                    }
                }
            ),
            encoding="utf-8",
        )
        code, out = self.run_main("--route-map", str(route_map))
        self.assertEqual(1, code, out)
        manifest = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("FAIL", manifest["status"])
        self.assertFalse(manifest["gating_eligible"])
        self.assertTrue(
            any("geometry unavailable" in problem for problem in manifest["errors"])
        )
        board = (self.out / "parity-board.html").read_text(encoding="utf-8")
        self.assertIn("geometry probe unavailable", board)
        self.assertNotIn("geometry probe: clean", board)

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    def test_geometry_probe_malformed_json_fails_the_capture(self) -> None:
        os.environ["STUB_GEOMETRY_MODE"] = "malformed"
        route_map = self.root / "route-map.json"
        route_map.write_text(
            json.dumps(
                {
                    "/home": {
                        "reference": {"selector": "#nav-home"},
                        "states": {"empty": {"app_eval": "window.__setEmpty()"}},
                    }
                }
            ),
            encoding="utf-8",
        )
        code, out = self.run_main("--route-map", str(route_map))
        self.assertEqual(1, code, out)
        manifest = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertTrue(
            any("no valid JSON object" in problem for problem in manifest["errors"])
        )

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    def test_browser_arguments_never_cross_a_windows_shell_boundary(self) -> None:
        arguments = [
            "open",
            'http://example.invalid/?x=&whoami|echo^%PATH%<(test)>"quoted"',
            "literal&(pipe|group)^<redirect>",
        ]
        sentinel = self.root / "injected.txt"
        completed = parity_capture._run_browser(
            [sys.executable, str(self.stub_py)],
            [*arguments, str(sentinel)],
        )
        self.assertEqual(0, completed.returncode)
        self.assertEqual([*arguments, str(sentinel)], self.calls()[-1])
        self.assertFalse(sentinel.exists())
        with self.assertRaisesRegex(RuntimeError, "direct native or Node argv"):
            parity_capture._run_browser(
                [str(self.root / "agent-browser.cmd")],
                arguments,
            )

    @unittest.skipUnless(sys.platform == "darwin", "macOS descriptor behavior")
    def test_darwin_launcher_binding_fails_closed_but_reads_still_bind(self) -> None:
        launcher = Path(sys.executable).resolve()
        with self.assertRaisesRegex(RuntimeError, "descriptor-backed launcher path is unavailable"):
            parity_capture._bind_posix_launcher(launcher)
        bound, descriptor = parity_capture._bind_posix_launcher(launcher, executable=False)
        try:
            self.assertEqual(f"/dev/fd/{descriptor}", bound)
        finally:
            os.close(descriptor)

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    @unittest.skipUnless(os.name != "nt", "descriptor launcher fixture is POSIX-only")
    def test_posix_launcher_binding_survives_path_replacement(self) -> None:
        launcher = self.root / "launcher"
        replacement = self.root / "replacement"
        launcher.write_text("#!/bin/sh\necho old\n", encoding="utf-8")
        replacement.write_text("#!/bin/sh\necho new\n", encoding="utf-8")
        launcher.chmod(0o755)
        replacement.chmod(0o755)
        bound, descriptor = parity_capture._bind_posix_launcher(launcher)
        try:
            os.replace(replacement, launcher)
            completed = subprocess.run(
                [bound], pass_fds=(descriptor,), capture_output=True, text=True, check=False
            )
            self.assertEqual("old\n", completed.stdout)
        finally:
            os.close(descriptor)

    @unittest.skipIf(sys.platform == "darwin", DARWIN_FD_EXEC)
    @unittest.skipUnless(os.name != "nt", "descriptor launcher fixture is POSIX-only")
    def test_posix_symlink_launcher_fails_closed_and_resolved_inode_stays_bound(self) -> None:
        original = self.root / "original"
        replacement = self.root / "replacement"
        link = self.root / "agent-browser"
        original.write_text("#!/bin/sh\necho original\n", encoding="utf-8")
        replacement.write_text("#!/bin/sh\necho replacement\n", encoding="utf-8")
        original.chmod(0o755)
        replacement.chmod(0o755)
        try:
            link.symlink_to(original)
        except OSError as exc:
            self.skipTest(f"symlink unavailable: {exc}")
        bound, descriptor = parity_capture._bind_posix_launcher(link)
        try:
            os.replace(replacement, original)
            completed = subprocess.run(
                [bound], pass_fds=(descriptor,), capture_output=True, text=True, check=False
            )
            self.assertEqual("original\n", completed.stdout)
        finally:
            os.close(descriptor)

    @unittest.skipIf(os.name != "nt", "Windows npm shim resolution needs native Windows pathlib")
    def test_windows_npm_shim_resolves_to_direct_node_argv(self) -> None:
        npm_bin = self.root / "npm-bin"
        javascript = (
            npm_bin
            / "node_modules"
            / "agent-browser"
            / "bin"
            / "agent-browser.js"
        )
        javascript.parent.mkdir(parents=True)
        javascript.write_text("// fixture\n", encoding="utf-8")
        wrapper = npm_bin / "agent-browser.cmd"
        wrapper.write_text("@echo off\n", encoding="utf-8")
        node = npm_bin / "node.exe"
        node.write_bytes(b"fixture")

        def which(name: str) -> str | None:
            return {
                "agent-browser": str(wrapper),
                "node.exe": str(node),
                "node": str(node),
            }.get(name)

        with patch.object(parity_capture.os, "name", "nt"), patch.object(
            parity_capture.shutil, "which", side_effect=which
        ), patch.object(
            parity_capture,
            "_trusted_launcher_path",
            side_effect=lambda path, _label: path.resolve(),
        ):
            resolved = self._old_resolve_cli()
        self.assertEqual(
            [str(node.resolve()), str(javascript.resolve())],
            resolved,
        )

    def test_missing_cli_degrades_with_install_hint(self) -> None:
        os.environ["PATH"] = str(self.root / "nowhere")
        parity_capture._resolve_cli = self._old_resolve_cli
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code, _ = self.run_main()
        self.assertEqual(1, code)
        self.assertIn("npm i -g agent-browser", stderr.getvalue())

    def test_missing_reference_file_is_refused(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = parity_capture.main(
                [
                    "--plan", str(self.plan),
                    "--reference", str(self.root / "missing.html"),
                    "--base-url", "http://localhost:3000",
                    "--out", str(self.out),
                ]
            )
        self.assertEqual(1, code)
        self.assertIn("reference HTML not found", stderr.getvalue())

    def test_browser_extension_capture_reports_manual_platform_group(self) -> None:
        self.plan.write_text(
            plan_markdown(
                [
                    {
                        "id": "UI-EXT",
                        "trace_ids": ["REQ-001"],
                        "route": "/popup",
                        "breakpoints": ["390", "768"],
                        "states": ["ready"],
                        "evidence_gate": "required",
                        "capture_mode": "browser-extension",
                    }
                ]
            ),
            encoding="utf-8",
        )
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code, stdout = self.run_main()
        self.assertEqual(0, code)
        self.assertIn("manual/platform groups", stdout)
        self.assertIn("browser-extension", stdout)
        self.assertFalse(self.out.exists())

    def test_native_capture_reports_manual_platform_group_without_base_url(self) -> None:
        self.plan.write_text(
            plan_markdown(
                [
                    {
                        "id": "UI-NATIVE",
                        "trace_ids": ["REQ-001"],
                        "route": "/home",
                        "breakpoints": ["compact", "regular"],
                        "states": ["ready"],
                        "evidence_gate": "required",
                        "capture_mode": "native",
                    }
                ]
            ),
            encoding="utf-8",
        )
        stderr = io.StringIO()
        stdout = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(stdout):
            code = parity_capture.main(
                [
                    "--plan", str(self.plan),
                    "--reference", str(self.reference),
                    "--out", str(self.out),
                ]
            )
        self.assertEqual(0, code)
        self.assertIn("manual/platform groups", stdout.getvalue())
        self.assertNotIn("--base-url is required", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
