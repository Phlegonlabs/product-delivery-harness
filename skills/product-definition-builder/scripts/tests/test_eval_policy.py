import copy
import contextlib
import hashlib
import io
import json
import random
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import eval_policy as ep
from contract_utils import canonical_product_bytes, machine_block_span, _without_machine_block
from eval_fixtures import encoded, inputs, prd


class EvalPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy, self.files = inputs()

    def test_frozen_inputs_and_approval_binding(self):
        self.assertEqual([], ep.validate_eval_policy(prd(self.policy), required=True))
        ep.parse_inputs(self.policy, self.files.__getitem__)
        changed = copy.deepcopy(self.policy)
        changed["minimum_rate"]["numerator"] -= 1
        self.assertNotEqual(canonical_product_bytes(prd(self.policy), "a", "s"),
                            canonical_product_bytes(prd(changed), "a", "s"))

    def test_legacy_missing_and_explicit_mode(self):
        self.assertEqual([], ep.validate_eval_policy("legacy"))
        self.assertTrue(ep.validate_eval_policy("legacy", required=True))
        self.assertIsNone(ep.parse_eval_policy("````\n" + prd(self.policy) + "\n````"))

    def test_approval_overlap_and_malformed_boundaries_rejected(self):
        approval_start = "<!-- product-definition-approval:start -->"
        approval_end = "<!-- product-definition-approval:end -->"
        valid = prd(self.policy)
        for candidate in (
                valid.replace(ep.START, approval_start + "\n" + ep.START).replace(ep.END, ep.END + "\n" + approval_end),
                valid.replace(ep.START, ep.START + "\n" + approval_start).replace(ep.END, approval_end + "\n" + ep.END),
                valid.replace(ep.START, approval_start + "\n" + ep.START).replace(ep.END, approval_end + "\n" + ep.END),
                valid + "\n" + approval_start, valid + "\n" + approval_end,
                valid + "\n" + approval_end + "\n" + approval_start):
            with self.subTest(candidate=candidate[:60]):
                self.assertTrue(ep.validate_eval_policy(candidate, required=True))
        self.assertEqual([], ep.validate_eval_policy(valid + "\n" + approval_start + "\n" + approval_end))

    def test_complete_approved_package_cannot_hide_threshold_in_approval(self):
        import check_product_package as package
        from test_product_package_checker import valid_prd, valid_architecture, valid_stack, strictize_approved_package
        policy_block = prd(self.policy).split(ep.START, 1)[1].split(ep.END, 1)[0]
        policy_block = ep.START + policy_block + ep.END
        normal = valid_prd().replace("## Business Rules", policy_block + "\n## Business Rules")
        normal, architecture, stack = strictize_approved_package(normal, valid_architecture(), valid_stack())
        self.assertEqual([], package.validate_texts(normal, architecture, stack,
                         require_filled=True, require_approved=True, eval_policy="eval-policy/1"))
        approval = re.search(r"<!-- product-definition-approval:start -->.*?<!-- product-definition-approval:end -->",
                             valid_prd(), re.S).group()
        source = valid_prd().replace(approval, "")
        enclosed = approval.replace("<!-- product-definition-approval:end -->",
                                    policy_block + "\n<!-- product-definition-approval:end -->")
        source = source.replace("## Business Rules", enclosed + "\n## Business Rules")
        source, architecture, stack = strictize_approved_package(source, valid_architecture(), valid_stack())
        weakened = source.replace('"numerator": 3', '"numerator": 2')
        self.assertEqual(canonical_product_bytes(source, architecture, stack),
                         canonical_product_bytes(weakened, architecture, stack))
        errors = package.validate_texts(weakened, architecture, stack,
                                      require_filled=True, require_approved=True, eval_policy="eval-policy/1")
        self.assertTrue(any("overlap" in error for error in errors), errors)

    def test_markers_must_be_active_unique_and_in_ai_section(self):
        valid = prd(self.policy)
        for candidate in (valid + valid, valid.replace(ep.END, ""), valid.replace("## AI and Automation", "## Other")):
            with self.subTest(candidate=candidate[:30]):
                self.assertTrue(ep.validate_eval_policy(candidate, required=True))

    def test_policy_fence_keeps_all_fields_visible_and_unicode_intact(self):
        self.assertEqual([], ep.validate_eval_policy(prd(self.policy), required=True))
        hidden = copy.deepcopy(self.policy)
        hidden.update(reason="Output quality <!--", owner="Jacky Chan -->")
        for policy in (self.policy, hidden):
            unfenced = prd(policy).replace("```json\n", "").replace("\n```", "")
            self.assertTrue(any("json fence" in error for error in ep.validate_eval_policy(unfenced, required=True)))
        for separator in ("\u0085", "\u2028", "\u2029"):
            policy = copy.deepcopy(self.policy)
            policy["delivery"]["full_argv"] += ["--prompt", "Before" + separator + "after"]
            source = prd(policy).replace(json.dumps(policy, indent=2), json.dumps(policy, indent=2, ensure_ascii=False))
            for newline in ("\n", "\r\n"):
                with self.subTest(separator=repr(separator), newline=repr(newline)):
                    self.assertEqual(policy, ep.parse_eval_policy(source.replace("\n", newline), required=True))

    def test_markdown_line_and_blank_boundaries_keep_policy_visible(self):
        hidden = copy.deepcopy(self.policy)
        hidden.update(reason="Output quality <!--", owner="Jacky Chan -->")
        source = prd(hidden)
        for separator in ("\x0b", "\x0c", "\x1c", "\x1d", "\x1e", "\x85", "\u2028", "\u2029"):
            for candidate in (source.replace(ep.START + "\n", ep.START + separator),
                              source.replace(ep.START, separator + ep.START),
                              source.replace("```json\n", separator + "```json\n"),
                              source.replace("\n```\n", "\n```" + separator + "\n")):
                with self.subTest(separator=repr(separator)), self.assertRaises(ep.PolicyError):
                    ep.parse_eval_policy(candidate, required=True)
        for whitespace in ("\u00a0", "\u1680", "\u2000", "\u2007", "\u202f", "\u205f", "\u3000"):
            for candidate in (source.replace(ep.START, "<details>\n" + whitespace + "\n" + ep.START),
                              source.replace("```json\n", whitespace + "```json\n"),
                              source.replace("\n```\n", "\n```" + whitespace + "\n")):
                with self.subTest(whitespace=repr(whitespace)), self.assertRaises(ep.PolicyError):
                    ep.parse_eval_policy(candidate, required=True)
        for newline in ("\n", "\r\n", "\r"):
            for blank in ("", " ", "\t", " \t"):
                candidate = source.replace(ep.START, "<details>\n" + blank + "\n" + ep.START)
                self.assertEqual(hidden, ep.parse_eval_policy(candidate.replace("\n", newline), required=True))

    def test_raw_digest_exclusion_matrix_cannot_hide_policy(self):
        import check_product_package as package
        from test_product_package_checker import valid_prd, valid_architecture, valid_stack, strictize_approved_package
        start = "<!-- product-definition-approval:start -->"
        block = ep.START + prd(self.policy).split(ep.START)[1].split(ep.END)[0] + ep.END
        for prefix in ("```markdown\n" + start + "\n```\n", "    " + start + "\n",
                       "<script>\n" + start + "\n</script>\n", "<!--\n" + start + "\n-->\n"):
            for newline in ("\n", "\r\n"):
                with self.subTest(prefix=prefix, newline=repr(newline)):
                    source = valid_prd().replace("## Business Rules", block + "\n## Business Rules")
                    source = source.replace("## AI and Automation", prefix + "## AI and Automation")
                    source, architecture, stack = strictize_approved_package(source, valid_architecture(), valid_stack())
                    source = source.replace("\n", newline)
                    weakened = source.replace('"numerator": 3', '"numerator": 2')
                    self.assertEqual(canonical_product_bytes(source, architecture, stack),
                                     canonical_product_bytes(weakened, architecture, stack))
                    errors = package.validate_texts(weakened, architecture, stack,
                        require_filled=True, require_approved=True, eval_policy="eval-policy/1")
                    self.assertTrue(any("overlaps the raw approval digest exclusion" in error for error in errors), errors)
        # Python splitlines recognizes these separators; the digest regex uses LF.
        for separator in ("\x0c", "\u2028", "\r"):
            candidate = prd(self.policy).replace(ep.START, "prefix" + separator + start + "\n" + ep.START)
            candidate += "\n<!-- product-definition-approval:end -->\n"
            self.assertTrue(ep.validate_eval_policy(candidate, required=True))

    def test_mixed_line_endings_preserve_historical_digest_and_policy_offsets(self):
        import check_product_package as package
        from test_product_package_checker import valid_prd, valid_architecture, valid_stack, strictize_approved_package
        start, end = "<!-- product-definition-approval:start -->", "<!-- product-definition-approval:end -->"
        historical = rf"(?ms)^\s*{re.escape(start)}\s*\n.*?^\s*{re.escape(end)}\s*\n?"
        separators = ("\n", "\r\n", "\r\r\n", "\r\r\r\n", "\u2028", "\x0c", "\r", "\x85", "\x1c")
        for before in separators:
            for inside in separators:
                raw = "a" + before * 2 + "b\n" + start + "\nfield" + inside + "\n" + end + "\nz"
                with self.subTest(before=repr(before), inside=repr(inside)):
                    self.assertEqual(re.sub(historical, "", raw.replace("\r\n", "\n"), count=1),
                                     _without_machine_block(raw, start, end))
        block = ep.START + prd(self.policy).split(ep.START)[1].split(ep.END)[0] + ep.END
        for separator in separators:
            source = valid_prd().replace("## AI and Automation", "```text\n" + start + "\n```\n## AI and Automation")
            source = source.replace("## Business Rules", separator * 200 + block + "\n## Business Rules")
            source, architecture, stack = strictize_approved_package(source, valid_architecture(), valid_stack())
            weakened = source.replace('"numerator": 3', '"numerator": 2')
            with self.subTest(policy_prefix=repr(separator)):
                self.assertEqual(canonical_product_bytes(source, architecture, stack),
                                 canonical_product_bytes(weakened, architecture, stack))
                errors = package.validate_texts(weakened, architecture, stack,
                    require_filled=True, require_approved=True, eval_policy="eval-policy/1")
                self.assertTrue(any("overlaps the raw approval digest exclusion" in error for error in errors), errors)

    def test_machine_block_first_span_matches_historical_whitespace_semantics(self):
        start, end = "<!-- product-definition-approval:start -->", "<!-- product-definition-approval:end -->"
        historical = re.compile(rf"(?ms)^\s*{re.escape(start)}\s*\n.*?^\s*{re.escape(end)}\s*\n?")
        tokens = (start, end, "x", "\n", "\r\n", "\r", "\t", " ", "\u2028", "\x85", "\x1c")
        generator = random.Random(7189)
        candidates = ["".join(generator.choices(tokens, k=20)) for _ in range(5000)]
        candidates += ["x\n\n  " + start + "\n\n " + end + "\n\t\u2028x",
                       start + "\n" + start + "\n" + end + "\n" + end,
                       "x\u2028 " + start + "\n" + end,
                       start + "\n\n" + end + "\n\n" + start + "\n" + end]
        for source in candidates:
            expected = historical.search(source)
            with self.subTest(source=repr(source)):
                self.assertEqual(expected.span() if expected else None, machine_block_span(source, start, end))

    def test_large_blank_prefix_and_quoted_markers_finish_under_child_deadline(self):
        program = ("import copy, sys\n"
                   "sys.path[:0] = sys.argv[1:3]\n"
                   "import eval_policy as ep\n"
                   "from contract_utils import machine_block_span\n"
                   "from eval_fixtures import inputs, prd\n"
                   "start = '<!-- product-definition-approval:start -->'\n"
                   "end = '<!-- product-definition-approval:end -->'\n"
                   "policy, _ = inputs()\n"
                   "prefix = '\\n' * 1000000\n"
                   "quoted = copy.deepcopy(policy)\n"
                   "quoted['delivery']['full_argv'] += ['--prompt', start + end]\n"
                   "for value in (policy, quoted):\n"
                   "    source = prefix + prd(value)\n"
                   "    assert len(source.encode()) < ep.MAX_BYTES\n"
                   "    assert ep.parse_eval_policy(source, required=True) == value\n"
                   "assert machine_block_span(start + '\\n' + prefix + 'x', start, end) is None\n"
                   "hidden = prefix + '```text\\n' + start + '\\n```\\n' + prd(policy) + '\\n```text\\n' + end + '\\n```\\n'\n"
                   "assert any('raw approval digest exclusion' in error\n"
                   "           for error in ep.validate_eval_policy(hidden, required=True))\n")
        result = subprocess.run([sys.executable, "-c", program, str(Path(ep.__file__).parent),
                                 str(Path(__file__).parent)], capture_output=True, text=True, timeout=60)
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)

    def test_ai_cannot_waive_and_tests_are_required_traced_and_distinct(self):
        waived = {"schema": "eval-policy/1", "applicability": "not_required",
                  "reason": "Ordinary deterministic product has no AI", "owner": "Jacky Chan"}
        self.assertTrue(ep.validate_eval_policy(prd(waived)))
        self.assertEqual([], ep.validate_eval_policy(prd(waived).replace("Gate: required", "Gate: not_required"), required=True))
        for old, new in (("| Yes |", "| No |"), ("AI-EVALUATION", "OTHER")):
            self.assertTrue(ep.validate_eval_policy(prd(self.policy).replace(old, new)))

    def test_scenario_id_may_name_a_feature_scenario_of_its_test(self):
        candidate = copy.deepcopy(self.policy)
        candidate["quality"]["scenario_id"] = "TEST-001/full-quality-run-meets-the-frozen-rate"
        candidate["handoff"]["scenario_id"] = "TEST-002/clean-checkout-run"
        self.assertEqual([], ep.validate_eval_policy(prd(candidate), required=True))
        for bad in ("TEST-002/full-quality-run", "TEST-001/Full-Run", "TEST-001/", "TEST-001/run/again"):
            candidate["quality"]["scenario_id"] = bad
            with self.subTest(scenario_id=bad):
                self.assertTrue(ep.validate_eval_policy(prd(candidate), required=True))

    def test_typed_policy_and_no_silent_extra_fields(self):
        for key, value in (("trials_per_case", True), ("retry_policy", "best-of-three"),
                           ("minimum_rate", {"numerator": 1, "denominator": 0}),
                           ("slices", [{"id": "core", "minimum_cases": 0, "minimum_rate": {"numerator": 1, "denominator": 1}}]),
                           ("extra", "ignored")):
            candidate = copy.deepcopy(self.policy)
            candidate[key] = value
            self.assertTrue(ep.validate_eval_policy(prd(candidate)))

    def test_eval_joins_only_the_canonical_test_table(self):
        valid = prd(self.policy)
        decoy = ("### Test Obligations rationale\n"
                 "| TEST-001 | Decoy quality | contract | Yes | AI-EVALUATION | pass |\n"
                 "| TEST-002 | Decoy handoff | contract | Yes | AI-EVALUATION | pass |\n")
        prefix = "See ## Test Obligations for the approved tests.\n"
        self.assertEqual([], ep.validate_eval_policy(prefix + valid, required=True))
        self.assertEqual([], ep.validate_eval_policy(valid.replace(ep.START, decoy + ep.START), required=True))
        mixed = valid.replace("| TEST-001 |", "| test-001 |").replace("| Yes |", "| yes |")
        mixed += "| TEST-OPTIONAL | Unrelated obligation | contract | No | PRD-002 | Other signal |\n"
        self.assertEqual([], ep.validate_eval_policy(mixed, required=True))
        optional = valid.replace("| Yes |", "| No |", 1).replace(ep.START, decoy + ep.START)
        self.assertTrue(any("Required-Yes" in error for error in ep.validate_eval_policy(optional, required=True)))
        section = valid.split("## Test Obligations\n", 1)[1]
        for candidate in (valid.replace("| TEST ID |", "| Code |"),
                          valid + "\n" + section,
                          valid + "\n## Test Obligations\n" + section,
                          valid.replace("## Test Obligations\n", "## Test Obligations\n## Other\n"),
                          valid.replace("| --- | --- | --- | --- | --- | --- |", "No table separator"),
                          valid + "\n" + section.splitlines()[-1]):
            with self.subTest(candidate=candidate[-70:]):
                self.assertTrue(ep.validate_eval_policy(candidate, required=True))

    def test_duplicate_json_and_nonfinite_rejected(self):
        for raw in ('{"schema": 1, "schema": 2}', '{"score": NaN}'):
            with self.assertRaises(ep.PolicyError):
                ep.json_object(raw)

    def test_malformed_numeric_and_path_inputs_return_policy_errors(self):
        with self.assertRaisesRegex(ep.PolicyError, "invalid UTF-8 JSON"):
            ep.json_object('{"value":' + '1' * 5000 + '}')
        candidate = prd(self.policy).replace('"numerator": 3', '"numerator":' + '1' * 5000)
        errors = ep.validate_eval_policy(candidate, required=True)
        self.assertTrue(errors and all(error.startswith("eval-policy:") for error in errors), errors)
        with tempfile.TemporaryDirectory() as directory:
            for control in ("\x00", "\t", "\n", "\x7f"):
                with self.subTest(control=repr(control)), self.assertRaises(ep.PolicyError):
                    ep.read_artifact(directory, "evals/a" + control + "b.json")
        with self.assertRaisesRegex(ep.PolicyError, "duplicate JSON key"):
            ep.json_object('{"value":1,"value":2}')
        import check_product_package as package
        from test_product_package_checker import valid_prd, valid_architecture, valid_stack
        block = ep.START + candidate.split(ep.START)[1].split(ep.END)[0] + ep.END
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sources = {"PRD.md": valid_prd().replace("## Business Rules", block + "\n## Business Rules"),
                       "architecture.md": valid_architecture(), "stack.md": valid_stack()}
            for name, source in sources.items():
                (root / name).write_text(source, encoding="utf-8")
            stdout, stderr = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = package.main(["--prd", str(root / "PRD.md"), "--architecture", str(root / "architecture.md"),
                    "--stack-decisions", str(root / "stack.md"), "--eval-policy", "eval-policy/1"])
            self.assertEqual(1, result)
            self.assertIn("eval-policy:", stderr.getvalue())
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_content_accepts_json_markup_todo_and_long_prompts(self):
        candidate, files = copy.deepcopy(self.policy), dict(self.files)
        cases = [json.loads(line) for line in files[candidate["dataset"]["path"]].splitlines()]
        cases[0].update(input="Add a TODO for Friday", expected='["<script>", "item"]')
        files[candidate["dataset"]["path"]] = b"".join(encoded(row) for row in cases)
        for name in ("rubric", "grader", "subject"):
            path = candidate[name]["path"]
            value = json.loads(files[path])
            if name == "rubric":
                value["dimensions"][0]["anchors"]["1"] = 'Returns the exact JSON array ["item"]'
                value["prohibited_assertions"]["no-side-effect"] = "Never emits <script>"
            elif name == "grader":
                value["instructions"] = "<instructions>" + "x" * 9000 + "</instructions>"
            else:
                value["configuration"] = '{"context": ["approved"]}'
            files[path] = encoded(value)
        for name in ("dataset", "rubric", "grader", "subject"):
            candidate[name]["sha256"] = hashlib.sha256(files[candidate[name]["path"]]).hexdigest()
        ep.parse_inputs(candidate, files.__getitem__)
        candidate["delivery"]["full_argv"] += ["--expected", '["item"]']
        self.assertEqual([], ep.validate_eval_policy(prd(candidate)))
        for value in ("", " ", None, 42):
            with self.assertRaises(ep.PolicyError):
                ep.data_text(value, "content")
        for owner in (42, None, [], {}):
            candidate["owner"] = owner
            self.assertTrue(ep.validate_eval_policy(prd(candidate)))

    def test_changed_inputs_rejected_without_weakened_hashes(self):
        for name in self.files:
            altered = dict(self.files)
            altered[name] += b" "
            with self.assertRaises(ep.PolicyError):
                ep.parse_inputs(self.policy, altered.__getitem__)

    def test_jsonl_keeps_unicode_separators_inside_prompts(self):
        original = [json.loads(line) for line in self.files["evals/cases.jsonl"].splitlines()]
        for separator in ("\u0085", "\u2028", "\u2029"):
            for newline in ("\n", "\r\n"):
                with self.subTest(separator=repr(separator), newline=repr(newline)):
                    cases = copy.deepcopy(original)
                    cases[0]["input"] = "Before" + separator + "after"
                    raw = (newline.join(json.dumps(case, ensure_ascii=False) for case in cases) + newline).encode()
                    policy = copy.deepcopy(self.policy)
                    policy["dataset"]["sha256"] = hashlib.sha256(raw).hexdigest()
                    files = dict(self.files, **{"evals/cases.jsonl": raw})
                    parsed = ep.parse_inputs(policy, files.__getitem__)
                    self.assertEqual(cases, parsed["dataset"])
            with self.subTest(invalid_record_separator=repr(separator)):
                raw = separator.join(json.dumps(case) for case in original).encode()
                policy = copy.deepcopy(self.policy)
                policy["dataset"]["sha256"] = hashlib.sha256(raw).hexdigest()
                with self.assertRaisesRegex(ep.PolicyError, "invalid UTF-8 JSON"):
                    ep.parse_inputs(policy, dict(self.files, **{"evals/cases.jsonl": raw}).__getitem__)

    def test_dataset_and_rubric_structure_validated(self):
        for path, raw in (("evals/cases.jsonl", self.files["evals/cases.jsonl"] * 2),
                          ("evals/rubric.json", encoded({"schema": "eval-rubric/1", "dimensions": [], "prohibited_assertions": {}}))):
            candidate = copy.deepcopy(self.policy)
            files = dict(self.files, **{path: raw})
            name = "dataset" if "cases" in path else "rubric"
            candidate[name]["sha256"] = hashlib.sha256(raw).hexdigest()
            with self.assertRaises(ep.PolicyError):
                ep.parse_inputs(candidate, files.__getitem__)

    def sparse_inputs(self, count):
        policy, files = inputs()
        cases = [{"case_id": f"case-{index}", "split": "heldout", "slices": [f"slice-{index}"],
                  "critical": False, "input": "x", "expected": "x"} for index in range(count)]
        policy["trials_per_case"] = 1
        policy["slices"] = [{"id": f"slice-{index}", "minimum_cases": 1,
                             "minimum_rate": {"numerator": 1, "denominator": 1}} for index in range(count)]
        files[policy["dataset"]["path"]] = b"".join(
            (json.dumps(case, separators=(",", ":")) + "\n").encode() for case in cases)
        policy["dataset"]["sha256"] = hashlib.sha256(files[policy["dataset"]["path"]]).hexdigest()
        return policy, files

    def test_sparse_slice_checks_visit_memberships_linearly(self):
        policy, files = self.sparse_inputs(1000)
        visits = []
        original = ep.json_object

        class Memberships(list):
            def __iter__(self):
                visits.append(len(self))
                return super().__iter__()

            def __contains__(self, value):
                visits.append(len(self))
                return super().__contains__(value)

        def counted_json(raw):
            value = original(raw)
            if "case_id" in value:
                value["slices"] = Memberships(value["slices"])
            return value

        with patch.object(ep, "json_object", side_effect=counted_json):
            ep.parse_inputs(policy, files.__getitem__)
        self.assertLessEqual(sum(visits), 8 * len(policy["slices"]))
        policy["slices"][-1]["minimum_cases"] = 2
        with self.assertRaisesRegex(ep.PolicyError, "fewer cases"):
            ep.parse_inputs(policy, files.__getitem__)

    def test_large_sparse_population_at_root_bound_product_entry(self):
        policy, files = self.sparse_inputs(50000)
        source = prd(policy).replace(json.dumps(policy, indent=2), json.dumps(policy, separators=(",", ":")))
        self.assertLess(len(source.encode()), 16 * 1024 * 1024)
        self.assertTrue(all(len(raw) < 16 * 1024 * 1024 for raw in files.values()))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, raw in files.items():
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
            path = root / "PRD.md"
            path.write_text(source, encoding="utf-8")
            program = ("import json, sys\nfrom pathlib import Path\n"
                       "sys.path.insert(0, sys.argv[1])\nimport eval_policy as ep\n"
                       "source = Path(sys.argv[2]).read_text(encoding='utf-8')\n"
                       "valid = ep.validate_eval_policy(source, required=True, repo_root=sys.argv[3])\n"
                       "changed = source.replace('\"minimum_cases\":1', '\"minimum_cases\":2', 1)\n"
                       "invalid = ep.validate_eval_policy(changed, required=True, repo_root=sys.argv[3])\n"
                       "print(json.dumps({'valid': valid, 'undersized': invalid}))\n"
                       "sys.exit(bool(valid) or not any('fewer cases' in error for error in invalid))\n")
            result = subprocess.run([sys.executable, "-c", program, str(Path(ep.__file__).parent),
                                     str(path), str(root)], capture_output=True, text=True, timeout=90)
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertEqual([], json.loads(result.stdout)["valid"])

    def test_file_boundary_and_package_api(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, raw in self.files.items():
                path = root / name
                path.parent.mkdir(exist_ok=True)
                path.write_bytes(raw)
            self.assertEqual([], ep.validate_eval_policy(prd(self.policy), repo_root=root))
            for path in ("../escape", ".env", "evals/auth-token.json", "evals\\cases.jsonl"):
                with self.assertRaises(ep.PolicyError):
                    ep.read_artifact(root, path)
        import check_product_package as package
        from test_product_package_checker import valid_prd, valid_architecture, valid_stack
        baseline = package.validate_texts(valid_prd(), valid_architecture(), valid_stack())
        explicit = package.validate_texts(valid_prd(), valid_architecture(), valid_stack(), eval_policy="eval-policy/1")
        self.assertFalse(any("eval-policy" in p for p in baseline))
        self.assertTrue(any("eval-policy" in p for p in explicit))


if __name__ == "__main__":
    unittest.main()
