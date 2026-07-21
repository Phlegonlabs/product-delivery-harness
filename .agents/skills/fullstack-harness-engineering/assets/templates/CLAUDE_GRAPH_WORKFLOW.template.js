export const meta = {
  name: "harness-graph-wave",
  description: "Run one accepted typed-graph mission or review wave.",
  phases: [
    { title: "Execute", detail: "Run isolated write missions" },
    { title: "Review", detail: "Run SHA-bound read-only reviews" },
  ],
};

const workflowArgs = typeof args === "string" ? JSON.parse(args) : args;

if (!workflowArgs || !Array.isArray(workflowArgs.nodes) || workflowArgs.nodes.length === 0) {
  throw new Error("harness-graph-wave requires a non-empty args.nodes array");
}

for (const field of [
  "run_id",
  "plan_id",
  "plan_revision",
  "plan_digest_sha256",
  "graph_revision",
  "batch_base_sha",
  "tool_profile",
]) {
  if (workflowArgs[field] === undefined || workflowArgs[field] === null || workflowArgs[field] === "") {
    throw new Error(`harness-graph-wave is missing args.${field}`);
  }
}

const toolProfiles = {
  mission_write: new Set(["mission"]),
  code_review_readonly: new Set(["review"]),
  visual_review_readonly: new Set(["review"]),
};
const allowedNodeKinds = toolProfiles[workflowArgs.tool_profile];
if (!allowedNodeKinds) {
  throw new Error(`harness-graph-wave has unsupported tool profile ${workflowArgs.tool_profile}`);
}
if (workflowArgs.nodes.some((node) => !allowedNodeKinds.has(node.node_kind))) {
  throw new Error(`harness-graph-wave tool profile ${workflowArgs.tool_profile} does not match every node`);
}

const stringArray = { type: "array", items: { type: "string" } };
const resultSchema = {
  type: "object",
  required: ["node_result"],
  properties: {
    node_result: {
      type: "object",
      required: [
        "run_id",
        "node_id",
        "attempt_id",
        "plan_id",
        "plan_revision",
        "plan_digest_sha256",
        "graph_revision",
        "batch_base_sha",
        "status",
        "outcome",
        "worker_result",
        "refinement_request",
        "evidence_paths",
      ],
      properties: {
        run_id: { type: "string" },
        node_id: { type: "string" },
        attempt_id: { type: "string" },
        plan_id: { type: "string" },
        plan_revision: { type: "integer" },
        plan_digest_sha256: { type: "string" },
        graph_revision: { type: "integer" },
        batch_base_sha: { type: "string" },
        status: { enum: ["succeeded", "failed", "blocked"] },
        outcome: {
          enum: [
            "pass",
            "fix_required",
            "retryable_failure",
            "blocked",
            "contract_gap",
          ],
        },
        worker_result: { type: ["object", "null"] },
        refinement_request: { type: ["object", "null"] },
        evidence_paths: stringArray,
      },
      additionalProperties: false,
    },
  },
  additionalProperties: false,
};

const fallbackResult = (node) => ({
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
    evidence_paths: ["workflow-agent-null"],
  },
});

const results = await pipeline(workflowArgs.nodes, async (node) => {
  const missionFields = [
    "node_id", "attempt_id", "mission_id", "lease_id", "branch_ref", "worktree_path", "failure_outcome", "worker_prompt", "model",
  ];
  const reviewFields = [
    "node_id", "attempt_id", "review_id", "review_type", "reviewed_sha", "review_path", "review_scope", "required_evidence", "failure_outcome", "worker_prompt", "model",
  ];
  const requiredFields = node.node_kind === "mission" ? missionFields : reviewFields;
  if (!["mission", "review"].includes(node.node_kind)) {
    throw new Error("each graph node requires node_kind mission or review");
  }
  for (const field of requiredFields) {
    if (!node[field]) {
      throw new Error(`each graph ${node.node_kind} node requires ${field}`);
    }
  }
  if (!["retryable_failure", "blocked"].includes(node.failure_outcome)) {
    throw new Error("each graph node requires retryable_failure or blocked failure_outcome");
  }

  const binding = node.node_kind === "mission"
    ? `- Mission ID: ${node.mission_id}.\n` +
      `- Lease ID: ${node.lease_id}.\n` +
      `- Assigned existing worktree: ${node.worktree_path}.\n` +
      `- Before any repository read, write, or shell action, call EnterWorktree with that exact path.\n` +
      `- After entering it, verify the repository root, branch ${node.branch_ref}, and batch base ${workflowArgs.batch_base_sha}.\n` +
      `- Return blocked if EnterWorktree is unavailable or any identity does not match.\n` +
      `- Do not create a replacement worktree, edit PLAN/RUN, integrate, push, open a PR, deploy, or delegate.\n`
    : `- Review ID: ${node.review_id}.\n` +
      `- Review type: ${node.review_type}.\n` +
      `- Review exact SHA ${node.reviewed_sha} at ${node.review_path}.\n` +
      `- Before any repository read, call EnterWorktree with that exact review path.\n` +
      `- Return blocked if EnterWorktree is unavailable or does not enter that exact path.\n` +
      `- Review scope: ${node.review_scope.join(", ")}.\n` +
      `- Required evidence: ${node.required_evidence.join(", ")}.\n` +
      `- This is read-only. Do not edit files, create commits or branches, run mutating tools, or delegate.\n` +
      `- Put the reviewed SHA, findings, and evidence summary inside worker_result.\n`;

  const phaseName = node.node_kind === "mission" ? "Execute" : "Review";
  const result = await agent(
    `${node.worker_prompt}\n\n` +
      `Typed graph binding:\n` +
      `- Run ID: ${workflowArgs.run_id}.\n` +
      `- Node ID: ${node.node_id}.\n` +
      `- Attempt ID: ${node.attempt_id}.\n` +
      binding +
      `- Plan ${workflowArgs.plan_id} revision ${workflowArgs.plan_revision}; graph revision ${workflowArgs.graph_revision}.\n` +
      `- Plan digest: ${workflowArgs.plan_digest_sha256}; batch base: ${workflowArgs.batch_base_sha}.\n` +
      `- Do not wait for user input. Use contract_gap with a refinement_request when a decision is needed.\n` +
      `- Return only one node_result object accepted by the supplied schema.`,
    {
      label: node.node_id,
      phase: phaseName,
      schema: resultSchema,
      model: node.model,
      ...(node.reasoning_effort ? { effort: node.reasoning_effort } : {}),
    },
  );
  return result || fallbackResult(node);
});

return results;
