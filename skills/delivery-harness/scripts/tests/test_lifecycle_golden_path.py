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
    git,
    init_repo,
    manifest_markdown,
)
from test_graph_orchestration import add_security_review as add_graph_security_review  # noqa: E402
import test_harness_strict_authority as strict_authority_fixtures  # noqa: E402
from test_structure_publication import modern_publication  # noqa: E402
from test_check_activation import task_block, task_fields, valid_record_v2  # noqa: E402
from test_check_seo_review import valid_review_v2  # noqa: E402
import check_activation  # noqa: E402
import check_deployment  # noqa: E402
import check_ui_design_contract  # noqa: E402
from check_design_system_pair import replace_generated_contract  # noqa: E402
from release_targets import parse_release_targets  # noqa: E402
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


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def refresh_plan_source_rows(
    plan: dict[str, object], paths: dict[str, Path], root: Path
) -> None:
    by_kind = {
        "prd": paths["prd"],
        "architecture": paths["architecture"],
        "stack decisions": paths["stack"],
        "ui design": paths["ui"],
        "wireframe": paths["wireframe"],
        "approved ui target": paths["target"],
        "design system": paths["design_markdown"],
        "design system json": paths["design_json"],
    }
    for row in plan["sources"]:
        path = by_kind[row["kind"]]
        row["location"] = path.relative_to(root).as_posix()
        row["content_sha256"] = sha256(path)


def refresh_required_pair(root: Path, paths: dict[str, Path]) -> None:
    """Rebind the existing compiler fixture after schema-5 publication."""

    markdown_path = paths["design_markdown"]
    registry_path = paths["design_json"]
    data = json.loads(registry_path.read_text(encoding="utf-8"))
    data["stateMatrix"] = ["ready", "updated"]

    ui_text = paths["ui"].read_text(encoding="utf-8")
    start = ui_text.index("## Design System Need Gate")
    head, gate = ui_text[:start], ui_text[start:]
    gate = gate.replace("Decision: not_required", "Decision: required", 1)
    gate = re.sub(
        r"^Replacement visual contract when.?not_required:.*$",
        "Compiled design system pair: "
        "docs/design/design-system.md @ sha256:" + "0" * 64
        + " and docs/design/design-system.json @ sha256:" + "0" * 64,
        gate,
        flags=re.MULTILINE,
    )
    ui_text = head + gate
    ui_digest = check_ui_design_contract.canonical_ui_approval_sha256(ui_text)
    data["sourceBindings"] = {
        "prd": {
            "path": paths["prd"].relative_to(root).as_posix(),
            "sha256": sha256(paths["prd"]),
        },
        "architecture": {
            "path": paths["architecture"].relative_to(root).as_posix(),
            "sha256": sha256(paths["architecture"]),
        },
        "stack": {
            "path": paths["stack"].relative_to(root).as_posix(),
            "sha256": sha256(paths["stack"]),
        },
        "uiDesign": {
            "path": paths["ui"].relative_to(root).as_posix(),
            "sha256": ui_digest,
        },
        "wireframe": {
            "path": paths["wireframe"].relative_to(root).as_posix(),
            "sha256": sha256(paths["wireframe"]),
        },
        "hifi": {
            "path": paths["target"].relative_to(root).as_posix(),
            "sha256": sha256(paths["target"]),
        },
    }
    registry_path.write_text(json.dumps(data), encoding="utf-8")
    markdown_path.write_text(
        replace_generated_contract("# Pair\n", data), encoding="utf-8"
    )
    pair_line = (
        "Compiled design system pair: "
        f"{markdown_path.relative_to(root).as_posix()} @ sha256:{sha256(markdown_path)} and "
        f"{registry_path.relative_to(root).as_posix()} @ sha256:{sha256(registry_path)}"
    )
    ui_text = re.sub(
        r"^Compiled design system pair:.*$",
        pair_line,
        ui_text,
        flags=re.MULTILINE,
    )
    paths["ui"].write_text(ui_text, encoding="utf-8")


def deployment_record(architecture: str, sha: str, artifact: str) -> str:
    contract, errors = parse_release_targets(architecture)
    if errors:
        raise AssertionError("fixture architecture is invalid: " + "; ".join(errors))
    targets = {target.stage: target for target in contract.targets}
    development = targets["development"]
    production = targets["production"]
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
        "| production | | | | | |",
        f"| production | https://example.com | {sha} | {sha} | 2026-09-07 | PASS |",
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
    return text


def activation_record(
    prd: str,
    architecture: str,
    deployment: str,
    sha: str,
    artifact: str,
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
        deployment, architecture_text=architecture
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
    def test_schema5_release_keeps_one_identity_through_harness_activation_and_seo(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            init_repo(root, "README.md")

            plan, _seed_run, original_paths = strict_authority_fixtures.StrictAuthorityJoinTests._ui_fixture(
                root, required=True
            )
            # Modernize the same logical package path, then rebind the required
            # compiler pair to the final schema-5 source bytes.
            ui_path, prd_path, wireframe_path, target_path = modern_publication(root)
            paths = {
                "prd": prd_path,
                "architecture": root / "docs/product/architecture.md",
                "stack": root / "docs/product/stack-decisions.md",
                "ui": ui_path,
                "wireframe": wireframe_path,
                "target": target_path,
                "design_markdown": original_paths["design_markdown"],
                "design_json": original_paths["design_json"],
            }
            self.assertEqual("wireframes/5", json.loads(
                check_ui_design_contract.check_wireframe_html.DATA_BLOCK_RE.search(
                    wireframe_path.read_text(encoding="utf-8")
                ).group("data")
            )["schema"])
            refresh_required_pair(root, paths)

            pair_check = run_cli(
                str(DS_SCRIPTS_DIR / "check_design_system_pair.py"),
                "--markdown", str(paths["design_markdown"]),
                "--registry", str(paths["design_json"]),
                "--repo-root", str(root),
                "--require-filled",
            )
            self.assertEqual(0, pair_check.returncode, pair_check.stdout + pair_check.stderr)

            # This negative case corrupts one compiler source binding, then
            # refreshes the pair. The separate enhancement workflow tests cover
            # changed versus preserved path scope; this does not claim to do so.
            unaffected = {
                key: paths[key].read_bytes()
                for key in ("prd", "architecture", "stack", "target")
            }
            registry = json.loads(paths["design_json"].read_text(encoding="utf-8"))
            registry["sourceBindings"]["wireframe"]["sha256"] = "0" * 64
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
            self.assertIn("wireframe", (stale_pair.stdout + stale_pair.stderr).lower())

            refresh_required_pair(root, paths)
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

            plan["security_review"] = {
                "status": "required",
                "skill_slot": "code_security_verification",
                "reason": None,
            }
            add_graph_security_review(plan)
            refresh_plan_source_rows(plan, paths, root)
            for trace in plan["traces"]:
                if trace["id"].startswith("DS-"):
                    trace["source_ids"] = ["SRC-DS-JSON"]
                else:
                    trace["source_ids"] = ["SRC-PRD"]
            for mission in plan.get("missions", []):
                mission["write_scope"] = ["docs/README.md"]
                if "DS-LAY-001" not in mission["trace_ids"]:
                    mission["trace_ids"].append("DS-LAY-001")
                for task in mission.get("tasks", []):
                    task["write_scope"] = ["docs/README.md"]
                    if "DS-LAY-001" not in task["trace_ids"]:
                        task["trace_ids"].append("DS-LAY-001")
                    for acceptance in task.get("acceptance_matrix", []):
                        if "DS-LAY-001" not in acceptance["trace_ids"]:
                            acceptance["trace_ids"].append("DS-LAY-001")
            for node in plan["graph"]["nodes"]:
                if isinstance(node.get("review"), dict):
                    node["review"]["scope"] = ["docs/README.md"]

            git(root, "add", "docs")
            git(root, "commit", "-qm", "freeze schema-5 product package")
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
                "--wireframes", str(paths["wireframe"]),
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
            )
            activation_path = root / "docs/ACTIVATION.md"
            activation_path.write_text(activation, encoding="utf-8")
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
                "--require-lifecycle",
            )
            self.assertEqual(0, seo_check.returncode, seo_check.stdout + seo_check.stderr)


if __name__ == "__main__":
    unittest.main()
