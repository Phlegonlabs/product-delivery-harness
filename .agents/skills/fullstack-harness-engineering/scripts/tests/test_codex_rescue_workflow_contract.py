import json
import shutil
import subprocess
import unittest
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[2]
PREFLIGHT_PATH = SKILL_ROOT / "assets/templates/CLAUDE_CODEX_PREFLIGHT.template.js"
GRAPH_WORKFLOW_PATH = SKILL_ROOT / "assets/templates/CLAUDE_CODEX_GRAPH_WORKFLOW.template.js"
NODE = shutil.which("node")


class CodexRescueWorkflowContractTests(unittest.TestCase):
    def test_preflight_uses_exact_read_only_foreground_agent_contract(self) -> None:
        preflight = PREFLIGHT_PATH.read_text(encoding="utf-8")

        self.assertIn('agentType: "codex:codex-rescue"', preflight)
        self.assertIn("`--wait --fresh\\n`", preflight)
        self.assertIn("read-only Harness runtime handshake", preflight)
        self.assertIn("Do not edit files, create commits, or inspect repository content", preflight)
        self.assertIn("HARNESS_CODEX_PREFLIGHT_V1_BEGIN", preflight)
        self.assertIn("HARNESS_CODEX_PREFLIGHT_V1_END", preflight)
        self.assertIn('driver: "codex_rescue_agent"', preflight)
        self.assertIn('command: "agent:codex:codex-rescue"', preflight)
        self.assertIn('completion_channel: "agent_result"', preflight)

    def test_graph_workflow_is_flat_and_isolates_each_write_mission(self) -> None:
        workflow = GRAPH_WORKFLOW_PATH.read_text(encoding="utf-8")

        self.assertIn("pipeline(workflowArgs.nodes", workflow)
        self.assertIn('agentType: "codex:codex-rescue"', workflow)
        self.assertIn('agentOptions.isolation = "worktree"', workflow)
        self.assertIn('const routeFlags = ["--wait", "--fresh"]', workflow)
        self.assertIn("if (workflowArgs.model)", workflow)
        self.assertIn("if (workflowArgs.reasoning_effort)", workflow)
        self.assertNotIn("--resume", workflow)
        self.assertIn("Do not switch branches", workflow)
        self.assertIn("Never edit PLAN.md or RUN.md", workflow)
        self.assertIn("durable commits", workflow)
        self.assertIn("Do not integrate, push, open or modify a PR, deploy", workflow)
        self.assertIn("or delegate to another agent", workflow)
        self.assertIn("Do not wait for user input", workflow)

    @unittest.skipUnless(NODE, "node is required to execute Workflow template contracts")
    def test_marker_parser_accepts_one_valid_result_and_rejects_bad_results(self) -> None:
        valid_candidate = self.candidate()
        valid_raw = self.marked(valid_candidate)

        valid = self.run_graph_workflow(valid_raw)
        self.assertEqual("succeeded", valid[0]["node_result"]["status"])
        self.assertEqual("pass", valid[0]["node_result"]["outcome"])
        self.assertEqual(valid_candidate["runtime_evidence"], valid[0]["runtime_evidence"])

        mismatched = self.candidate()
        mismatched["node_result"]["node_id"] = "N-WRONG"
        wrong_review_head = self.candidate()
        wrong_review_head["runtime_evidence"]["head_sha"] = "c" * 40
        cases = {
            "missing": "{}",
            "malformed": "HARNESS_NODE_RESULT_V1_BEGIN\n{\nHARNESS_NODE_RESULT_V1_END",
            "duplicate": (
                "HARNESS_NODE_RESULT_V1_BEGIN\n"
                "HARNESS_NODE_RESULT_V1_BEGIN\n{}\n"
                "HARNESS_NODE_RESULT_V1_END"
            ),
            "identity": self.marked(mismatched),
            "review_head": self.marked(wrong_review_head),
        }
        for name, raw_result in cases.items():
            with self.subTest(name=name):
                result = self.run_graph_workflow(raw_result)
                node_result = result[0]["node_result"]
                self.assertEqual("failed", node_result["status"])
                self.assertEqual("retryable_failure", node_result["outcome"])
                self.assertTrue(
                    node_result["evidence_paths"][0].startswith("codex-result-invalid:"),
                    node_result["evidence_paths"],
                )
                self.assertIsNone(result[0]["runtime_evidence"])

    def workflow_args(self) -> dict[str, object]:
        return {
            "run_id": "RUN-TEST",
            "plan_id": "PLAN-TEST",
            "plan_revision": 1,
            "plan_digest_sha256": "d" * 64,
            "graph_revision": 1,
            "batch_base_sha": "a" * 40,
            "tool_profile": "code_review_readonly",
            "model": None,
            "reasoning_effort": None,
            "nodes": [
                {
                    "node_id": "N-REVIEW",
                    "attempt_id": "ATT-N-REVIEW-1",
                    "node_kind": "review",
                    "failure_outcome": "retryable_failure",
                    "worker_prompt": "Review the assigned change.",
                    "review_id": "REVIEW-1",
                    "review_type": "backend_code",
                    "reviewed_sha": "b" * 40,
                    "review_path": ".",
                    "review_scope": ["src/**"],
                    "required_evidence": ["findings"],
                }
            ],
        }

    def candidate(self) -> dict[str, object]:
        args = self.workflow_args()
        node = args["nodes"][0]
        return {
            "node_result": {
                "run_id": args["run_id"],
                "node_id": node["node_id"],
                "attempt_id": node["attempt_id"],
                "plan_id": args["plan_id"],
                "plan_revision": args["plan_revision"],
                "plan_digest_sha256": args["plan_digest_sha256"],
                "graph_revision": args["graph_revision"],
                "batch_base_sha": args["batch_base_sha"],
                "status": "succeeded",
                "outcome": "pass",
                "worker_result": {
                    "reviewed_sha": node["reviewed_sha"],
                    "findings": [],
                    "evidence_summary": "No blocking findings.",
                },
                "refinement_request": None,
                "evidence_paths": ["review complete"],
            },
            "runtime_evidence": {
                "worktree_path": "C:/repo/worktrees/review",
                "branch_ref": "refs/heads/main",
                "head_sha": node["reviewed_sha"],
            },
        }

    @staticmethod
    def marked(candidate: dict[str, object]) -> str:
        return (
            "HARNESS_NODE_RESULT_V1_BEGIN\n"
            + json.dumps(candidate, separators=(",", ":"))
            + "\nHARNESS_NODE_RESULT_V1_END"
        )

    def run_graph_workflow(self, raw_result: str) -> object:
        runner = r"""
const fs = require("fs");
const payload = JSON.parse(fs.readFileSync(0, "utf8"));
let source = fs.readFileSync(payload.template_path, "utf8");
source = source.replace("export const meta =", "const meta =");
const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
const execute = new AsyncFunction("args", "pipeline", "agent", "phase", source);
const pipeline = async (items, stage) => Promise.all(items.map((item) => stage(item)));
const agent = async () => payload.raw_result;
execute(payload.args, pipeline, agent, () => {}).then(
  (result) => process.stdout.write(JSON.stringify(result)),
  (error) => {
    process.stderr.write(error.stack || String(error));
    process.exitCode = 1;
  },
);
"""
        completed = subprocess.run(
            [NODE, "-e", runner],
            input=json.dumps(
                {
                    "template_path": str(GRAPH_WORKFLOW_PATH),
                    "args": self.workflow_args(),
                    "raw_result": raw_result,
                }
            ),
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        return json.loads(completed.stdout)


if __name__ == "__main__":
    unittest.main()
