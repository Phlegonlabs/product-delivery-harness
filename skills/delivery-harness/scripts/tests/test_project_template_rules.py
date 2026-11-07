"""Seeded project rules must agree with the canonical Harness contracts."""

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SKILL_ROOT.parents[1]
GOVERNANCE = SKILL_ROOT / "references/governance"


def read(relative_path: str) -> str:
    return (SKILL_ROOT / relative_path).read_text(encoding="utf-8")


class ProjectTemplateRuleTests(unittest.TestCase):
    def read_owner(self, name: str) -> str:
        return (GOVERNANCE / name).read_text(encoding="utf-8")

    def section(self, text: str, heading: str) -> str:
        self.assertIn(heading, text)
        return text.split(heading, 1)[1].split("\n## ", 1)[0]

    def test_routine_maintenance_is_limited_to_none_or_style_ui_impact(self) -> None:
        # review-workflow.md accepts a maintenance record only with UI impact
        # none or style; structural changes keep their design gates.
        template = read("assets/templates/PROJECT_AGENTS.template.md")
        route = "delivery-harness/references/governance/product-contracts.md#consumer-keep-product-contracts-current"
        self.assertIn(route, template)
        owner = self.section(
            self.read_owner("product-contracts.md"),
            "## Consumer Keep Product Contracts Current",
        )
        self.assertIn("Routine maintenance with UI impact `none` or `style`", owner)
        self.assertIn("A structural impact (`structure` or `both`) follows affected design gates", owner)
        self.assertNotIn("Routine maintenance updates the actual product", template)

        owner_route = "governance/product-contracts.md#consumer-keep-product-contracts-current)"
        self.assertIn("references/" + owner_route, read("SKILL.md"))
        self.assertIn(owner_route, read("references/design-input-updates.md"))
        self.assertIn("An already frozen managed RUN keeps its pinned contract", owner)

        contract = read("references/ui-implementation-contract.md")
        self.assertIn("Routine maintenance is valid only with UI impact `none` or `style`", contract)
        self.assertIn("In routine maintenance, which allows only `none` or `style`", contract)

        agents = REPO_ROOT / "AGENTS.md"
        if agents.is_file() and (REPO_ROOT / "install.sh").is_file():
            root = agents.read_text(encoding="utf-8")
            self.assertIn(
                "skills/delivery-harness/references/governance/product-contracts.md#source-keep-product-contracts-current",
                root,
            )
            source_owner = self.section(
                self.read_owner("product-contracts.md"),
                "## Source Keep Product Contracts Current",
            )
            self.assertIn("(#consumer-keep-product-contracts-current)", source_owner)

    def test_managed_default_branch_must_be_main(self) -> None:
        # archive_run.py and the promotion contract bind only `main` refs, so
        # the template states that as a precondition instead of asking agents
        # to resolve an arbitrary default branch name.
        template = read("assets/templates/PROJECT_AGENTS.template.md")
        route = "delivery-harness/references/governance/managed-delivery.md#git-safety"
        self.assertIn(route, template)
        git_safety = self.section(self.read_owner("managed-delivery.md"), "## Git Safety")
        self.assertIn("Managed Harness requires the default branch to be named `main`", git_safety)
        self.assertIn("If it differs, stop before managed work and ask the owner.", git_safety)
        self.assertNotIn("never assume its name", template)
        self.assertNotIn("real default branch", template)

    def test_documents_template_names_the_current_epic(self) -> None:
        # Entry reads the Handoff block of one Epic, so the index names it.
        template = read("assets/templates/DOCUMENTS.template.md")
        self.assertEqual(1, template.count("\nCurrent Epic: [EPIC-<id>](epics/EPIC-<id>.md)\n"))
        self.assertNotRegex(template, r"\| `?docs/epics/EPIC-")
        entry = self.section(self.read_owner("task-and-handoff.md"), "## Project Entry And Current Work")
        self.assertIn("The current Epic is the one the `Current Epic:` line in `docs/DOCUMENTS.md` names.", entry)
        self.assertIn("When the task selects or creates a different Epic, rewrite the `Current Epic:` line.", entry)
        card = read("references/stages/stage-cards.md").split("## Card 1", 1)[1].split("## Card 2", 1)[0]
        self.assertIn("the Epic the `Current Epic:` line in `docs/DOCUMENTS.md` names", card)

    def test_epic_status_lives_only_on_the_epic(self) -> None:
        bounded = read("references/bounded-enhancement.md")
        self.assertIn("Its status lives only on its own `Status:` line", bounded)
        self.assertNotIn("indexed with its status", bounded)
        self.assertNotIn("indexed in `docs/DOCUMENTS.md`", self.read_owner("task-and-handoff.md"))
        index = REPO_ROOT / "docs/DOCUMENTS.md"
        if index.is_file() and (REPO_ROOT / "install.sh").is_file():
            text = index.read_text(encoding="utf-8")
            self.assertNotRegex(text, r"\| `docs/epics/EPIC-")
            target = re.search(r"^Current Epic: \[[^]]+\]\(([^)]+)\)$", text, re.MULTILINE)
            self.assertIsNotNone(target)
            self.assertTrue((index.parent / target.group(1)).is_file())

    def test_branch_promotion_record_carries_landing_fields(self) -> None:
        # Condition 7 lets a tree-equal server SHA S land, so the record names
        # base, protection, authorization, mechanism, S and its evidence origin.
        block = self.section(read("assets/templates/DEPLOYMENT.template.md"), "## Branch Promotion")
        labels = re.findall(r"^- ([^:]+):", block, re.MULTILINE)
        self.assertEqual(
            [
                "Delivery kind", "Main protection readback", "Run branch", "Frozen base SHA",
                "Candidate SHA", "Candidate branch pushed and read back",
                "Preview fixed deployment URL / ID", "Candidate environment verification",
                "Promotion authorization", "Main before", "Candidate ancestry from frozen base",
                "Mechanism", "Main after (S), read back", "Main exact-SHA result",
                "Inherited evidence origin", "Production deployed SHA and smoke",
            ],
            labels,
        )
        self.assertIn("<exact | tree_equal_S (candidate tree, main tree) | new_candidate | pending>", block)
        self.assertNotIn("PASS when remote main equals", block)
        self.assertIn("unavailable: HTTP status, message, owner decision ref", block)
        contract = read("references/branch-promotion-contract.md")
        self.assertIn("record `unavailable` with the HTTP status and message", contract)
        self.assertIn("landing waits for a recorded owner decision that names its scope", contract)

    def test_store_build_awaiting_availability_stays_pending(self) -> None:
        # Upload, submission or store approval is not availability.
        status = self.section(read("assets/templates/DEPLOYMENT.template.md"), "## Release Target Status")
        contract = read("references/deployment-contract.md")
        for text in (status, contract):
            self.assertIn("A store or signed-installer PASS needs install or download proof through the named channel", text)
            self.assertIn("uploaded, submitted or approved but not yet installable stays `pending`", text)
        self.assertNotIn("prove install/download or artifact/build identity", status + contract)
        promotion = read("references/branch-promotion-contract.md")
        self.assertIn("the promotion pass ends after the main-SHA artifact and submission read-back", promotion)
        self.assertIn("moves the row to PASS without a new promotion; a changed artifact is a new candidate", promotion)

    def test_wrangler_steps_name_the_vite_redirected_config(self) -> None:
        # vite build redirects later wrangler deploys to the built dev config.
        cloudflare = self.section(read("references/deployment-contract.md"), "## Platform: cloudflare")
        self.assertIn("`vite build` writes `.wrangler/deploy/config.json`", cloudflare)
        self.assertIn("not with a deploy-time `--env`", cloudflare)
        template = read("assets/templates/DEPLOYMENT.template.md")
        wrangler = template.split("#### Wrangler Workers", 1)[1].split("\n### ", 1)[0]
        self.assertIn("`CLOUDFLARE_ENV=<env> vite build`, never a deploy-time `--env`", wrangler)

    def test_release_log_keeps_one_row_per_release(self) -> None:
        # Current-state tables are overwritten each release; the log keeps history.
        log = self.section(read("assets/templates/DEPLOYMENT.template.md"), "## Release Log")
        header = next(line for line in log.splitlines() if line.startswith("| "))
        self.assertEqual(
            ["Date", "Release (slug or tag)", "Candidate / main SHA", "Units: deploy or build ID, status",
             "Migrations", "Rollback target", "Evidence"],
            [cell.strip() for cell in header.strip("|").split("|")],
        )
        contract = self.section(read("references/deployment-contract.md"), "## Recording The Model In A Repository")
        self.assertIn("append one Release Log row for the outgoing release, keyed by date and slug, never by SHA", contract)
        self.assertIn("`docs/release/<YYYYMMDD>-<slug>/` with a `MANIFEST.sha256`", contract)
        self.assertIn("| `docs/release/` | `docs/release/` | release (when required) |",
                      read("assets/templates/DOCUMENTS.template.md"))

    def test_gitattributes_contract_owns_byte_storage(self) -> None:
        # Every stage hashes raw bytes, so one contract owns how Git stores them.
        contract = read("references/gitattributes-contract.md")
        self.assertIn("`<root>/** -text -filter`", contract)
        for root in ("docs/product", "docs/design", "docs/verification", "docs/goal"):
            self.assertIn(f"`{root}`", contract)
        self.assertIn("`text eol=lf` and `text=auto` do not qualify", contract)
        self.assertIn("--check --require-resolved", contract)
        self.assertIn("so it needs owner approval", contract)
        self.assertIn(
            "| A task adds a hash-bound file class or root | `delivery-harness/references/gitattributes-contract.md` |",
            read("assets/templates/PROJECT_AGENTS.template.md"),
        )
        for owner in ("references/delivery-acceptance-contract.md", "references/eval-acceptance-contract.md"):
            text = read(owner)
            self.assertIn("(gitattributes-contract.md)", text)
            self.assertNotIn("docs/verification/evidence/** -text -filter", text)
        plan = read("assets/templates/HARNESS_PLAN.template.md")
        self.assertIn("if it fails, follow `references/gitattributes-contract.md`, put `.gitattributes`", plan)

    def test_gitattributes_template_satisfies_the_byte_check(self) -> None:
        template = read("assets/templates/PROJECT_GITATTRIBUTES.template")
        header, *rules = template.splitlines()
        self.assertEqual("# Hash-bound files stay byte-exact: delivery-harness/references/gitattributes-contract.md", header)
        self.assertEqual(
            {
                "docs/product/**": "-text -filter",
                "docs/design/**": "-text -filter",
                "docs/goal/**": "-text -filter",
                "docs/verification/**": "-text -filter",
                "docs/verification/evidence/**": "-text -filter -whitespace",
            },
            dict(rule.split(" ", 1) for rule in rules),
        )
        sys.path.insert(0, str(SKILL_ROOT / "scripts"))
        import configure_project_context as context

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            subprocess.run(["git", "init", "-q"], cwd=root, check=True)
            for name in ("docs/product/PRD.md", "docs/verification/evidence/run.txt"):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_bytes(b"line\r\n")
            subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
            (root / ".gitattributes").write_text(template, encoding="utf-8")
            report = context.byte_attribute_findings(root)
        self.assertTrue(report["checked"], report)
        self.assertEqual([], report["findings"])
        self.assertEqual([], report["gitattributes_lines"])

    def test_repo_restore_rule_uses_the_installer(self) -> None:
        # The installers have no restore mode, and manual moves are banned, so
        # a bad install is replaced by installing the previous release.
        agents = REPO_ROOT / "AGENTS.md"
        if not (agents.is_file() and (REPO_ROOT / "install.sh").is_file()):
            self.skipTest("no source repository checkout")
        root = agents.read_text(encoding="utf-8")
        self.assertIn(
            "skills/delivery-harness/references/governance/source-maintenance.md#update-local-skills",
            root,
        )
        text = self.read_owner("source-maintenance.md")
        # Rollback is installer-owned: a bad copy is backed up by the previous
        # release's installer, never restored by a manual move or deleted.
        self.assertIn("A failed install rolls itself back.", text)
        self.assertIn(
            "If post-install verification fails, rerun the installer from the "
            "previous release tag so it backs up the bad copy first.",
            text,
        )
        self.assertIn("never overwrite or delete prior copies or backups.", text)
        self.assertNotIn("Restore the backup if verification fails", text)
        self.assertIn("`./install.sh` (in Git Bash on Windows)", text)
        self.assertNotIn("install.ps1", text)
        self.assertIn(
            "CI on the candidate SHA is that run; a local full run happens only when CI is unavailable.",
            text,
        )

    def test_repo_instructions_cover_every_shared_template_section(self) -> None:
        # The handoff audit compares repo AGENTS.md/CLAUDE.md with the seeded
        # templates. Each template section is present or named as a
        # deliberate source-repo omission, so the audit has a clear answer.
        agents = REPO_ROOT / "AGENTS.md"
        if not (agents.is_file() and (REPO_ROOT / "install.sh").is_file()):
            self.skipTest("no source repository checkout")
        root_agents = agents.read_text(encoding="utf-8")
        omitted = root_agents.split("This source repository intentionally omits", 1)[1]
        omitted = omitted.split("\n", 1)[0]
        owners = {
            name: self.read_owner(name)
            for name in (
                "task-and-handoff.md", "development-rules.md",
                "product-contracts.md", "source-maintenance.md",
                "managed-delivery.md",
            )
        }
        owner_headings = {
            heading
            for text in owners.values()
            for heading in re.findall(r"^## (.+)$", text, re.MULTILINE)
        }
        template_only_headings = {
            "Skill Activation", "Runtime Boundary", "Mandatory Governance Routes", "Deployment",
            "Behavior Specs",
        }
        template = read("assets/templates/PROJECT_AGENTS.template.md")
        for heading in re.findall(r"^## (.+)$", template, re.MULTILINE):
            with self.subTest(heading=heading):
                self.assertTrue(
                    heading in owner_headings or heading in template_only_headings or heading in omitted,
                    heading,
                )
        self.assertIn("task-and-handoff.md#project-entry-and-current-work", root_agents)
        self.assertIn("Select the record before implementation", owners["task-and-handoff.md"])

        root_claude = (REPO_ROOT / "CLAUDE.md").read_text(encoding="utf-8")
        claude_template = read("assets/templates/PROJECT_CLAUDE.template.md")
        for line in claude_template.splitlines():
            if line.startswith("- "):
                with self.subTest(line=line[:60]):
                    self.assertIn(line, root_claude)


if __name__ == "__main__":
    unittest.main()
