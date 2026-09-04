from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import harness_ui_evidence as subject  # noqa: E402


def write_artifact(root: Path, filename: str, contents: bytes) -> Path:
    artifact = root / "docs" / "goal" / "evidence" / filename
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(contents)
    return artifact


def evidence_run(root: Path, artifact: Path, schema_version: int) -> dict[str, object]:
    contents = artifact.read_bytes()
    return {
        "schema_version": schema_version,
        "ui_evidence": [
            {
                "artifact_path": artifact.relative_to(root).as_posix(),
                "artifact_sha256": hashlib.sha256(contents).hexdigest(),
            }
        ],
    }


class UiEvidenceImageValidationTests(unittest.TestCase):
    def test_manifest_cli_modules_import_without_site_packages_or_pillow(self) -> None:
        probe = subprocess.run(
            [
                sys.executable,
                "-S",
                "-c",
                (
                    "import sys; "
                    f"sys.path.insert(0, {str(SCRIPTS_DIR)!r}); "
                    "import harness_manifest"
                ),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(0, probe.returncode, probe.stderr)

    def test_missing_pillow_reports_a_clear_ui_evidence_dependency_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = write_artifact(root, "missing-pillow.png", b"placeholder")
            with mock.patch.object(
                subject,
                "_image_module",
                side_effect=RuntimeError(
                    "UI image evidence decoding requires Pillow; install the engineering test dependencies"
                ),
            ):
                errors = subject.validate_ui_evidence_files(
                    evidence_run(root, artifact, 9), root
                )
        self.assertTrue(any("requires Pillow" in error for error in errors), errors)
        # A missing Pillow install is an environment gap, not evidence corruption:
        # it must not be folded into the generic "cannot be decoded" wrapper, or
        # an operator (and the gate reason) cannot tell the two causes apart.
        self.assertFalse(any("cannot be decoded" in error for error in errors), errors)
        self.assertEqual(
            errors,
            [
                "run.ui_evidence[0].artifact_path: UI image evidence decoding "
                "requires Pillow; install the engineering test dependencies"
            ],
        )

    def assert_real_formats_accepted(self, schema_version: int) -> None:
        for suffix, image_format in (
            (".png", "PNG"),
            (".jpg", "JPEG"),
            (".webp", "WEBP"),
        ):
            with self.subTest(schema_version=schema_version, image_format=image_format):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    artifact = root / "docs" / "goal" / "evidence" / f"screen{suffix}"
                    artifact.parent.mkdir(parents=True)
                    Image.new("RGB", (3, 2), "blue").save(artifact, format=image_format)
                    run = evidence_run(root, artifact, schema_version)
                    self.assertEqual(subject.validate_ui_evidence_files(run, root), [])

    def test_schema_v9_accepts_real_png_jpeg_and_webp_images(self) -> None:
        self.assert_real_formats_accepted(9)

    def test_rejects_png_signature_followed_by_garbage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = write_artifact(
                root,
                "signature-garbage.png",
                b"\x89PNG\r\n\x1a\nthis is not a decoded image",
            )
            errors = subject.validate_ui_evidence_files(
                evidence_run(root, artifact, 9), root
            )
        self.assertTrue(any("cannot be decoded" in error for error in errors), errors)

    def test_rejects_truncated_image_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "docs" / "goal" / "evidence" / "truncated.png"
            artifact.parent.mkdir(parents=True)
            Image.new("RGB", (10, 10), "green").save(artifact, format="PNG")
            artifact.write_bytes(artifact.read_bytes()[:20])
            errors = subject.validate_ui_evidence_files(
                evidence_run(root, artifact, 9), root
            )
        self.assertTrue(any("cannot be decoded" in error for error in errors), errors)

    def test_rejects_suffix_and_decoded_format_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "docs" / "goal" / "evidence" / "jpeg-as-png.png"
            artifact.parent.mkdir(parents=True)
            Image.new("RGB", (3, 2), "red").save(artifact, format="JPEG")
            errors = subject.validate_ui_evidence_files(
                evidence_run(root, artifact, 9), root
            )
        self.assertTrue(any("decoded format JPEG" in error for error in errors), errors)

    def test_rejects_zero_dimension_decoded_image(self) -> None:
        class ZeroDimensionImage:
            format = "PNG"
            size = (0, 2)

            def __enter__(self) -> ZeroDimensionImage:
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def verify(self) -> None:
                return None

            def load(self) -> None:
                return None

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = write_artifact(root, "zero-dimension.png", b"placeholder")
            run = evidence_run(root, artifact, 9)
            with mock.patch.object(
                subject.Image,
                "open",
                side_effect=[ZeroDimensionImage(), ZeroDimensionImage()],
            ):
                errors = subject.validate_ui_evidence_files(run, root)
        self.assertTrue(any("non-zero dimensions" in error for error in errors), errors)


class UiEvidenceGitBindingTests(unittest.TestCase):
    @staticmethod
    def git(root: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError(
                f"git {' '.join(args)} failed:\\n{result.stdout}\\n{result.stderr}"
            )
        return result.stdout.strip()

    def init_git(self, root: Path) -> None:
        self.git(root, "init")
        self.git(root, "config", "user.name", "Harness Test")
        self.git(root, "config", "user.email", "harness@example.invalid")

    def test_schema_v10_reads_artifact_from_accepted_commit_not_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_git(root)
            original = io.BytesIO()
            Image.new("RGB", (3, 2), "blue").save(original, format="PNG")
            artifact = write_artifact(root, "accepted.png", original.getvalue())
            self.git(root, "add", "docs")
            self.git(root, "commit", "-m", "accepted screenshot")
            accepted_sha = self.git(root, "rev-parse", "HEAD")
            run = evidence_run(root, artifact, 10)
            run["ui_evidence"][0]["head_sha"] = accepted_sha

            mutated = io.BytesIO()
            Image.new("RGB", (3, 2), "red").save(mutated, format="PNG")
            artifact.write_bytes(mutated.getvalue())

            self.assertEqual([], subject.validate_ui_evidence_files(run, root))

            run["ui_evidence"][0]["artifact_sha256"] = hashlib.sha256(
                mutated.getvalue()
            ).hexdigest()
            errors = subject.validate_ui_evidence_files(run, root)
            self.assertTrue(any("sha256 does not match artifact_sha256" in error for error in errors), errors)

    def test_schema_v10_rejects_worktree_only_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.init_git(root)
            (root / "README.md").write_text("base\n", encoding="utf-8")
            self.git(root, "add", "README.md")
            self.git(root, "commit", "-m", "base")
            accepted_sha = self.git(root, "rev-parse", "HEAD")
            artifact = write_artifact(root, "uncommitted.png", b"not in commit")
            run = evidence_run(root, artifact, 10)
            run["ui_evidence"][0]["head_sha"] = accepted_sha

            errors = subject.validate_ui_evidence_files(run, root)

        self.assertTrue(any("accepted Git commit" in error for error in errors), errors)


class TargetComparisonSchemaTests(unittest.TestCase):
    @staticmethod
    def row(**target_comparison: object) -> dict[str, object]:
        return {
            "surface_id": "home",
            "route": "/home",
            "breakpoint": "mobile-390",
            "state": "ready",
            "artifact_path": "docs/goal/evidence/home-mobile-390-ready.png",
            "artifact_sha256": "a" * 64,
            "head_sha": "b" * 40,
            "status": "PASS",
            "target_comparison": target_comparison,
        }

    def validate(self, schema_version: int, item: dict[str, object]) -> list[str]:
        plan = {
            "ui_surfaces": [
                {
                    "id": "home",
                    "route": "/home",
                    "breakpoints": ["mobile-390"],
                    "states": ["ready"],
                    "evidence_gate": "required",
                }
            ]
        }
        run = {
            "schema_version": schema_version,
            "ui_evidence": [item],
            "integration": {"integration_head_sha": "b" * 40},
        }
        errors: list[str] = []
        subject._validate_ui_evidence(errors, plan, run)
        return errors

    def test_v11_row_without_target_comparison_is_rejected(self) -> None:
        item = self.row()
        item.pop("target_comparison")
        errors = self.validate(11, item)
        self.assertTrue(
            any("target_comparison" in error for error in errors), errors
        )

    def test_v9_row_without_target_comparison_still_passes_schema(self) -> None:
        item = self.row()
        item.pop("target_comparison")
        self.assertEqual(self.validate(9, item), [])

    def test_valid_html_target_pass_row_is_accepted(self) -> None:
        self.assertEqual(
            self.validate(
                11,
                self.row(
                    baseline="html_target",
                    baseline_artifact=(
                        "docs/goal/evidence/parity-home-ready-mobile-390-target.png"
                    ),
                    verdict="pass",
                ),
            ),
            [],
        )

    def test_valid_design_system_deviation_row_is_accepted(self) -> None:
        self.assertEqual(
            self.validate(
                11,
                self.row(
                    baseline="design_system",
                    baseline_artifact="check_ui_contract:clean-run",
                    verdict="deviation",
                    differences=["link underline token differs from registry"],
                ),
            ),
            [],
        )

    def test_unknown_baseline_is_rejected(self) -> None:
        errors = self.validate(
            11, self.row(baseline="wireframe", baseline_artifact="x", verdict="pass")
        )
        self.assertTrue(
            any("baseline" in error for error in errors), errors
        )

    def test_html_target_requires_an_evidence_image_path(self) -> None:
        errors = self.validate(
            11,
            self.row(
                baseline="html_target",
                baseline_artifact="docs/design/ui-references/run-1/home.html",
                verdict="pass",
            ),
        )
        self.assertTrue(
            any("baseline_artifact" in error for error in errors), errors
        )

    def test_deviation_without_differences_is_rejected(self) -> None:
        errors = self.validate(
            11,
            self.row(
                baseline="design_system",
                baseline_artifact="check_ui_contract:clean-run",
                verdict="deviation",
            ),
        )
        self.assertTrue(
            any("differences" in error for error in errors), errors
        )

    def test_pass_verdict_must_not_list_differences(self) -> None:
        errors = self.validate(
            11,
            self.row(
                baseline="design_system",
                baseline_artifact="check_ui_contract:clean-run",
                verdict="pass",
                differences=["one lingering difference"],
            ),
        )
        self.assertTrue(
            any("differences" in error for error in errors), errors
        )


class TargetComparisonArtifactTests(unittest.TestCase):
    @staticmethod
    def git(root: Path, *args: str) -> str:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise AssertionError(
                f"git {' '.join(args)} failed:\n{result.stdout}\n{result.stderr}"
            )
        return result.stdout.strip()

    def test_v11_reads_html_target_baseline_from_accepted_commit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.git(root, "init")
            self.git(root, "config", "user.name", "Harness Test")
            self.git(root, "config", "user.email", "harness@example.invalid")
            actual = io.BytesIO()
            Image.new("RGB", (3, 2), "blue").save(actual, format="PNG")
            artifact = write_artifact(root, "actual.png", actual.getvalue())
            target = io.BytesIO()
            Image.new("RGB", (3, 2), "red").save(target, format="PNG")
            target_path = write_artifact(root, "parity-target.png", target.getvalue())
            self.git(root, "add", "docs")
            self.git(root, "commit", "-m", "accepted screenshots")
            accepted_sha = self.git(root, "rev-parse", "HEAD")

            run = evidence_run(root, artifact, 11)
            run["ui_evidence"][0]["head_sha"] = accepted_sha
            run["ui_evidence"][0]["target_comparison"] = {
                "baseline": "html_target",
                "baseline_artifact": target_path.relative_to(root).as_posix(),
                "verdict": "pass",
            }
            self.assertEqual([], subject.validate_ui_evidence_files(run, root))

            # A reference render that only exists in the working tree, never in
            # the accepted commit, is not parity evidence.
            uncommitted = io.BytesIO()
            Image.new("RGB", (3, 2), "green").save(uncommitted, format="PNG")
            worktree_only = write_artifact(root, "worktree-only-target.png", uncommitted.getvalue())
            run["ui_evidence"][0]["target_comparison"]["baseline_artifact"] = (
                worktree_only.relative_to(root).as_posix()
            )
            errors = subject.validate_ui_evidence_files(run, root)
            self.assertTrue(
                any(
                    "target_comparison.baseline_artifact" in error
                    and "accepted Git commit" in error
                    for error in errors
                ),
                errors,
            )

    def test_v11_rejects_undecodable_html_target_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.git(root, "init")
            self.git(root, "config", "user.name", "Harness Test")
            self.git(root, "config", "user.email", "harness@example.invalid")
            actual = io.BytesIO()
            Image.new("RGB", (3, 2), "blue").save(actual, format="PNG")
            artifact = write_artifact(root, "actual.png", actual.getvalue())
            target = write_artifact(root, "parity-target.png", b"not an image")
            self.git(root, "add", "docs")
            self.git(root, "commit", "-m", "accepted screenshots")
            accepted_sha = self.git(root, "rev-parse", "HEAD")

            run = evidence_run(root, artifact, 11)
            run["ui_evidence"][0]["head_sha"] = accepted_sha
            run["ui_evidence"][0]["target_comparison"] = {
                "baseline": "html_target",
                "baseline_artifact": target.relative_to(root).as_posix(),
                "verdict": "pass",
            }
            errors = subject.validate_ui_evidence_files(run, root)
            self.assertTrue(
                any(
                    "target_comparison.baseline_artifact" in error
                    and "cannot be decoded" in error
                    for error in errors
                ),
                errors,
            )


class IntegrationHeadGitCrossCheckTests(unittest.TestCase):
    def test_repo_root_that_is_not_a_git_checkout_reports_a_distinct_cause(self) -> None:
        # The CLI uses the current directory for legacy live-Git checks when
        # --repo-root is omitted, so a wrong working directory must not look like
        # an ordinary rev-parse failure (e.g. an unknown branch) on a real checkout.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)  # deliberately never `git init`-ed
            run = {
                "integration": {
                    "branch": "development",
                    "integration_head_sha": "a" * 40,
                }
            }
            errors = subject.validate_integration_head_against_git(run, root)
        self.assertEqual(len(errors), 1)
        self.assertIn("could not be verified against live Git", errors[0])
        self.assertIn("is not a Git checkout", errors[0])
        self.assertIn(str(root), errors[0])
        self.assertNotIn("does not match the live Git head", errors[0])


class UiSurfaceDesignCoverageTests(unittest.TestCase):
    def validate(
        self, surfaces: list[dict[str, object]], registry: dict[str, object]
    ) -> list[str]:
        with tempfile.TemporaryDirectory() as directory:
            registry_path = Path(directory) / "design-system.json"
            registry_path.write_text(json.dumps(registry), encoding="utf-8")
            return subject.validate_ui_surface_design_coverage(
                {"ui_surfaces": surfaces}, registry_path
            )

    @staticmethod
    def surface(
        surface_id: str,
        *,
        route: str = "/home",
        breakpoints: list[str] | None = None,
        states: list[str] | None = None,
    ) -> dict[str, object]:
        return {
            "id": surface_id,
            "trace_ids": ["REQ-001"],
            "route": route,
            "breakpoints": breakpoints or ["mobile-390"],
            "states": states or ["ready"],
            "evidence_gate": "required",
        }

    def test_web_viewports_match_exact_or_delimited_numeric_suffixes(self) -> None:
        registry = {
            "viewports": [390, 768.5],
            "stateMatrix": ["ready"],
        }
        surfaces = [
            self.surface("home", breakpoints=["mobile-390", "tablet_768.5"])
        ]
        self.assertEqual(self.validate(surfaces, registry), [])

        surfaces[0]["breakpoints"] = ["desktop-1390", "tablet_768.5"]
        errors = self.validate(surfaces, registry)
        self.assertTrue(any("responsive target 390" in error for error in errors), errors)

    def test_native_size_classes_require_exact_membership(self) -> None:
        registry = {
            "sizeClasses": ["compact", "regular"],
            "stateMatrix": ["ready"],
        }
        self.assertEqual(
            self.validate(
                [self.surface("home", breakpoints=["compact", "regular"])],
                registry,
            ),
            [],
        )
        errors = self.validate(
            [self.surface("home", breakpoints=["phone-compact", "regular"])],
            registry,
        )
        self.assertTrue(any("responsive target compact" in error for error in errors), errors)

    def test_responsive_registry_requires_exactly_one_nonempty_unique_set(self) -> None:
        invalid_registries = (
            {"stateMatrix": ["ready"]},
            {
                "viewports": [390],
                "sizeClasses": ["compact"],
                "stateMatrix": ["ready"],
            },
            {"viewports": [], "stateMatrix": ["ready"]},
            {
                "viewports": [390, 390],
                "stateMatrix": ["ready"],
            },
            {
                "sizeClasses": ["compact", "compact"],
                "stateMatrix": ["ready"],
            },
        )
        for registry in invalid_registries:
            with self.subTest(registry=registry):
                errors = self.validate([self.surface("home")], registry)
                self.assertTrue(
                    any("exactly one non-empty unique responsive set" in error for error in errors),
                    errors,
                )

    def test_state_matrix_must_be_a_nonempty_string_list(self) -> None:
        for bad in ({}, {"stateMatrix": []}, {"stateMatrix": ["ready", " "]}, {"stateMatrix": "ready"}):
            with self.subTest(registry=bad):
                registry = dict(bad, viewports=[390])
                errors = self.validate([self.surface("home")], registry)
                self.assertTrue(
                    any("stateMatrix" in error for error in errors), errors
                )

    def test_an_explicit_na_marker_covers_an_inapplicable_state(self) -> None:
        registry = {"viewports": [390], "stateMatrix": ["ready", "offline"]}
        covered = self.validate(
            [self.surface("home", states=["ready", "offline:n/a — always online"])],
            registry,
        )
        self.assertEqual(covered, [])

        omitted = self.validate([self.surface("home", states=["ready"])], registry)
        self.assertTrue(any("omits state offline" in error for error in omitted), omitted)

    def test_same_route_surfaces_cannot_union_states_or_breakpoints(self) -> None:
        registry = {
            "viewports": [390, 768],
            "stateMatrix": ["ready", "error"],
        }
        surfaces = [
            self.surface("compact", breakpoints=["390"], states=["ready"]),
            self.surface("wide", breakpoints=["768"], states=["error"]),
        ]
        joined = " ".join(self.validate(surfaces, registry))
        self.assertIn("surface compact route /home omits state error", joined)
        self.assertIn("surface compact route /home omits responsive target 768", joined)
        self.assertIn("surface wide route /home omits state ready", joined)
        self.assertIn("surface wide route /home omits responsive target 390", joined)


if __name__ == "__main__":
    unittest.main()
