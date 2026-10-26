import re
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]
STAGE = "references/stages/product-definition.md"


class ProductDefinitionBuilderSkillContractTests(unittest.TestCase):
    def test_eval_inputs_keep_durable_paths_and_separate_mutation_authority(self) -> None:
        for path in ("references/eval-policy-contract.md", "references/artifact-lifecycle.md"):
            text = self.read(path)
            for required in ("evals/inputs/<revision>/", "outside", ".prd-staging", "creation authority",
                             "Never overwrite", "publication", "mutation list", "Retain superseded"):
                self.assertIn(required, text, (path, required))

    def read(self, relative_path: str) -> str:
        return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")

    def test_eval_approval_and_publication_invocations_keep_both_checks(self) -> None:
        for path in ("references/stages/product-definition.md", "references/eval-policy-contract.md",
                     "references/output-contract.md", "references/artifact-lifecycle.md"):
            text = self.read(path)
            lines = [line for line in text.splitlines() if "--eval-policy eval-policy/1" in line]
            self.assertTrue(lines, path)
            for line in lines:
                self.assertIn("--repo-root", line, (path, line))
        output = self.read("references/output-contract.md")
        completeness = output.split("### Completeness", 1)[1].split("### Publication", 1)[0]
        self.assertIn("--eval-policy eval-policy/1", completeness)
        lifecycle = self.read("references/artifact-lifecycle.md")
        staging = lifecycle.split("## Stage and Validate", 1)[1].split("## Publication Authorization Gate", 1)[0]
        self.assertIn("--eval-policy eval-policy/1", staging)

    def test_skill_routes_browser_products_to_frontend_selection(self) -> None:
        skill = self.read(STAGE)

        self.assertIn("references/frontend-stack-selection.md", skill)
        self.assertIn("present two or three coherent bundles with every coupled layer", skill)
        self.assertIn("`Recommended` or `Provisional` blocks the checkpoint", skill)

    def test_product_definition_stops_before_ui_design_or_harness(self) -> None:
        skill = self.read(STAGE)
        entry = self.read("SKILL.md")

        self.assertIn("After step 15 passes, create no UI artifact", skill)
        self.assertIn("later explicit `ui-design-builder` request", skill)
        self.assertIn("UI design and implementation are separate optional phases", skill)
        self.assertIn("No UI design, implementation, PLAN/RUN, or E2E evidence register starts here", entry)
        self.assertIn("does not launch downstream work automatically", entry)

    def test_deployment_document_seeds_the_human_configuration_handoff(self) -> None:
        skill = self.read(STAGE)
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")

        for phrase in (
            "Required Secrets and Variables",
            "External Console Setup",
            "Record names and destinations only, never values",
            "delivery-harness` to reconcile from the first usable build",
            "before its separately authorized deployment",
        ):
            self.assertIn(phrase, skill)
        self.assertIn("Which secret and variable names go where", contract)
        self.assertIn("contain secret names only and no secret values", contract)
        self.assertIn("before a deployable push", lifecycle)

    def test_publish_uses_distinct_repository_context_templates(self) -> None:
        skill = self.read(STAGE)

        self.assertIn(
            "<delivery-harness-skill-root>/scripts/"
            'configure_project_context.py" --root <target-root> --check',
            skill,
        )
        self.assertIn("PROJECT_AGENTS.template.md` for `AGENTS.md`", skill)
        self.assertIn("PROJECT_CLAUDE.template.md` for `CLAUDE.md`", skill)
        self.assertIn("never copy one template to both files", skill)
        self.assertIn("--check --merge-agents", skill)
        self.assertIn("then a reviewed merge plan", skill)
        self.assertIn(
            "then `--check --require-resolved --stage product-definition`",
            skill,
        )
        self.assertIn("not template byte equality", skill)
        self.assertNotIn(
            "`--check --merge-agents --require-resolved --stage product-definition`",
            skill,
        )
        self.assertIn("entry bootstrap is the first source task for a new or existing target", skill)
        self.assertIn("run only the context bootstrap moves", skill)
        self.assertIn(
            "`check_skill_bindings.py --stage ui-design` before directions/HiFi",
            skill,
        )
        self.assertIn("`--stage design-compilation` before compilation", skill)
        self.assertIn("`--stage backend` (or all slots for mixed scope) before execution/security", skill)
        self.assertIn("Preserve confirmed pins", skill)
        self.assertIn("future slots may remain pending", skill)
        self.assertNotIn("Keep Skill Bindings pending here", skill)
        self.assertNotIn("List locally installed binding candidates", skill)
        self.assertNotIn(
            "both files exist before any implementation run starts", skill
        )

    def test_ui_design_is_an_explicit_downstream_skill(self) -> None:
        skill = self.read(STAGE)
        entry = self.read("SKILL.md")
        contract = self.read("references/output-contract.md")

        for content in (skill, contract):
            self.assertIn("ui-design-builder", content)
        self.assertNotIn("design-taste-frontend", skill)
        self.assertIn("complete frontend and backend architecture", contract)
        self.assertIn("A later explicit UI request invokes `ui-design-builder`", entry)
        self.assertIn("## UI Surface Contract", contract)
        self.assertIn("<!-- ui-surface-contract:start -->", contract)
        self.assertIn("<!-- ui-surface-contract:end -->", contract)
        self.assertIn("- `route`: [One literal route value", contract)
        self.assertIn("- `states`: [Comma-separated state IDs", contract)
        self.assertIn("- `responsive`: [This surface's exact responsive set", contract)
        self.assertIn("- `releaseSurface`:", contract)
        self.assertIn("- `surfaceClass`:", contract)
        self.assertIn("- `captureMode`:", contract)
        self.assertIn("invariant machine anchors", contract)
        self.assertNotIn("wireframes.md", contract)
        self.assertIn("## UI Design Handoff Status", contract)

    def test_seo_metadata_is_part_of_the_ui_surface_contract(self) -> None:
        contract = self.read("references/output-contract.md")

        self.assertIn(
            "- SEO metadata: [Per-route `<title>` and meta description", contract
        )
        self.assertIn(
            "canonical URL or `n/a — <reason>`", contract
        )
        self.assertIn("not an implementation-time invention", contract)
        self.assertIn("unique `<title>` and meta description", contract)
        self.assertIn("sitemap and robots policy", contract)
        self.assertIn("traces to its own `TEST-*` row", contract)

    def test_product_approval_presents_and_waits_on_the_complete_candidate(self) -> None:
        skill = self.read(STAGE)
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")

        self.assertIn(
            "verified absolute Markdown links to the complete actual current PRD",
            skill,
        )
        for marker in (
            "Use staging paths while the candidate remains staged",
            "ask explicitly for Product Definition Approval",
            "Opening a file or browser panel is convenience only",
            "presenting the package is not approval",
            "published canonical absolute Markdown links",
            "if publication is deferred, report the actual staging links instead",
            "Wait for the owner's explicit decision before continuing",
        ):
            self.assertIn(marker, skill)
        self.assertIn("#### Human Review Presentation", contract)
        self.assertIn(
            "complete current PRD, architecture, and stack source",
            contract,
        )
        for marker in (
            "Link the staging location while the candidate remains staged",
            "canonical locations after publication",
            "plain path cannot replace those links",
            "do not claim approval readiness",
        ):
            self.assertIn(marker, contract)
        self.assertIn("awaiting explicit approval", lifecycle)

    def test_selection_guide_separates_layers_and_product_patterns(self) -> None:
        guide = self.read("references/frontend-stack-selection.md")

        self.assertIn("## First Separate the Layers", guide)
        self.assertIn("## Product-Fit Patterns", guide)
        self.assertIn("Astro + React islands", guide)
        self.assertIn("React + Vite", guide)
        self.assertIn("Cloudflare Workers with Static Assets", guide)
        self.assertIn("## Official Sources to Recheck", guide)

    def test_output_contract_requires_decision_and_verification(self) -> None:
        contract = self.read("references/output-contract.md")

        self.assertIn("## Frontend Delivery Requirements", contract)
        self.assertIn("## Frontend Technology Decision", contract)
        self.assertIn(
            "| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |",
            contract,
        )
        self.assertIn("### Recorded or Approved Stack", contract)
        self.assertIn("### Rendering and Route Strategy", contract)
        self.assertIn("### Platform Compatibility Verification", contract)
        self.assertIn("### Unresolved Decision Protocol", contract)
        self.assertIn("A bare `TBD` does not pass validation", contract)

    def test_discovery_and_architecture_capture_selection_evidence(self) -> None:
        interview = self.read("references/interview-guide.md")
        architecture = self.read("references/architecture-playbook.md")

        self.assertIn("content-led, interaction-led", interview)
        self.assertIn("rendering needs", interview)
        self.assertIn(
            "For products with a browser frontend, frontend technology layers",
            architecture,
        )
        self.assertIn("official-source verification date", architecture)

    def test_platform_is_resolved_via_askuserquestion_not_defaulted(self) -> None:
        skill = self.read(STAGE)
        architecture = self.read("references/architecture-playbook.md")
        frontend = self.read("references/frontend-stack-selection.md")
        contract = self.read("references/output-contract.md")

        self.assertNotIn("default the deployment platform to Cloudflare", skill)
        self.assertNotIn("## Default Cloudflare Release Pattern", architecture)
        self.assertIn(
            "an evidence-narrowed deployment-platform choice for hosted surfaces",
            skill,
        )
        self.assertIn("## Candidate-to-Production Release Pattern", architecture)
        self.assertIn("resolve the platform before drafting", architecture)
        self.assertIn("one repository and one codebase", architecture)
        self.assertIn("native Workers Previews and production", frontend)
        self.assertIn("Exact PR/branch candidate", contract)
        self.assertIn("Verified main landing SHA", contract)
        self.assertIn("main-preview/1", contract)
        self.assertIn("Ordinary work and hotfixes both freeze remote main", self.read("references/interview-guide.md"))
        self.assertIn("candidate run branch/SHA", architecture)
        self.assertIn(
            "Source policy: [`stage=development; ref=run.integration.branch; ",
            contract,
        )
        for content in (architecture, frontend, contract):
            self.assertIn("development", content.lower())
            self.assertIn("production", content.lower())
            self.assertIn("cloudflare", content.lower())

    def test_frontend_release_sources_follow_explicit_protocol(self) -> None:
        frontend = self.read("references/frontend-stack-selection.md")
        platform = frontend.split("### Any Platform", 1)[1].split("### Cloudflare", 1)[0]

        self.assertIn("output-contract.md#release-targets", platform)
        self.assertNotIn(
            "Development releases build from the exact candidate run branch/SHA and use",
            platform,
        )

    def test_interview_marks_closed_set_questions_for_askuserquestion(self) -> None:
        skill = self.read(STAGE)
        interview = self.read("references/interview-guide.md")

        self.assertIn(
            "Bullets marked `(AskUserQuestion)` are a closed, enumerable set", interview
        )
        for marked_bullet in (
            "or a hybrid? (AskUserQuestion)",
            "[AQ-DEPLOYMENT-PLATFORM] For a deployable web, API, or hosted backend target",
            "recurring usability benchmarking? (AskUserQuestion)",
        ):
            self.assertIn(marked_bullet, interview)
        self.assertNotIn("existing brand reference. (AskUserQuestion", interview)
        self.assertIn(
            "do not call `AskUserQuestion` during any free-text segment",
            skill,
        )
        self.assertIn(
            "start the closed questions only after every applicable segment has a reply",
            interview,
        )
        self.assertNotIn(
            "Immediately follow it with the `AskUserQuestion` batch(es)", skill
        )
        self.assertNotIn("immediately after the free-text interview message", interview)

    def test_open_ended_interview_has_four_adaptive_segments(self) -> None:
        skill = self.read(STAGE)
        interview = self.read("references/interview-guide.md")
        headings = (
            "### Segment 1 — Product and users",
            "### Segment 2 — Workflows, data, and rules",
            "### Segment 3 — Delivery, success, and risk",
            "### Segment 4 — Ambition",
        )

        self.assertIn("four bounded free-text turns", skill)
        self.assertIn("four planned free-text turns", interview)
        self.assertIn("Segments 1+2, then 3+4", interview)
        self.assertEqual(4, sum(interview.count(heading) for heading in headings))
        self.assertLess(interview.index(headings[0]), interview.index(headings[1]))
        self.assertLess(interview.index(headings[1]), interview.index(headings[2]))
        self.assertLess(interview.index(headings[2]), interview.index(headings[3]))
        user_facing = interview.split("## Segmented Free-Text Sequence", 1)[1].split(
            "## Question Routing Reference", 1
        )[0]
        self.assertNotIn("(AskUserQuestion)", user_facing)
        segments = user_facing.split("### Segment ")[1:]
        self.assertEqual(4, len(segments))
        for segment in segments:
            prompts = [
                line
                for line in segment.split("Capture internally:", 1)[0].splitlines()
                if line.startswith("- ")
            ]
            self.assertGreaterEqual(len(prompts), 2)
            self.assertLessEqual(len(prompts), 4)
            for prompt in prompts:
                self.assertLessEqual(len(prompt), 160)
        self.assertIn("Ask only one segment per turn", interview)
        self.assertIn("remove prompts", interview)
        self.assertIn("run only the segments touched or reopened", interview)
        self.assertIn("one compact targeted free-text follow-up", interview)
        self.assertIn("Begin the closed `AskUserQuestion` phase only after", interview)
        self.assertNotIn("ask one organized free-text interview message", skill.lower())

    def test_delivery_profile_and_prd_review_budget(self) -> None:
        skill = self.read("SKILL.md")
        stage = self.read(STAGE)
        interview = self.read("references/interview-guide.md")
        self.assertIn("Delivery profile: standard | mvp", skill)
        self.assertIn("one owner call", skill)
        self.assertIn("| Delivery profile | standard / mvp |", stage)
        self.assertIn("this checkpoint and step 15's Product Definition Approval are one owner call", stage)
        self.assertIn("may conclude `documented assumptions`", stage)
        self.assertIn("compresses the four segments into two turns", stage)
        self.assertIn("compresses them into two turns: Segments 1+2, then 3+4", interview)
        self.assertIn("complete PRD review budget; no independent review wave", stage)
        self.assertIn("PRD delta round", stage)
        self.assertNotIn("exactly four planned free-text turns", interview)
        self.assertNotIn("exactly four bounded free-text turns", stage)

    def test_skill_routes_backend_products_to_backend_selection(self) -> None:
        skill = self.read(STAGE)
        architecture = self.read("references/architecture-playbook.md")
        contract = self.read("references/output-contract.md")

        self.assertIn("references/backend-stack-selection.md", skill)
        self.assertIn("references/backend-stack-selection.md", architecture)
        for content in (skill, architecture, contract):
            self.assertIn("backend, persistent data, or auth requirement", content)

    def test_backend_selection_guide_separates_layers_and_product_patterns(
        self,
    ) -> None:
        guide = self.read("references/backend-stack-selection.md")

        for heading in (
            "## First Separate the Layers",
            "## Collect Decision Evidence",
            "## Product-Fit Patterns",
            "## Data and Auth Decision Rules",
            "## Selection Procedure",
            "## Required Architecture Record",
            "## Official Sources to Recheck",
            "## Failure Modes",
        ):
            self.assertIn(heading, guide)
        self.assertIn("Database category", guide)
        self.assertIn("Auth strategy", guide)
        for option in (
            "Relational",
            "Document",
            "key-value or cache only",
            "Build custom",
            "managed third-party",
        ):
            self.assertIn(option, guide)

    def test_isolated_development_is_seeded_with_mock_content_data(self) -> None:
        architecture = self.read("references/architecture-playbook.md")
        backend = self.read("references/backend-stack-selection.md")

        for content in (architecture, backend):
            self.assertIn("Isolation does not mean development stays empty", content)
            self.assertIn("explicitly authorizes and scopes", content)
        self.assertIn(
            "seed the development environment with representative mock/sample data",
            architecture,
        )
        self.assertIn("seed development with representative mock/sample data", backend)
        self.assertIn(
            "Do not let a development environment access production customer data",
            architecture,
        )
        self.assertIn(
            "Never let development access production customer data or live sessions.",
            backend,
        )

    def test_output_contract_adds_backend_and_data_technology_decision(self) -> None:
        contract = self.read("references/output-contract.md")

        self.assertIn("## Backend and Data Technology Decision", contract)
        self.assertIn("### Data Entity to Store Mapping", contract)
        self.assertIn("### Platform and Vendor Compatibility Verification", contract)
        self.assertIn(
            "database category and auth strategy trace back to the interview's",
            contract,
        )

    def test_interview_marks_backend_and_auth_questions_for_askuserquestion(
        self,
    ) -> None:
        skill = self.read(STAGE)
        interview = self.read("references/interview-guide.md")

        self.assertIn("no persistent database, or an evidence-backed recommendation? (AskUserQuestion)", interview)
        self.assertIn("no auth, or an evidence-backed recommendation? (AskUserQuestion)", interview)
        self.assertIn("database category and auth strategy", skill)
        self.assertIn(
            "the resolved database category and auth strategy (or explicit recommendation request)",
            interview,
        )

    def test_skill_gates_the_backend_askuserquestion_call(self) -> None:
        skill = self.read(STAGE)

        self.assertIn(
            "skip database/auth questions only when the product provably has no backend", skill
        )
        self.assertIn(
            "Skip resolved or inapplicable questions", skill
        )
        self.assertIn(
            "Do not silently select a provider, framework, component system, CSS approach, database/auth implementation",
            skill,
        )

    def test_archetype_dependent_questions_come_after_the_archetype_answer(
        self,
    ) -> None:
        skill = self.read(STAGE)
        interview = self.read("references/interview-guide.md")

        self.assertIn("Keep deployment and UI design preferences out of this call", skill)
        self.assertIn("depends on step 5's archetype answer", skill)
        self.assertIn("question tool's actual per-call question and option limits", interview)
        self.assertIn("There is no host-specific or cross-phase total-call cap", interview)
        self.assertIn(
            "Never ask a final-phase question in the archetype call", interview
        )
        for slotted_bullet in (
            "[AQ-MOBILE-TARGETS] If the answer includes a mobile app",
            "[AQ-DESKTOP-TARGETS] If the answer includes a desktop app",
            "[AQ-CLIENT-STRATEGY] For a mobile or desktop client",
            "[AQ-BROWSER-TARGETS] If the answer is browser extension",
            "[AQ-STACK-DECISION-MODE] How should unresolved implementation technology be decided",
        ):
            self.assertIn(slotted_bullet, interview)
        self.assertIn(
            "Never drop an applicable decision",
            interview,
        )

    def test_trace_ids_and_publish_approval_are_explicit(self) -> None:
        skill = self.read(STAGE)
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")

        for trace_prefix in ("`PRD-*`", "`ARCH-*`", "`UX-*`", "`TEST-*`"):
            self.assertIn(trace_prefix, skill)
        self.assertIn("## Architecture Trace Index", contract)
        self.assertIn("`design-system-compiler`", contract)
        self.assertIn("`UI-*`", contract)
        self.assertIn("| TEST ID | Test Type", contract)
        self.assertIn(
            "Passing validation also does not authorize an overwrite, move, or archive",
            lifecycle,
        )
        self.assertIn("keep the staged package", lifecycle)
        self.assertIn("publish the mutations listed in step 15 when the owner's reply approved them", skill)
        self.assertIn("ask one explicit yes/no question for the list", skill)
        self.assertIn(
            "execute the approved publish and archive moves in the same run", skill
        )
        self.assertIn("An owner reply that approves the package and those paths grants both", lifecycle)
        self.assertIn("approves only the content", lifecycle)

    def test_prd_contract_requires_measurable_nfrs_and_test_obligations(self) -> None:
        contract = self.read("references/output-contract.md")
        interview = self.read("references/interview-guide.md")

        self.assertLess(
            contract.index("## Functional Requirements"),
            contract.index("## Non-Functional Requirements"),
        )
        self.assertLess(
            contract.index("## Non-Functional Requirements"),
            contract.index("## UX Requirements"),
        )
        self.assertLess(
            contract.index("## Open Questions"),
            contract.index("## Test Obligations"),
        )
        self.assertLess(
            contract.index("## Test Obligations"),
            contract.index("## UI Design Handoff Status"),
        )
        self.assertIn(
            "| ID | Quality attribute | Scope / requirement | Measure | Target / threshold | TEST IDs |",
            contract,
        )
        self.assertIn(
            "| TEST ID | Obligation | Test type | Required | Upstream trace IDs | Expected signal |",
            contract,
        )
        self.assertIn(
            "units, tested population or traffic shape, measurement window, and percentile",
            contract,
        )
        self.assertIn(
            "record the category as explicitly `N/A` with a reason", contract
        )
        self.assertIn(
            "Every `Must` functional requirement and every applicable non-functional requirement",
            contract,
        )
        self.assertIn("maps to at least one row whose `Required` value is `Yes`", contract)
        self.assertIn("The PRD assigns stable `TEST-*` IDs during synthesis", interview)

    def test_test_ids_are_reused_and_preserved_in_enhancements(self) -> None:
        contract = self.read("references/output-contract.md")
        skill = self.read(STAGE)
        interview = self.read("references/interview-guide.md")

        self.assertIn("Reuse the canonical `TEST-*` IDs from `PRD.md`", contract)
        self.assertIn(
            "must not create anonymous replacements or duplicate TEST identities", skill
        )
        self.assertIn(
            "Preserve existing `TEST-*` IDs for unchanged obligations", interview
        )
        self.assertIn("mint new TEST IDs only for newly uncovered obligations", skill)
        self.assertIn(
            "new TEST IDs cover only obligations that were previously uncovered",
            contract,
        )

    def test_stack_rows_record_per_layer_status_and_cited_authority(self) -> None:
        contract = self.read("references/output-contract.md")
        frontend = self.read("references/frontend-stack-selection.md")
        backend = self.read("references/backend-stack-selection.md")
        mobile = self.read("references/mobile-stack-selection.md")
        monetization = self.read("references/monetization-and-partner-channel-guide.md")

        header = "| Layer | Selection | Status | Authority / evidence | Why It Fits | Constraint / follow-up |"
        self.assertEqual(6, contract.count(header))
        self.assertIn("## CLI and Toolchain Decision", contract)
        for status_rule in (
            "`Required` means a user, organization, or hard external constraint",
            "`Selected` means the current product or repository already adopted it",
            "`Approved` means the human owner accepted a new choice",
            "`Recommended` is evidence-backed advice not yet accepted",
            "`Provisional` is a leading choice pending named evidence",
        ):
            self.assertIn(status_rule, contract)
        self.assertIn("A section may mix statuses", contract)
        self.assertIn("Authority is not another status label", contract)
        for guide in (frontend, backend, mobile, monetization):
            self.assertIn(
                "Assign status per layer; one section may mix statuses", guide
            )
            self.assertIn("Authority is the cited source, not a status label", guide)
            self.assertIn("Selection, status, cited authority/evidence", guide)

    def test_service_topology_is_the_first_backend_layer_everywhere(self) -> None:
        contract = self.read("references/output-contract.md")
        backend = self.read("references/backend-stack-selection.md")
        architecture = self.read("references/architecture-playbook.md")

        backend_section = contract[
            contract.index("## Backend and Data Technology Decision") :
        ]
        self.assertLess(
            backend_section.index("| Service topology |"),
            backend_section.index("| Backend runtime / framework |"),
        )
        layers = backend[
            backend.index("## First Separate the Layers") : backend.index(
                "## Service Topology Decision"
            )
        ]
        self.assertLess(
            layers.index("| Service topology |"),
            layers.index("| Backend runtime / framework |"),
        )
        self.assertIn(
            "backend technology layers in this order: service topology", architecture
        )
        for content in (contract, backend, architecture):
            self.assertIn("monolith", content.lower())
            self.assertIn("monorepo", content.lower())
            self.assertIn("polyrepo", content.lower())

    def test_release_discovery_is_provider_neutral_and_complete(self) -> None:
        interview = self.read("references/interview-guide.md")
        architecture = self.read("references/architecture-playbook.md")
        contract = self.read("references/output-contract.md")

        self.assertIn("## Provider-Neutral Release Target Pattern", architecture)
        self.assertIn("## Release Targets", contract)
        for field in (
            "stable target ID",
            "Surface class",
            "Public discoverability",
            "Surface suffix",
            "Release name",
            "development",
            "production",
            "Source policy",
            "Artifact kind",
            "Signing requirement",
            "Exact channel / track",
            "Submission / promotion / review / manual approval path",
            "Availability signal",
            "Rollout",
            "Rollback / forward-fix",
        ):
            self.assertIn(field, contract)
        self.assertIn(
            "complete inventory of expected deployable web, API, mobile, desktop, or browser-extension surfaces",
            interview,
        )
        self.assertIn(
            "at least one `development` target and one `production` target", contract
        )
        self.assertIn("Expected deployable surfaces:", contract)
        self.assertIn("- Surface: [Stable expected surface ID]", contract)
        self.assertIn(
            "- Provider: [Stage-specific hosting, store, or distribution provider]",
            contract,
        )
        self.assertIn(
            "one surface may use different providers by stage", contract
        )
        for content in (interview, architecture, contract):
            self.assertIn("<product-slug>-<surface-suffix>", content)
            self.assertIn("-dev", content)
            self.assertIn("-prod", content)
        self.assertIn("`web`, `api`, and `extension`", architecture)
        self.assertIn("`ios`, `android`, `macos`, or `windows`", architecture)
        self.assertIn("Chrome, Firefox", architecture)
        self.assertIn("public listing title may differ", architecture.lower())
        for content in (interview, architecture, contract):
            self.assertIn("release name", content.lower())
            self.assertIn("surface", content.lower())
        self.assertIn(
            "Preserve stable release target IDs for unchanged targets", interview
        )
        self.assertIn("stable release target IDs from the prior package", contract)

    def test_release_availability_and_native_recovery_are_explicit(self) -> None:
        interview = self.read("references/interview-guide.md")
        architecture = self.read("references/architecture-playbook.md")
        contract = self.read("references/output-contract.md")

        for content in (interview, architecture, contract):
            self.assertIn("not availability", content.lower())
            self.assertIn("forward-fix", content.lower())
        self.assertIn(
            "Do not use this two-row hosted-environment table for native", contract
        )
        self.assertIn("Do not force TestFlight, Play tracks", architecture)
        self.assertIn("actually installable or downloadable", contract)
        self.assertIn("halting a phased or staged rollout", contract)

    def test_release_sources_enforce_candidate_branch_and_main_only(self) -> None:
        interview = self.read("references/interview-guide.md")
        architecture = self.read("references/architecture-playbook.md")
        contract = self.read("references/output-contract.md")
        frontend = self.read("references/frontend-stack-selection.md")

        for content in (interview, architecture, contract, frontend):
            for retired in (
                "PLAN-v5",
                "pr_head",
                "integration_head`",
                "production_head",
                "merged_main",
            ):
                self.assertNotIn(retired, content)
        self.assertTrue("branch or ref" in interview or "branch/ref" in interview)
        self.assertIn("refs/heads/main", interview)
        self.assertIn("tags and alternative production refs are rejected", interview.lower())
        self.assertIn("promotion.verified_main_sha", contract)

    def test_migration_order_drops_plan_v5_field_mapping(self) -> None:
        architecture = self.read("references/architecture-playbook.md")
        contract = self.read("references/output-contract.md")

        for content in (architecture, contract):
            self.assertNotIn("`migration_classification`", content)
            self.assertNotIn("`commands.migrate`", content)
            self.assertNotIn("`prerequisites`", content)
            self.assertNotIn("`migration_command`", content)

    def test_market_research_role_forbids_fabricated_evidence(self) -> None:
        skill = self.read(STAGE)
        guide = self.read("references/market-research-guide.md")
        contract = self.read("references/output-contract.md")

        for content in (skill, guide, contract):
            self.assertIn("UNVALIDATED", content)
        self.assertIn("## Source Rules", guide)
        self.assertIn("Never state an unsourced claim as fact", guide)
        self.assertIn(
            "Do not invent competitor names, pricing, funding, user counts", guide
        )
        self.assertIn("| `sourced` |", guide)
        self.assertIn("| `reported` |", guide)
        self.assertIn("## Blocked Path", guide)
        self.assertIn("never invent a competitor, price, or market figure", skill)

    def test_market_research_artifact_is_contracted_and_published(self) -> None:
        skill = self.read(STAGE)
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")

        self.assertIn("references/market-research-guide.md", skill)
        self.assertIn("`MR-*` for market-research findings", skill)
        self.assertIn("## `market-research.md`", contract)
        self.assertIn(
            "| MR ID | Finding | Lands in | Recommended change | Confidence | Sources |",
            contract,
        )
        self.assertIn(
            "| Source ID | Publisher | Title | URL | Retrieved | Type |", contract
        )
        self.assertIn(
            "`docs/product/market-research.md` when the market-research gap pass produced it",
            lifecycle,
        )
        self.assertIn(
            'is also this package\'s own artifact, not the general "research"',
            lifecycle,
        )
        self.assertIn("do not archive a prior `market-research.md` at all", lifecycle)
        self.assertIn("the market context is unvalidated", contract)

    def test_research_first_gate_runs_before_any_closed_set_decision(self) -> None:
        skill = self.read(STAGE)
        guide = self.read("references/research-first-guide.md")
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")
        market = self.read("references/market-research-guide.md")

        # The assessment is its own workflow step, ordered between the
        # free-text interview and the first AskUserQuestion batch.
        self.assertIn("4. Run the research-first assessment", skill)
        interview_at = skill.index("Conduct four bounded free-text turns")
        assessment_at = skill.index("4. Run the research-first assessment")
        first_batch_at = skill.index("5. After all applicable free-text segments")
        self.assertLess(interview_at, assessment_at)
        self.assertLess(assessment_at, first_batch_at)
        self.assertIn(
            "before any closed-set decision", skill,
        )
        self.assertIn("In enhancement mode, skip this step entirely", skill)

        # The gate vocabulary, owner, and stop behavior are pinned.
        self.assertIn("`go | clarify | stop`", skill)
        self.assertIn("The researcher recommends; the human owner decides", guide)
        self.assertIn("Draft nothing. Report the findings", guide)
        self.assertIn("recorded as `clarify` with the decisive question stated", guide)

        # Source discipline is reused from the market-research guide, not duplicated.
        self.assertIn(
            "Apply `references/market-research-guide.md`'s Source Rules", guide
        )
        self.assertIn("never invent a competitor, price, user count, or market figure", guide)

        # The artifact, its publish path, and its trace family are contracted.
        self.assertIn("`RA-*` for research-first assessment findings", skill)
        self.assertIn("## `research-assessment.md`", contract)
        self.assertIn("| RA ID | Finding | Confidence | Sources |", guide)
        self.assertIn(
            "`docs/product/research-assessment.md` when the research-first assessment produced it",
            lifecycle,
        )
        self.assertIn("never while keeping a `PRD.md` that cites its `RA-*` IDs", lifecycle)
        self.assertIn("`RA-*` IDs follow the `MR-*` discipline", guide)

        # PRD records the gate; a silently missing gate does not validate.
        self.assertIn("### Research Gate", contract)
        self.assertIn(
            "Research Gate: [go / clarify / stop / skipped]",
            contract,
        )
        self.assertIn("every retained `docs/product/outcomes/*.md` record in full", skill)

        # The post-draft pass reconciles the assessment instead of
        # researching the same ground twice.
        self.assertIn("plus `research-assessment.md` when the pre-draft pass ran", skill)
        self.assertIn("The pass is a reconciliation", skill)
        self.assertIn(
            "`research-assessment.md` when the pre-draft research-first assessment ran",
            market,
        )
        self.assertIn("carry still-valid `RA-*` findings", market)

    def test_research_draft_recommendations_owner_choice_then_final_approvals(
        self,
    ) -> None:
        skill = self.read(STAGE)

        order = [
            skill.index("4. Run the research-first assessment"),
            skill.index("12. Draft or repair the core Markdown package"),
            skill.index("Produce evidence-based Platform Optimization Recommendations"),
            skill.index("14. Run the Stack Decision Checkpoint"),
            skill.index("15. Run Product Definition Approval"),
        ]
        self.assertEqual(order, sorted(order))
        self.assertIn(
            "present the complete candidate and every recommendation to the owner",
            skill,
        )
        self.assertIn(
            "Apply only an owner-recorded accepted proposal",
            skill,
        )

    def test_research_reuses_assessment_and_limits_new_search(self) -> None:
        skill = self.read(STAGE)
        guide = self.read("references/research-first-guide.md")
        market = self.read("references/market-research-guide.md")

        self.assertIn(
            "feature baseline, differentiation, pricing/business-model baseline, and category benchmarks",
            skill,
        )
        for heading in (
            "## Feature Baseline And Differentiation",
            "## Pricing And Business Model Baseline",
            "## Category Benchmarks",
        ):
            self.assertIn(heading, guide)
        self.assertIn(
            "Record these as evidence inputs, not speculative final requirements",
            guide,
        )
        self.assertIn(
            "research only newly raised, stale, or `UNVALIDATED` gaps",
            market,
        )
        self.assertIn(
            "research only newly raised, stale, or `UNVALIDATED` gaps",
            skill,
        )
        self.assertIn(
            "do not re-research settled market context or force a full market rerun",
            market,
        )

    def test_platform_optimization_recommendations_require_evidence_and_owner_decision(
        self,
    ) -> None:
        skill = self.read(STAGE)
        guide = self.read("references/market-research-guide.md")
        contract = self.read("references/output-contract.md")

        for content in (guide, contract):
            self.assertIn("## Platform Optimization Recommendations", content)
            self.assertIn("at most five useful", content)
            self.assertIn("None — [evidence-backed reason]", content)
            self.assertIn("Expected benefit hypothesis", content)
            self.assertIn(
                "`pending | accepted | revise | deferred | rejected`",
                content,
            )
        self.assertIn("Affected PRD: [sections and existing", guide)
        self.assertIn("Affected PRD: [section names and existing", contract)
        self.assertIn("never a measured-benefit claim", guide)
        self.assertIn("no measured-benefit claim", contract)
        self.assertIn("Never infer approval from silence", skill)
        self.assertIn("cannot erase an approval-blocking gap", skill)
        self.assertIn(
            "Deferral or rejection never clears an approval-blocking gap",
            contract,
        )

    def test_approval_presents_complete_prd_and_recommendation_links(self) -> None:
        skill = self.read(STAGE)
        contract = self.read("references/output-contract.md")

        self.assertIn(
            "complete actual current PRD, architecture, stack decisions, every produced market/research artifact, and its Platform Optimization Recommendations",
            skill,
        )
        self.assertIn(
            "complete current PRD, architecture, and stack source; include every produced market/research artifact, its Platform Optimization Recommendations and decision statuses",
            contract,
        )
        self.assertIn("verified absolute Markdown links", skill)
        self.assertIn("plain path cannot replace those links", contract)

    def test_outcome_review_closes_the_loop_after_deployment(self) -> None:
        skill = self.read(STAGE)
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")
        template = self.read("assets/templates/OUTCOME_REVIEW.template.md")

        # The review is an owner-initiated post-publish step with a closed
        # verdict vocabulary and real measurement windows.
        self.assertIn("24. When the owner asks for an outcome review", skill)
        self.assertIn("`no_change`, `enhancement`, or `incident`", skill)
        self.assertIn("never leave a run open waiting for adoption", skill)
        self.assertIn("One record covers one production release target", contract)
        self.assertIn(
            "equal the Deployment PASS row", contract
        )
        self.assertIn(
            "The measurement window is real elapsed time after deployment", contract
        )
        self.assertIn(
            'A review written at deploy time with "pending" actuals is a stub',
            contract,
        )

        # It publishes under an immutable dated path and feeds the next enhancement run.
        self.assertIn(
            "`docs/product/outcomes/YYYY-MM-DD-<release-set>.md` after each deployed release-set outcome review",
            lifecycle,
        )
        self.assertIn("every retained `docs/product/outcomes/*.md` record in full", skill)
        self.assertIn("`docs/product/outcomes/` contains immutable post-deployment records", lifecycle)
        fence_open = False
        architecture_active = False
        for line in contract.splitlines():
            if line.startswith("```"):
                fence_open = not fence_open
            if line.strip() == "## `architecture.md`":
                architecture_active = not fence_open
        self.assertFalse(fence_open, "output contract Markdown fences must be balanced")
        self.assertTrue(architecture_active, "architecture output section must remain active Markdown")
        self.assertIn("| Incident | Containment | Human owner |", template)
        for retired in ("Target Reviews", "Target Measurements", "Verdict History", "Prior outcome sha256"):
            self.assertNotIn(retired, template)

    def test_activation_seed_is_create_once_and_owned_downstream(self) -> None:
        skill = self.read(STAGE)
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")

        for source in (skill, contract, lifecycle):
            self.assertIn("ACTIVATION.md", source)
            self.assertIn("product-activation", source)
        self.assertIn("does not already exist", skill)
        self.assertIn("preserve it byte-for-byte", skill)
        self.assertIn("one Outcome Coverage row for every PRD metric", skill)
        self.assertIn("any release target with an activation scope", skill)
        self.assertIn("api / backend", skill)
        self.assertIn("android", skill)
        self.assertIn("macos", skill)
        self.assertIn("windows", skill)
        self.assertIn("including hybrids", skill)
        self.assertIn('check_activation.py" --activation', skill)
        self.assertIn("--architecture <staged architecture.md>", skill)
        self.assertIn("never falls back to a bundled default", skill)
        self.assertIn("creates it only when absent", contract)
        self.assertIn("never stages, overwrites, archives, resets", contract)
        self.assertIn("Exclude it from the superseded-document inventory", lifecycle)

    def test_implementation_plan_handoff_signals_are_not_a_harness_graph(self) -> None:
        contract = self.read("references/output-contract.md")

        self.assertIn("## Harness Handoff Signals", contract)
        self.assertIn("not a canonical Harness PLAN or RUN graph", contract)

    def test_lifecycle_keeps_the_package_in_docs_product_not_flat_docs(self) -> None:
        lifecycle = self.read("references/artifact-lifecycle.md")

        self.assertIn(
            "Never publish PRD artifacts at the repository root or flat in `docs/` by default.",
            lifecycle,
        )
        self.assertIn("They belong in `docs/product/`.", lifecycle)
        self.assertIn(
            "in `docs/product/`, the repository root, or a legacy flat `docs/` directory",
            lifecycle,
        )
        self.assertNotIn("or under `docs/product/` by default", lifecycle)
        self.assertNotIn("or a legacy `docs/product/` directory", lifecycle)

    def test_closed_questions_batch_without_dropping_decisions(self) -> None:
        interview = self.read("references/interview-guide.md")
        skill = self.read(STAGE)

        self.assertNotIn("Codex CLI caps", skill)
        self.assertNotIn("drop order", interview)
        self.assertIn("minimum number of calls", interview)
        self.assertIn("do not drop an applicable decision", skill)
        rows = re.findall(
            r"^\| (AQ-[A-Z-]+) \| (independent|final) \| ([^|]+?) \|$",
            interview,
            re.MULTILINE,
        )
        expected = [
            ("AQ-ARCHETYPE", "independent", "Product archetype"),
            ("AQ-VALIDATION-DEPTH", "independent", "Validation depth"),
            ("AQ-DEPLOYMENT-PLATFORM", "final", "Deployment platform"),
            ("AQ-MOBILE-TARGETS", "final", "Mobile target operating systems"),
            ("AQ-DESKTOP-TARGETS", "final", "Desktop target operating systems"),
            ("AQ-CLIENT-STRATEGY", "final", "Native versus cross-platform client strategy"),
            ("AQ-BROWSER-TARGETS", "final", "Browser-extension targets"),
            ("AQ-MONETIZATION-MODEL", "final", "Monetization model"),
            ("AQ-PARTNER-CHANNEL", "final", "Partner channel"),
            ("AQ-DATABASE-CATEGORY", "final", "Database category"),
            ("AQ-AUTH-STRATEGY", "final", "Auth strategy"),
            ("AQ-STACK-DECISION-MODE", "final", "How the owner wants unresolved technology choices decided"),
        ]
        self.assertEqual(expected, rows)

        marked_bullets = [
            line
            for line in interview.splitlines()
            if re.match(r"^\s+- .*\(AskUserQuestion(?:,|\))", line)
        ]
        bullet_ids = [
            match.group(1)
            for line in marked_bullets
            if (match := re.match(r"^\s+- \[(AQ-[A-Z-]+)\]", line))
        ]
        inventory_ids = [row[0] for row in rows]
        self.assertEqual(len(inventory_ids), len(set(inventory_ids)))
        self.assertEqual(len(inventory_ids), len(marked_bullets))
        self.assertCountEqual(inventory_ids, bullet_ids)
        for question_id in inventory_ids:
            self.assertEqual(1, bullet_ids.count(question_id))

        for per_call_limit in range(1, 6):
            flattened: list[str] = []
            for phase in ("independent", "final"):
                phase_ids = [row[0] for row in rows if row[1] == phase]
                batches = [
                    phase_ids[start : start + per_call_limit]
                    for start in range(0, len(phase_ids), per_call_limit)
                ]
                flattened.extend(item for batch in batches for item in batch)
            self.assertEqual(inventory_ids, flattened)

    def test_browser_extension_is_a_supported_archetype(self) -> None:
        skill = self.read(STAGE)
        interview = self.read("references/interview-guide.md")
        architecture = self.read("references/architecture-playbook.md")
        frontend = self.read("references/frontend-stack-selection.md")

        self.assertIn(
            "web app, mobile app, desktop app, browser extension, internal tool",
            skill,
        )
        self.assertIn(
            "browser extension, internal tool, automation or agent workflow, API, or a hybrid? (AskUserQuestion)",
            interview,
        )
        self.assertIn(
            "[AQ-BROWSER-TARGETS] If the answer is browser extension", interview
        )
        self.assertIn(
            "A browser extension skips the hosted deployment-platform question",
            interview,
        )
        self.assertIn("## Browser Extension Pattern", architecture)
        for marker in (
            "Manifest V3",
            "service worker",
            "Content scripts",
            "extension pages",
            "Permissions model",
            "chrome.runtime",
            "Chrome Web Store",
        ):
            self.assertIn(marker, architecture)
        self.assertIn("## Browser Extension Stacks", frontend)
        for marker in ("CRXJS", "WXT", "UI framework: optional", "Manifest V3"):
            self.assertIn(marker, frontend)

    def test_market_research_findings_can_land_in_stack_decisions(self) -> None:
        skill = self.read(STAGE)
        guide = self.read("references/market-research-guide.md")

        self.assertIn(
            "Evidence that strengthens or contradicts a named technology choice",
            guide,
        )
        self.assertIn("The applicable `stack-decisions.md` technology table", guide)
        self.assertIn(
            "| An alternative the market evidence speaks to | "
            "`stack-decisions.md` shared `Alternatives Considered` table",
            guide,
        )
        self.assertIn(
            "including evidence that strengthens or contradicts a "
            "`stack-decisions.md` layer row or alternative",
            skill,
        )

    def test_architecture_contract_has_frontend_and_backend_sections(self) -> None:
        contract = self.read("references/output-contract.md")

        component = contract.index("## Component Architecture")
        frontend = contract.index("## Frontend Architecture")
        backend = contract.index("## Backend Architecture")
        data_model = contract.index("## Data Model")
        self.assertLess(component, frontend)
        self.assertLess(frontend, backend)
        self.assertLess(backend, data_model)

        architecture_block = contract[component:data_model]
        for marker in (
            "surface composition",
            "state and data-fetch approach",
            "routing",
            "build/bundling",
            "`stack-decisions.md`",
        ):
            self.assertIn(marker, architecture_block)
        self.assertIn("Omit this section only when the product ships no frontend", architecture_block)
        self.assertIn("service boundaries, API style, data access, and background jobs", architecture_block)
        self.assertIn("one line stating that there is no backend and why", architecture_block)

    def test_unapproved_stack_rows_gate_product_approval_and_delivery(self) -> None:
        skill = self.read(STAGE)
        contract = self.read("references/output-contract.md")

        self.assertIn(
            "only `Required`, `Selected`, or `Approved` executable stack rows",
            skill,
        )
        self.assertIn(
            "`Recommended`, `Provisional`, or a blocked checkpoint remains staged and cannot enter Harness",
            skill,
        )
        self.assertIn("or rely on an explicit prior delegation", contract)
        self.assertIn(
            "Only `Required`, `Selected`, and `Approved` are executable", contract
        )
        self.assertIn(
            "`Recommended` and `Provisional` rows keep this checkpoint blocked", contract
        )

    def test_design_time_ui_contract_gap_is_one_owner_approved_delta(self) -> None:
        refinement = self.read("references/prd-refinement.md")
        contract = self.read("references/output-contract.md")
        skill = self.read(STAGE)
        lifecycle = self.read("references/artifact-lifecycle.md")
        self.assertIn("as a contract delta", contract)
        self.assertIn("full package revision and Product Definition Approval", contract)
        for phrase in (
            "Update the Chinese copy and compare only the changed sections",
            "Recheck only the affected scope",
            "One owner decision approves the delta and its in-place write",
            "new package revision and digest",
            "Do not stage.",
        ):
            self.assertIn(phrase, refinement)
        self.assertIn("A bounded enhancement and a design-time contract delta", skill)
        self.assertIn("Bounded enhancement (no stack change): edit the published files in place; Git is the archive", lifecycle)

    def test_output_contract_templates_are_read_per_artifact(self) -> None:
        skill = self.read(STAGE)
        contract = self.read("references/output-contract.md")
        self.assertIn("read each artifact's section of it when drafting that artifact", skill)
        self.assertIn("Run the Quality Checklist section of `references/output-contract.md`, without rereading", skill)
        for heading in ("## How To Read This Package", "## Quality Checklist"):
            self.assertIn(heading, contract)

    def test_one_author_self_review_carries_both_journey_perspectives(self) -> None:
        skill = self.read(STAGE)
        refinement = self.read("references/prd-refinement.md")
        self.assertIn("Do not review this candidate separately here", skill)
        self.assertIn("This is the only author pass over the candidate", skill)
        self.assertIn("No separate first-candidate review runs before it", refinement)
        self.assertNotIn("review this first candidate", skill)

    def test_full_link_inventory_runs_only_at_the_two_owner_gates(self) -> None:
        presentation = " ".join(self.read("references/review-presentation.md").split())
        skill = self.read(STAGE)
        self.assertIn("at the two owner gates: Product Definition Approval and Visual Approval", presentation)
        self.assertIn("do not repeat the inventory", presentation)
        self.assertNotIn("final handoff", presentation)
        self.assertIn("do not repeat its full inventory here", skill)

    def test_full_hifi_copy_review_does_not_require_a_circular_prd_rewrite(self) -> None:
        contract = self.read("references/output-contract.md")
        lifecycle = self.read("references/artifact-lifecycle.md")

        for content in (contract, lifecycle):
            self.assertIn("full HiFi approval", content)
        self.assertIn(
            "A full HiFi approval may advance a PRD `draft` responsibility "
            "to approved exact copy without rewriting the PRD status",
            contract,
        )
        self.assertIn(
            "full HiFi approval confirms the embedded copy contract "
            "(or validated wireframe copy in a pinned legacy package) without a circular PRD rewrite",
            lifecycle,
        )
        self.assertIn(
            "`revision_requested` or `blocked` PRD copy stops active UI design work",
            lifecycle,
        )
        self.assertNotIn(
            "any applicable Wireframe Approval, passing checkers",
            lifecycle,
        )

    def test_stack_checkpoint_separates_and_approves_implementation_layers(self) -> None:
        skill = self.read(STAGE)
        contract = self.read("references/output-contract.md")
        frontend = self.read("references/frontend-stack-selection.md")

        for marker in (
            "<!-- stack-decision-checkpoint:start -->",
            "<!-- stack-decision-checkpoint:end -->",
            "## Stack Decision Checkpoint",
            "### Coherent Options Presented",
            "| Option ID | Area | Complete bundle | Best fit | Tradeoffs / ownership | Disposition |",
            "| Language |",
            "| Package manager |",
            "| Component foundation |",
            "| Styling approach |",
            "## AI and Automation Technology Decision",
        ):
            self.assertIn(marker, contract)
        self.assertIn("React and shadcn/ui are not peers", frontend)
        self.assertIn("headless primitives (Base UI, Radix Primitives)", frontend)
        self.assertIn("Radix Themes is a separate styled library", frontend)
        self.assertIn("two or three coherent stack bundles", frontend)
        self.assertIn("Mark accepted new choices `Approved`", frontend)
        self.assertIn("`Recommended` or `Provisional` blocks", skill)

    def test_data_trust_ai_metrics_and_open_questions_are_owner_decisions(self) -> None:
        skill = self.read(STAGE)
        contract = self.read("references/output-contract.md")
        interview = self.read("references/interview-guide.md")

        for marker in (
            "Data and Trust Gate:",
            "AI and Automation Gate:",
            "| Metric | Definition | Baseline | Target / guardrail | Stretch | Measurement window | Source / method | Owner |",
            "| Question | Why it matters | Owner | Decision deadline | Blocks approval | Status / resolution |",
            "## Data and Trust Architecture",
            "## AI and Automation Architecture",
        ):
            self.assertIn(marker, contract)
        self.assertIn("Which data is sensitive", interview)
        self.assertIn("For AI/automation", interview)
        self.assertIn("Security Requirements Gate and Security scope", skill)

    def test_mobile_destinations_are_separate_from_client_strategy(self) -> None:
        interview = self.read("references/interview-guide.md")
        mobile = self.read("references/mobile-stack-selection.md")

        for question_id in (
            "AQ-MOBILE-TARGETS",
            "AQ-DESKTOP-TARGETS",
            "AQ-CLIENT-STRATEGY",
            "AQ-BROWSER-TARGETS",
        ):
            self.assertIn(question_id, interview)
        self.assertIn("This decides destinations, not framework", interview)
        self.assertIn("Target operating systems", mobile)
        self.assertIn("Target operating systems, code-sharing strategy", mobile)


if __name__ == "__main__":
    unittest.main()
