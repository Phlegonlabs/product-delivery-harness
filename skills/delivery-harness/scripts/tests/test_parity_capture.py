"""Tests for parity_capture.py using a stubbed agent-browser CLI."""

from __future__ import annotations

import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import parity_capture  # noqa: E402

STUB_PY = r"""
import json, os, sys
argv = sys.argv[1:]
log = os.environ.get("STUB_LOG")
if log:
    with open(log, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(argv) + "\n")
if argv[:1] == ["--version"]:
    print("agent-browser 0.36.0-stub")
    raise SystemExit(0)
if argv[:1] == ["screenshot"]:
    path = argv[-1]
    with open(path, "wb") as handle:
        handle.write(b"\x89PNG\r\n\x1a\nstub")
    raise SystemExit(0)
if argv[:1] == ["eval"]:
    body = sys.stdin.read() if not sys.stdin.isatty() else ""
    if "overflowX" in body:
        print('{"overflowX": 0, "scanned": 5, "overlaps": []}')
    elif "a[href=" in body:
        print(os.environ.get("STUB_PROBE_RESULT", "false"))
    else:
        print("undefined")
    raise SystemExit(0)
print("stub ok")
"""

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


class ParityCaptureTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

        stub_dir = self.root / "bin"
        stub_dir.mkdir()
        (stub_dir / "_stub_browser.py").write_text(STUB_PY, encoding="utf-8")
        (stub_dir / "agent-browser").write_text(STUB_SH, encoding="utf-8")
        (stub_dir / "agent-browser.bat").write_text(STUB_BAT, encoding="utf-8")
        self.log_path = self.root / "calls.jsonl"
        self._old_env = {
            "PATH": os.environ.get("PATH"),
            "STUB_LOG": os.environ.get("STUB_LOG"),
            "STUB_PROBE_RESULT": os.environ.get("STUB_PROBE_RESULT"),
        }
        os.environ["PATH"] = str(stub_dir) + os.pathsep + (self._old_env["PATH"] or "")
        os.environ["STUB_LOG"] = str(self.log_path)
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

    def test_captures_ready_pairs_skips_untriggered_and_na_states(self) -> None:
        route_map = self.root / "route-map.json"
        route_map.write_text(
            json.dumps({"/home": {"reference": {"selector": "#nav-home"}}}),
            encoding="utf-8",
        )
        code, out = self.run_main("--route-map", str(route_map))
        self.assertEqual(0, code, out)

        for width in ("390", "768", "1200"):
            target = self.out / f"home-ready-{width}-target.png"
            actual = self.out / f"home-ready-{width}-actual.png"
            self.assertTrue(target.exists(), target)
            self.assertTrue(actual.exists(), actual)
        manifest = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(3, len(manifest["captured"]))
        self.assertEqual(3, len(manifest["skipped"]))
        self.assertTrue(
            all("no app_eval trigger for state 'empty'" in item["reason"] for item in manifest["skipped"])
        )
        self.assertNotIn("loading", {item["state"] for item in manifest["captured"] + manifest["skipped"]})
        self.assertEqual(
            "route-map selector #nav-home", manifest["reference_nav"]["/home"]
        )
        board = (self.out / "parity-board.html").read_text(encoding="utf-8")
        self.assertIn("target (design reference)", board)
        self.assertIn("actual (implementation)", board)
        self.assertIn("home-ready-390-target.png", board)

        calls = self.calls()
        self.assertIn(["set", "viewport", "390", "1000"], calls)
        self.assertIn(["open", "http://localhost:3000/home"], calls)

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
        self.assertTrue((self.out / "home-empty-768-actual.png").exists())
        manifest = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(6, len(manifest["captured"]))
        self.assertEqual(0, len(manifest["skipped"]))
        self.assertIn(["eval", "--stdin"], self.calls())

    def test_reference_probe_failure_skips_with_reason(self) -> None:
        os.environ["STUB_PROBE_RESULT"] = "false"
        code, out = self.run_main()
        self.assertEqual(0, code, out)
        manifest = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(0, len(manifest["captured"]))
        self.assertEqual(6, len(manifest["skipped"]))
        # Ready reaches navigation and fails there; untriggered states are
        # skipped earlier for their missing app_eval trigger.
        reasons = [item["reason"] for item in manifest["skipped"]]
        self.assertEqual(
            3, sum(1 for reason in reasons if "reference nav" in reason)
        )
        self.assertEqual(
            3, sum(1 for reason in reasons if "no app_eval trigger" in reason)
        )

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
        self.assertEqual(0, code, out)
        self.assertTrue((self.out / "settings-ready-390-target.png").exists())
        self.assertFalse((self.out / "home-ready-390-target.png").exists())

    def test_missing_cli_degrades_with_install_hint(self) -> None:
        os.environ["PATH"] = str(self.root / "nowhere")
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


if __name__ == "__main__":
    unittest.main()
