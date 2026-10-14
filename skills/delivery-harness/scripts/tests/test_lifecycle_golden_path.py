"""One synthetic release carried through UI, Harness, Activation, and SEO."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


TESTS_DIR = Path(__file__).resolve().parent
SCRIPTS_DIR = TESTS_DIR.parent
SKILLS_ROOT = Path(__file__).resolve().parents[3]
UI_TESTS_DIR = SKILLS_ROOT / "ui-design-builder" / "scripts" / "tests"
PDB_TESTS_DIR = SKILLS_ROOT / "product-definition-builder" / "scripts" / "tests"
DS_SCRIPTS_DIR = SKILLS_ROOT / "design-system-compiler" / "scripts"
DS_TESTS_DIR = DS_SCRIPTS_DIR / "tests"
ACTIVATION_SCRIPTS_DIR = SKILLS_ROOT / "product-activation" / "scripts"
ACTIVATION_TESTS_DIR = ACTIVATION_SCRIPTS_DIR / "tests"
SEO_SCRIPTS_DIR = SKILLS_ROOT / "seo-growth-review" / "scripts"
SEO_TESTS_DIR = SEO_SCRIPTS_DIR / "tests"

_ORIGINAL_SYS_PATH = list(sys.path)
for candidate in (
    TESTS_DIR,
    SCRIPTS_DIR,
    UI_TESTS_DIR,
    PDB_TESTS_DIR,
    DS_SCRIPTS_DIR,
    DS_TESTS_DIR,
    ACTIVATION_SCRIPTS_DIR,
    ACTIVATION_TESTS_DIR,
    SEO_SCRIPTS_DIR,
    SEO_TESTS_DIR,
):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from harness_core import load_run as _load_run  # noqa: E402
from manifest_fixtures import (  # noqa: E402
    eval_exempt_product_fixture,
    git,
    manifest_markdown,
)
import contract_package_fixture  # noqa: E402
if str(UI_TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(UI_TESTS_DIR))
from test_check_activation import task_block, task_fields, valid_record_v2  # noqa: E402
from test_check_seo_review import valid_review_v2  # noqa: E402
import check_activation  # noqa: E402
import check_deployment  # noqa: E402
from release_targets import parse_release_targets, parse_source_policy  # noqa: E402
from test_deployment_record import GOOD_DEPLOYMENT  # noqa: E402
from test_validate_node_result import running_result  # noqa: E402

# These fixture modules share short import names across skill test directories.
# Restore the exact importer state to keep discovery deterministic.
sys.path[:] = _ORIGINAL_SYS_PATH


def run_cli(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", *arguments],
        cwd=Path(__file__).resolve().parents[4],
        check=False,
        capture_output=True,
        text=True,
        timeout=45,
    )


def retained_observation(
    repo_root: Path,
    target: str,
    source_ref: str,
    resolved_ref: str,
    sha: str,
    artifact: str,
) -> str:
    output = json.dumps(
        {
            "repository": "synthetic/lifecycle-fixture",
            "ref": resolved_ref,
            "sha": sha,
            "artifact": artifact,
        },
        separators=(",", ":"),
    )
    value = {
        "schema": "deployment-source-observation/1",
        "target": target,
        "repository": "synthetic/lifecycle-fixture",
        "source_ref": source_ref,
        "resolved_ref": resolved_ref,
        "source_sha": sha,
        "artifact": artifact,
        "observed_at": "2026-09-07T18:00:00Z",
        "readback": {
            "kind": "command",
            "request": "git rev-parse HEAD",
            "status": 0,
            "output": output,
        },
    }
    relative = f"docs/deployment-evidence/{target}.json"
    path = repo_root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (json.dumps(value, separators=(",", ":")) + "\n").encode("utf-8")
    path.write_bytes(content)
    digest = hashlib.sha256(content).hexdigest()
    return (
        "repo=synthetic/lifecycle-fixture; "
        f"ref={source_ref}; sha={sha}; observed=2026-09-07T18:00:00Z; "
        f"readback=file:{relative}@sha256:{digest}"
    )


def deployment_record(
    architecture: str,
    sha: str,
    artifact: str,
    repo_root: Path,
) -> str:
    contract, errors = parse_release_targets(architecture)
    if errors:
        raise AssertionError("fixture architecture is invalid: " + "; ".join(errors))
    targets = {target.stage: target for target in contract.targets}
    development = targets["development"]
    production = targets["production"]
    development_authority, development_errors = parse_source_policy(
        development.source_policy,
        expected_stage=development.stage,
        source_policy_protocol=development.source_policy_protocol,
    )
    production_authority, production_errors = parse_source_policy(
        production.source_policy,
        expected_stage=production.stage,
        source_policy_protocol=production.source_policy_protocol,
    )
    if development_errors or production_errors:
        raise AssertionError("fixture architecture has invalid source policies")
    unit_row = (
        "| web-app | web | example-web | example-web-dev | "
        "Cloudflare;production route | Cloudflare;development route |"
    )
    updated_unit_row = (
        f"| web-app | web | {production.release_name} | {development.release_name} | "
        f"{production.provider};{production.channel} | "
        f"{development.provider};{development.channel} |"
    )
    text = GOOD_DEPLOYMENT.replace(unit_row, updated_unit_row, 1)
    text = text.replace(
        "## Record\n",
        "## Record\n\n- Record schema: deployment/2\n",
        1,
    )
    text = text.replace(
        "| production | | | | | |",
        f"| production | https://example.com | {sha} | {sha} | 2026-09-07T18:04:00Z | PASS |",
        1,
    )
    text += """

## Release Target Status

| Release target | Surface | Stage | Provider / channel | Endpoint / domain | Expected SHA | Deployed SHA | Artifact / build identity | Availability evidence | Checked | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
"""
    text += (
        f"| {development.target_id} | {development.surface} | development | "
        f"{development.provider};{development.channel} | pending | pending | pending | "
        "pending | pending | pending | pending |\n"
    )
    text += (
        f"| {production.target_id} | {production.surface} | production | "
        f"{production.provider};{production.channel} | https://example.com | {sha} | {sha} | "
        f"{artifact} | production route answered the smoke check | "
        "2026-09-07T18:04:00Z | PASS |\n"
    )
    text += f"""

## Release Source Provenance

| Release target | Source ref | Source SHA | Authority evidence |
| --- | --- | --- | --- |
| {development.target_id} | {development_authority.ref} | pending | pending |
| {production.target_id} | {production_authority.ref} | {sha} | {retained_observation(repo_root, production.target_id, production_authority.ref, production_authority.ref, sha, artifact)} |
"""
    return text


def activation_record(
    prd: str,
    architecture: str,
    deployment: str,
    sha: str,
    artifact: str,
    repo_root: Path,
    expected_repository: str,
    candidate_ref: str,
) -> tuple[str, str]:
    contract, errors = parse_release_targets(architecture)
    if errors:
        raise AssertionError("fixture architecture is invalid: " + "; ".join(errors))
    production = next(target for target in contract.targets if target.stage == "production")
    development = next(target for target in contract.targets if target.stage == "development")
    product_match = re.search(r"^# PRD:\s*(.+)$", prd, re.MULTILINE)
    if product_match is None:
        raise AssertionError("fixture PRD has no product title")
    product = product_match.group(1).strip()
    binding = f"{production.target_id}@{sha}#{artifact}"

    fields = task_fields()
    fields["Release bindings"] = binding
    digest = check_activation.action_digest(
        "ACT-001",
        fields,
        {"CAP-001": fields["Target"], "CAP-002": fields["Target"]},
    )
    fields["Action digest"] = digest
    fields["Authorized digest"] = digest
    text = valid_record_v2(task_blocks=[task_block("ACT-001", fields)])
    text = text.replace("Product: Example", f"Product: {product}", 1)
    text = re.sub(r"\bweb-prod\b", production.target_id, text)
    text = re.sub(r"\bweb-dev\b", development.target_id, text)
    text = text.replace("Cloudflare", production.provider)
    text = text.replace("fixture-production-route", production.channel)
    text = text.replace("fixture-development-route", development.channel)
    text = text.replace("a" * 40, sha)
    text = re.sub(r"(?<!fixture-)web-build-1", artifact, text)

    details, detail_errors = check_activation._prd_signal_details(prd)
    if detail_errors:
        raise AssertionError("fixture PRD outcome rows are invalid: " + "; ".join(detail_errors))
    rows = [
        "| Signal | Definition / obligation | Baseline | Target / guardrail | Measurement window | Expected signal | Release targets | Source / method | Owner | Source ID | Status |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for signal, detail in sorted(details.items()):
        cells = [
            signal,
            detail["definition"],
            detail["baseline"],
            detail["target"],
            detail["window"],
            detail["expected"],
            production.target_id,
            detail["source_method"],
            detail["owner"],
            "MS-001",
            "verified",
        ]
        rows.append("| " + " | ".join(cells) + " |")
    start = text.index("## Outcome Coverage")
    end = text.index("## Measurement Sources", start)
    prefix = text[:start]
    suffix = text[end:]
    text = prefix + "## Outcome Coverage\n" + "\n".join(rows) + "\n\n" + suffix

    # Source fields in the activation fixture are a non-secret synthetic GA4
    # property; release bindings use the exact architecture-backed target.
    deployment_errors = check_deployment.check_deployment_text(
        deployment,
        architecture_text=architecture,
        repo_root=repo_root,
        expected_repository=expected_repository,
        candidate_ref=candidate_ref,
    )
    if deployment_errors:
        raise AssertionError("fixture Deployment is invalid: " + "; ".join(deployment_errors))
    return text, production.target_id


def seo_review(
    activation: str,
    product: str,
    architecture: str,
    production_target: str,
    sha: str,
    artifact: str,
) -> str:
    contract, errors = parse_release_targets(architecture)
    if errors:
        raise AssertionError("fixture architecture is invalid: " + "; ".join(errors))
    production = next(target for target in contract.targets if target.stage == "production")
    text = valid_review_v2()
    text = text.replace("Product: Example", f"Product: {product}")
    text = re.sub(r"\bweb-prod\b", production_target, text)
    text = text.replace("a" * 40, sha)
    text = re.sub(r"(?<=#)web-build-1", artifact, text)
    text = re.sub(
        r"^- Artifact / build identity:.*$",
        f"- Artifact / build identity: {artifact}",
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"^- Deployment identity:.*$",
        f"- Deployment identity: {production.release_name};{production.channel};{artifact}",
        text,
        flags=re.MULTILINE,
    )
    text = re.sub(
        r"^- Activation sha256:.*$",
        "- Activation sha256: " + hashlib.sha256(activation.encode("utf-8")).hexdigest(),
        text,
        flags=re.MULTILINE,
    )
    return text


class SharedLifecycleGoldenPathTests(unittest.TestCase):
    def test_current_release_keeps_one_identity_through_harness_activation_and_seo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with eval_exempt_product_fixture():
                package = contract_package_fixture.current_package(
                    root, pin=(SCRIPTS_DIR.parent / "VERSION").read_text(encoding="utf-8").strip()
                )
            plan = package["plan"]
            paths = package["paths"]
            self.assertIn("UI contract: ui-design/3", paths["ui"].read_text(encoding="utf-8"))
            self.assertFalse((root / "docs/design/wireframes.html").exists())
            registry = json.loads(paths["design_json"].read_text(encoding="utf-8"))
            self.assertEqual("design-system/4", registry["schema"])
            self.assertTrue(paths["preview"].is_file())

            pair_check = run_cli(
                str(DS_SCRIPTS_DIR / "check_design_system_pair.py"),
                "--markdown", str(paths["design_markdown"]),
                "--registry", str(paths["design_json"]),
                "--repo-root", str(root),
                "--require-filled",
            )
            self.assertEqual(0, pair_check.returncode, pair_check.stdout + pair_check.stderr)

            # This negative case corrupts one compiler source binding, then
            # restores those exact bytes. The separate enhancement workflow
            # tests cover changed versus preserved path scope.
            unaffected = {
                key: paths[key].read_bytes()
                for key in ("prd", "architecture", "stack", "target")
            }
            correct_registry = paths["design_json"].read_bytes()
            registry = json.loads(correct_registry.decode("utf-8"))
            registry["sourceBindings"]["hifi"]["sha256"] = "0" * 64
            paths["design_json"].write_text(
                json.dumps(registry), encoding="utf-8"
            )
            stale_pair = run_cli(
                str(DS_SCRIPTS_DIR / "check_design_system_pair.py"),
                "--markdown", str(paths["design_markdown"]),
                "--registry", str(paths["design_json"]),
                "--repo-root", str(root),
                "--require-filled",
            )
            self.assertNotEqual(0, stale_pair.returncode, stale_pair.stdout + stale_pair.stderr)
            self.assertIn("hifi", (stale_pair.stdout + stale_pair.stderr).lower())

            paths["design_json"].write_bytes(correct_registry)
            self.assertEqual(
                unaffected,
                {key: paths[key].read_bytes() for key in unaffected},
            )
            pair_check = run_cli(
                str(DS_SCRIPTS_DIR / "check_design_system_pair.py"),
                "--markdown", str(paths["design_markdown"]),
                "--registry", str(paths["design_json"]),
                "--repo-root", str(root),
                "--require-filled",
            )
            self.assertEqual(0, pair_check.returncode, pair_check.stdout + pair_check.stderr)

            release_sha = git(root, "rev-parse", "HEAD")
            plan_path = root / "PLAN.md"
            plan_path.write_text(
                manifest_markdown("## Harness Plan Manifest", "harness_plan", plan),
                encoding="utf-8",
            )
            run_path = root / "RUN.md"
            generated = run_cli(
                str(SCRIPTS_DIR / "new_run.py"),
                "--plan", str(plan_path),
                "--run-id", "RUN-LIFECYCLE",
                "--branch", "refs/heads/run/lifecycle",
                "--repo-root", str(root),
                "--out", str(run_path),
            )
            self.assertEqual(0, generated.returncode, generated.stdout + generated.stderr)

            harness_check = run_cli(
                str(SCRIPTS_DIR / "validate_harness_plan.py"),
                "--plan", str(plan_path),
                "--run", str(run_path),
                "--repo-root", str(root),
                "--prd", str(paths["prd"]),
                "--design-system-markdown", str(paths["design_markdown"]),
                "--design-system", str(paths["design_json"]),
            )
            self.assertEqual(0, harness_check.returncode, harness_check.stdout + harness_check.stderr)
            self.assertEqual("PASS", json.loads(harness_check.stdout)["status"])

            run = json.loads(json.dumps(_load_run(run_path)))
            run["integration"]["batch_base_sha"] = release_sha
            node_path = root / "node-result.json"
            node_path.write_text(
                json.dumps({"node_result": running_result(plan, run)}),
                encoding="utf-8",
            )
            run_path.write_text(
                manifest_markdown("## Harness Run State", "harness_run", run),
                encoding="utf-8",
            )
            result_check = run_cli(
                str(SCRIPTS_DIR / "validate_result.py"),
                "--plan", str(plan_path),
                "--run", str(run_path),
                "--node-result", str(node_path),
                "--repo-root", str(root),
            )
            self.assertEqual(0, result_check.returncode, result_check.stdout + result_check.stderr)
            self.assertEqual("PASS", json.loads(result_check.stdout)["status"])

            production = next(
                target for target in parse_release_targets(
                    paths["architecture"].read_text(encoding="utf-8")
                )[0].targets if target.stage == "production"
            )
            artifact = "fixture-web-build-1"
            deployment = deployment_record(
                paths["architecture"].read_text(encoding="utf-8"),
                release_sha,
                artifact,
                root,
            )
            deployment_path = root / "docs/DEPLOYMENT.md"
            deployment_path.parent.mkdir(parents=True, exist_ok=True)
            deployment_path.write_text(deployment, encoding="utf-8")
            activation, activation_target = activation_record(
                paths["prd"].read_text(encoding="utf-8"),
                paths["architecture"].read_text(encoding="utf-8"),
                deployment,
                release_sha,
                artifact,
                root,
                "synthetic/lifecycle-fixture",
                "refs/heads/run/lifecycle",
            )
            activation_path = root / "docs/ACTIVATION.md"
            activation_path.write_text(activation, encoding="utf-8")
            production_evidence_path = (
                root / "docs/deployment-evidence" / f"{production.target_id}.json"
            )
            production_evidence_bytes = production_evidence_path.read_bytes()
            production_evidence_path.write_bytes(
                production_evidence_bytes.replace(release_sha.encode(), ("f" * 40).encode(), 1)
            )
            mismatched_check = run_cli(
                str(ACTIVATION_SCRIPTS_DIR / "check_activation.py"),
                "--activation", str(activation_path),
                "--prd", str(paths["prd"]),
                "--architecture", str(paths["architecture"]),
                "--deployment", str(deployment_path),
                "--stack-decisions", str(paths["stack"]),
                "--repo-root", str(root),
                "--require-verified-sources",
                "--require-ready", activation_target,
                "--expected-repository", "synthetic/lifecycle-fixture",
                "--candidate-ref", "refs/heads/run/lifecycle",
            )
            self.assertNotEqual(
                0,
                mismatched_check.returncode,
                mismatched_check.stdout + mismatched_check.stderr,
            )
            self.assertIn(
                "hash does not match authority evidence",
                mismatched_check.stdout + mismatched_check.stderr,
            )
            production_evidence_path.write_bytes(production_evidence_bytes)
            deployment_path.write_text(deployment, encoding="utf-8")
            activation_check = run_cli(
                str(ACTIVATION_SCRIPTS_DIR / "check_activation.py"),
                "--activation", str(activation_path),
                "--prd", str(paths["prd"]),
                "--architecture", str(paths["architecture"]),
                "--deployment", str(deployment_path),
                "--stack-decisions", str(paths["stack"]),
                "--repo-root", str(root),
                "--require-verified-sources",
                "--require-ready", activation_target,
                "--expected-repository", "synthetic/lifecycle-fixture",
                "--candidate-ref", "refs/heads/run/lifecycle",
            )
            self.assertEqual(0, activation_check.returncode, activation_check.stdout + activation_check.stderr)

            product_match = re.search(
                r"^# PRD:\s*(.+)$", paths["prd"].read_text(encoding="utf-8"), re.MULTILINE
            )
            assert product_match is not None
            review_text = seo_review(
                activation,
                product_match.group(1).strip(),
                paths["architecture"].read_text(encoding="utf-8"),
                production.target_id,
                release_sha,
                artifact,
            )
            review_path = root / "docs/seo/reviews/2026-09-10-lifecycle.md"
            review_path.parent.mkdir(parents=True, exist_ok=True)
            review_path.write_text(review_text, encoding="utf-8")
            seo_check = run_cli(
                str(SEO_SCRIPTS_DIR / "check_seo_review.py"),
                "--review", str(review_path),
                "--prd", str(paths["prd"]),
                "--architecture", str(paths["architecture"]),
                "--stack-decisions", str(paths["stack"]),
                "--deployment", str(deployment_path),
                "--activation", str(activation_path),
                "--repo-root", str(root),
                "--expected-repository", "synthetic/lifecycle-fixture",
                "--candidate-ref", "refs/heads/run/lifecycle",
                "--require-lifecycle",
            )
            self.assertEqual(0, seo_check.returncode, seo_check.stdout + seo_check.stderr)


if __name__ == "__main__":
    unittest.main()
