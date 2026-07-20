export const meta = {
  name: "harness-codex-graph-wave",
  description: "Run one typed-graph wave through isolated cc-codex agents.",
  phases: [
    { title: "Execute", detail: "Run isolated Codex write missions" },
  ],
};

const workflowArgs = typeof args === "string" ? JSON.parse(args) : args;

for (const field of [
  "run_id",
  "plan_id",
  "plan_revision",
  "plan_digest_sha256",
  "graph_revision",
  "batch_base_sha",
  "tool_profile",
]) {
  if (!workflowArgs || workflowArgs[field] === undefined || workflowArgs[field] === null || workflowArgs[field] === "") {
    throw new Error(`harness-codex-graph-wave is missing args.${field}`);
  }
}
if (!Array.isArray(workflowArgs.nodes) || workflowArgs.nodes.length === 0) {
  throw new Error("harness-codex-graph-wave requires a non-empty args.nodes array");
}
const modelToken = /^[A-Za-z0-9][A-Za-z0-9._-]*$/;
const reasoningEfforts = new Set(["none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra"]);
if (
  workflowArgs.model !== null &&
  workflowArgs.model !== undefined &&
  (typeof workflowArgs.model !== "string" || !modelToken.test(workflowArgs.model))
) {
  throw new Error("harness-codex-graph-wave args.model must be null or a safe model token");
}
if (
  workflowArgs.reasoning_effort !== null &&
  workflowArgs.reasoning_effort !== undefined &&
  (typeof workflowArgs.reasoning_effort !== "string" || !reasoningEfforts.has(workflowArgs.reasoning_effort))
) {
  throw new Error("harness-codex-graph-wave args.reasoning_effort has an unsupported value");
}
if (workflowArgs.tool_profile !== "mission_write") {
  throw new Error("harness-codex-graph-wave supports mission_write only");
}
if (workflowArgs.nodes.some((node) => !node || node.node_kind !== "mission")) {
  throw new Error("harness-codex-graph-wave supports mission nodes only");
}

const beginMarker = "HARNESS_NODE_RESULT_V1_BEGIN";
const endMarker = "HARNESS_NODE_RESULT_V1_END";
const exactNodeResultFields = [
  "attempt_id",
  "batch_base_sha",
  "evidence_paths",
  "graph_revision",
  "node_id",
  "outcome",
  "plan_digest_sha256",
  "plan_id",
  "plan_revision",
  "refinement_request",
  "run_id",
  "status",
  "worker_result",
].sort();
const exactRuntimeEvidenceFields = ["branch_ref", "head_sha", "worktree_path"].sort();

const fallbackResult = (node, reason) => ({
  node_result: {
    run_id: workflowArgs.run_id,
    node_id: node.node_id,
    attempt_id: node.attempt_id,
    plan_id: workflowArgs.plan_id,
    plan_revision: workflowArgs.plan_revision,
    plan_digest_sha256: workflowArgs.plan_digest_sha256,
    graph_revision: workflowArgs.graph_revision,
    batch_base_sha: workflowArgs.batch_base_sha,
    status: node.failure_outcome === "retryable_failure" ? "failed" : "blocked",
    outcome: node.failure_outcome,
    worker_result: null,
    refinement_request: null,
    evidence_paths: [reason],
  },
  runtime_evidence: null,
});

const validateCandidate = (node, candidate) => {
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) {
    throw new Error("marked result must be an object");
  }
  if (Object.keys(candidate).sort().join(",") !== "node_result,runtime_evidence") {
    throw new Error("marked result must contain only node_result and runtime_evidence");
  }
  const result = candidate.node_result;
  if (
    !result ||
    typeof result !== "object" ||
    Array.isArray(result) ||
    Object.keys(result).sort().join(",") !== exactNodeResultFields.join(",")
  ) {
    throw new Error("node_result has the wrong fields");
  }
  const identities = {
    run_id: workflowArgs.run_id,
    node_id: node.node_id,
    attempt_id: node.attempt_id,
    plan_id: workflowArgs.plan_id,
    plan_revision: workflowArgs.plan_revision,
    plan_digest_sha256: workflowArgs.plan_digest_sha256,
    graph_revision: workflowArgs.graph_revision,
    batch_base_sha: workflowArgs.batch_base_sha,
  };
  for (const [field, expected] of Object.entries(identities)) {
    if (result[field] !== expected) {
      throw new Error(`node_result.${field} does not match the immutable wave`);
    }
  }
  const allowedStatusOutcomes = {
    succeeded: new Set(["pass", "fix_required"]),
    failed: new Set(["retryable_failure"]),
    blocked: new Set(["blocked", "contract_gap"]),
  };
  if (!allowedStatusOutcomes[result.status] || !allowedStatusOutcomes[result.status].has(result.outcome)) {
    throw new Error("node_result status and outcome do not match");
  }
  if (!Array.isArray(result.evidence_paths) || result.evidence_paths.some((item) => typeof item !== "string" || !item)) {
    throw new Error("node_result.evidence_paths must contain non-empty strings");
  }
  if (result.outcome === "contract_gap") {
    if (!result.refinement_request || typeof result.refinement_request !== "object") {
      throw new Error("contract_gap requires a refinement_request");
    }
  } else if (result.refinement_request !== null) {
    throw new Error("refinement_request must be null without contract_gap");
  }
  const runtimeEvidence = candidate.runtime_evidence;
  if (
    !runtimeEvidence ||
    typeof runtimeEvidence !== "object" ||
    Array.isArray(runtimeEvidence) ||
    Object.keys(runtimeEvidence).sort().join(",") !== exactRuntimeEvidenceFields.join(",")
  ) {
    throw new Error("runtime_evidence has the wrong fields");
  }
  for (const field of exactRuntimeEvidenceFields) {
    if (typeof runtimeEvidence[field] !== "string" || !runtimeEvidence[field]) {
      throw new Error(`runtime_evidence.${field} must be a non-empty string`);
    }
  }
  if (node.node_kind === "mission" && result.status === "succeeded") {
    if (!result.worker_result || typeof result.worker_result !== "object") {
      throw new Error("a succeeded mission requires worker_result");
    }
    if (result.worker_result.mission_id !== node.mission_id) {
      throw new Error("worker_result.mission_id does not match the mission");
    }
    if (result.worker_result.lease_id !== node.lease_id) {
      throw new Error("worker_result.lease_id does not match the lease");
    }
    if (result.worker_result.base_sha !== workflowArgs.batch_base_sha) {
      throw new Error("worker_result.base_sha does not match the batch base");
    }
    if (result.worker_result.head_sha !== runtimeEvidence.head_sha) {
      throw new Error("worker_result.head_sha does not match runtime evidence");
    }
  }
  return candidate;
};

const parseResult = (node, rawResult) => {
  if (typeof rawResult !== "string") {
    throw new Error("cc-codex agent did not return text");
  }
  if (
    rawResult.split(beginMarker).length !== 2 ||
    rawResult.split(endMarker).length !== 2 ||
    rawResult.indexOf(beginMarker) > rawResult.indexOf(endMarker)
  ) {
    throw new Error("cc-codex agent returned missing or duplicate result markers");
  }
  const payloadText = rawResult
    .slice(rawResult.indexOf(beginMarker) + beginMarker.length, rawResult.indexOf(endMarker))
    .trim();
  return validateCandidate(node, JSON.parse(payloadText));
};

const routeFlags = ["--wait", "--fresh"];
if (workflowArgs.model) {
  routeFlags.push("--model", workflowArgs.model);
}
if (workflowArgs.reasoning_effort) {
  routeFlags.push("--effort", workflowArgs.reasoning_effort);
}

const results = await pipeline(workflowArgs.nodes, async (node) => {
  for (const field of ["node_id", "attempt_id", "node_kind", "failure_outcome", "worker_prompt"]) {
    if (!node[field]) {
      throw new Error(`each cc-codex graph node requires ${field}`);
    }
  }
  if (!new Set(["retryable_failure", "blocked"]).has(node.failure_outcome)) {
    throw new Error("each cc-codex graph node requires a workflow failure outcome");
  }

  for (const field of ["mission_id", "lease_id", "write_scope", "deny_scope", "task_ids", "verifier_ids"]) {
    if (node[field] === undefined || node[field] === null) {
      throw new Error(`each cc-codex mission requires ${field}`);
    }
  }
  const binding =
    `This is write-capable mission ${node.mission_id} under lease ${node.lease_id}.\n` +
    `Your current working directory is the assigned Claude-managed isolated worktree. Before editing, verify its initial HEAD is exactly ${workflowArgs.batch_base_sha}; if not, return blocked without changing files.\n` +
    `Do not switch branches, pull, fetch-and-merge, rebase, merge, create another worktree, or delegate to another agent.\n` +
    `Write scope: ${JSON.stringify(node.write_scope)}. Deny scope: ${JSON.stringify(node.deny_scope)}. Never edit PLAN.md or RUN.md.\n` +
    `Tasks: ${JSON.stringify(node.task_ids)}. Required verifiers: ${JSON.stringify(node.verifier_ids)}.\n` +
    `A successful isolated handoff requires durable commits, with every commit attributed to exactly one task and the final commit equal to worker_result.head_sha.\n` +
    `Do not integrate, push, open or modify a PR, deploy, clean up worktrees, or delete branches.\n` +
    `Report worker_passed only. The parent alone may validate and mark integrated.\n`;

  const prompt =
    `${routeFlags.join(" ")}\n` +
    `${node.worker_prompt}\n\n` +
    `Typed graph binding:\n` +
    `Run ${workflowArgs.run_id}; node ${node.node_id}; attempt ${node.attempt_id}.\n` +
    `Plan ${workflowArgs.plan_id} revision ${workflowArgs.plan_revision}; graph revision ${workflowArgs.graph_revision}.\n` +
    `Plan digest ${workflowArgs.plan_digest_sha256}; fixed batch base ${workflowArgs.batch_base_sha}.\n` +
    binding +
    `Do not wait for user input. Return contract_gap with REFINEMENT_REQUEST when a decision is required.\n` +
    `Your final message must contain exactly one marked JSON result. The marked object must contain only node_result and runtime_evidence. ` +
    `node_result must use the exact Harness typed-node fields. runtime_evidence must contain non-empty worktree_path, branch_ref, and head_sha observed from Git. ` +
    `A mission worker_result must use the WORKER_RESULT contract, include changed_files, task and verifier evidence, durable commit SHAs, and subagent_activity with status not_applicable and no children.\n` +
    `Output ${beginMarker}, then the JSON object, then ${endMarker}. Do not place either marker anywhere else.`;

  const agentOptions = {
    label: node.node_id,
    phase: "Execute",
    agentType: "codex:codex-rescue",
    isolation: "worktree",
  };

  const rawResult = await agent(prompt, agentOptions);
  if (rawResult === null || rawResult === undefined) {
    return fallbackResult(node, "codex-agent-null");
  }
  try {
    return parseResult(node, rawResult);
  } catch (error) {
    return fallbackResult(node, `codex-result-invalid:${error.message}`);
  }
});

return results;
