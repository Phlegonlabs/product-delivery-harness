#!/usr/bin/env python3
"""Focused tests for deployment/2 release-source provenance."""

from __future__ import annotations

import sys
import unittest
import re
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


def actual_evidence(sha: str, ref: str = "refs/heads/main") -> str:
    return (
        f"repo=example/deployment; ref={ref}; sha={sha}; "
        f"observed={OBSERVED}; readback=command:git rev-parse {ref}"
    )


class DeploymentSourceProvenanceTests(unittest.TestCase):
    def test_valid_preparation_and_pass(self) -> None:
        preparation = deployment_record()
        self.assertEqual(
            [],
            check_deployment.check_deployment_text(
                preparation, architecture_text=ARCHITECTURE
            ),
        )

        passing = deployment_record(
            web_sha=SHA,
            prod_sha=SHA,
            web_evidence=actual_evidence(SHA, "run.integration.branch"),
            prod_evidence=actual_evidence(SHA),
        ).replace(SHA, SHA)
        self.assertEqual(
            [],
            check_deployment.check_deployment_text(
                passing, architecture_text=ARCHITECTURE
            ),
        )

    def test_wrong_ref_sha_and_tampered_evidence_fail(self) -> None:
        wrong_ref = deployment_record(prod_ref="refs/heads/release")
        findings = check_deployment.check_deployment_text(
            wrong_ref, architecture_text=ARCHITECTURE
        )
        self.assertTrue(
            any("source ref must be" in item for item in findings), findings
        )

        evidence = actual_evidence(SHA)
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
        self.assertTrue(any("begin with command:" in item for item in findings))

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

        full = deployment_record(
            web_sha=SHA,
            prod_sha=SHA,
            web_evidence=actual_evidence(SHA, "run.integration.branch"),
            prod_evidence=actual_evidence(SHA),
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
            ),
        )

    def test_strict_evidence_ref_and_readback_payload_must_match(self) -> None:
        strict = deployment_record(
            web_sha=SHA,
            prod_sha=SHA,
            web_evidence=actual_evidence(SHA, "run.integration.branch"),
            prod_evidence=actual_evidence(SHA),
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

        evil_evidence_ref = strict.replace(
            "ref=refs/heads/main; sha=",
            "ref=refs/heads/evil; sha=",
            1,
        )
        findings = check_deployment.check_deployment_text(
            evil_evidence_ref,
            architecture_text=ARCHITECTURE,
            require_source_provenance=True,
        )
        self.assertTrue(
            any("needs actual source provenance" in item for item in findings),
            findings,
        )

        empty_payload = strict.replace(
            "readback=command:git rev-parse refs/heads/main",
            "readback=command:",
            1,
        )
        findings = check_deployment.check_deployment_text(
            empty_payload,
            architecture_text=ARCHITECTURE,
            require_source_provenance=True,
        )
        self.assertTrue(
            any("needs actual source provenance" in item for item in findings),
            findings,
        )

        artifact = "b" * 64
        artifact_record = strict.replace(
            "deployment-1", artifact, 1
        ).replace(
            "readback=command:git rev-parse refs/heads/main",
            f"readback=command:git rev-parse refs/heads/main artifact-sha256={artifact}",
            1,
        )
        self.assertEqual(
            [],
            check_deployment.check_deployment_text(
                artifact_record,
                architecture_text=ARCHITECTURE,
                require_source_provenance=True,
            ),
        )
        tampered_artifact = artifact_record.replace(artifact, "d" * 64, 1)
        findings = check_deployment.check_deployment_text(
            tampered_artifact,
            architecture_text=ARCHITECTURE,
            require_source_provenance=True,
        )
        self.assertTrue(
            any("needs actual source provenance" in item for item in findings),
            findings,
        )


if __name__ == "__main__":
    unittest.main()
