from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_wrangler_binding_isolation as subject  # noqa: E402


def isolated_config() -> dict[str, object]:
    return {
        "name": "my-worker",
        "compatibility_date": "2026-01-01",
        "env": {
            "development": {
                "name": "my-worker-development",
                "d1_databases": [{"binding": "DB", "database_id": "dev-db-id"}],
                "kv_namespaces": [{"binding": "KV", "id": "dev-kv-id"}],
                "r2_buckets": [{"binding": "BUCKET", "bucket_name": "dev-bucket"}],
                "vars": {"APP_NAME": "my-worker"},
            },
            "production": {
                "name": "my-worker-production",
                "d1_databases": [{"binding": "DB", "database_id": "prod-db-id"}],
                "kv_namespaces": [{"binding": "KV", "id": "prod-kv-id"}],
                "r2_buckets": [{"binding": "BUCKET", "bucket_name": "prod-bucket"}],
                "vars": {"APP_NAME": "my-worker"},
            },
        },
    }


def write_config(directory: Path, config: dict[str, object], *, raw: str | None = None) -> Path:
    path = directory / "wrangler.jsonc"
    path.write_text(raw if raw is not None else json.dumps(config), encoding="utf-8")
    return path


class CheckWranglerBindingIsolationTests(unittest.TestCase):
    def test_well_isolated_config_reports_no_errors(self) -> None:
        errors = subject.check_binding_isolation(isolated_config())
        self.assertEqual(errors, [])

    def test_shared_d1_database_id_is_flagged(self) -> None:
        config = isolated_config()
        config["env"]["production"]["d1_databases"][0]["database_id"] = "dev-db-id"
        errors = subject.check_binding_isolation(config)
        self.assertEqual(
            errors,
            [
                "d1_databases binding 'DB' shares database_id 'dev-db-id' between development and "
                "production — these must be isolated per-environment"
            ],
        )

    def test_shared_kv_namespace_id_is_flagged(self) -> None:
        config = isolated_config()
        config["env"]["production"]["kv_namespaces"][0]["id"] = "dev-kv-id"
        errors = subject.check_binding_isolation(config)
        self.assertIn(
            "kv_namespaces binding 'KV' shares id 'dev-kv-id' between development and production "
            "— these must be isolated per-environment",
            errors,
        )

    def test_shared_r2_bucket_name_is_flagged(self) -> None:
        config = isolated_config()
        config["env"]["production"]["r2_buckets"][0]["bucket_name"] = "dev-bucket"
        errors = subject.check_binding_isolation(config)
        self.assertIn(
            "r2_buckets binding 'BUCKET' shares bucket_name 'dev-bucket' between development and "
            "production — these must be isolated per-environment",
            errors,
        )

    def test_shared_queue_name_between_producers_is_flagged(self) -> None:
        config = isolated_config()
        config["env"]["development"]["queues"] = {
            "producers": [{"binding": "QUEUE", "queue": "shared-queue"}]
        }
        config["env"]["production"]["queues"] = {
            "producers": [{"binding": "QUEUE", "queue": "shared-queue"}]
        }
        errors = subject.check_binding_isolation(config)
        self.assertIn(
            "queues.producers binding 'QUEUE' shares queue 'shared-queue' between development and "
            "production — these must be isolated per-environment",
            errors,
        )

    def test_shared_queue_name_between_consumers_is_flagged(self) -> None:
        config = isolated_config()
        config["env"]["development"]["queues"] = {
            "consumers": [{"queue": "shared-queue"}]
        }
        config["env"]["production"]["queues"] = {
            "consumers": [{"queue": "shared-queue"}]
        }
        errors = subject.check_binding_isolation(config)
        self.assertIn(
            "queues.consumers references queue 'shared-queue' in both development and production "
            "— consumers must be isolated per-environment",
            errors,
        )

    def test_shared_durable_object_script_and_class_is_flagged(self) -> None:
        config = isolated_config()
        config["env"]["development"]["durable_objects"] = {
            "bindings": [{"name": "DO", "class_name": "MyClass", "script_name": "external-worker"}]
        }
        config["env"]["production"]["durable_objects"] = {
            "bindings": [{"name": "DO", "class_name": "MyClass", "script_name": "external-worker"}]
        }
        errors = subject.check_binding_isolation(config)
        self.assertIn(
            "durable_objects binding 'DO' shares class_name 'MyClass' and script_name "
            "'external-worker' between development and production — these must be isolated "
            "per-environment",
            errors,
        )

    def test_durable_object_without_script_name_is_not_flagged(self) -> None:
        config = isolated_config()
        config["env"]["development"]["durable_objects"] = {
            "bindings": [{"name": "DO", "class_name": "MyClass"}]
        }
        config["env"]["production"]["durable_objects"] = {
            "bindings": [{"name": "DO", "class_name": "MyClass"}]
        }
        errors = subject.check_binding_isolation(config)
        self.assertEqual(errors, [])

    def test_shared_vars_value_is_not_flagged(self) -> None:
        errors = subject.check_binding_isolation(isolated_config())
        self.assertFalse(any("APP_NAME" in error or "vars" in error for error in errors))

    def test_binding_declared_only_at_top_level_is_flagged(self) -> None:
        config = isolated_config()
        config["d1_databases"] = [{"binding": "SHARED_DB", "database_id": "top-level-db-id"}]
        errors = subject.check_binding_isolation(config)
        self.assertIn(
            "d1_databases binding 'SHARED_DB' is declared only at the top level with database_id "
            "'top-level-db-id' and has no development or production override — Wrangler bindings "
            "are non-inheritable, so it will not be isolated between environments",
            errors,
        )

    def test_binding_overridden_in_one_environment_is_not_flagged_as_orphan(self) -> None:
        config = isolated_config()
        config["d1_databases"] = [{"binding": "SHARED_DB", "database_id": "top-level-db-id"}]
        config["env"]["production"]["d1_databases"].append(
            {"binding": "SHARED_DB", "database_id": "prod-only-db-id"}
        )
        errors = subject.check_binding_isolation(config)
        self.assertFalse(any("SHARED_DB" in error for error in errors))


class CheckWranglerBindingIsolationCliTests(unittest.TestCase):
    def run_cli(self, config_path: Path) -> subprocess.CompletedProcess[str]:
        command = [
            sys.executable,
            str(SCRIPTS_DIR / "check_wrangler_binding_isolation.py"),
            "--wrangler-config",
            str(config_path),
        ]
        return subprocess.run(command, check=False, capture_output=True, text=True)

    def test_isolated_config_exits_zero_with_no_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path = write_config(Path(directory), isolated_config())
            result = self.run_cli(config_path)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.strip(), "")

    def test_collision_exits_one_with_sorted_error_lines(self) -> None:
        config = isolated_config()
        config["env"]["production"]["d1_databases"][0]["database_id"] = "dev-db-id"
        config["env"]["production"]["kv_namespaces"][0]["id"] = "dev-kv-id"
        with tempfile.TemporaryDirectory() as directory:
            config_path = write_config(Path(directory), config)
            result = self.run_cli(config_path)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        lines = result.stdout.strip("\n").split("\n")
        self.assertEqual(lines, sorted(lines))
        self.assertEqual(len(lines), 2)

    def test_jsonc_comments_and_trailing_commas_are_parsed(self) -> None:
        raw = """
        {
          // top-level worker name
          "name": "my-worker",
          "compatibility_date": "2026-01-01",
          /* environment sections */
          "env": {
            "development": {
              "d1_databases": [
                { "binding": "DB", "database_id": "dev-db-id", },
              ],
            },
            "production": {
              "d1_databases": [
                { "binding": "DB", "database_id": "prod-db-id" },
              ],
            },
          },
        }
        """
        with tempfile.TemporaryDirectory() as directory:
            config_path = write_config(Path(directory), {}, raw=raw)
            result = self.run_cli(config_path)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_string_containing_comment_like_sequences_is_preserved(self) -> None:
        raw = json.dumps(
            {
                "name": "my-worker",
                "env": {
                    "development": {
                        "vars": {"NOTE": "https://example.com // not a comment"},
                        "d1_databases": [{"binding": "DB", "database_id": "dev-db-id"}],
                    },
                    "production": {
                        "vars": {"NOTE": "/* still not a comment */"},
                        "d1_databases": [{"binding": "DB", "database_id": "prod-db-id"}],
                    },
                },
            }
        )
        with tempfile.TemporaryDirectory() as directory:
            config_path = write_config(Path(directory), {}, raw=raw)
            result = self.run_cli(config_path)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_malformed_jsonc_exits_two_with_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path = write_config(Path(directory), {}, raw="{ this is not valid json")
            result = self.run_cli(config_path)
        self.assertEqual(result.returncode, 2)
        self.assertNotEqual(result.stdout.strip(), "")

    def test_missing_file_exits_two(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing_path = Path(directory) / "does-not-exist.jsonc"
            result = self.run_cli(missing_path)
        self.assertEqual(result.returncode, 2)
        self.assertNotEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
