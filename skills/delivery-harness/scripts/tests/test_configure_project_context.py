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


if __name__ == "__main__":
    unittest.main()
