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
from unittest.mock import patch

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
        mode = os.environ.get("STUB_GEOMETRY_MODE", "pass")
        if mode == "exit":
            print("geometry unavailable", file=sys.stderr)
            raise SystemExit(3)
        if mode == "malformed":
            print("not json")
        else:
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
        self._old_env = {
            "PATH": os.environ.get("PATH"),
            "STUB_LOG": os.environ.get("STUB_LOG"),
            "STUB_PROBE_RESULT": os.environ.get("STUB_PROBE_RESULT"),
            "STUB_GEOMETRY_MODE": os.environ.get("STUB_GEOMETRY_MODE"),
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
            target = self.out / f"home-ready-{width}-target.png"
            actual = self.out / f"home-ready-{width}-actual.png"
            self.assertTrue(target.exists(), target)
            self.assertTrue(actual.exists(), actual)
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
        self.assertTrue((self.out / "settings-ready-390-target.png").exists())
        self.assertFalse((self.out / "home-ready-390-target.png").exists())
        manifest = json.loads((self.out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual("PARTIAL", manifest["status"])
        self.assertFalse(manifest["gating_eligible"])
        self.assertEqual(2, manifest["required_combinations"])
        self.assertEqual(1, manifest["selected_combinations"])
        self.assertEqual(["/settings"], manifest["only_routes"])

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
