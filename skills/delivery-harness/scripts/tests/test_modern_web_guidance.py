#!/usr/bin/env python3
"""modern_web_guidance.py runs the pinned CLI with telemetry off and the PRD's Baseline target."""

from __future__ import annotations

import io
import json
import os
import stat
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import modern_web_guidance  # noqa: E402


class FakeRun:
    """Stands in for subprocess.run and records what the CLI process would receive."""

    def __init__(self, returncode: int) -> None:
        self.returncode = returncode
        self.calls: list[dict[str, object]] = []

    def __call__(self, command, *, cwd, env, check):
        directory = Path(cwd)
        self.calls.append({
            "command": command,
            "cwd": directory,
            "files": sorted(path.name for path in directory.iterdir()),
            "mwgrc": json.loads((directory / ".mwgrc").read_text(encoding="utf-8")),
            "telemetry": env.get("DISABLE_TELEMETRY"),
            "file logging": env.get("ENABLE_FILE_LOGGING"),
        })
        return mock.Mock(returncode=self.returncode)


def run_cli(*argv: str, returncode: int = 0, npx: str | None = "/fake/npx"):
    fake = FakeRun(returncode)
    stdout, stderr = io.StringIO(), io.StringIO()
    with mock.patch.object(modern_web_guidance, "find_npx", return_value=npx), \
            mock.patch.object(modern_web_guidance.subprocess, "run", fake), \
            mock.patch.dict(os.environ, {"DISABLE_TELEMETRY": "0", "ENABLE_FILE_LOGGING": "true"}), \
            redirect_stdout(stdout), redirect_stderr(stderr):
        try:
            code = modern_web_guidance.main(list(argv))
        except SystemExit as exit_:
            code = exit_.code
    return code, fake.calls, stdout.getvalue(), stderr.getvalue()


class ModernWebGuidanceTests(unittest.TestCase):
    def test_retrieve_runs_the_exact_version_with_telemetry_off_in_an_empty_directory(self) -> None:
        code, calls, _, _ = run_cli("--baseline", "Baseline 2024", "retrieve", "dialog,menu", returncode=3)
        self.assertEqual(3, code)
        [call] = calls
        npx, flag, package, *rest = call["command"]
        self.assertEqual(("/fake/npx", "-y", ["retrieve", "dialog,menu"]), (npx, flag, rest))
        self.assertRegex(package, r"^modern-web-guidance@\d+\.\d+\.\d+$")
        self.assertEqual(("1", "false"), (call["telemetry"], call["file logging"]))
        self.assertEqual([".mwgrc"], call["files"])
        self.assertEqual({"baseline": "2024"}, call["mwgrc"])
        self.assertNotEqual(Path.cwd().resolve(), call["cwd"].resolve())
        self.assertFalse(call["cwd"].exists())

    def test_each_browser_support_form_becomes_the_cli_target(self) -> None:
        for value, target in (("Baseline Widely available", "widely"), ("baseline newly available", "newly"),
                              (" Baseline 2023 ", "2023")):
            with self.subTest(value=value):
                code, [call], _, _ = run_cli("--baseline", value, "retrieve", "dialog")
                self.assertEqual((0, {"baseline": target}), (code, call["mwgrc"]))

    def test_search_and_list_need_no_target(self) -> None:
        for argv in (("search", "light dismiss dialog"), ("list",)):
            with self.subTest(argv=argv):
                code, [call], _, _ = run_cli(*argv)
                self.assertEqual((0, {}, list(argv)), (code, call["mwgrc"], call["command"][3:]))

    def test_other_commands_unknown_targets_and_a_missing_target_never_run(self) -> None:
        for argv in (("install",), ("update",), ("legacy-scan", "."), ("set-baseline", "limited"),
                     ("set-allow-origin-trials",), ("retrieve", "dialog"),
                     ("--baseline", "last 2 versions", "retrieve", "dialog"),
                     ("--baseline", "Baseline Limited availability", "search", "menu"), ()):
            with self.subTest(argv=argv):
                code, calls, _, _ = run_cli(*argv)
                self.assertEqual((2, []), (code, calls))

    def test_cmd_metacharacters_and_options_never_reach_npx(self) -> None:
        for argument in ("dialog & calc", "a|b", "100%", 'say "hi"', "x^y", "<tag>", "--json", "-v", "(menu)", ""):
            with self.subTest(argument=argument):
                code, calls, _, _ = run_cli("search", argument)
                self.assertEqual((2, []), (code, calls))
        code, [call], _, _ = run_cli("search", "user's sign-in form, step 2/3: retry+help")
        self.assertEqual((0, ["search", "user's sign-in form, step 2/3: retry+help"]), (code, call["command"][3:]))

    def test_npx_is_found_on_path_but_never_in_the_current_directory(self) -> None:
        name = "npx.cmd" if sys.platform == "win32" else "npx"
        with tempfile.TemporaryDirectory() as temp:
            planted, installed = Path(temp, "project"), Path(temp, "bin")
            for directory in (planted, installed):
                directory.mkdir()
                tool = directory / name
                tool.write_text("@echo off\n" if sys.platform == "win32" else "#!/bin/sh\n", encoding="utf-8")
                tool.chmod(tool.stat().st_mode | stat.S_IEXEC)
            previous = os.getcwd()
            os.chdir(planted)
            try:
                for path, expected in ((os.pathsep.join(["", ".", str(installed)]), installed / name),
                                       (os.pathsep.join(["", "."]), None)):
                    with self.subTest(path=path), mock.patch.dict(os.environ, {"PATH": path}):
                        found = modern_web_guidance.find_npx()
                        self.assertEqual(expected, found and Path(found))
            finally:
                os.chdir(previous)

    def test_missing_npx_is_reported(self) -> None:
        code, calls, _, stderr = run_cli("search", "menu", npx=None)
        self.assertEqual((2, []), (code, calls))
        self.assertIn("npx not found", stderr)

    def test_pin_prints_the_binding_row(self) -> None:
        code, calls, stdout, _ = run_cli("--pin")
        self.assertEqual((0, []), (code, calls))
        cells = [cell.strip() for cell in stdout.strip().strip("|").split("|")]
        self.assertEqual("web_platform_guidance", cells[0])
        self.assertRegex(cells[2], r"^`modern-web-guidance@\d+\.\d+\.\d+`$")
        self.assertRegex(cells[3], r"^`[0-9a-f]{64}`$")


if __name__ == "__main__":
    unittest.main()
