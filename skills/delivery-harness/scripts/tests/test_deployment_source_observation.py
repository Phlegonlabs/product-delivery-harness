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
            self.assertTrue(any("repository root" in item for item in missing[1]))

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
            self.assertTrue(any("link or reparse" in item for item in link_result[1]))

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


if __name__ == "__main__":
    unittest.main()
