import importlib.util
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest import mock


SKILL_ROOT = Path(__file__).resolve().parents[2]
INSTALL_PATH = SKILL_ROOT / "scripts" / "install.py"


def load_install_module():
    spec = importlib.util.spec_from_file_location("cloudflare_install", INSTALL_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load installer: {INSTALL_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class InstallerSafetyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_install_module()

    def test_production_workflow_requires_default_branch_and_checks_out_event_sha(self) -> None:
        rendered = self.module.render_production_workflow(
            Namespace(github_production_environment="production-gate")
        )

        workflow = self.parse_workflow(rendered)
        if workflow is None:
            return
        self.assertEqual(set(workflow["on"]), {"workflow_dispatch"})
        self.assertEqual(set(workflow["jobs"]), {"deploy"})
        deploy = workflow["jobs"]["deploy"]
        self.assertIn("github.event_name == 'workflow_dispatch'", deploy["if"])
        self.assertIn(
            "github.ref == format('refs/heads/{0}', github.event.repository.default_branch)",
            deploy["if"],
        )
        self.assertIn("ref: ${{ github.sha }}", rendered)
        self.assertEqual(deploy["environment"], "production-gate")
        production_runs = [
            step.get("run", "")
            for step in deploy["steps"]
            if "production-deploy" in step.get("run", "")
        ]
        self.assertEqual(production_runs, ["node scripts/cloudflare-branch-worker.mjs production-deploy"])

    @staticmethod
    def parse_workflow(rendered: str) -> dict:
        """Parse the generated YAML without interpreting GitHub's `on` as bool."""

        try:
            import yaml
        except ImportError:
            InstallerSafetyTests.check_workflow_without_yaml(rendered)
            return None

        class GitHubLoader(yaml.SafeLoader):
            pass

        GitHubLoader.yaml_implicit_resolvers = {
            key: list(value)
            for key, value in yaml.SafeLoader.yaml_implicit_resolvers.items()
        }
        # YAML 1.1's default resolver turns the key `on` into True. Remove only
        # that implicit boolean rule; all other YAML parsing remains safe_load.
        GitHubLoader.yaml_implicit_resolvers["o"] = [
            resolver
            for resolver in GitHubLoader.yaml_implicit_resolvers.get("o", [])
            if resolver[0] != "tag:yaml.org,2002:bool"
        ]
        document = yaml.load(rendered, Loader=GitHubLoader)
        if not isinstance(document, dict) or not isinstance(document.get("jobs"), dict):
            raise AssertionError("production workflow YAML must contain a jobs mapping")
        return document

    @staticmethod
    def check_workflow_without_yaml(rendered: str) -> None:
        """Check the exact top-level YAML shape without fabricating a document."""

        lines = rendered.splitlines()

        def direct_children(parent: str) -> list[str]:
            parent_key = parent.removesuffix(":")
            matches: list[tuple[int, str]] = []
            for index, line in enumerate(lines):
                if not line or line[0].isspace():
                    continue
                key, separator, value = line.partition(":")
                if separator and key == parent_key:
                    matches.append((index, value))
            if len(matches) != 1 or matches[0][1].strip():
                raise AssertionError(
                    f"{parent_key!r} must be one unique top-level block mapping"
                )

            start = matches[0][0]
            children: list[str] = []
            for line in lines[start + 1 :]:
                if not line.strip():
                    continue
                indent = len(line) - len(line.lstrip(" "))
                if indent == 0:
                    break
                if indent == 2:
                    child, separator, _value = line.strip().partition(":")
                    if not separator or not child:
                        raise AssertionError(
                            f"invalid direct child under {parent_key!r}: {line!r}"
                        )
                    children.append(child)
            return children

        if direct_children("on:") != ["workflow_dispatch"]:
            raise AssertionError("production workflow triggers must be exactly workflow_dispatch")
        if direct_children("jobs:") != ["deploy"]:
            raise AssertionError("production workflow jobs must be exactly deploy")
        required_fragments = (
            "github.event_name == 'workflow_dispatch'",
            "github.ref == format('refs/heads/{0}', github.event.repository.default_branch)",
            "github.event.inputs.confirmation == 'deploy-production'",
            "ref: ${{ github.sha }}",
            'environment: "production-gate"',
            "run: node scripts/cloudflare-branch-worker.mjs production-deploy",
        )
        for fragment in required_fragments:
            if sum(fragment in line for line in lines) != 1:
                raise AssertionError(f"production workflow contract missing or duplicated: {fragment}")

    def test_skill_requires_environment_branch_policy(self) -> None:
        skill = (SKILL_ROOT / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn(
            "Restrict that GitHub Environment's deployment branch/tag policy to the repository's default branch.",
            skill,
        )

    def test_dependency_free_workflow_check_rejects_extra_trigger_and_job(self) -> None:
        rendered = self.module.render_production_workflow(
            Namespace(github_production_environment="production-gate")
        )
        with mock.patch.dict(sys.modules, {"yaml": None}):
            self.assertIsNone(self.parse_workflow(rendered))
        unsafe_variants = (
            rendered.replace(
                "  workflow_dispatch:\n",
                "  workflow_dispatch:\n  schedule: []\n",
            ),
            rendered.replace("  deploy:\n", "  deploy:\n  unsafe: {}\n"),
            rendered + "\non: [push]\n",
            rendered + "\njobs: {}\n",
        )
        for unsafe in unsafe_variants:
            with self.subTest(unsafe=unsafe[-80:]):
                with self.assertRaises(AssertionError):
                    self.check_workflow_without_yaml(unsafe)

    def test_is_link_treats_windows_junctions_as_links(self) -> None:
        path = Path("junction")
        with mock.patch.object(Path, "is_symlink", return_value=False):
            with mock.patch.object(Path, "is_junction", return_value=True):
                self.assertTrue(self.module.is_link(path))

    def test_apply_fails_closed_without_posix_dirfd_support(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            repo.mkdir()
            destination = repo / "file.txt"
            with mock.patch.object(self.module.os, "name", "nt"):
                with self.assertRaises(self.module.UnsupportedSecureWriteError):
                    self.module.apply_files({destination: b"replacement\n"}, repo, True)
            self.assertFalse(destination.exists())

    def test_secure_write_requires_follow_symlinks_and_dirfd_capabilities(self) -> None:
        with mock.patch.object(self.module.os, "supports_follow_symlinks", set()):
            self.assertFalse(self.module.secure_write_supported())
        with mock.patch.object(
            self.module.os,
            "supports_follow_symlinks",
            {self.module.os.stat},
        ):
            self.assertFalse(self.module.secure_write_supported())
        with mock.patch.object(self.module.os, "supports_dir_fd", set()):
            self.assertFalse(self.module.secure_write_supported())

    def test_rejects_symlinked_final_destination_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            outside = root / "outside.txt"
            repo.mkdir()
            outside.write_text("preserve\n", encoding="utf-8")
            destination = repo / "scripts" / "cloudflare-branch-worker.mjs"
            destination.parent.mkdir()
            destination.symlink_to(outside)

            with self.assertRaisesRegex(ValueError, "symlinked destination target"):
                self.module.validate_destinations({destination: b"replacement\n"}, repo)

            self.assertEqual(outside.read_text(encoding="utf-8"), "preserve\n")

    def run_cli(self, repo: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                str(INSTALL_PATH),
                "--repo",
                str(repo),
                "--worker-prefix",
                "example-preview",
                "--workers-dev-subdomain",
                "example-account",
                "--protected-worker",
                "example-production",
                "--apply",
                "--overwrite",
                *extra,
            ],
            check=False,
            capture_output=True,
            text=True,
        )

    def test_cli_apply_rejects_final_link_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            outside = root / "outside.txt"
            repo.mkdir()
            (repo / ".git").mkdir()
            outside.write_text("preserve\n", encoding="utf-8")
            destination = repo / "scripts" / "cloudflare-branch-worker.mjs"
            destination.parent.mkdir()
            destination.symlink_to(outside)

            result = self.run_cli(repo)

            self.assertEqual(result.returncode, 4, result.stderr)
            self.assertIn("symlinked destination target", result.stderr)
            self.assertEqual(outside.read_text(encoding="utf-8"), "preserve\n")
            self.assertFalse((repo / ".cloudflare").exists())

    def test_cli_apply_rejects_ancestor_link_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            outside = root / "outside"
            repo.mkdir()
            (repo / ".git").mkdir()
            outside.mkdir()
            sentinel = outside / "sentinel.txt"
            sentinel.write_text("preserve\n", encoding="utf-8")
            (repo / ".github").symlink_to(outside, target_is_directory=True)

            result = self.run_cli(repo)

            self.assertEqual(result.returncode, 4, result.stderr)
            self.assertIn("symlinked destination ancestor", result.stderr)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve\n")
            self.assertFalse((outside / "workflows").exists())

    def test_ancestor_swap_after_validation_is_rejected_without_outside_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            outside = root / "outside"
            repo.mkdir()
            (repo / ".git").mkdir()
            (repo / ".github" / "workflows").mkdir(parents=True)
            outside.mkdir()
            sentinel = outside / "sentinel.txt"
            sentinel.write_text("preserve\n", encoding="utf-8")
            destination = repo / ".github" / "workflows" / "cloudflare-production.yml"

            def swap_ancestor() -> None:
                (repo / ".github").rename(repo / ".github-original")
                (repo / ".github").symlink_to(outside, target_is_directory=True)

            with mock.patch.object(self.module, "before_apply_write", side_effect=swap_ancestor):
                with self.assertRaisesRegex(
                    self.module.SecureInstallerError,
                    "symlinked destination ancestor",
                ):
                    self.module.apply_files({destination: b"replacement\n"}, repo, True)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve\n")
            self.assertFalse((outside / "workflows").exists())

    def test_create_only_race_preserves_new_file_and_reports_exact_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            destination = repo / "scripts" / "cloudflare-branch-worker.mjs"
            destination.parent.mkdir(parents=True)

            def create_race_file() -> None:
                destination.write_text("race content\n", encoding="utf-8")

            with mock.patch.object(
                self.module,
                "before_apply_write",
                side_effect=create_race_file,
            ):
                with self.assertRaises(self.module.ExistingFilesError) as raised:
                    self.module.apply_files(
                        {destination: b"replacement\n"}, repo, overwrite=False
                    )

            self.assertEqual(raised.exception.paths, [destination])
            self.assertEqual(
                destination.read_text(encoding="utf-8"),
                "race content\n",
            )

    def test_main_reports_create_only_race_as_return_three_with_exact_target(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            repo.mkdir()
            repo = repo.resolve()
            (repo / ".git").mkdir()
            destination = repo / "scripts" / "cloudflare-branch-worker.mjs"
            destination.parent.mkdir()
            args = Namespace(repo=str(repo), apply=True, overwrite=False)

            def create_race_file() -> None:
                destination.write_text("race content\n", encoding="utf-8")

            with mock.patch.object(self.module, "parse_args", return_value=args):
                with mock.patch.object(
                    self.module,
                    "planned_files",
                    return_value={destination: b"replacement\n"},
                ):
                    with mock.patch.object(
                        self.module,
                        "before_apply_write",
                        side_effect=create_race_file,
                    ):
                        with mock.patch("sys.stderr") as stderr:
                            result = self.module.main()

            self.assertEqual(result, 3)
            error_output = "".join(call.args[0] for call in stderr.write.call_args_list)
            self.assertIn("scripts/cloudflare-branch-worker.mjs", error_output)
            self.assertEqual(
                destination.read_text(encoding="utf-8"),
                "race content\n",
            )

    def test_create_only_publication_writes_absent_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            destination = repo / "scripts" / "cloudflare-branch-worker.mjs"
            repo.mkdir()

            self.module.apply_files(
                {destination: b"created\n"}, repo, overwrite=False
            )

            self.assertEqual(destination.read_text(encoding="utf-8"), "created\n")
            self.assertTrue(destination.stat().st_mode & 0o111)

    def test_rejects_symlinked_ancestor_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            outside = root / "outside"
            repo.mkdir()
            outside.mkdir()
            sentinel = outside / "sentinel.txt"
            sentinel.write_text("preserve\n", encoding="utf-8")
            (repo / ".github").symlink_to(outside, target_is_directory=True)
            destination = repo / ".github" / "workflows" / "cloudflare-production.yml"

            with self.assertRaisesRegex(ValueError, "symlinked destination ancestor"):
                self.module.validate_destinations({destination: b"replacement\n"}, repo)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve\n")

    def test_rejects_resolved_destination_outside_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repo = root / "repo"
            repo.mkdir()
            destination = root / "outside.txt"

            with self.assertRaisesRegex(ValueError, "outside the repository"):
                self.module.validate_destinations({destination: b"replacement\n"}, repo)

    def test_atomic_write_replaces_regular_file_and_preserves_executable_bit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            repo = Path(temporary) / "repo"
            destination = repo / "scripts" / "cloudflare-branch-worker.mjs"
            destination.parent.mkdir(parents=True)
            destination.write_text("old\n", encoding="utf-8")
            destination.chmod(0o755)

            with self.module.SecureRepository(repo) as secure_repository:
                secure_repository.write(destination, b"new\n")

            self.assertEqual(destination.read_text(encoding="utf-8"), "new\n")
            self.assertEqual(destination.stat().st_mode & 0o111, 0o111)
            self.assertEqual(list(destination.parent.glob(f".{destination.name}.*")), [])


if __name__ == "__main__":
    unittest.main()
