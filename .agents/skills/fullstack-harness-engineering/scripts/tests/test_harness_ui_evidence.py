from __future__ import annotations

import hashlib
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
                    evidence_run(root, artifact, 10), root
                )
        self.assertTrue(any("requires Pillow" in error for error in errors), errors)

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

    def test_schema_v10_accepts_real_png_jpeg_and_webp_images(self) -> None:
        self.assert_real_formats_accepted(10)

    def test_rejects_png_signature_followed_by_garbage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = write_artifact(
                root,
                "signature-garbage.png",
                b"\x89PNG\r\n\x1a\nthis is not a decoded image",
            )
            errors = subject.validate_ui_evidence_files(
                evidence_run(root, artifact, 10), root
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
                evidence_run(root, artifact, 10), root
            )
        self.assertTrue(any("cannot be decoded" in error for error in errors), errors)

    def test_rejects_suffix_and_decoded_format_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            artifact = root / "docs" / "goal" / "evidence" / "jpeg-as-png.png"
            artifact.parent.mkdir(parents=True)
            Image.new("RGB", (3, 2), "red").save(artifact, format="JPEG")
            errors = subject.validate_ui_evidence_files(
                evidence_run(root, artifact, 10), root
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
            run = evidence_run(root, artifact, 10)
            with mock.patch.object(
                subject.Image,
                "open",
                side_effect=[ZeroDimensionImage(), ZeroDimensionImage()],
            ):
                errors = subject.validate_ui_evidence_files(run, root)
        self.assertTrue(any("non-zero dimensions" in error for error in errors), errors)


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
