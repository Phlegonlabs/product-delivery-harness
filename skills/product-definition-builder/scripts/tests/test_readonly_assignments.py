"""Focused behavior tests for versioned read-only assignment packets."""

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = SKILL_ROOT / "scripts" / "readonly_assignments.cjs"
GRAPH_PATH = SKILL_ROOT / "scripts" / "product_agent_graph.cjs"


def canonical_request() -> dict:
    return {
        "schema_version": "readonly-assignments/1",
        "run_id": "product-run-1",
        "business_role": "market-research",
        "execution_role": "market_researcher",
        "phase": "post_draft_market_research",
        "authorization": {"delegation": True, "readonly_tools": True},
        "capability": {"readonly_tools": True, "launch_runtime": True},
        "attempt_number": 1,
        "binding_required": False,
        "skip_allowed": False,
        "requested_identity": {
            "execution_role": "market_researcher",
            "model": "fixture-model",
            "effort": "high",
        },
        "questions": [
            {
                "question_id": "Q-CATEGORY",
                "prompt": "What capabilities does this category treat as table stakes?",
                "input": {"source_paths": ["docs/research/category.md"], "source_revision": "abc123"},
                "substantive": True,
                "independent": True,
            },
            {
                "question_id": "Q-PRICING",
                "prompt": "What published pricing models apply to this segment?",
                "input": {"source_paths": ["docs/research/pricing.md"], "source_revision": "abc123"},
                "substantive": True,
                "independent": True,
            },
        ],
    }


def canonical_graph_request() -> dict:
    return {
        "run_id": "product-run-1",
        "product_name": "Fixture Product",
        "interview_summary": "A bounded product fixture.",
        "product_archetypes": ["internal tool"],
        "source_paths": ["docs/research"],
        "browser_frontend": False,
        "ui_bearing": True,
        "ui_design_owner": "Product owner",
        "has_backend": True,
        "deployable": False,
        "hosted_deployable": False,
        "deployable_surfaces": [],
        "release_targets": [],
        "has_public_marketing_content": False,
        "monetization_model": "none",
        "partner_channel_model": "none",
        "stack_decision_mode": "review_recommendation",
        "data_trust_gate": "not_required",
        "security_requirements_gate": "required",
        "security_scope": "executable",
        "ai_automation_gate": "not_required",
        "include_implementation_plan": False,
        "market_research": True,
        "tool_profile": "builder_readonly",
        "multi_agent_authorized": True,
        "result_join_mode": "readonly_assignments_v1",
        "research_question_inventory": canonical_request()["questions"],
        "readonly_authorization": {"delegation": True, "readonly_tools": True},
        "readonly_capability": {"readonly_tools": True, "launch_runtime": True},
        "readonly_phase": "post_draft_market_research",
        "readonly_binding_required": True,
        "readonly_binding_requirements": {"authority": "parent-owned", "runtime": "readonly-sandbox"},
        "requested_research_identity": {
            "execution_role": "market_researcher",
            "model": "fixture-model",
            "effort": "high",
        },
    }


class ReadonlyAssignmentPacketTests(unittest.TestCase):
    def run_node(
        self,
        script: str,
        payload: object | None = None,
        module_path: Path = MODULE_PATH,
        extra_args: list[str] | None = None,
    ) -> dict:
        node = shutil.which("node")
        if node is None:
            self.skipTest("Node.js is required for readonly assignment tests")
        with tempfile.TemporaryDirectory(prefix="readonly-assignments-") as temp:
            temp_path = Path(temp)
            script_path = temp_path / "test.js"
            payload_path = temp_path / "payload.json"
            stdout_path = temp_path / "stdout.log"
            stderr_path = temp_path / "stderr.log"
            script_path.write_text(script, encoding="utf-8")
            payload_path.write_text(json.dumps(payload), encoding="utf-8")
            environment = os.environ.copy()
            with stdout_path.open("w", encoding="utf-8", newline="") as stdout_log, stderr_path.open(
                "w", encoding="utf-8", newline=""
            ) as stderr_log:
                completed = subprocess.run(
                    [
                        node,
                        str(script_path),
                        str(module_path),
                        str(payload_path),
                        *(extra_args or []),
                    ],
                    cwd=Path.cwd(),
                    env=environment,
                    stdout=stdout_log,
                    stderr=stderr_log,
                    timeout=10,
                    check=False,
                )
            stderr_tail = stderr_path.read_text(encoding="utf-8", errors="replace")[-2000:]
            self.assertEqual(0, completed.returncode, stderr_tail)
            return json.loads(stdout_path.read_text(encoding="utf-8"))

    def load_plan_script(self) -> str:
        return r"""
const fs = require("fs");
const { createReadonlyAssignments } = require(process.argv[2]);
const request = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
process.stdout.write(JSON.stringify(createReadonlyAssignments(request)));
"""

    def test_agent_selected_worker_reuse_keeps_assignment_and_launch_provenance(self) -> None:
        request = canonical_request()
        request["distinct_workers"] = False
        request["binding_required"] = True
        request["binding_requirements"] = {"authority": "parent-owned", "runtime": "readonly-sandbox"}
        script = r"""
const fs = require("fs");
const assert = require("node:assert/strict");
const api = require(process.argv[2]);
const request = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const plan = api.createReadonlyAssignments(request);
const identity = {...request.requested_identity, worker_id: "shared-worker", session_id: "shared-session"};
const results = plan.instances.map(instance => api.readonlyResult(instance, {
  status: "complete", observed_identity: identity,
  result: {findings: [instance.question_id], sources: ["https://example.com/source"]},
}));
const records = plan.instances.map((instance, index) => ({
  assignment_id: instance.assignment_id, attempt_id: instance.attempt_id, input_id: instance.input_id,
  ...request.binding_requirements, ...identity, reservation_id: `reservation-${index}`,
}));
const joined = api.joinReadonlyResults(plan, results.reverse(), records);
assert.equal(joined.status, "ready");
assert.equal(new Set(joined.results.map(r => r.assignment_id)).size, 2);
const duplicateReservation = JSON.parse(JSON.stringify(records));
duplicateReservation[1].reservation_id = duplicateReservation[0].reservation_id;
assert.throws(() => api.joinReadonlyResults(plan, results, duplicateReservation), /reservation_id/);
const mixedIdentity = JSON.parse(JSON.stringify(records));
mixedIdentity[1].session_id = "another-session";
assert.throws(() => api.joinReadonlyResults(plan, results, mixedIdentity), /worker_id/);
const changedPolicy = JSON.parse(JSON.stringify(plan));
changedPolicy.distinct_workers = true;
assert.throws(() => api.joinReadonlyResults(changedPolicy, results, records), /staffing policy/);
const corroboration = api.createReadonlyAssignments({...request, distinct_workers: true});
assert.notEqual(corroboration.instances[0].input_id, plan.instances[0].input_id);
const strictResults = corroboration.instances.map(instance => api.readonlyResult(instance, {
  status: "complete", observed_identity: identity,
  result: {findings: [instance.question_id], sources: ["https://example.com/source"]},
}));
const strictRecords = corroboration.instances.map((instance, index) => ({
  assignment_id: instance.assignment_id, attempt_id: instance.attempt_id, input_id: instance.input_id,
  ...request.binding_requirements, ...identity, reservation_id: `strict-${index}`,
}));
assert.throws(() => api.joinReadonlyResults(corroboration, strictResults, strictRecords), /worker_id/);
assert.throws(() => api.createReadonlyAssignments({...request, distinct_workers: "no"}), /boolean/);
process.stdout.write(JSON.stringify(joined));
"""
        self.assertEqual("ready", self.run_node(script, request)["status"])

    def test_graph_research_reuse_never_reuses_an_independent_verifier(self) -> None:
        from test_graph_identity import PRELUDE
        script = PRELUDE + r"""
args.research_distinct_workers = false;
args.role_bindings["market-research"].execution_role = "custom-research-agent";
const s = setup();
const researchIds = s.tasks.filter(t => t.assignment.business_role === "market-research")
  .map(t => t.assignment.assignment_id);
for (const result of s.results.filter(r => researchIds.includes(r.assignment_id)))
  Object.assign(result.observed_identity, {worker_id: "shared-research", session_id: "shared-session"});
for (const record of s.launches.filter(r => researchIds.includes(r.assignment_id)))
  Object.assign(record, {worker_id: "shared-research", session_id: "shared-session"});
const joined = finish(s);
assert.equal(joined.status, "candidate_ready");
const verifier = s.results.find(r => !researchIds.includes(r.assignment_id));
for (const record of s.launches.filter(r => researchIds.includes(r.assignment_id)))
  Object.assign(record, {worker_id: verifier.observed_identity.worker_id, session_id: verifier.observed_identity.session_id});
assert.throws(() => finish(s));
process.stdout.write(JSON.stringify({ok: true}));
"""
        result = self.run_node(script, canonical_graph_request(), GRAPH_PATH, [str(MODULE_PATH)])
        self.assertTrue(result["ok"])

    def test_same_role_questions_fan_out_with_unique_identities_and_no_observed_claim(self) -> None:
        request = canonical_request()
        plan = self.run_node(self.load_plan_script(), request)
        instances = plan["instances"]

        self.assertEqual(2, len(instances))
        self.assertEqual({"market_researcher"}, {item["execution_role"] for item in instances})
        for field in ("assignment_id", "attempt_id", "question_id", "input_id"):
            values = [item[field] for item in instances]
            self.assertEqual(len(values), len(set(values)))
        for instance in instances:
            self.assertNotIn("observed_identity", instance)
            self.assertTrue(instance["readonly"])
            self.assertTrue(instance["required_result"])
            self.assertEqual(request["requested_identity"], instance["requested_identity"])

    def test_identity_join_accepts_reorder_and_explicit_no_sources(self) -> None:
        request = canonical_request()
        request["skip_allowed"] = True
        request["skip_reason"] = "user declined this optional scope"
        script = r"""
const fs = require("fs");
const { createReadonlyAssignments, readonlyResult, joinReadonlyResults } = require(process.argv[2]);
const request = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const plan = createReadonlyAssignments(request);
const observed = {
  execution_role: "market_researcher",
  model: "fixture-model",
  effort: "high",
  worker_id: "W1",
  session_id: "S1",
};
const first = readonlyResult(plan.instances[0], {
  status: "complete",
  result: {findings: ["MR-001"], sources: ["https://example.com/pricing"]},
  observed_identity: observed,
});
const second = readonlyResult(plan.instances[1], {
  status: "no_sources",
  result: {searched: "public pricing pages", unresolved: "No comparable public pricing was found"},
  observed_identity: {...observed, worker_id: "W2", session_id: "S2"},
});
process.stdout.write(JSON.stringify(joinReadonlyResults(plan, [second, first])));
"""
        joined = self.run_node(script, request)

        self.assertEqual("ready", joined["status"])
        self.assertEqual([], joined["blockers"])
        self.assertEqual(["Q-PRICING", "Q-CATEGORY"], [item["question_id"] for item in joined["results"]])

    def test_unrequested_effort_allows_host_default_launch_identity(self) -> None:
        request = canonical_request()
        request["requested_identity"].pop("effort")
        request["binding_required"] = True
        request["binding_requirements"] = {"authority": "parent-owned", "runtime": "readonly-sandbox"}
        script = r"""
const fs = require("fs");
const api = require(process.argv[2]);
const request = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const plan = api.createReadonlyAssignments(request);
const observed = (worker, session) => ({
  execution_role: "market_researcher",
  model: "fixture-model",
  effort: "high",
  worker_id: worker,
  session_id: session,
});
const launch = (instance, identity) => ({
  assignment_id: instance.assignment_id,
  attempt_id: instance.attempt_id,
  input_id: instance.input_id,
  authority: "parent-owned",
  runtime: "readonly-sandbox",
  reservation_id: `R-${identity.worker_id}`,
  execution_role: identity.execution_role,
  model: identity.model,
  effort: identity.effort,
  worker_id: identity.worker_id,
  session_id: identity.session_id,
});
const result = (instance, identity) => api.readonlyResult(instance, {
  status: "complete",
  result: {findings: ["MR-001"], sources: ["https://example.com/category"]},
  observed_identity: identity,
});
const identities = [observed("W1", "S1"), observed("W2", "S2")];
const records = plan.instances.map((instance, index) => launch(instance, identities[index]));
const results = plan.instances.map((instance, index) => result(instance, identities[index]));
process.stdout.write(JSON.stringify(api.joinReadonlyResults(plan, results, records)));
"""
        joined = self.run_node(script, request)

        self.assertEqual("ready", joined["status"])
        self.assertEqual({"high"}, {item["observed_identity"]["effort"] for item in joined["results"]})

    def test_host_required_launch_binding_is_separate_from_child_result_echo(self) -> None:
        request = canonical_request()
        request["binding_required"] = True
        request["binding_requirements"] = {"authority": "parent-owned", "runtime": "readonly-sandbox"}
        script = r"""
const fs = require("fs");
const api = require(process.argv[2]);
const request = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const clone = (value) => JSON.parse(JSON.stringify(value));
const plan = api.createReadonlyAssignments(request);
function observe(index, worker, session) {
  return {
    execution_role: "market_researcher",
    model: "fixture-model",
    effort: "high",
    worker_id: worker,
    session_id: session,
  };
}
function launch(observeValue, reservation, instance) {
  return {
    assignment_id: instance.assignment_id,
    attempt_id: instance.attempt_id,
    input_id: instance.input_id,
    authority: "parent-owned",
    runtime: "readonly-sandbox",
    reservation_id: reservation,
    execution_role: observeValue.execution_role,
    effort: observeValue.effort,
    model: observeValue.model,
    worker_id: observeValue.worker_id,
    session_id: observeValue.session_id,
  };
}
const firstObserved = observe(0, "W1", "S1");
const secondObserved = observe(1, "W2", "S2");
const completePayload = {
  findings: [{id: "MR-Q1", change: "pricing baseline"}],
  sources: [{publisher: "Example", url: "https://example.com/source", retrieved_at: "2026-09-29"}],
};
const first = api.readonlyResult(plan.instances[0], {
  status: "complete",
  result: clone(completePayload),
  observed_identity: firstObserved,
});
const second = api.readonlyResult(plan.instances[1], {
  status: "complete",
  result: clone(completePayload),
  observed_identity: secondObserved,
});
const records = [launch(firstObserved, "R1", plan.instances[0]), launch(secondObserved, "R2", plan.instances[1])];
const output = {joined: api.joinReadonlyResults(plan, [second, first], records), errors: []};
function expectError(operation, fragment) {
  try {
    operation();
  } catch (error) {
    if (!error.message.includes(fragment)) throw error;
    output.errors.push(error.message);
    return;
  }
  throw new Error(`expected error containing ${fragment}`);
}
expectError(
  () => api.joinReadonlyResults(plan, [{...first, launch_observation: records[0]}, second]),
  "required parent launch records",
);
const wrongAuthority = clone(records);
wrongAuthority[0].authority = "child-owned";
expectError(() => api.joinReadonlyResults(plan, [first, second], wrongAuthority), "wrong launch authority");
const echoedModel = clone(first);
echoedModel.observed_identity.model = "child-echo-model";
expectError(() => api.joinReadonlyResults(plan, [echoedModel, second], records), "wrong observed model");
const launchOnlyModel = clone(records);
launchOnlyModel[0].model = "parent-launch-model";
expectError(
  () => api.joinReadonlyResults(plan, [first, second], launchOnlyModel),
  "wrong launch model",
);
const missingLaunchEffort = clone(records);
delete missingLaunchEffort[0].effort;
expectError(
  () => api.joinReadonlyResults(plan, [first, second], missingLaunchEffort),
  "wrong launch effort",
);
const wrongLaunchEffort = clone(records);
wrongLaunchEffort[0].effort = "other-effort";
expectError(() => api.joinReadonlyResults(plan, [first, second], wrongLaunchEffort), "wrong launch effort");
expectError(
  () => api.readonlyResult(plan.instances[0], {status: "complete", result: {}, observed_identity: firstObserved}),
  "complete result requires non-empty findings and sources",
);
const emptyFindings = clone(first);
emptyFindings.result.findings = [];
expectError(
  () => api.joinReadonlyResults(plan, [emptyFindings, second], records),
  "complete requires non-empty findings and sources",
);
process.stdout.write(JSON.stringify(output));
"""
        result = self.run_node(script, request)

        self.assertEqual("ready", result["joined"]["status"])
        self.assertEqual({"W1", "W2"}, {item["observed_identity"]["worker_id"] for item in result["joined"]["results"]})
        self.assertEqual(8, len(result["errors"]))

    def test_missing_authorization_capability_and_required_results_block_without_fallback(self) -> None:
        script = r"""
const fs = require("fs");
const api = require(process.argv[2]);
const request = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const clone = (value) => JSON.parse(JSON.stringify(value));
const errors = [];
function expectError(operation, fragment) {
  try {
    operation();
  } catch (error) {
    if (!error.message.includes(fragment)) throw error;
    errors.push(error.message);
    return;
  }
  throw new Error(`expected error containing ${fragment}`);
}
for (const field of ["delegation", "readonly_tools"]) {
  const unauthorized = clone(request);
  unauthorized.authorization[field] = false;
  expectError(() => api.createReadonlyAssignments(unauthorized), "mandatory delegation is blocked");
}
const plan = api.createReadonlyAssignments(request);
const observed = {
  execution_role: "market_researcher",
  model: "fixture-model",
  effort: "high",
  worker_id: "W1",
  session_id: "S1",
};
const result = api.readonlyResult(plan.instances[0], {
  status: "complete",
  result: {findings: ["MR-001"], sources: ["https://example.com/category"]},
  observed_identity: observed,
});
expectError(() => api.joinReadonlyResults(plan, [result]), "required results are missing");
expectError(() => api.joinReadonlyResults(plan, [result, clone(result)]), "duplicate assignment_id");
const otherObserved = {...observed, worker_id: "W2", session_id: "S2"};
const otherResult = api.readonlyResult(plan.instances[1], {
  status: "complete",
  result: {findings: ["MR-002"], sources: ["https://example.com/pricing"]},
  observed_identity: otherObserved,
});
const stale = clone(result);
stale.input_id = "sha256:stale";
expectError(() => api.joinReadonlyResults(plan, [otherResult, stale]), "stale or mismatched input_id");
const oldAttempt = clone(result);
oldAttempt.attempt_id = `${oldAttempt.assignment_id}:attempt-000`;
expectError(() => api.joinReadonlyResults(plan, [otherResult, oldAttempt]), "stale or mismatched attempt_id");
const wrongQuestion = clone(result);
wrongQuestion.question_id = "Q-OTHER";
expectError(() => api.joinReadonlyResults(plan, [otherResult, wrongQuestion]), "stale or mismatched question_id");
const wrongRole = clone(result);
wrongRole.observed_identity.execution_role = "code_explorer";
expectError(() => api.joinReadonlyResults(plan, [otherResult, wrongRole]), "wrong observed execution role");
const wrongModel = clone(result);
wrongModel.observed_identity.model = "other-model";
expectError(() => api.joinReadonlyResults(plan, [otherResult, wrongModel]), "wrong observed model");
process.stdout.write(JSON.stringify({errors}));
"""
        result = self.run_node(script, canonical_request())
        self.assertEqual(9, len(result["errors"]))

    def test_explicit_block_remains_visible_and_unauthorized_skip_is_rejected(self) -> None:
        script = r"""
const fs = require("fs");
const api = require(process.argv[2]);
const request = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const plan = api.createReadonlyAssignments(request);
const observed = {
  execution_role: "market_researcher",
  model: "fixture-model",
  effort: "high",
  worker_id: "W1",
  session_id: "S1",
};
const complete = api.readonlyResult(plan.instances[0], {
  status: "complete",
  result: {findings: ["MR-001"], sources: ["https://example.com/category"]},
  observed_identity: observed,
});
const blocked = api.readonlyResult(plan.instances[1], {
  status: "blocked",
  result: {reason: "required web tool unavailable"},
  observed_identity: {...observed, worker_id: "W2", session_id: "S2"},
});
const output = {blocked: api.joinReadonlyResults(plan, [complete, blocked])};
const noSkipRequest = JSON.parse(JSON.stringify(request));
noSkipRequest.skip_allowed = false;
const noSkipPlan = api.createReadonlyAssignments(noSkipRequest);
const skipped = api.readonlyResult(noSkipPlan.instances[0], {
  status: "skipped",
  result: {reason: "not authorized"},
  observed_identity: observed,
});
try {
  api.joinReadonlyResults(noSkipPlan, [skipped, complete]);
  throw new Error("expected unauthorized skip to be rejected");
} catch (error) {
  output.unauthorizedSkip = error.message;
}
process.stdout.write(JSON.stringify(output));
"""
        result = self.run_node(script, canonical_request())

        self.assertEqual("blocked", result["blocked"]["status"])
        self.assertEqual(
            [{
                "assignment_id": result["blocked"]["results"][1]["assignment_id"],
                "reason": "required web tool unavailable",
                "reason_code": "blocked_result",
            }],
            result["blocked"]["blockers"],
        )
        self.assertIn("no authorized skip", result["unauthorizedSkip"])

    def test_capability_scoping_instance_uniqueness_and_input_revalidation(self) -> None:
        script = r"""
const fs = require("fs");
const api = require(process.argv[2]);
const request = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));
const clone = (value) => JSON.parse(JSON.stringify(value));
const errors = [];
function expectError(operation, fragment) {
  try {
    operation();
  } catch (error) {
    if (!error.message.includes(fragment)) throw error;
    errors.push(error.message);
    return;
  }
  throw new Error(`expected error containing ${fragment}`);
}
const unavailable = clone(request);
unavailable.capability.launch_runtime = false;
expectError(() => api.createReadonlyAssignments(unavailable), "capability.readonly_tools and capability.launch_runtime");

const pre = clone(request);
pre.phase = "pre_draft_research";
const prePlan = api.createReadonlyAssignments(pre);
const ui = clone(request);
ui.phase = "ui_research";
ui.execution_role = "code_explorer";
ui.requested_identity.execution_role = "code_explorer";
const uiPlan = api.createReadonlyAssignments(ui);
if (prePlan.instances[0].assignment_id === uiPlan.instances[0].assignment_id) {
  throw new Error("phase and role did not scope the assignment identity");
}
if (prePlan.instances[0].input_id === uiPlan.instances[0].input_id) {
  throw new Error("phase and role did not scope the input identity");
}

const observed = {
  execution_role: "market_researcher",
  model: "fixture-model",
  effort: "high",
  worker_id: "W1",
  session_id: "S1",
};
const first = api.readonlyResult(prePlan.instances[0], {
  status: "complete",
  result: {findings: ["MR-001"], sources: ["https://example.com/category"]},
  observed_identity: observed,
});
const reused = clone(first);
reused.assignment_id = prePlan.instances[1].assignment_id;
reused.attempt_id = prePlan.instances[1].attempt_id;
reused.question_id = prePlan.instances[1].question_id;
reused.input_id = prePlan.instances[1].input_id;
expectError(() => api.joinReadonlyResults(prePlan, [first, reused]), "reuses observed worker_id W1");
const uniqueSession = clone(reused);
uniqueSession.observed_identity.worker_id = "W2";
expectError(() => api.joinReadonlyResults(prePlan, [first, uniqueSession]), "reuses observed session_id S1");

const mutatedPlan = clone(prePlan);
mutatedPlan.instances[0].input.source_paths = ["changed-after-hash"];
const second = clone(uniqueSession);
second.observed_identity.session_id = "S2";
expectError(
  () => api.joinReadonlyResults(mutatedPlan, [first, second]),
  `plan input identity changed for ${prePlan.instances[0].assignment_id}`,
);
process.stdout.write(JSON.stringify({errors}));
"""
        result = self.run_node(script, canonical_request())
        self.assertEqual(4, len(result["errors"]))

    def test_graph_identity_branch_fans_out_and_joins_reordered_results(self) -> None:
        from test_graph_identity import PRELUDE
        script = PRELUDE + r"""
const s = setup();
const result = finish(s);
assert.throws(() => finish(s, s.results.slice(1)));
process.stdout.write(JSON.stringify({tasks: s.tasks.map(t => t.label), result}));
"""
        result = self.run_node(
            script,
            canonical_graph_request(),
            module_path=GRAPH_PATH,
            extra_args=[str(MODULE_PATH)],
        )
        self.assertEqual(
            ["prd:trace-verifier", "prd:consistency-verifier", "prd:market_researcher:Q-CATEGORY", "prd:market_researcher:Q-PRICING"],
            result["tasks"],
        )
        self.assertEqual("readonly-assignments/1", result["result"]["readonly_assignment_mode"])
        self.assertEqual("ready", result["result"]["research_join"]["status"])
        self.assertEqual(2, len(result["result"]["research"]))


if __name__ == "__main__":
    unittest.main()
