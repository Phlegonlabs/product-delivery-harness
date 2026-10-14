#!/usr/bin/env python3
"""Focused tests for deployment/2 release-source provenance."""

from __future__ import annotations

import sys
import unittest
import re
import hashlib
import json
import subprocess
import tempfile
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parent.parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import check_deployment  # noqa: E402
import test_deployment_record as deployment_fixtures  # noqa: E402


SHA = "c" * 40
OBSERVED = "2026-09-03T12:00:00Z"
ARCHITECTURE = deployment_fixtures.RELEASE_ARCHITECTURE


def deployment_record(
    *,
    schema: str | None = "deployment/2",
    web_ref: str = "run.integration.branch",
    prod_ref: str = "refs/heads/main",
    web_sha: str = "pending",
    prod_sha: str = "pending",
    web_evidence: str = "pending",
    prod_evidence: str = "pending",
) -> str:
    record = deployment_fixtures.ARCHITECTURE_BACKED_DEPLOYMENT
    record = re.sub(
        r"\| web-dev .*?\n",
        "| web-dev | web-app | development | Cloudflare;development route | "
        "https://dev.example.com | pending | pending | pending | pending | "
        "pending | "
        "pending |\n",
        record,
        count=1,
    )
    record = re.sub(
        r"\| web-prod .*?\n",
        "| web-prod | web-app | production | Cloudflare;production route | "
        "https://example.com | pending | pending | pending | pending | pending "
        "| pending |\n",
        record,
        count=1,
    )
    if schema is None:
        return record
    record = record.replace(
        "## Record\n",
        f"## Record\n\n- Record schema: {schema}\n",
        1,
    )
    rows = [
        f"| web-dev | {web_ref} | {web_sha} | {web_evidence} |",
        f"| web-prod | {prod_ref} | {prod_sha} | {prod_evidence} |",
    ]
    table = (
        "\n\n## Release Source Provenance\n\n"
        "| Release target | Source ref | Source SHA | Authority evidence |\n"
        "| --- | --- | --- | --- |\n"
        + "\n".join(rows)
    )
    return record + table


def write_retained(
    root: Path,
    sha: str,
    ref: str,
    *,
    artifact: str = "deployment-1",
    repository: str = "example/deployment",
    target: str = "web-prod",
    kind: str = "command",
    status: int = 0,
    resolved_ref: str | None = None,
    output_artifact: str | None = None,
) -> str:
    resolved_ref = resolved_ref or ref
    output_artifact = output_artifact or artifact
    output = json.dumps(
        {
            "repository": repository,
            "ref": resolved_ref,
            "sha": sha,
            "artifact": output_artifact,
        },
        separators=(",", ":"),
    )
    value = {
        "schema": "deployment-source-observation/1",
        "target": target,
        "repository": repository,
        "source_ref": ref,
        "resolved_ref": resolved_ref,
        "source_sha": sha,
        "artifact": artifact,
        "observed_at": OBSERVED,
        "readback": {
            "kind": kind,
            "request": "git rev-parse refs/heads/main",
            "status": status,
            "output": output,
        },
    }
    safe_name = re.sub(r"[^a-z0-9]+", "-", ref.casefold()).strip("-")
    relative = f"docs/deployment-evidence/{safe_name}.json"
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (json.dumps(value, separators=(",", ":")) + "\n").encode("utf-8")
    path.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    return (
        f"repo={repository}; ref={ref}; sha={sha}; observed={OBSERVED}; "
        f"readback=file:{relative}@sha256:{digest}"
    )


class DeploymentSourceProvenanceTests(unittest.TestCase):
    def test_strict_flag_requires_architecture(self) -> None:
        findings = check_deployment.check_deployment_text(
            deployment_record(schema=None),
            require_source_provenance=True,
        )
        self.assertIn(
            "architecture: strict source provenance requires architecture.md",
            findings,
        )

        with tempfile.TemporaryDirectory() as temp:
            deployment = Path(temp) / "DEPLOYMENT.md"
            deployment.write_text(deployment_record(schema=None), encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPTS / "check_deployment.py"),
                    "--deployment",
                    str(deployment),
                    "--require-source-provenance",
                ],
                text=True,
                capture_output=True,
                check=False,
            )
        self.assertEqual(2, result.returncode)
        self.assertIn(
            "--require-source-provenance requires --architecture",
            result.stderr,
        )

    def test_valid_preparation_and_pass(self) -> None:
        preparation = deployment_record()
        self.assertEqual(
            [],
            check_deployment.check_deployment_text(
                preparation, architecture_text=ARCHITECTURE
            ),
        )

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            passing = deployment_record(
                web_sha=SHA,
                prod_sha=SHA,
                web_evidence=write_retained(
                    root,
                    SHA,
                    "run.integration.branch",
                    target="web-dev",
                    artifact="deployment-dev",
                    resolved_ref="refs/heads/run/lifecycle",
                ),
                prod_evidence=write_retained(root, SHA, "refs/heads/main"),
            )
            self.assertEqual(
                [],
                check_deployment.check_deployment_text(
                    passing,
                    architecture_text=ARCHITECTURE,
                    repo_root=root,
                    expected_repository="example/deployment",
                    candidate_ref="refs/heads/run/lifecycle",
                ),
            )

    def test_wrong_ref_sha_and_tampered_evidence_fail(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            wrong_ref = deployment_record(prod_ref="refs/heads/release")
            findings = check_deployment.check_deployment_text(
                wrong_ref, architecture_text=ARCHITECTURE
            )
            self.assertTrue(
                any("source ref must be" in item for item in findings), findings
            )

            evidence = write_retained(root, SHA, "refs/heads/main")
            wrong_sha = deployment_record(prod_sha="d" * 40, prod_evidence=evidence)
            findings = check_deployment.check_deployment_text(
                wrong_sha, architecture_text=ARCHITECTURE
            )
            self.assertTrue(any("does not match" in item for item in findings))

            tampered = deployment_record(
                prod_sha=SHA,
                prod_evidence=evidence.replace(SHA, "d" * 40, 1),
            )
            findings = check_deployment.check_deployment_text(
                tampered, architecture_text=ARCHITECTURE
            )
            self.assertTrue(any("does not match" in item for item in findings))

    def test_missing_unsafe_and_nonregular_evidence_fail(self) -> None:
        missing = deployment_record().replace(
            "| web-dev | run.integration.branch | pending | pending |\n", ""
        )
        findings = check_deployment.check_deployment_text(
            missing, architecture_text=ARCHITECTURE
        )
        self.assertTrue(any("architecture targets are missing" in item for item in findings))

        unsafe = deployment_record(prod_ref="../main")
        findings = check_deployment.check_deployment_text(
            unsafe, architecture_text=ARCHITECTURE
        )
        self.assertTrue(any("path-unsafe" in item for item in findings))

        prose = deployment_record(
            prod_sha=SHA,
            prod_evidence=(
                f"repo=example/deployment; ref=refs/heads/main; sha={SHA}; "
                f"observed={OBSERVED}; readback=A trusted person said this SHA "
                "is deployed."
            ),
        )
        findings = check_deployment.check_deployment_text(
            prose, architecture_text=ARCHITECTURE
        )
        self.assertTrue(any("evidence must use repo=" in item for item in findings))

    def test_legacy_record_remains_compatible_but_fails_strict(self) -> None:
        legacy = deployment_record(schema=None)
        self.assertEqual(
            [],
            check_deployment.check_deployment_text(
                legacy, architecture_text=ARCHITECTURE
            ),
        )
        findings = check_deployment.check_deployment_text(
            legacy,
            architecture_text=ARCHITECTURE,
            require_source_provenance=True,
        )
        self.assertTrue(any("actual source proof" in item for item in findings))

    def test_strict_flag_requires_complete_matching_pass(self) -> None:
        findings = check_deployment.check_deployment_text(
            deployment_record(),
            architecture_text=ARCHITECTURE,
            require_source_provenance=True,
        )
        self.assertTrue(any("cannot gain strict readiness" in item for item in findings))

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            full = deployment_record(
                web_sha=SHA,
                prod_sha=SHA,
                web_evidence=write_retained(
                    root,
                    SHA,
                    "run.integration.branch",
                    target="web-dev",
                    artifact="deployment-dev",
                    resolved_ref="refs/heads/run/lifecycle",
                ),
                prod_evidence=write_retained(root, SHA, "refs/heads/main"),
            )
            full = re.sub(
                r"\| web-dev .*?\n",
                "| web-dev | web-app | development | Cloudflare;development route | "
                f"https://dev.example.com | {SHA} | {SHA} | deployment-dev | development "
                f"route answered the smoke check | {OBSERVED} | PASS |\n",
                full,
                count=1,
            )
            full = re.sub(
                r"\| web-prod .*?\n",
                "| web-prod | web-app | production | Cloudflare;production route | "
                f"https://example.com | {SHA} | {SHA} | deployment-1 | production "
                f"route answered the API smoke check | {OBSERVED} | PASS |\n",
                full,
                count=1,
            )
            self.assertEqual(
                [],
                check_deployment.check_deployment_text(
                    full,
                    architecture_text=ARCHITECTURE,
                    require_source_provenance=True,
                    repo_root=root,
                    expected_repository="example/deployment",
                    candidate_ref="refs/heads/run/lifecycle",
                ),
            )

    def test_strict_evidence_ref_and_readback_payload_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            strict = deployment_record(
                web_sha=SHA,
                prod_sha=SHA,
                web_evidence=write_retained(
                    root,
                    SHA,
                    "run.integration.branch",
                    target="web-dev",
                    artifact="deployment-dev",
                    resolved_ref="refs/heads/run/lifecycle",
                ),
                prod_evidence=write_retained(root, SHA, "refs/heads/main"),
            )
            strict = re.sub(
                r"\| web-dev .*?\n",
                f"| web-dev | web-app | development | Cloudflare;development route | https://dev.example.com | {SHA} | {SHA} | deployment-dev | development route answered the smoke check | {OBSERVED} | PASS |\n",
                strict,
                count=1,
            )
            strict = re.sub(
                r"\| web-prod .*?\n",
                f"| web-prod | web-app | production | Cloudflare;production route | https://example.com | {SHA} | {SHA} | deployment-1 | production route answered the API smoke check | {OBSERVED} | PASS |\n",
                strict,
                count=1,
            )
            context = {
                "repo_root": root,
                "expected_repository": "example/deployment",
                "candidate_ref": "refs/heads/run/lifecycle",
            }
            self.assertEqual(
                [],
                check_deployment.check_deployment_text(
                    strict,
                    architecture_text=ARCHITECTURE,
                    require_source_provenance=True,
                    **context,
                ),
                msg=strict,
            )

            evil_evidence_ref = strict.replace(
                "ref=refs/heads/main; sha=",
                "ref=refs/heads/evil; sha=",
                1,
            )
            findings = check_deployment.check_deployment_text(
                evil_evidence_ref,
                architecture_text=ARCHITECTURE,
                require_source_provenance=True,
                **context,
            )
            self.assertTrue(
                any("evidence ref differs" in item for item in findings),
                findings,
            )

            Path(root, "docs/deployment-evidence/refs-heads-main.json").unlink()
            findings = check_deployment.check_deployment_text(
                strict,
                architecture_text=ARCHITECTURE,
                require_source_provenance=True,
                **context,
            )
            self.assertTrue(
                any("cannot be read safely" in item for item in findings),
                findings,
            )

    def test_retained_observation_joins_deployment_identity(self) -> None:
        mutations = (
            {"repository": "other/project"},
            {"artifact": "other-build"},
            {"output_artifact": "other-build"},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                record = deployment_record(
                    web_sha=SHA,
                    prod_sha=SHA,
                    web_evidence=write_retained(
                        root,
                        SHA,
                        "run.integration.branch",
                        target="web-dev",
                        artifact="deployment-dev",
                        resolved_ref="refs/heads/run/lifecycle",
                    ),
                    prod_evidence=write_retained(root, SHA, "refs/heads/main", **mutation),
                )
                record = re.sub(
                    r"\| web-prod .*?\n",
                    f"| web-prod | web-app | production | Cloudflare;production route | https://example.com | {SHA} | {SHA} | deployment-1 | production route answered the API smoke check | {OBSERVED} | PASS |\n",
                    record,
                    count=1,
                )
                findings = check_deployment.check_deployment_text(
                    record,
                    architecture_text=ARCHITECTURE,
                    require_source_provenance=True,
                    strict_target_subset=("web-prod",),
                    repo_root=root,
                    expected_repository="example/deployment",
                    candidate_ref="refs/heads/run/lifecycle",
                )
                self.assertTrue(findings, mutation)

    def test_command_and_provider_retained_observations_pass(self) -> None:
        for kind, status in (("command", 0), ("provider", 204)):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                record = deployment_record(
                    web_sha=SHA,
                    prod_sha=SHA,
                    web_evidence="pending",
                    prod_evidence=write_retained(
                        root,
                        SHA,
                        "refs/heads/main",
                        kind=kind,
                        status=status,
                    ),
                )
                record = re.sub(
                    r"\| web-prod .*?\n",
                    f"| web-prod | web-app | production | Cloudflare;production route | https://example.com | {SHA} | {SHA} | deployment-1 | production route answered the API smoke check | {OBSERVED} | PASS |\n",
                    record,
                    count=1,
                )
                self.assertEqual(
                    [],
                    check_deployment.check_deployment_text(
                        record,
                        architecture_text=ARCHITECTURE,
                        require_source_provenance=True,
                        strict_target_subset=("web-prod",),
                        repo_root=root,
                        expected_repository="example/deployment",
                    ),
                )

    def test_strict_target_subset_does_not_require_unclaimed_dev_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            record = deployment_record(
                web_sha=SHA,
                prod_sha=SHA,
                web_evidence="pending",
                prod_evidence=write_retained(root, SHA, "refs/heads/main"),
            )
            record = re.sub(
                r"\| web-prod .*?\n",
                f"| web-prod | web-app | production | Cloudflare;production route | https://example.com | {SHA} | {SHA} | deployment-1 | production route answered the API smoke check | {OBSERVED} | PASS |\n",
                record,
                count=1,
            )
            self.assertEqual(
                [],
                check_deployment.check_deployment_text(
                    record,
                    architecture_text=ARCHITECTURE,
                    require_source_provenance=True,
                    strict_target_subset=("web-prod",),
                    repo_root=root,
                    expected_repository="example/deployment",
                ),
            )

            findings = check_deployment.check_deployment_text(
                record,
                architecture_text=ARCHITECTURE,
                require_source_provenance=True,
                strict_target_subset=("invented-prod",),
                repo_root=root,
                expected_repository="example/deployment",
            )
            self.assertTrue(any("unknown strict target" in item for item in findings))


if __name__ == "__main__":
    unittest.main()
