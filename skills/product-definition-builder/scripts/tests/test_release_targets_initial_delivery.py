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


def target(
    stage: str,
    *,
    surface: str = "web-app",
    suffix: str = "web",
    release_name: str | None = None,
    surface_class: str = "hosted_web",
    discoverable: str = "yes",
    source: str | None = None,
) -> str:
    name = release_name or (f"fixture-{suffix}-dev" if stage == "development" else f"fixture-{suffix}")
    source = source or (DEVELOPMENT_SOURCE if stage == "development" else PRODUCTION_SOURCE)
    return f"""### Release Target: {surface}-{stage}
- Surface: {surface}
- Surface class: {surface_class}
- Public discoverability: {discoverable}
- Surface suffix: {suffix}
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


def architecture(
    *,
    header: str = POLICY + "\n" + MARKER,
    stages=("development", "production"),
    targets: str | None = None,
    expected: str = "web-app",
) -> str:
    body = targets if targets is not None else "\n".join(target(stage) for stage in stages)
    return (
        "# Architecture\n\n## Release Targets\n\n"
        + (header + "\n\n" if header else "")
        + f"Expected deployable surfaces: {expected}\n\n"
        + body
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


class ProductionOnlySurfaceTests(unittest.TestCase):
    def findings(self, **kwargs) -> list[str]:
        return parse_release_targets(architecture(**kwargs))[1]

    def test_marked_surface_may_declare_only_production(self) -> None:
        contract, findings = parse_release_targets(architecture(stages=("production",)))
        self.assertEqual([], findings)
        self.assertEqual("production-first/1", contract.initial_delivery_protocol)
        self.assertEqual(["production"], [item.stage for item in contract.targets])

    def test_marked_package_may_mix_production_only_and_full_pairs(self) -> None:
        targets = "\n".join(
            (
                target("production"),
                target("development", surface="public-api", suffix="api", surface_class="hosted_api", discoverable="no"),
                target("production", surface="public-api", suffix="api", surface_class="hosted_api", discoverable="no"),
            )
        )
        self.assertEqual([], self.findings(targets=targets, expected="web-app, public-api"))

    def test_marked_full_pair_is_still_accepted(self) -> None:
        self.assertEqual([], self.findings())

    def test_unmarked_package_still_requires_the_development_target(self) -> None:
        for header in ("", POLICY):
            with self.subTest(header=header):
                findings = self.findings(header=header, stages=("production",))
                self.assertEqual(
                    ["architecture: expected surface 'web-app' is missing development release targets"],
                    findings,
                )

    def test_invalid_marker_does_not_relax_the_development_requirement(self) -> None:
        for header in (f"{POLICY}\nInitial delivery: production-first/2", f"{POLICY}\n{MARKER}\n{MARKER}", MARKER):
            with self.subTest(header=header):
                findings = self.findings(header=header, stages=("production",))
                self.assertIn(
                    "architecture: expected surface 'web-app' is missing development release targets",
                    findings,
                )

    def test_marked_surface_without_production_target_fails(self) -> None:
        self.assertEqual(
            ["architecture: expected surface 'web-app' is missing production release targets"],
            self.findings(stages=("development",)),
        )
        targets = target("production")
        findings = self.findings(targets=targets, expected="web-app, public-api")
        self.assertIn(
            "architecture: expected surface 'public-api' is missing production release targets",
            findings,
        )

    def test_production_name_checks_still_run_without_a_development_target(self) -> None:
        prod_suffix = target("production", release_name="fixture-web-prod")
        self.assertTrue(
            any("must not end in -prod" in item for item in self.findings(targets=prod_suffix)),
        )
        wrong_suffix = target("production", release_name="fixture-site")
        self.assertTrue(
            any("production release name 'fixture-site' must end in -web" in item for item in self.findings(targets=wrong_suffix)),
        )

    def test_production_target_fields_are_still_validated(self) -> None:
        wrong_source = target("production", source=DEVELOPMENT_SOURCE)
        self.assertTrue(
            any("Source policy must be stage=production" in item for item in self.findings(targets=wrong_source)),
        )

    def test_present_development_target_is_validated_as_today(self) -> None:
        cases = {
            "suffix": (
                target("development", suffix="development-web"),
                "must use the same surface suffix",
            ),
            "class": (
                target("development", surface_class="hosted_api", discoverable="no"),
                "must use the same Surface class",
            ),
            "discoverability": (
                target("development", discoverable="no"),
                "must use the same Public discoverability value",
            ),
            "name": (
                target("development", release_name="fixture-web-staging"),
                "not a canonical 'web' development/production pair",
            ),
            "source": (
                target("development", source=PRODUCTION_SOURCE),
                "Source policy must be stage=development",
            ),
        }
        for name, (development, expected) in cases.items():
            with self.subTest(name=name):
                targets = development + "\n" + target("production")
                self.assertTrue(
                    any(expected in item for item in self.findings(targets=targets)),
                    self.findings(targets=targets),
                )


if __name__ == "__main__":
    unittest.main()
