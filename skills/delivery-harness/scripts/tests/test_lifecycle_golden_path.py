"""One synthetic release carried through UI, Harness and the deployment record."""

from __future__ import annotations

import hashlib
import json
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

_ORIGINAL_SYS_PATH = list(sys.path)
for candidate in (
    TESTS_DIR,
    SCRIPTS_DIR,
    UI_TESTS_DIR,
    PDB_TESTS_DIR,
    DS_SCRIPTS_DIR,
    DS_TESTS_DIR,
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
        encoding="utf-8",
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


def first_prd_signal(prd: str) -> str:
    """Return the first PRD metric name so the fixture source measures a real signal."""
    metrics = prd.split("## Metrics", 1)[1] if "## Metrics" in prd else prd
    for line in metrics.splitlines():
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0] and not set(cells[0]) <= {"-", " "} and cells[0].casefold() != "metric":
            return cells[0]
    raise AssertionError("fixture PRD has no metric row")


def deployment_record(
    architecture: str,
    sha: str,
    artifact: str,
    repo_root: Path,
    signal: str = "TEST-001",
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

## Measurement Sources

| MS ID | Signals | Target | Environment | Retrieval | Source role | Release bindings | Owner | Status | Verified at | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MS-001 | {signal} | GA4 property 123456789 stream 987654321 | production | organic sessions by landing page, complete days only | ga4 | {production.target_id}@{sha}#{artifact} | Jane Doe | verified | 2026-09-07T18:10:00Z | GA4 Data API read-back returned rows for the exact release binding |
"""
    return text


class SharedLifecycleGoldenPathTests(unittest.TestCase):
    def test_current_release_keeps_one_identity_through_harness_and_deployment(self) -> None:
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
                signal=first_prd_signal(paths["prd"].read_text(encoding="utf-8")),
            )
            deployment_path = root / "docs/DEPLOYMENT.md"
            deployment_path.parent.mkdir(parents=True, exist_ok=True)
            deployment_path.write_text(deployment, encoding="utf-8")
            deployment_errors = check_deployment.check_deployment_text(
                deployment,
                architecture_text=paths["architecture"].read_text(encoding="utf-8"),
                repo_root=root,
                expected_repository="synthetic/lifecycle-fixture",
                candidate_ref="refs/heads/run/lifecycle",
                require_source_provenance=True,
                require_measurement_sources=True,
                strict_target_subset=(production.target_id,),
            )
            self.assertEqual([], deployment_errors)
            production_evidence_path = (
                root / "docs/deployment-evidence" / f"{production.target_id}.json"
            )
            production_evidence_bytes = production_evidence_path.read_bytes()
            production_evidence_path.write_bytes(
                production_evidence_bytes.replace(release_sha.encode(), ("f" * 40).encode(), 1)
            )
            common = (
                "--deployment", str(deployment_path),
                "--architecture", str(paths["architecture"]),
                "--repo-root", str(root),
                "--expected-repository", "synthetic/lifecycle-fixture",
                "--candidate-ref", "refs/heads/run/lifecycle",
                "--require-measurement-sources",
            )
            mismatched_check = run_cli(str(SCRIPTS_DIR / "check_deployment.py"), *common)
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
            deployment_check = run_cli(str(SCRIPTS_DIR / "check_deployment.py"), *common)
            self.assertEqual(0, deployment_check.returncode, deployment_check.stdout + deployment_check.stderr)

if __name__ == "__main__":
    unittest.main()
