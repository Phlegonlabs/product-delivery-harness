import subprocess
import sys
import tempfile
import unittest
import hashlib
import json
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

import configure_project_context  # noqa: E402
from configure_project_context import _level_two_sections, configure_context  # noqa: E402


SCRIPT = SCRIPTS_DIR / "configure_project_context.py"


class ConfigureProjectContextTests(unittest.TestCase):
    def test_seed_routes_installed_references_and_direct_commits(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            configure_context(root)
            self.assertFalse((root / "skills").exists())
            text = (root / "AGENTS.md").read_text(encoding="utf-8")
            self.assertIn("observed installed delivery-harness skill root", text)
            self.assertNotIn("under `skills/` in this source repository", text)
            self.assertIn(
                "delivery-harness/references/governance/managed-delivery.md#git-safety",
                text,
            )
            owner_root = SCRIPTS_DIR.parent / "references" / "governance"
            git_rules = (owner_root / "managed-delivery.md").read_text(
                encoding="utf-8"
            ).split("## Git Safety", 1)[1].split("\n## ", 1)[0]
            self.assertIn("references/commit-convention.md", git_rules)
            self.assertIn("Direct tasks use `<type>(<scope>): <imperative summary>`", git_rules)
            self.assertIn("trailers apply only inside managed runs", git_rules)

    def test_product_definition_pending_bindings_check_is_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            configure_context(root)
            agents = root / "AGENTS.md"
            # Product-owned deployment context is resolved; only future bindings remain.
            import re
            agents.write_text(re.sub(r"<fill>|<databases[^>]*>", "fixture", agents.read_text(encoding="utf-8")), encoding="utf-8")
            before = (root / "AGENTS.md").read_bytes()
            result = subprocess.run([sys.executable, str(SCRIPT), "--root", str(root),
                                     "--check", "--require-resolved", "--stage", "product-definition"],
                                    capture_output=True, text=True, encoding="utf-8", cwd=SCRIPTS_DIR.parents[2])
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual(before, (root / "AGENTS.md").read_bytes())
            strict = subprocess.run([sys.executable, str(SCRIPT), "--root", str(root),
                                     "--check", "--require-resolved"], capture_output=True)
            self.assertEqual(1, strict.returncode)

    def make_templates(self, root: Path) -> tuple[Path, Path]:
        agents_template = root / "agents-template.md"
        claude_template = root / "claude-template.md"
        agents_template.write_text(
            "# Shared Rules\n\n- Verify changes.\n", encoding="utf-8"
        )
        claude_template.write_text(
            "# Claude Rules\n\n@AGENTS.md\n\n- Use Claude workers.\n",
            encoding="utf-8",
        )
        return agents_template, claude_template

    def make_merge_templates(self, root: Path) -> tuple[Path, Path]:
        agents_template = root / "merge-agents-template.md"
        claude_template = root / "merge-claude-template.md"
        agents_template.write_bytes(
            b"# Shared Rules\n\n"
            b"## New Shared Rule\n\n- Add this guidance.\n\n"
            b"## Owner Rule\n\n- Template wording.\n"
        )
        claude_template.write_bytes(
            b"# Claude Rules\n\n@AGENTS.md\n\n- Use Claude workers.\n"
        )
        return agents_template, claude_template

    def write_merge_plan(
        self,
        root: Path,
        agents_hash: str,
        template_hash: str,
        *,
        additions: list[str],
        acknowledgements: list[str],
    ) -> Path:
        path = root / "context-merge-plan.json"
        path.write_text(
            json.dumps(
                {
                    "schema": "pdh-context-merge/1",
                    "reviewed": True,
                    "agents_sha256": agents_hash,
                    "template_sha256": template_hash,
                    "add_sections": additions,
                    "acknowledged_divergences": acknowledgements,
                }
            ),
            encoding="utf-8",
        )
        return path

    def test_merge_requires_reviewed_plan_and_appends_selected_sections_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agents_template, claude_template = self.make_merge_templates(root)
            agents = root / "AGENTS.md"
            original = "# Owner Rules\n\n## Owner Rule\n\n- Keep owner wording.\n"
            agents.write_text(original, encoding="utf-8")
            override = root / "AGENTS.override.md"
            override_bytes = b"owner override\n"
            override.write_bytes(override_bytes)

            proposal = configure_context(
                root, agents_template, claude_template, merge_agents=True
            )
            self.assertEqual(original, agents.read_text(encoding="utf-8"))
            agents_hash = hashlib.sha256(agents.read_bytes()).hexdigest()
            template_hash = hashlib.sha256(agents_template.read_bytes()).hexdigest()
            plan = self.write_merge_plan(
                root,
                agents_hash,
                template_hash,
                additions=["New Shared Rule"],
                acknowledgements=["Owner Rule"],
            )
            plan_check = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--root",
                    str(root),
                    "--check",
                    "--merge-agents",
                    "--merge-plan",
                    str(plan),
                    "--agents-template",
                    str(agents_template),
                    "--claude-template",
                    str(claude_template),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=SCRIPTS_DIR,
                timeout=10,
            )
            self.assertEqual(0, plan_check.returncode, plan_check.stdout + plan_check.stderr)
            self.assertEqual(original, agents.read_text(encoding="utf-8"))
            applied = configure_context(
                root,
                agents_template,
                claude_template,
                merge_agents=True,
                merge_plan=plan,
            )
            merged_text = agents.read_text(encoding="utf-8")
            followup = configure_context(
                root, agents_template, claude_template, merge_agents=True
            )

            self.assertEqual(["CLAUDE.md"], proposal["created"])
            self.assertEqual("proposal_required", proposal["agents_merge"]["status"])
            self.assertTrue(proposal["agents_merge"]["semantic_review_required"])
            self.assertEqual(
                ["New Shared Rule"], proposal["agents_merge"]["proposed_additions"]
            )
            self.assertEqual(
                "Owner Rule",
                proposal["agents_merge"]["unresolved_divergences"][0]["heading"],
            )
            self.assertEqual("applied", applied["agents_merge"]["status"])
            self.assertEqual(
                ["New Shared Rule"], applied["agents_merge"]["applied_additions"]
            )
            self.assertTrue(merged_text.startswith(original))
            self.assertIn("## New Shared Rule\n\n- Add this guidance.\n", merged_text)
            self.assertNotIn("- Template wording.", merged_text)
            self.assertEqual(1, merged_text.count("## Owner Rule"))
            self.assertIn("- Keep owner wording.", merged_text)
            self.assertEqual(override_bytes, override.read_bytes())
            self.assertEqual([], followup["created"])
            self.assertEqual([], followup["agents_merge"]["proposed_additions"])
            self.assertEqual(merged_text, agents.read_text(encoding="utf-8"))
            with self.assertRaises(ValueError):
                configure_context(
                    root,
                    agents_template,
                    claude_template,
                    merge_agents=True,
                    merge_plan=plan,
                )

    def test_race_after_the_final_owner_observation_is_never_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agents_template, claude_template = self.make_merge_templates(root)
            agents = root / "AGENTS.md"
            original = b"# Owner Rules\n\n## Owner Rule\n\n- Keep owner wording.\n"
            agents.write_bytes(original)
            agents_hash = hashlib.sha256(original).hexdigest()
            template_hash = hashlib.sha256(agents_template.read_bytes()).hexdigest()
            plan = self.write_merge_plan(
                root,
                agents_hash,
                template_hash,
                additions=["New Shared Rule"],
                acknowledgements=["Owner Rule"],
            )
            real_write = configure_project_context.os.write
            owner_race_complete = False

            def owner_appends_before_tool_write(descriptor: int, data: bytes) -> int:
                nonlocal owner_race_complete
                if not owner_race_complete:
                    with agents.open("ab") as handle:
                        handle.write(b"- owner added this during the race\n")
                    owner_race_complete = True
                return real_write(descriptor, data)

            configure_project_context.os.write = owner_appends_before_tool_write
            try:
                with self.assertRaisesRegex(ValueError, "context append could not be verified"):
                    configure_context(
                        root,
                        agents_template,
                        claude_template,
                        merge_agents=True,
                        merge_plan=plan,
                    )
            finally:
                configure_project_context.os.write = real_write

            merged = agents.read_bytes()
            self.assertTrue(merged.startswith(original))
            self.assertIn(b"- owner added this during the race\n", merged)
            self.assertIn(b"## New Shared Rule\n", merged)

    def test_same_inode_change_before_open_is_rejected_without_appending(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "AGENTS.md"
            original = b"# Owner rules\n"
            external = b"- owner added this before open\n"
            block = b"\n## New Shared Rule\n"
            path.write_bytes(original)
            real_check = configure_project_context._file_has_exact_bytes

            def owner_appends_after_check(target: Path, expected: bytes) -> bool:
                matches = real_check(target, expected)
                with target.open("ab") as handle:
                    handle.write(external)
                return matches

            configure_project_context._file_has_exact_bytes = owner_appends_after_check
            try:
                with self.assertRaisesRegex(ValueError, "context file changed"):
                    configure_project_context._append_merge(path, original, block)
            finally:
                configure_project_context._file_has_exact_bytes = real_check
            self.assertEqual(original + external, path.read_bytes())

    def test_same_size_owner_edit_after_observation_is_not_appended(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "AGENTS.md"
            original, external = b"# Owner rules\n", b"# Other rules\n"
            self.assertEqual(len(original), len(external))
            path.write_bytes(original)
            real_check = configure_project_context._file_has_exact_bytes

            def owner_edits_after_check(target: Path, expected: bytes) -> bool:
                matches = real_check(target, expected)
                target.write_bytes(external)
                return matches

            configure_project_context._file_has_exact_bytes = owner_edits_after_check
            try:
                with self.assertRaisesRegex(ValueError, "context file changed"):
                    configure_project_context._append_merge(path, original, b"\n## New Shared Rule\n")
            finally:
                configure_project_context._file_has_exact_bytes = real_check
            self.assertEqual(external, path.read_bytes())

    def test_second_template_upgrade_appends_under_the_existing_heading(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agents_template, claude_template = self.make_merge_templates(root)
            agents = root / "AGENTS.md"
            original = "# Owner Rules\n\n## Owner Rule\n\n- Keep owner wording.\n"
            agents.write_text(original, encoding="utf-8")

            configure_context(
                root, agents_template, claude_template, merge_agents=True
            )
            first_plan = self.write_merge_plan(
                root,
                hashlib.sha256(agents.read_bytes()).hexdigest(),
                hashlib.sha256(agents_template.read_bytes()).hexdigest(),
                additions=["New Shared Rule"],
                acknowledgements=["Owner Rule"],
            )
            configure_context(
                root,
                agents_template,
                claude_template,
                merge_agents=True,
                merge_plan=first_plan,
            )

            agents_template.write_bytes(
                b"# Shared Rules\n\n"
                b"## New Shared Rule\n\n- Add this guidance.\n\n"
                b"## Second Shared Rule\n\n- Add later guidance.\n\n"
                b"## Owner Rule\n\n- Template wording.\n"
            )
            upgrade_proposal = configure_context(
                root, agents_template, claude_template, merge_agents=True
            )
            second_plan = self.write_merge_plan(
                root,
                hashlib.sha256(agents.read_bytes()).hexdigest(),
                hashlib.sha256(agents_template.read_bytes()).hexdigest(),
                additions=["Second Shared Rule"],
                acknowledgements=[
                    "Owner Rule",
                    "# Project Delivery Harness Shared Guidance",
                ],
            )
            upgrade = configure_context(
                root,
                agents_template,
                claude_template,
                merge_agents=True,
                merge_plan=second_plan,
            )
            upgraded_text = agents.read_text(encoding="utf-8")

            self.assertEqual("proposal_required", upgrade_proposal["agents_merge"]["status"])
            self.assertEqual(
                ["Second Shared Rule"],
                upgrade_proposal["agents_merge"]["proposed_additions"],
            )
            self.assertIn(
                {"heading": "# Project Delivery Harness Shared Guidance",
                 "diff": ["+## Second Shared Rule"]},
                upgrade_proposal["agents_merge"]["unresolved_divergences"],
            )
            self.assertEqual("applied", upgrade["agents_merge"]["status"])
            self.assertEqual(
                ["Second Shared Rule"], upgrade["agents_merge"]["applied_additions"]
            )
            self.assertTrue(upgraded_text.startswith(original))
            self.assertEqual(1, upgraded_text.count("# Project Delivery Harness Shared Guidance"))
            self.assertIn("## New Shared Rule\n\n- Add this guidance.\n", upgraded_text)
            self.assertIn("## Second Shared Rule\n\n- Add later guidance.\n", upgraded_text)

    def test_merge_plan_without_merge_agent_reports_usage_not_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--root",
                    str(root),
                    "--merge-plan",
                    str(root / "unused-plan.json"),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=SCRIPTS_DIR,
                timeout=10,
            )

            self.assertEqual(2, result.returncode)
            self.assertIn("--merge-plan requires --merge-agents", result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse((root / "AGENTS.md").exists())

    def test_merge_agents_without_plan_is_idempotent_for_created_or_unchanged_files(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agents_template = root / "idempotent-agents-template.md"
            claude_template = root / "idempotent-claude-template.md"
            agents_template.write_bytes(b"# Shared Rules\n\n- Verify changes.\n")
            claude_template.write_bytes(b"# Claude Rules\n\n@AGENTS.md\n")
            base_arguments = [
                sys.executable,
                str(SCRIPT),
                "--root",
                str(root),
                "--merge-agents",
                "--agents-template",
                str(agents_template),
                "--claude-template",
                str(claude_template),
            ]

            first = subprocess.run(
                base_arguments,
                capture_output=True,
                text=True,
                cwd=SCRIPTS_DIR,
                timeout=10,
            )
            first_result = json.loads(first.stdout)
            first_agents = agents_template.read_bytes()
            first_claude = claude_template.read_bytes()
            second = subprocess.run(
                base_arguments,
                capture_output=True,
                text=True,
                cwd=SCRIPTS_DIR,
                timeout=10,
            )
            second_result = json.loads(second.stdout)

            self.assertEqual(0, first.returncode, first.stdout + first.stderr)
            self.assertEqual(["AGENTS.md", "CLAUDE.md"], first_result["created"])
            self.assertEqual("not_requested", first_result["agents_merge"]["status"])
            self.assertEqual(first_agents, (root / "AGENTS.md").read_bytes())
            self.assertEqual(first_claude, (root / "CLAUDE.md").read_bytes())
            self.assertEqual(0, second.returncode, second.stdout + second.stderr)
            self.assertEqual([], second_result["created"])
            self.assertEqual("unchanged", second_result["agents_merge"]["status"])
            self.assertEqual(first_agents, (root / "AGENTS.md").read_bytes())
            self.assertEqual(first_claude, (root / "CLAUDE.md").read_bytes())

    def test_duplicate_and_fenced_headings_do_not_drive_a_merge(self) -> None:
        text = (
            "# Owner Rules\n\n"
            "## Real Rule\n\n- Owner policy.\n\n"
            "```text\n"
            "## Fenced Rule\n\n- Not a heading.\n"
            "```\n\n"
            "## Real Rule\n\n- Duplicate owner policy.\n"
        )
        sections, duplicates = _level_two_sections(text)
        self.assertEqual({"Real Rule"}, set(sections))
        self.assertEqual(["Real Rule"], duplicates)
        self.assertNotIn("Fenced Rule", sections)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agents_template, claude_template = self.make_merge_templates(root)
            agents = root / "AGENTS.md"
            agents.write_text(text, encoding="utf-8")
            before = agents.read_bytes()
            result = configure_context(
                root, agents_template, claude_template, merge_agents=True
            )

            self.assertEqual("blocked", result["agents_merge"]["status"], result["agents_merge"])
            self.assertEqual([], result["agents_merge"]["proposed_additions"])
            self.assertTrue(result["agents_merge"]["parser_errors"])
            self.assertEqual(before, agents.read_bytes())

    def test_merge_check_is_read_only_and_reports_the_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agents_template, claude_template = self.make_merge_templates(root)
            agents = root / "AGENTS.md"
            agents.write_text("# Owner Rules\n", encoding="utf-8")
            before = agents.read_bytes()

            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--root",
                    str(root),
                    "--check",
                    "--merge-agents",
                    "--agents-template",
                    str(agents_template),
                    "--claude-template",
                    str(claude_template),
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=SCRIPTS_DIR,
                timeout=10,
            )

            self.assertEqual(1, result.returncode)
            self.assertIn('"New Shared Rule"', result.stdout)
            self.assertIn('"semantic_review_required": true', result.stdout)
            self.assertEqual(before, agents.read_bytes())
            self.assertFalse((root / "CLAUDE.md").exists())

    def test_both_missing_receive_distinct_host_templates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agents_template, claude_template = self.make_templates(root)

            result = configure_context(root, agents_template, claude_template)

            self.assertEqual(["AGENTS.md", "CLAUDE.md"], result["created"])
            self.assertEqual(agents_template.read_bytes(), (root / "AGENTS.md").read_bytes())
            self.assertEqual(claude_template.read_bytes(), (root / "CLAUDE.md").read_bytes())
            self.assertNotEqual(
                (root / "AGENTS.md").read_bytes(), (root / "CLAUDE.md").read_bytes()
            )

    def test_existing_agents_is_preserved_and_claude_uses_its_own_template(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agents_template, claude_template = self.make_templates(root)
            agents = root / "AGENTS.md"
            agents.write_text("# Existing Agents\n", encoding="utf-8")

            result = configure_context(root, agents_template, claude_template)

            self.assertEqual(["CLAUDE.md"], result["created"])
            self.assertEqual("# Existing Agents\n", agents.read_text(encoding="utf-8"))
            self.assertEqual(
                claude_template.read_bytes(), (root / "CLAUDE.md").read_bytes()
            )
            self.assertIn("@AGENTS.md", (root / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_existing_claude_is_preserved_and_agents_uses_its_own_template(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agents_template, claude_template = self.make_templates(root)
            claude = root / "CLAUDE.md"
            claude.write_text("# Existing Claude\n", encoding="utf-8")

            result = configure_context(root, agents_template, claude_template)

            self.assertEqual(["AGENTS.md"], result["created"])
            self.assertEqual("# Existing Claude\n", claude.read_text(encoding="utf-8"))
            self.assertEqual(
                agents_template.read_bytes(), (root / "AGENTS.md").read_bytes()
            )

    def test_existing_pair_is_never_changed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            agents_template, claude_template = self.make_templates(root)
            agents = root / "AGENTS.md"
            claude = root / "CLAUDE.md"
            agents.write_text("agents\n", encoding="utf-8")
            claude.write_text("claude\n", encoding="utf-8")

            result = configure_context(root, agents_template, claude_template)

            self.assertEqual([], result["created"])
            self.assertEqual("agents\n", agents.read_text(encoding="utf-8"))
            self.assertEqual("claude\n", claude.read_text(encoding="utf-8"))

    def test_check_mode_is_read_only_and_reports_missing_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", str(root), "--check"],
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
            )

            self.assertEqual(1, result.returncode)
            self.assertIn('"AGENTS.md"', result.stdout)
            self.assertIn('"CLAUDE.md"', result.stdout)
            self.assertFalse((root / "AGENTS.md").exists())
            self.assertFalse((root / "CLAUDE.md").exists())


class TemplateAuditTests(unittest.TestCase):
    """--check --merge-agents and --check --documents report only real drift."""

    def run_check(self, root: Path, *extra: str) -> tuple[int, dict]:
        before = {path: path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(root), "--check", *extra],
            capture_output=True, text=True, encoding="utf-8", timeout=60,
        )
        self.assertEqual(before, {path: path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()})
        return result.returncode, json.loads(result.stdout)

    def test_trailing_blank_lines_and_line_endings_are_not_divergence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template = root / "agents-template.md"
            template.write_bytes(b"# Shared\n\n## Owner Rule\n\n- Same wording.\n\n## Last Rule\n\n- Last.\n")
            (root / "AGENTS.md").write_bytes(
                b"# Owner\r\n\r\n## Owner Rule\r\n\r\n- Same wording.\r\n\r\n\r\n\r\n## Last Rule\r\n\r\n- Last.\r\n\r\n"
            )
            result = configure_context(root, template, template, merge_agents=True, dry_run=True)
        self.assertEqual("unchanged", result["agents_merge"]["status"])
        self.assertEqual([], result["agents_merge"]["unresolved_divergences"])

    def test_divergence_is_a_unified_diff_not_a_hash_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            template = root / "agents-template.md"
            template.write_bytes(b"# Shared\n\n## Owner Rule\n\n- Context line.\n- Template wording.\n")
            (root / "AGENTS.md").write_bytes(b"# Owner\n\n## Owner Rule\n\n- Context line.\n- Keep owner wording.\n")
            divergences = configure_context(
                root, template, template, merge_agents=True, dry_run=True
            )["agents_merge"]["unresolved_divergences"]
        self.assertEqual(["heading", "diff"], list(divergences[0]))
        self.assertEqual("Owner Rule", divergences[0]["heading"])
        diff = divergences[0]["diff"]
        self.assertEqual(["--- AGENTS.md ## Owner Rule", "+++ template ## Owner Rule"], diff[:2])
        self.assertEqual([" - Context line.", "-- Keep owner wording.", "+- Template wording."], diff[3:])

    def test_filled_skill_bindings_match_the_seed_but_other_cells_do_not(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            configure_context(root)
            agents = root / "AGENTS.md"
            seeded = agents.read_text(encoding="utf-8")
            filled = seeded.replace(
                "| ui_design | approved Product Definition → UI intake, directions, HiFi, approval | `pending` | `pending` |",
                "|ui_design|approved Product Definition → UI intake, directions, HiFi, approval|`ui-design-builder`|`" + "a" * 64 + "`|",
            )
            self.assertNotEqual(seeded, filled)
            agents.write_text(filled + "\n\n", encoding="utf-8")
            code, result = self.run_check(root, "--merge-agents")
            self.assertEqual(0, code, result["agents_merge"])
            self.assertEqual([], result["agents_merge"]["unresolved_divergences"])

            agents.write_text(filled.replace("directions, HiFi, approval", "directions only", 1), encoding="utf-8")
            code, result = self.run_check(root, "--merge-agents")
        self.assertEqual(1, code)
        [divergence] = result["agents_merge"]["unresolved_divergences"]
        self.assertEqual("Skill Bindings", divergence["heading"])
        self.assertIn("-| ui_design | approved Product Definition → UI intake, directions only | <skill> | <pin> |",
                      divergence["diff"])
        self.assertNotIn("a" * 64, "\n".join(divergence["diff"]))

    def test_documents_check_reports_template_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            configure_context(root)
            template = (SCRIPTS_DIR.parent / "assets/templates/DOCUMENTS.template.md").read_text(encoding="utf-8")
            manifest = root / "docs" / "DOCUMENTS.md"
            manifest.parent.mkdir()
            code, result = self.run_check(root, "--documents")
            self.assertEqual(1, code)
            self.assertFalse(result["documents"]["present"])

            manifest.write_text(template, encoding="utf-8")
            code, result = self.run_check(root, "--documents")
            self.assertEqual(0, code, result["documents"])
            self.assertEqual(
                {"path": "docs/DOCUMENTS.md", "present": True, "missing_rows": [],
                 "single_record_rows": [], "intro_paragraph_missing": False},
                result["documents"],
            )

            intro = template.split("\n\n")[1]
            features_row = next(line for line in template.splitlines() if line.startswith("| `docs/product/features/`"))
            record_row = "| EPIC-001 | `docs/epics/EPIC-001.md` | enhancement | owner | round record | open |"
            drifted = (
                template.replace(intro, "The manifest of every document. Add a row when a document is created.")
                .replace(features_row, record_row)
            )
            manifest.write_text(drifted, encoding="utf-8")
            code, result = self.run_check(root, "--documents")
        self.assertEqual(1, code)
        documents = result["documents"]
        self.assertEqual(["docs/product/features/"], documents["missing_rows"])
        line = drifted.splitlines().index(record_row) + 1
        self.assertEqual(
            [{"line": line, "path": "docs/epics/EPIC-001.md", "directory": "docs/epics/"}],
            documents["single_record_rows"],
        )
        self.assertTrue(documents["intro_paragraph_missing"])

    def test_documents_requires_check(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--root", temp, "--documents"],
                capture_output=True, text=True, encoding="utf-8", timeout=60,
            )
            self.assertEqual(2, result.returncode)
            self.assertIn("--documents requires --check", result.stderr)
            self.assertEqual([], list(Path(temp).iterdir()))


class ByteAttributeCheckTests(unittest.TestCase):
    """`--check` reads Git attributes of the hashed docs roots and writes nothing."""

    def repo(self, attributes: str | None) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name).resolve()
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        for name, data in (
            ("docs/product/PRD.md", b"# PRD\n"),
            ("docs/design/logo.png", b"\x89PNG fixture"),
            ("docs/verification/delivery-results.json", b"{}\n"),
            ("docs/goal/PLAN.md", b"# PLAN\n"),
        ):
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_bytes(data)
        subprocess.run(["git", "add", "-A"], cwd=root, check=True, capture_output=True)
        # check-attr reads the working-tree rules; staging under them would run the filters.
        if attributes is not None:
            (root / ".gitattributes").write_bytes(attributes.encode("utf-8"))
        configure_context(root)
        agents = root / "AGENTS.md"
        import re
        agents.write_text(
            re.sub(r"<fill>|<databases[^>]*>", "fixture", agents.read_text(encoding="utf-8")),
            encoding="utf-8",
        )
        return root

    def check(self, root: Path, *, require_resolved: bool = True) -> tuple[int, dict]:
        def snapshot() -> dict[str, bytes]:
            return {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in sorted(root.rglob("*")) if path.is_file()
            }

        before = snapshot()
        command = [sys.executable, str(SCRIPT), "--root", str(root), "--check",
                   "--stage", "product-definition"]
        if require_resolved:
            command.append("--require-resolved")
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(before, snapshot(), "the check must not write, index included")
        return result.returncode, json.loads(result.stdout)["byte_attributes"]

    def test_missing_rules_fail_and_print_the_lines_that_fix_them(self) -> None:
        root = self.repo(None)
        code, report = self.check(root)
        self.assertEqual(1, code, report)
        self.assertTrue(report["checked"])
        self.assertIn("docs/product/PRD.md: text unspecified", report["findings"])
        self.assertIn("new files under docs/goal/: text unspecified", report["findings"])
        self.assertEqual(
            ["docs/product/** -text", "docs/design/** -text",
             "docs/verification/** -text", "docs/goal/** -text"],
            report["gitattributes_lines"],
        )
        self.assertEqual(0, self.check(root, require_resolved=False)[0])
        (root / ".gitattributes").write_text("\n".join(report["gitattributes_lines"]) + "\n", encoding="utf-8")
        code, report = self.check(root)
        self.assertEqual(0, code, report)
        self.assertEqual([], report["findings"])

    def test_unset_text_passes_without_unsetting_filter(self) -> None:
        for attributes in ("docs/** -text\n", "docs/** binary\n", "docs/** -text -filter -ident\n"):
            with self.subTest(attributes=attributes):
                code, report = self.check(self.repo(attributes))
                self.assertEqual(0, code, report)
                self.assertEqual(([], [], []), (report["findings"], report["gitattributes_lines"], report["warnings"]))

    def test_rewriting_filter_ident_and_encoding_are_named(self) -> None:
        code, report = self.check(self.repo(
            "docs/** -text\n*.png filter=lfs\ndocs/goal/** ident working-tree-encoding=UTF-16\n"
        ))
        self.assertEqual(1, code, report)
        self.assertIn("docs/design/logo.png: filter lfs", report["findings"])
        self.assertIn(
            "docs/goal/PLAN.md: ident set, working-tree-encoding UTF-16", report["findings"]
        )
        self.assertEqual(
            ["docs/design/** -text -filter", "docs/goal/** -text -ident !working-tree-encoding"],
            report["gitattributes_lines"],
        )

    def test_local_info_attributes_rules_warn(self) -> None:
        root = self.repo(None)
        info = root / ".git" / "info" / "attributes"
        info.parent.mkdir(exist_ok=True)
        info.write_text("# local only\ndocs/** -text\n", encoding="utf-8")
        code, report = self.check(root)
        self.assertEqual(0, code, report)
        self.assertEqual([], report["findings"])
        self.assertEqual(1, len(report["warnings"]))
        self.assertIn("info/attributes holds attribute rules that clones and CI do not get", report["warnings"][0])

    def test_outside_a_git_checkout_nothing_is_checked(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            report = configure_project_context.byte_attribute_findings(Path(temp).resolve())
        self.assertFalse(report["checked"])
        self.assertEqual([], report["findings"])
        self.assertIn("not the root of a Git checkout", report["warnings"][0])


if __name__ == "__main__":
    unittest.main()
