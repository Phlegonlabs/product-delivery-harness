#!/usr/bin/env python3
"""Bounded retained Deployment source-observation reader tests."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest


SCRIPTS_DIR = Path(__file__).resolve().parent.parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import deployment_source_observation as m
from deployment_source_observation import load_retained_observation


SHA = "a" * 40
ARTIFACT = "deployment-1"
OBSERVED = "2026-09-07T18:00:00Z"
CHECKED = "2026-09-07T18:04:00Z"


def observation_value(
    *,
    repository: str = "example/project",
    target: str = "web-prod",
    source_ref: str = "refs/heads/main",
    resolved_ref: str = "refs/heads/main",
    source_sha: str = SHA,
    artifact: str = ARTIFACT,
    observed_at: str = OBSERVED,
    kind: str = "command",
    status: int | str = 0,
    output: str | None = None,
) -> dict:
    if output is None:
        output = json.dumps(
            {
                "repository": repository,
                "ref": resolved_ref,
                "sha": source_sha,
                "artifact": artifact,
            },
            separators=(",", ":"),
        )
    return {
        "schema": "deployment-source-observation/1",
        "target": target,
        "repository": repository,
        "source_ref": source_ref,
        "resolved_ref": resolved_ref,
        "source_sha": source_sha,
        "artifact": artifact,
        "observed_at": observed_at,
        "readback": {
            "kind": kind,
            "request": "git rev-parse refs/heads/main",
            "status": status,
            "output": output,
        },
    }


def write_observation(
    root: Path,
    value: dict,
    *,
    relative_path: str = "docs/deployment-evidence/web-prod.json",
) -> tuple[str, str]:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (json.dumps(value, separators=(",", ":")) + "\n").encode("utf-8")
    path.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    return relative_path, digest


def load(
    root: Path,
    *,
    reference: str,
    expected_hash: str,
    repository: str = "example/project",
    target: str = "web-prod",
    source_ref: str = "refs/heads/main",
    resolved_ref: str = "refs/heads/main",
    source_sha: str = SHA,
    artifact: str = ARTIFACT,
    checked: str = CHECKED,
):
    return load_retained_observation(
        repo_root=root,
        reference=reference,
        expected_hash=expected_hash,
        expected_repository=repository,
        target=target,
        source_ref=source_ref,
        resolved_ref=resolved_ref,
        source_sha=source_sha,
        artifact=artifact,
        checked_at=None if checked == "pending" else _timestamp(checked),
    )


def _timestamp(value: str):
    from datetime import datetime

    return datetime.fromisoformat(value.replace("Z", "+00:00"))


class RetainedObservationTests(unittest.TestCase):
    def test_command_and_provider_observations_pass(self) -> None:
        for kind, status in (
            ("command", 0),
            ("provider", 204),
        ):
            with self.subTest(kind=kind):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    value = observation_value(kind=kind, status=status)
                    relative, digest = write_observation(root, value)
                    observation, findings = load(
                        root,
                        reference=f"file:{relative}@sha256:{digest}",
                        expected_hash=digest,
                    )
                    self.assertEqual([], findings)
                    self.assertEqual(value["target"], observation["target"])

    def test_concrete_candidate_ref_is_joined(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = observation_value(
                source_ref="run.integration.branch",
                resolved_ref="refs/heads/run/lifecycle",
            )
            relative, digest = write_observation(root, value)
            observation, findings = load(
                root,
                reference=f"file:{relative}@sha256:{digest}",
                expected_hash=digest,
                source_ref="run.integration.branch",
                resolved_ref="refs/heads/run/lifecycle",
            )
            self.assertEqual([], findings)
            self.assertEqual("refs/heads/run/lifecycle", observation["resolved_ref"])

    def test_missing_tampered_and_unsafe_files_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = observation_value()
            relative, digest = write_observation(root, value)

            missing = load(
                root / "absent",
                reference=f"file:{relative}@sha256:{digest}",
                expected_hash=digest,
            )
            self.assertTrue(
                any(
                    "cannot be read safely" in item
                    for item in missing[1]
                )
            )

            root.joinpath(relative).write_bytes(b"tampered")
            tampered = load(
                root,
                reference=f"file:{relative}@sha256:{digest}",
                expected_hash=digest,
            )
            self.assertTrue(any("hash does not match" in item for item in tampered[1]))

            for unsafe in (
                "/absolute/path.json",
                "../outside.json",
                "docs\\evidence.json",
                "file://evidence.json",
                ".env",
                "stream:hidden.json",
            ):
                unsafe_result = load(
                    root,
                    reference=f"file:{unsafe}@sha256:{digest}",
                    expected_hash=digest,
                )
                self.assertTrue(unsafe_result[1], unsafe)

    def test_links_directories_oversize_and_encoding_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target_dir = root / "docs" / "deployment-evidence"
            target_dir.mkdir(parents=True)
            link = target_dir / "linked.json"
            if os.name == "nt":
                import _winapi

                _winapi.CreateJunction(str(target_dir), str(link))
            else:
                os.symlink(target_dir, link)
            link_result = load(
                root,
                reference="file:docs/deployment-evidence/linked.json@sha256:" + "0" * 64,
                expected_hash="0" * 64,
            )
            expected_link_diagnostic = (
                "link or reparse" if os.name == "nt" else "symlink"
            )
            self.assertTrue(
                any(expected_link_diagnostic in item for item in link_result[1]),
                link_result[1],
            )

            directory_result = load(
                root,
                reference="file:docs/deployment-evidence@sha256:" + "0" * 64,
                expected_hash="0" * 64,
            )
            self.assertTrue(any("regular file" in item for item in directory_result[1]))

            root.joinpath("large.json").write_bytes(b"x" * (1024 * 1024 + 1))
            oversize_result = load(
                root,
                reference="file:large.json@sha256:" + "0" * 64,
                expected_hash="0" * 64,
            )
            self.assertTrue(any("exceeds 1 MiB" in item for item in oversize_result[1]))

            root.joinpath("invalid.json").write_bytes(b"\xff\xfe")
            encoding_result = load(
                root,
                reference="file:invalid.json@sha256:"
                + hashlib.sha256(b"\xff\xfe").hexdigest(),
                expected_hash=hashlib.sha256(b"\xff\xfe").hexdigest(),
            )
            self.assertTrue(any("strict UTF-8 JSON" in item for item in encoding_result[1]))

    def test_closed_json_types_and_time_rules_fail(self) -> None:
        cases = {
            "duplicate": b'{"schema":"x","schema":"y"}',
            "nonfinite": b'{"schema":"x","count":NaN}',
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, content in cases.items():
                path = root / f"{name}.json"
                path.write_bytes(content)
                result = load(
                    root,
                    reference=f"file:{name}.json@sha256:{hashlib.sha256(content).hexdigest()}",
                    expected_hash=hashlib.sha256(content).hexdigest(),
                )
                self.assertTrue(any("strict UTF-8 JSON" in item for item in result[1]))

            value = observation_value()
            value["target"] = 7
            relative, digest = write_observation(root, value, relative_path="wrong-type.json")
            wrong_type = load(
                root,
                reference=f"file:{relative}@sha256:{digest}",
                expected_hash=digest,
            )
            self.assertTrue(any("must be a string" in item for item in wrong_type[1]))

            value = observation_value(observed_at="2099-09-07T18:00:00Z")
            relative, digest = write_observation(root, value, relative_path="future.json")
            future = load(
                root,
                reference=f"file:{relative}@sha256:{digest}",
                expected_hash=digest,
            )
            self.assertTrue(any("cannot be in the future" in item for item in future[1]))

            value = observation_value(observed_at="2026-09-07T19:00:00Z")
            relative, digest = write_observation(root, value, relative_path="late.json")
            late = load(
                root,
                reference=f"file:{relative}@sha256:{digest}",
                expected_hash=digest,
            )
            self.assertTrue(any("newer than deployment" in item for item in late[1]))

    def test_malformed_scalars_and_kind_return_findings_without_raising(self) -> None:
        invalid_values = (None, [], {}, True, False)
        fields = ("repository", "source_sha", "observed_at", "kind")
        for field in fields:
            for value in invalid_values:
                with self.subTest(field=field, value=repr(value)):
                    with tempfile.TemporaryDirectory() as directory:
                        root = Path(directory)
                        value_overrides = {field: value}
                        if field == "kind" and value in (True, False):
                            value_overrides["status"] = 0
                        observation = observation_value(**value_overrides)
                        relative, digest = write_observation(
                            root,
                            observation,
                            relative_path="malformed.json",
                        )
                        result = load(
                            root,
                            reference=f"file:{relative}@sha256:{digest}",
                            expected_hash=digest,
                        )
                        self.assertIsNone(result[0])
                        self.assertTrue(
                            any("must be a string" in item for item in result[1]),
                            result[1],
                        )

    def test_output_members_surrogates_placeholders_and_credentials_fail(self) -> None:
        nested_output_values = (
            {"repository": [], "ref": "refs/heads/main", "sha": SHA, "artifact": ARTIFACT},
            {"repository": "example/project", "ref": {}, "sha": SHA, "artifact": ARTIFACT},
            {"repository": "example/project", "ref": "refs/heads/main", "sha": True, "artifact": ARTIFACT},
        )
        credential_requests = (
            "https://user:credential@example.com/read",
            "Authorization: Bearer synthetic-credential",
            "curl --data password=synthetic-credential",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, output_value in enumerate(nested_output_values):
                output = json.dumps(output_value, separators=(",", ":"))
                observation = observation_value(output=output)
                relative, digest = write_observation(
                    root,
                    observation,
                    relative_path=f"nested-output-{index}.json",
                )
                result = load(
                    root,
                    reference=f"file:{relative}@sha256:{digest}",
                    expected_hash=digest,
                )
                self.assertIsNone(result[0])
                self.assertTrue(
                    any("retained output" in item and "must be a string" in item
                        for item in result[1]),
                    result[1],
                )

            surrogate = observation_value(repository="\ud800")
            relative, digest = write_observation(
                root,
                surrogate,
                relative_path="surrogate.json",
            )
            result = load(
                root,
                reference=f"file:{relative}@sha256:{digest}",
                expected_hash=digest,
            )
            self.assertIsNone(result[0])
            self.assertTrue(
                any("valid UTF-8 scalar text" in item for item in result[1]),
                result[1],
            )

            placeholder = observation_value()
            placeholder["readback"]["request"] = "<todo>"
            relative, digest = write_observation(
                root,
                placeholder,
                relative_path="placeholder.json",
            )
            result = load(
                root,
                reference=f"file:{relative}@sha256:{digest}",
                expected_hash=digest,
            )
            self.assertIsNone(result[0])
            self.assertTrue(
                any("request must be substantive" in item for item in result[1]),
                result[1],
            )

            for index, request in enumerate(credential_requests):
                observation = observation_value()
                observation["readback"]["request"] = request
                relative, digest = write_observation(
                    root,
                    observation,
                    relative_path=f"credential-{index}.json",
                )
                result = load(
                    root,
                    reference=f"file:{relative}@sha256:{digest}",
                    expected_hash=digest,
                )
                self.assertIsNone(result[0])
                self.assertTrue(
                    any(
                        "credential-bearing syntax" in item
                        for item in result[1]
                    ),
                    result[1],
                )

    def test_identity_and_output_joins_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            mutations = (
                {"repository": "other/project"},
                {"target": "other-prod"},
                {"source_ref": "refs/heads/other"},
                {"resolved_ref": "refs/heads/other"},
                {"source_sha": "b" * 40},
                {"artifact": "other-build"},
                {"output": '{"repository":"other/project","ref":"refs/heads/main","sha":"' + SHA + '","artifact":"deployment-1"}'},
            )
            for index, mutation in enumerate(mutations):
                value = observation_value(**mutation)
                relative, digest = write_observation(
                    root,
                    value,
                    relative_path=f"wrong-{index}.json",
                )
                result = load(
                    root,
                    reference=f"file:{relative}@sha256:{digest}",
                    expected_hash=digest,
                )
                self.assertTrue(result[1], mutation)

    def test_root_and_parent_links_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "actual"
            target.mkdir()
            evidence = target / "observation.json"
            evidence.write_bytes(b"{}")
            digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
            root_link = root / "linked-root"
            parent_link = root / "linked-parent"
            if os.name == "nt":
                import _winapi

                _winapi.CreateJunction(str(target), str(root_link))
                _winapi.CreateJunction(str(target), str(parent_link))
            else:
                os.symlink(target, root_link, target_is_directory=True)
                os.symlink(target, parent_link, target_is_directory=True)

            root_result = load(
                root_link,
                reference=f"file:observation.json@sha256:{digest}",
                expected_hash=digest,
            )
            parent_result = load(
                root,
                reference=f"file:linked-parent/observation.json@sha256:{digest}",
                expected_hash=digest,
            )
            self.assertIsNone(root_result[0])
            self.assertIsNone(parent_result[0])
            self.assertTrue(
                any("link" in item or "symlink" in item for item in root_result[1])
            )
            self.assertTrue(
                any("link" in item or "symlink" in item for item in parent_result[1])
            )

    def test_exact_bound_passes_and_one_byte_over_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            value = observation_value()
            body = (json.dumps(value, separators=(",", ":")) + "\n").encode("utf-8")
            body += b" " * (1024 * 1024 - len(body))
            relative = "docs/exact.json"
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(body)
            digest = hashlib.sha256(body).hexdigest()
            reader = (
                m._read_bounded_regular_windows
                if os.name == "nt"
                else m._read_bounded_regular_posix
            )
            content, actual_digest, findings = reader(root, ("docs", "exact.json"), "target")
            self.assertEqual([], findings)
            self.assertEqual(body, content)
            self.assertEqual(digest, actual_digest)

            path.write_bytes(body + b" ")
            content, actual_digest, findings = reader(root, ("docs", "exact.json"), "target")
            self.assertEqual(b"", content)
            self.assertEqual("", actual_digest)
            self.assertTrue(any("exceeds 1 MiB" in item for item in findings))

    def test_known_credential_paths_reject_before_open(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            credential = root / ".env.production"
            credential.write_bytes(b"SECRET=synthetic")
            digest = hashlib.sha256(credential.read_bytes()).hexdigest()
            platform_calls: list[tuple[Path, tuple[str, ...], str]] = []
            original_platform_reader = (
                m._read_bounded_regular_windows
                if os.name == "nt"
                else m._read_bounded_regular_posix
            )

            def platform_reader_spy(repo_root: Path, parts: tuple[str, ...], label: str):
                platform_calls.append((repo_root, parts, label))
                return original_platform_reader(repo_root, parts, label)

            platform_reader_name = (
                "_read_bounded_regular_windows"
                if os.name == "nt"
                else "_read_bounded_regular_posix"
            )
            setattr(m, platform_reader_name, platform_reader_spy)
            try:
                result = load(
                    root,
                    reference=f"file:.env.production@sha256:{digest}",
                    expected_hash=digest,
                )
            finally:
                setattr(m, platform_reader_name, original_platform_reader)
            self.assertIsNone(result[0])
            self.assertEqual([], platform_calls)
            self.assertTrue(
                any("known credential path" in item for item in result[1])
            )
            self.assertEqual(b"SECRET=synthetic", credential.read_bytes())

    def test_race_probe_mutations_are_detected(self) -> None:
        cases = (
            ("growth", "after-open"),
            ("metadata", "after-open"),
            ("parent-replacement", "after-read"),
        )
        for case, stage in cases:
            with self.subTest(case=case):
                with tempfile.TemporaryDirectory() as directory:
                    root = Path(directory)
                    parent = root / "docs"
                    leaf = parent / "observation.json"
                    leaf.parent.mkdir(parents=True)
                    leaf.write_bytes(b"{}")
                    original_parent_bytes = leaf.read_bytes()
                    original_parent_digest = hashlib.sha256(original_parent_bytes).hexdigest()
                    mutation_blocked = False

                    def probe(stage: str, path: Path) -> None:
                        if stage == "after-open" and case == "growth":
                            path.write_bytes(path.read_bytes() + b"x")
                        elif stage == "after-open" and case == "metadata":
                            os.utime(path, (0, 0))
                        elif stage == "after-read" and case == "parent-replacement":
                            if os.name == "nt":
                                nonlocal mutation_blocked

                                try:
                                    os.replace(path.parent, root / "replacement")
                                except PermissionError:
                                    mutation_blocked = True
                                    return
                                (root / "docs").mkdir()
                            else:
                                replacement = root / "replacement"
                                os.replace(path.parent, replacement)
                                (root / "docs").mkdir()

                    reader = (
                        m._read_bounded_regular_windows
                        if os.name == "nt"
                        else m._read_bounded_regular_posix
                    )
                    result = reader(root, ("docs", "observation.json"), "target x", _race_probe=probe)
                    if os.name == "nt" and case == "parent-replacement":
                        self.assertTrue(mutation_blocked)
                        self.assertEqual(
                            (original_parent_bytes, original_parent_digest),
                            (result[0], result[1]),
                        )
                        self.assertEqual([], result[2])
                        self.assertFalse((root / "replacement").exists())
                    else:
                        self.assertEqual(b"", result[0])
                        self.assertEqual("", result[1])
                        self.assertTrue(result[2], case)
                    if case == "growth":
                        self.assertTrue(any("changed" in item for item in result[2]))
                    elif case == "metadata":
                        self.assertTrue(any("changed" in item for item in result[2]))
                    elif os.name != "nt":
                        self.assertTrue(any("parent changed" in item for item in result[2]))


if __name__ == "__main__":
    unittest.main()
