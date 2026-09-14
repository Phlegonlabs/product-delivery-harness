"""Cross-skill Product Definition -> Activation seed/reconciliation coverage."""

from __future__ import annotations

import sys
import subprocess
import tempfile
import unittest
import importlib.util
import re
from pathlib import Path


PDB_TESTS = Path(__file__).resolve().parent
PDB_SCRIPTS = PDB_TESTS.parent
ACTIVATION_TESTS = PDB_SCRIPTS.parent.parent / "product-activation" / "scripts" / "tests"
ACTIVATION_SCRIPTS = ACTIVATION_TESTS.parent
for path in (PDB_SCRIPTS, ACTIVATION_SCRIPTS, ACTIVATION_TESTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import check_product_package  # noqa: E402
import check_activation  # noqa: E402


def _load_fixture_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load fixture module {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


activation_fixtures = _load_fixture_module(
    "_activation_seed_activation_fixtures",
    ACTIVATION_TESTS / "test_check_activation.py",
)
product_fixtures = _load_fixture_module(
    "_activation_seed_product_fixtures",
    PDB_TESTS / "test_product_package_checker.py",
)
from release_targets import parse_release_targets  # noqa: E402

# Keep cross-skill fixture imports from changing later unittest discovery.
for path in (ACTIVATION_SCRIPTS, ACTIVATION_TESTS):
    while str(path) in sys.path:
        sys.path.remove(str(path))


SHA = "a" * 40
PRODUCTION = {
    "api-prod": ("hosted_api", "api", "Cloudflare", "fixture-api-build-1", "deployed"),
    "android-prod": ("android", "android", "Google Play", "fixture-android-build-1", "installable"),
    "macos-prod": ("macos", "macos", "Apple Developer", "fixture-macos-build-1", "downloadable"),
    "windows-prod": ("windows", "windows", "Microsoft Store", "fixture-windows-build-1", "downloadable"),
}
SURFACES = {
    "api-backend": ("hosted_api", "api", "Cloudflare", "fixture-api-build-1", "deployed"),
    "android-app": ("android", "android", "Google Play", "fixture-android-build-1", "installable"),
    "macos-app": ("macos", "macos", "Apple Developer", "fixture-macos-build-1", "downloadable"),
    "windows-app": ("windows", "windows", "Microsoft Store", "fixture-windows-build-1", "downloadable"),
}


def architecture_with_hybrid_targets() -> str:
    targets: list[str] = []
    for surface, (surface_class, suffix, provider, artifact, _availability) in SURFACES.items():
        production_name = f"fixture-{suffix}"
        targets.extend(
            [
                f"### Release Target: {suffix}-dev",
                f"- Surface: {surface}",
                f"- Surface class: {surface_class}",
                "- Public discoverability: no",
                f"- Surface suffix: {suffix}",
                f"- Release name: {production_name}-dev",
                f"- Provider: {provider}",
                "- Stage: development",
                "- Source policy: stage=development; ref=run.integration.branch; sha=run.integration.integration_head_sha",
                f"- Artifact kind: {artifact}",
                "- Signing requirement: release signing is handled by the owner-approved channel",
                f"- Exact channel / track: fixture-{suffix}-development-track",
                "- Submission / promotion / review / manual approval path: candidate checks and owner approval",
                "- Availability signal: development smoke or acceptance check passes",
                "- Rollout: development testers receive the candidate",
                "- Rollback / forward-fix: publish a corrected signed forward-fix",
                "",
                f"### Release Target: {suffix}-prod",
                f"- Surface: {surface}",
                f"- Surface class: {surface_class}",
                "- Public discoverability: no",
                f"- Surface suffix: {suffix}",
                f"- Release name: {production_name}",
                f"- Provider: {provider}",
                "- Stage: production",
                "- Source policy: stage=production; ref=refs/heads/main; sha=promotion.verified_main_sha",
                f"- Artifact kind: {artifact}",
                "- Signing requirement: release signing is handled by the owner-approved channel",
                f"- Exact channel / track: fixture-{suffix}-production-track",
                "- Submission / promotion / review / manual approval path: candidate checks, main promotion, and owner approval",
                "- Availability signal: production smoke or acceptance check passes",
                "- Rollout: the intended production audience receives the release",
                "- Rollback / forward-fix: publish a corrected signed forward-fix",
                "",
            ]
        )
    return product_fixtures.valid_architecture().replace(
        "Expected deployable surfaces: none — fixture ships no deployable surface.",
        "Expected deployable surfaces: " + ", ".join(SURFACES),
    ).replace(
        "Expected deployable surfaces: " + ", ".join(SURFACES),
        "Expected deployable surfaces: " + ", ".join(SURFACES) + "\n\n" + "\n".join(targets).rstrip(),
    )


def deployment_for_hybrid_targets() -> str:
    rows = [
        "| Release target | Surface | Stage | Provider / channel | Endpoint / domain | Expected SHA | Deployed SHA | Artifact / build identity | Availability evidence | Checked | Status |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for surface, (surface_class, suffix, provider, artifact, availability) in SURFACES.items():
        for stage, target_id in (("development", f"{suffix}-dev"), ("production", f"{suffix}-prod")):
            channel = f"fixture-{suffix}-{stage}-track"
            if stage == "development":
                rows.append(
                    f"| {target_id} | {surface} | development | {provider};{channel} | pending | pending | pending | pending | pending | pending | n/a |"
                )
            else:
                rows.append(
                    f"| {target_id} | {surface} | production | {provider};{channel} | n/a — store or signed installer target | {SHA} | {SHA} | {artifact} | production {availability} smoke check passed | 2026-09-12T18:04:00Z | PASS |"
                )
    return "# Deployment\n\n## Release Target Status\n\n" + "\n".join(rows) + "\n"


def activation_for_hybrid_targets() -> str:
    production_bindings = [
        f"{target}@{SHA}#{artifact}"
        for target, (_class, _suffix, _provider, artifact, _availability) in PRODUCTION.items()
    ]
    binding_text = ", ".join(production_bindings)
    production_targets = ", ".join(PRODUCTION)
    capability_scope = production_targets
    fields = activation_fixtures.task_fields("ACT-001")
    fields.update(
        {
            "Source refs": "PRD-001, TEST-001",
            "Release bindings": binding_text,
            "Target": capability_scope,
            "Execution capability": "CAP-001",
            "Read-back capability": "CAP-001",
            "Evidence IDs": ", ".join(
                f"EVID-{index:03d}" for index in range(1, 1 + len(PRODUCTION) * 3)
            ),
        }
    )
    digest = check_activation.action_digest("ACT-001", fields, {"CAP-001": capability_scope})
    fields["Action digest"] = digest
    fields["Authorized digest"] = digest
    task_block = activation_fixtures.task_block("ACT-001", fields, "Reconcile every production target")

    evidence_rows: list[str] = []
    evidence_id = 1
    for binding in production_bindings:
        for kind, reference in (
            ("manual", "owner-approved target publication receipt"),
            ("readback", "target identity visible after refresh"),
            ("behavior", "target smoke or acceptance check passed"),
        ):
            evidence_rows.append(
                f"| EVID-{evidence_id:03d} | ACT-001 | {kind} | browser;{digest};{binding} | 2026-09-12T18:{evidence_id:02d}:00Z | PASS | {reference} |"
            )
            evidence_id += 1
    source_evidence_start = evidence_id
    for binding in production_bindings:
        for kind, reference in (
            ("readback", "verified source read-back for the release target"),
            ("behavior", "verified measurement or release behavior for the target"),
        ):
            evidence_rows.append(
                f"| EVID-{evidence_id:03d} | MS-001 | {kind} | browser;n/a;{binding} | 2026-09-12T18:{evidence_id:02d}:00Z | PASS | {reference} |"
            )
            evidence_id += 1
    source_evidence_ids = ", ".join(
        f"EVID-{index:03d}" for index in range(source_evidence_start, evidence_id)
    )

    return f"""# Product Activation

## Record
- Schema: product-activation/1
- Product: Fixture
- Activation owner: Product owner
- Release reference: v1.0.0
- Status: handoff_ready
- Updated: 2026-09-12T18:00:00Z
- Measurement window starts: 2026-09-12T18:00:00Z

## Applied Profiles
| Profile | Applies | Reason | Owner |
| --- | --- | --- | --- |
| core | yes | shared release identity and read-back baseline | Product owner |
| api / backend | yes | hosted API production target requires activation reconciliation | API owner |
| android | yes | Android production target requires store release reconciliation | Android owner |
| macos | yes | macOS production target requires signed artifact reconciliation | macOS owner |
| windows | yes | Windows production target requires signed artifact reconciliation | Windows owner |

## Capability Observations
| Observation ID | Route | Status | Supports | Target scope | Environment | Checked | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CAP-001 | browser | available | read, write, readback | {capability_scope} | production | 2026-09-12T17:55:00Z | owner-approved release consoles and artifact read-back available |

## Outcome Coverage
| Signal | Definition / obligation | Baseline | Target / guardrail | Measurement window | Expected signal | Release targets | Source ID | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Completion | Completed runs | 0 | 90% | 30 days | n/a — metric row | {production_targets} | MS-001 | verified |
| TEST-001 | Complete fixture | none recorded | n/a — required test has no numeric target | integration test | Completion observed | {production_targets} | MS-001 | verified |
| TEST-002 | Reliable fixture | none recorded | n/a — required test has no numeric target | reliability test | All runs pass | {production_targets} | MS-001 | verified |

## Measurement Sources
| MS ID | Target | Environment | Retrieval | Source role | Route / capability | Release bindings | Owner | Status | Evidence IDs |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MS-001 | {capability_scope} | production | bounded release-console and artifact read-back query | first_party | browser;CAP-001 | {binding_text} | Analytics owner | verified | {source_evidence_ids} |

## Activation Tasks
<!-- activation-task-contract:start -->
{task_block}
<!-- activation-task-contract:end -->

## Verification Evidence
| Evidence ID | Item ID | Kind | Route / action / release binding | Checked | Result | Reference |
| --- | --- | --- | --- | --- | --- | --- |
{chr(10).join(evidence_rows)}

## Manual Handoff
| Item ID | Owner | Exact step | Expected evidence | Status |
| --- | --- | --- | --- | --- |
| ACT-001 | n/a | n/a | n/a | n/a |

## Target Readiness
| Release target | Stage | Provider / channel | Source SHA | Artifact / build identity | Availability state | Status | Checked | N/A reason | Blockers |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
""" + "\n".join(
        f"| {suffix}-dev | development | {provider};fixture-{suffix}-development-track | pending | pending | n/a | n/a | n/a | n/a — development candidate is not an activation target | none |"
        for _surface, (_class, suffix, provider, _artifact, _availability) in SURFACES.items()
    ) + "\n" + "\n".join(
        f"| {target} | production | {provider};fixture-{suffix}-production-track | {SHA} | {artifact} | {availability} | ready | 2026-09-12T18:30:00Z | none | none |"
        for target, (_class, suffix, provider, artifact, availability) in PRODUCTION.items()
    ) + """

## Open Blockers
| Blocker ID | Release targets | Kind | Owner | Next step | Status | Notes |
| --- | --- | --- | --- | --- | --- | --- |
"""


def _replace_section(text: str, heading: str, replacement: str) -> str:
    start = text.index(heading)
    after = text[start + len(heading):]
    next_heading = re.search(r"\n## ", after)
    end = start + len(heading) + (next_heading.start() if next_heading else len(after))
    return text[:start] + heading + "\n" + replacement.rstrip() + "\n" + text[end:]


def seeded_activation_for_hybrid_targets() -> str:
    """Create-once seed: target/profile authority present, actions pending."""

    text = activation_for_hybrid_targets()
    text = text.replace("- Status: handoff_ready", "- Status: seeded", 1)
    text = text.replace(" | verified |", " | planned |")
    text = text.replace(" | deployed | ready |", " | pending | pending |")
    text = text.replace(
        "| CAP-001 | browser | available | read, write, readback | "
        + ", ".join(PRODUCTION)
        + " | production | 2026-09-12T17:55:00Z | owner-approved release consoles and artifact read-back available |",
        "| CAP-001 | unselected | unobserved | n/a | pending | pending | pending | pending |",
    )
    text = re.sub(
        r"^\| MS-001 \|.*$",
        "| MS-001 | pending | pending | pending | first_party | unselected;pending | pending@pending#pending | Analytics owner | planned | none |",
        text,
        flags=re.MULTILINE,
    )
    text = _replace_section(
        text,
        "## Verification Evidence",
        "| Evidence ID | Item ID | Kind | Route / action / release binding | Checked | Result | Reference |\n"
        "| --- | --- | --- | --- | --- | --- | --- |",
    )
    task_fields = (
        "Release bindings",
        "Target",
        "Environment",
        "Precondition",
        "Desired state",
        "Execution route",
        "Execution capability",
        "Read-back route",
        "Read-back capability",
        "Authorization",
        "Authorization source",
        "Action digest",
        "Authorized digest",
        "Status",
        "Verification",
        "Evidence IDs",
        "Blocker / N/A reason",
        "Updated",
    )
    for field in task_fields:
        value = "pending@pending#pending" if field == "Release bindings" else "unselected" if field in {"Execution route", "Read-back route"} else "none" if field == "Evidence IDs" else "pending"
        text = re.sub(rf"^- {re.escape(field)}:.*$", f"- {field}: {value}", text, flags=re.MULTILINE)
    text = text.replace("- Status: pending", "- Status: seeded", 1)
    text = text.replace(
        "| CAP-001 | unselected | unobserved | n/a | pending | pending | pending | pending |",
        f"| CAP-001 | browser | unobserved | n/a | {', '.join(PRODUCTION)} | production | pending | pending |",
    )
    capability_scope = ", ".join(PRODUCTION)
    text = text.replace(
        "| MS-001 | pending | pending | pending | first_party | unselected;pending | pending@pending#pending | Analytics owner | planned | none |",
        f"| MS-001 | {capability_scope} | production | pending release-source query | first_party | browser;CAP-001 | pending@pending#pending | Analytics owner | planned | none |",
    )
    for target, (_class, suffix, provider, _artifact, _availability) in PRODUCTION.items():
        text = re.sub(
            rf"^\| {re.escape(target)} \| production \|.*$",
            f"| {target} | production | {provider};fixture-{suffix}-production-track | pending | pending | pending | pending | pending | none | none |",
            text,
            flags=re.MULTILINE,
        )
    text = re.sub(r"\| (Completion|TEST-001|TEST-002) \|([^\n]+?)\| MS-001 \| planned \|", r"| \1 |\2| pending | planned |", text)
    return text


class ProductDefinitionActivationSeedTests(unittest.TestCase):
    def test_real_hybrid_release_targets_seed_and_reconcile_all_profiles(self) -> None:
        architecture = architecture_with_hybrid_targets()
        stack = product_fixtures.valid_stack()
        prd = product_fixtures.valid_prd()
        contract, target_findings = parse_release_targets(architecture)
        self.assertEqual([], target_findings)
        self.assertEqual(
            {"hosted_api", "android", "macos", "windows"},
            {target.surface_class for target in contract.targets},
        )
        product_findings = check_product_package.validate_texts(
            prd,
            architecture,
            stack,
            require_filled=True,
            require_approved=True,
        )
        self.assertEqual([], product_findings)

        activation = activation_for_hybrid_targets()
        deployment = deployment_for_hybrid_targets()
        findings = check_activation.check_activation_text(
            activation,
            prd_text=prd,
            architecture_text=architecture,
            deployment_text=deployment,
            require_verified_sources=True,
            require_ready=tuple(PRODUCTION),
        )
        self.assertEqual([], findings)

    def test_documented_seed_command_uses_staged_architecture_and_deployment(self) -> None:
        architecture = architecture_with_hybrid_targets()
        activation = seeded_activation_for_hybrid_targets()
        deployment = deployment_for_hybrid_targets()
        prd = product_fixtures.valid_prd()
        checker = ACTIVATION_SCRIPTS / "check_activation.py"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = {
                "ACTIVATION.md": activation,
                "PRD.md": prd,
                "architecture.md": architecture,
                "DEPLOYMENT.md": deployment,
            }
            for name, content in paths.items():
                (root / name).write_text(content, encoding="utf-8")
            result = subprocess.run(
                [
                    sys.executable,
                    str(checker),
                    "--activation",
                    str(root / "ACTIVATION.md"),
                    "--prd",
                    str(root / "PRD.md"),
                    "--architecture",
                    str(root / "architecture.md"),
                    "--deployment",
                    str(root / "DEPLOYMENT.md"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_seed_rejects_invented_or_omitted_target_and_profile(self) -> None:
        architecture = architecture_with_hybrid_targets()
        deployment = deployment_for_hybrid_targets()
        prd = product_fixtures.valid_prd()
        valid = seeded_activation_for_hybrid_targets()
        invented = valid.replace("| api-prod | production |", "| invented-prod | production |", 1)
        omitted = valid.replace(
            "| api-prod | production | Cloudflare;fixture-api-production-track | pending | pending | pending | pending | pending | none | none |",
            "",
            1,
        )
        missing_profile = valid.replace(
            "| macos | yes | macOS production target requires signed artifact reconciliation | macOS owner |\n",
            "",
            1,
        )
        for label, candidate, expected in (
            ("invented", invented, "not an architecture release target"),
            ("omitted", omitted, "needs a readiness or concrete n/a row"),
            ("profile", missing_profile, "require profile 'macos'"),
        ):
            with self.subTest(label):
                findings = check_activation.check_activation_text(
                    candidate,
                    prd_text=prd,
                    architecture_text=architecture,
                    deployment_text=deployment,
                    require_verified_sources=True,
                    require_ready=tuple(PRODUCTION),
                )
                self.assertIn(expected, "\n".join(findings))


if __name__ == "__main__":
    unittest.main()
