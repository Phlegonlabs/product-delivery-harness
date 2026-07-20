#!/usr/bin/env python3
"""Tests for Claude runtime session capability caching."""

from __future__ import annotations

import copy
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import claude_runtime_bridge as bridge  # noqa: E402


PREFLIGHT_RESULT = {
    "provider": "claude_code",
    "driver": "dynamic_workflow",
    "protocol_version": 1,
    "status": "available",
    "probe_count": 2,
    "probe_labels": ["probe-a", "probe-b"],
}


class ClaudeRuntimeCacheTests(unittest.TestCase):
    def setUp(self) -> None:
        bridge._VERSION_CACHE.clear()
        bridge._PREFLIGHT_CACHE.clear()
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.command = self.root / "claude.exe"
        self.command.write_bytes(b"fake-claude-v1")
        self.cache = self.root / "session-cache"
        self.cwd = self.root / "cwd"
        self.cwd.mkdir()

    def tearDown(self) -> None:
        bridge._VERSION_CACHE.clear()
        bridge._PREFLIGHT_CACHE.clear()
        self.temp.cleanup()

    def version_result(self, version: str = "2.1.214 (Claude Code)") -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            [str(self.command), "--version"],
            0,
            stdout=version + "\n",
            stderr="",
        )

    def test_successful_preflight_and_version_reuse_survive_memory_reset(self) -> None:
        with (
            mock.patch.object(bridge, "_resolve_claude", return_value=str(self.command)),
            mock.patch.object(bridge.subprocess, "run", return_value=self.version_result()) as version,
            mock.patch.object(bridge, "_invoke", return_value=PREFLIGHT_RESULT) as invoke,
        ):
            first = bridge.preflight(
                claude="claude",
                script=bridge.DEFAULT_PREFLIGHT,
                cwd=self.cwd,
                timeout=30,
                max_budget_usd=0.1,
                session_cache_root=self.cache,
            )
            bridge._VERSION_CACHE.clear()
            bridge._PREFLIGHT_CACHE.clear()
            second = bridge.preflight(
                claude="claude",
                script=bridge.DEFAULT_PREFLIGHT,
                cwd=self.cwd,
                timeout=30,
                max_budget_usd=0.1,
                session_cache_root=self.cache,
            )

        self.assertEqual(first["metrics"]["preflight_executed"], 1)
        self.assertEqual(second["metrics"]["preflight_reused"], 1)
        self.assertEqual(version.call_count, 1)
        self.assertEqual(invoke.call_count, 1)

    def test_model_script_and_executable_identity_invalidate_preflight(self) -> None:
        alternate_script = self.root / "preflight.js"
        alternate_script.write_text(
            bridge.DEFAULT_PREFLIGHT.read_text(encoding="utf-8") + "\n",
            encoding="utf-8",
        )
        with (
            mock.patch.object(bridge, "_resolve_claude", return_value=str(self.command)),
            mock.patch.object(bridge.subprocess, "run", return_value=self.version_result()) as version,
            mock.patch.object(bridge, "_invoke", return_value=PREFLIGHT_RESULT) as invoke,
        ):
            bridge.preflight(
                claude="claude",
                script=bridge.DEFAULT_PREFLIGHT,
                cwd=self.cwd,
                timeout=30,
                max_budget_usd=0.1,
                session_cache_root=self.cache,
            )
            bridge.preflight(
                claude="claude",
                script=bridge.DEFAULT_PREFLIGHT,
                cwd=self.cwd,
                timeout=30,
                max_budget_usd=0.1,
                model="sonnet",
                session_cache_root=self.cache,
            )
            bridge.preflight(
                claude="claude",
                script=alternate_script,
                cwd=self.cwd,
                timeout=30,
                max_budget_usd=0.1,
                session_cache_root=self.cache,
            )
            self.command.write_bytes(b"fake-claude-v2-with-new-identity")
            bridge.preflight(
                claude="claude",
                script=bridge.DEFAULT_PREFLIGHT,
                cwd=self.cwd,
                timeout=30,
                max_budget_usd=0.1,
                session_cache_root=self.cache,
            )

        self.assertEqual(invoke.call_count, 4)
        self.assertEqual(version.call_count, 2)

    def test_failed_preflight_is_never_cached(self) -> None:
        unexpected = copy.deepcopy(PREFLIGHT_RESULT)
        unexpected["status"] = "unavailable"
        with (
            mock.patch.object(bridge, "_resolve_claude", return_value=str(self.command)),
            mock.patch.object(bridge.subprocess, "run", return_value=self.version_result()) as version,
            mock.patch.object(bridge, "_invoke", return_value=unexpected) as invoke,
        ):
            for _ in range(2):
                with self.assertRaisesRegex(bridge.BridgeError, "Unexpected"):
                    bridge.preflight(
                        claude="claude",
                        script=bridge.DEFAULT_PREFLIGHT,
                        cwd=self.cwd,
                        timeout=30,
                        max_budget_usd=0.1,
                        session_cache_root=self.cache,
                    )

        self.assertEqual(version.call_count, 1)
        self.assertEqual(invoke.call_count, 2)

    def test_force_refresh_bypasses_successful_session_entry(self) -> None:
        with (
            mock.patch.object(bridge, "_resolve_claude", return_value=str(self.command)),
            mock.patch.object(bridge.subprocess, "run", return_value=self.version_result()) as version,
            mock.patch.object(bridge, "_invoke", return_value=PREFLIGHT_RESULT) as invoke,
        ):
            bridge.preflight(
                claude="claude",
                script=bridge.DEFAULT_PREFLIGHT,
                cwd=self.cwd,
                timeout=30,
                max_budget_usd=0.1,
                session_cache_root=self.cache,
            )
            refreshed = bridge.preflight(
                claude="claude",
                script=bridge.DEFAULT_PREFLIGHT,
                cwd=self.cwd,
                timeout=30,
                max_budget_usd=0.1,
                session_cache_root=self.cache,
                force_refresh=True,
            )

        self.assertEqual(refreshed["metrics"]["preflight_executed"], 1)
        self.assertEqual(version.call_count, 2)
        self.assertEqual(invoke.call_count, 2)

    def test_failed_force_refresh_revokes_stale_disk_preflight(self) -> None:
        unexpected = copy.deepcopy(PREFLIGHT_RESULT)
        unexpected["status"] = "unavailable"
        with (
            mock.patch.object(bridge, "_resolve_claude", return_value=str(self.command)),
            mock.patch.object(bridge.subprocess, "run", return_value=self.version_result()) as version,
            mock.patch.object(
                bridge,
                "_invoke",
                side_effect=[PREFLIGHT_RESULT, unexpected, PREFLIGHT_RESULT],
            ) as invoke,
        ):
            bridge.preflight(
                claude="claude",
                script=bridge.DEFAULT_PREFLIGHT,
                cwd=self.cwd,
                timeout=30,
                max_budget_usd=0.1,
                session_cache_root=self.cache,
            )
            bridge._VERSION_CACHE.clear()
            bridge._PREFLIGHT_CACHE.clear()
            with self.assertRaisesRegex(bridge.BridgeError, "Unexpected"):
                bridge.preflight(
                    claude="claude",
                    script=bridge.DEFAULT_PREFLIGHT,
                    cwd=self.cwd,
                    timeout=30,
                    max_budget_usd=0.1,
                    session_cache_root=self.cache,
                    force_refresh=True,
                )
            bridge._VERSION_CACHE.clear()
            bridge._PREFLIGHT_CACHE.clear()
            fresh = bridge.preflight(
                claude="claude",
                script=bridge.DEFAULT_PREFLIGHT,
                cwd=self.cwd,
                timeout=30,
                max_budget_usd=0.1,
                session_cache_root=self.cache,
            )
            bridge._VERSION_CACHE.clear()
            bridge._PREFLIGHT_CACHE.clear()
            reused = bridge.preflight(
                claude="claude",
                script=bridge.DEFAULT_PREFLIGHT,
                cwd=self.cwd,
                timeout=30,
                max_budget_usd=0.1,
                session_cache_root=self.cache,
            )

        self.assertEqual(fresh["metrics"]["preflight_executed"], 1)
        self.assertEqual(reused["metrics"]["preflight_reused"], 1)
        self.assertEqual(version.call_count, 2)
        self.assertEqual(invoke.call_count, 3)

    def test_repository_internal_session_cache_is_rejected(self) -> None:
        checkout = self.root / "repo"
        checkout.mkdir()
        (checkout / ".git").mkdir()
        outside = self.root / "outside"
        outside.mkdir()

        for cwd in (checkout, outside):
            with self.subTest(cwd=cwd):
                with self.assertRaisesRegex(
                    bridge.BridgeError,
                    "outside the repository checkout",
                ):
                    bridge.preflight(
                        claude="claude",
                        script=bridge.DEFAULT_PREFLIGHT,
                        cwd=cwd,
                        timeout=30,
                        max_budget_usd=0.1,
                        session_cache_root=checkout / ".cache",
                    )

    def test_later_failed_refresh_keeps_an_earlier_success_revoked(self) -> None:
        scope_key = "a" * 64
        cache_key = "b" * 64
        bridge._revoke_preflight_disk_cache(self.cache, scope_key)
        observed = bridge._preflight_revocation_identity(self.cache, scope_key)
        self.assertIsNotNone(observed)

        bridge._revoke_preflight_disk_cache(self.cache, scope_key)
        newer = bridge._preflight_revocation_identity(self.cache, scope_key)
        self.assertNotEqual(observed, newer)
        bridge._restore_preflight_disk_cache(
            self.cache,
            scope_key,
            cache_key,
            observed,
        )

        self.assertTrue(
            bridge._preflight_disk_revoked(self.cache, scope_key, cache_key)
        )
        bridge._restore_preflight_disk_cache(
            self.cache,
            scope_key,
            cache_key,
            newer,
        )
        self.assertFalse(
            bridge._preflight_disk_revoked(self.cache, scope_key, cache_key)
        )

    def test_cli_passes_force_refresh_to_preflight(self) -> None:
        result = {"status": "PASS"}
        with (
            mock.patch.object(bridge, "preflight", return_value=result) as preflight,
            mock.patch("sys.stdout", new=io.StringIO()),
        ):
            exit_code = bridge.main(["preflight", "--force-refresh"])

        self.assertEqual(exit_code, 0)
        self.assertTrue(preflight.call_args.kwargs["force_refresh"])


if __name__ == "__main__":
    unittest.main()
