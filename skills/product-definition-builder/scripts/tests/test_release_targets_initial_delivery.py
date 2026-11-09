import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

from release_targets import ReleaseTargetContract, parse_release_targets  # noqa: E402


POLICY = "Release source policy: main-preview/1"
MARKER = "Initial delivery: production-first/1"

DEVELOPMENT_SOURCE = (
    "stage=development; ref=run.integration.branch; "
    "sha=run.integration.integration_head_sha"
)
PRODUCTION_SOURCE = "stage=production; ref=refs/heads/main; sha=promotion.verified_main_sha"


def target(stage: str, *, surface: str = "web-app", release_name: str | None = None) -> str:
    name = release_name or ("fixture-web-dev" if stage == "development" else "fixture-web")
    source = DEVELOPMENT_SOURCE if stage == "development" else PRODUCTION_SOURCE
    return f"""### Release Target: {surface}-{stage}
- Surface: {surface}
- Surface class: hosted_web
- Public discoverability: yes
- Surface suffix: web
- Release name: {name}
- Provider: Cloudflare
- Stage: {stage}
- Source policy: {source}
- Artifact kind: static production bundle
- Signing requirement: not required
- Exact channel / track: fixture-{stage}
- Submission / promotion / review / manual approval path: candidate checks, owner approval, deploy
- Availability signal: URL answers the smoke check and the intended user reaches the route
- Rollout: all users after smoke passes
- Rollback / forward-fix: deploy the prior bundle or a corrected forward-fix
"""


def architecture(*, header: str = POLICY + "\n" + MARKER, stages=("development", "production")) -> str:
    targets = "\n".join(target(stage) for stage in stages)
    return (
        "# Architecture\n\n## Release Targets\n\n"
        + (header + "\n\n" if header else "")
        + "Expected deployable surfaces: web-app\n\n"
        + targets
        + "\n## Observability\n\nLogs.\n"
    )


class InitialDeliveryMarkerTests(unittest.TestCase):
    def test_marker_is_parsed(self) -> None:
        contract, findings = parse_release_targets(architecture())
        self.assertEqual([], findings)
        self.assertEqual("production-first/1", contract.initial_delivery_protocol)
        self.assertEqual("main-preview/1", contract.source_policy_protocol)

    def test_unmarked_package_has_no_protocol(self) -> None:
        contract, findings = parse_release_targets(architecture(header=POLICY))
        self.assertEqual([], findings)
        self.assertIsNone(contract.initial_delivery_protocol)

    def test_constructor_stays_positional_compatible(self) -> None:
        contract = ReleaseTargetContract((), (), None, "main-preview/1")
        self.assertIsNone(contract.initial_delivery_protocol)
        self.assertIsNone(ReleaseTargetContract((), (), None).initial_delivery_protocol)

    def test_wrong_value_is_a_finding(self) -> None:
        for value in ("production-first/2", "production-first", "dev-first/1", ""):
            with self.subTest(value=value):
                contract, findings = parse_release_targets(
                    architecture(header=f"{POLICY}\nInitial delivery: {value}")
                )
                self.assertIsNone(contract.initial_delivery_protocol)
                self.assertTrue(
                    any("only supported Initial delivery marker" in item for item in findings),
                    findings,
                )

    def test_duplicate_marker_is_a_finding(self) -> None:
        contract, findings = parse_release_targets(
            architecture(header=f"{POLICY}\n{MARKER}\n{MARKER}")
        )
        self.assertIsNone(contract.initial_delivery_protocol)
        self.assertTrue(
            any("at most one active Initial delivery marker" in item for item in findings),
            findings,
        )

    def test_marker_needs_the_main_preview_policy(self) -> None:
        for header in (
            MARKER,
            f"Release source policy: dual-branch/1\n{MARKER}",
            f"Release source policy: main-preview/2\n{MARKER}",
        ):
            with self.subTest(header=header):
                contract, findings = parse_release_targets(architecture(header=header))
                self.assertIsNone(contract.initial_delivery_protocol)
                self.assertTrue(
                    any("requires the Release source policy: main-preview/1" in item for item in findings),
                    findings,
                )

    def test_hidden_example_marker_is_ignored(self) -> None:
        hidden = {
            "fence": f"```text\n{MARKER}\n```",
            "wrong value in fence": "```text\nInitial delivery: production-first/9\n```",
            "comment": f"<!-- {MARKER} -->",
            "indented code": f"    {MARKER}",
        }
        for name, block in hidden.items():
            with self.subTest(name=name):
                contract, findings = parse_release_targets(
                    architecture(header=f"{POLICY}\n\n{block}")
                )
                self.assertEqual([], findings)
                self.assertIsNone(contract.initial_delivery_protocol)

    def test_hidden_marker_does_not_duplicate_the_active_one(self) -> None:
        contract, findings = parse_release_targets(
            architecture(header=f"{POLICY}\n{MARKER}\n\n```text\n{MARKER}\n```")
        )
        self.assertEqual([], findings)
        self.assertEqual("production-first/1", contract.initial_delivery_protocol)


if __name__ == "__main__":
    unittest.main()
