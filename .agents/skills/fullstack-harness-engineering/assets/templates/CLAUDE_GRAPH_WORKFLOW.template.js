export const meta = {
  name: "harness-graph-wave",
  description: "Run one accepted typed-graph mission or review wave.",
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
]) {
  if (workflowArgs[field] === undefined || workflowArgs[field] === null || workflowArgs[field] === "") {
    throw new Error(`harness-graph-wave is missing args.${field}`);
  }
}

const stringArray = { type: "array", items: { type: "string" } };
const resultSchema = {
  type: "object",
  required: ["node_result"],
  properties: {
    node_result: {
      type: "object",
      required: [
        "node_id",
        "attempt_id",
        "plan_id",
        "plan_revision",
        "plan_digest_sha256",
        "graph_revision",
        "status",
        "outcome",
        "worker_result",
        "refinement_request",
        "evidence_paths",
      ],
      properties: {
        node_id: { type: "string" },
        attempt_id: { type: "string" },
        plan_id: { type: "string" },
        plan_revision: { type: "integer" },
        plan_digest_sha256: { type: "string" },
        graph_revision: { type: "integer" },
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

const results = await pipeline(workflowArgs.nodes, (node) => {
  const missionFields = [
    "node_id", "attempt_id", "mission_id", "lease_id", "branch_ref", "worktree_path", "worker_prompt",
  ];
  const reviewFields = [
    "node_id", "attempt_id", "review_id", "reviewed_sha", "review_path", "review_scope", "required_evidence", "worker_prompt",
  ];
  const requiredFields = node.node_kind === "mission" ? missionFields : reviewFields;
  if (!['mission', 'review'].includes(node.node_kind)) {
    throw new Error("each graph node requires node_kind mission or review");
  }
  for (const field of requiredFields) {
    if (!node[field]) {
      throw new Error(`each graph ${node.node_kind} node requires ${field}`);
    }
  }

  const binding = node.node_kind === "mission"
    ? `- Mission ID: ${node.mission_id}.\n` +
      `- Lease ID: ${node.lease_id}.\n` +
      `- Work only inside ${node.worktree_path} on ${node.branch_ref}.\n` +
      `- Enter the existing worktree before any repository action. Return blocked if it does not match.\n` +
      `- Do not create worktrees, edit PLAN/RUN, integrate, push, open a PR, deploy, or delegate.\n`
    : `- Review ID: ${node.review_id}.\n` +
      `- Review exact SHA ${node.reviewed_sha} at ${node.review_path}.\n` +
      `- Review scope: ${node.review_scope.join(", ")}.\n` +
      `- Required evidence: ${node.required_evidence.join(", ")}.\n` +
      `- This is read-only. Do not edit files, create commits or branches, run mutating tools, or delegate.\n` +
      `- Put the reviewed SHA, findings, and evidence summary inside worker_result.\n`;

  return agent(
    `${node.worker_prompt}\n\n` +
      `Typed graph binding:\n` +
      `- Node ID: ${node.node_id}.\n` +
      `- Attempt ID: ${node.attempt_id}.\n` +
      binding +
      `- Plan ${workflowArgs.plan_id} revision ${workflowArgs.plan_revision}; graph revision ${workflowArgs.graph_revision}.\n` +
      `- Plan digest: ${workflowArgs.plan_digest_sha256}; batch base: ${workflowArgs.batch_base_sha}.\n` +
      `- Do not wait for user input. Use contract_gap with a refinement_request when a decision is needed.\n` +
      `- Return only one node_result object accepted by the supplied schema.`,
    { label: node.node_id, schema: resultSchema },
  );
});

return results;
