export const meta = {
  name: "harness-wave",
  description: "Run one accepted Product Delivery Harness mission wave.",
  phases: [
    { title: "Execute", detail: "Run isolated mission workers" },
  ],
};

// This is the Harness blueprint for a one-off or saved Claude Code workflow.
// The parent supplies frozen mission handoffs and allocated worktree paths.

const workflowArgs = typeof args === "string" ? JSON.parse(args) : args;

if (!workflowArgs || !Array.isArray(workflowArgs.missions) || workflowArgs.missions.length === 0) {
  throw new Error("harness-wave requires a non-empty args.missions array");
}

const requiredRunFields = [
  "plan_id",
  "plan_revision",
  "plan_digest_sha256",
  "batch_base_sha",
];
for (const field of requiredRunFields) {
  if (workflowArgs[field] === undefined || workflowArgs[field] === null || workflowArgs[field] === "") {
    throw new Error(`harness-wave is missing args.${field}`);
  }
}

const stringArray = { type: "array", items: { type: "string" } };

const taskResultSchema = {
  type: "object",
  required: [
    "task_id",
    "status",
    "head_sha",
    "verifier_ids",
    "commits",
    "evidence_paths",
  ],
  properties: {
    task_id: { type: "string" },
    status: { enum: ["worker_passed", "blocked", "worker_failed"] },
    head_sha: { type: ["string", "null"] },
    verifier_ids: stringArray,
    commits: stringArray,
    evidence_paths: stringArray,
  },
  additionalProperties: false,
};

const verifierSchema = {
  type: "object",
  required: ["id", "status", "evidence"],
  properties: {
    id: { type: "string" },
    status: { enum: ["PASS", "FAIL", "BLOCKED", "UNVALIDATED"] },
    evidence: { type: "string" },
  },
  additionalProperties: false,
};

const subagentActivitySchema = {
  type: "object",
  required: ["status", "skip_reason", "children"],
  properties: {
    // RUN-v11 is flat: every current worker reports this shape and no child
    // entries. Legacy v6-v9 manifests are validated by the compatibility path.
    status: { enum: ["not_applicable"] },
    skip_reason: { type: "string" },
    children: {
      type: "array",
      maxItems: 0,
      items: {},
    },
  },
  additionalProperties: false,
};

const workerResultSchema = {
  type: "object",
  required: ["worker_result"],
  properties: {
    worker_result: {
      type: "object",
      required: [
        "type",
        "run_id",
        "plan_id",
        "mission_id",
        "lease_id",
        "status",
        "current_task_id",
        "plan_revision",
        "plan_digest_sha256",
        "base_sha",
        "head_sha",
        "diff_summary",
        "changed_files",
        "task_results",
        "verifiers",
        "commits",
        "evidence_paths",
        "subagent_activity",
        "blockers",
        "residual_risks",
        "integration_notes",
      ],
      properties: {
        type: { enum: ["WORKER_RESULT"] },
        run_id: { type: "string" },
        plan_id: { type: "string" },
        mission_id: { type: "string" },
        lease_id: { type: "string" },
        status: { enum: ["worker_passed", "blocked", "worker_failed"] },
        current_task_id: { type: ["string", "null"] },
        plan_revision: { type: "integer" },
        plan_digest_sha256: { type: "string" },
        base_sha: { type: "string" },
        head_sha: { type: ["string", "null"] },
        diff_summary: { type: "string" },
        changed_files: stringArray,
        task_results: { type: "array", items: taskResultSchema },
        verifiers: { type: "array", items: verifierSchema },
        commits: stringArray,
        evidence_paths: stringArray,
        subagent_activity: subagentActivitySchema,
        blockers: stringArray,
        residual_risks: stringArray,
        integration_notes: { type: "string" },
      },
      additionalProperties: false,
    },
  },
  additionalProperties: false,
};

const refinementRequestSchema = {
  type: "object",
  required: [
    "type",
    "run_id",
    "plan_id",
    "mission_id",
    "task_id",
    "plan_revision",
    "plan_digest_sha256",
    "lease_id",
    "observed_head_sha",
    "reason",
    "proposed_children",
    "acceptance_matrix_items",
    "scope_or_contract_gap",
    "evidence",
  ],
  properties: {
    type: { enum: ["REFINEMENT_REQUEST"] },
    run_id: { type: "string" },
    plan_id: { type: "string" },
    mission_id: { type: "string" },
    task_id: { type: "string" },
    plan_revision: { type: "integer" },
    plan_digest_sha256: { type: "string" },
    lease_id: { type: "string" },
    observed_head_sha: { type: "string" },
    reason: { type: "string" },
    proposed_children: {
      type: "array",
      items: {
        type: "object",
        required: ["alias", "deliverable", "trace_ids", "write_scope", "verifiers"],
        properties: {
          alias: { type: "string" },
          deliverable: { type: "string" },
          trace_ids: stringArray,
          write_scope: stringArray,
          verifiers: {
            type: "array",
            items: {
              type: "object",
              required: ["id", "cwd", "argv", "pass_signal"],
              properties: {
                id: { type: "string" },
                cwd: { type: "string" },
                argv: stringArray,
                pass_signal: { type: "string" },
              },
              additionalProperties: false,
            },
          },
        },
        additionalProperties: false,
      },
    },
    acceptance_matrix_items: stringArray,
    scope_or_contract_gap: { type: ["string", "null"] },
    evidence: stringArray,
  },
  additionalProperties: false,
};

const resultSchema = {
  oneOf: [workerResultSchema, refinementRequestSchema],
};

phase("Execute");
const results = await pipeline(workflowArgs.missions, (mission) => {
  if (
    !mission.mission_id ||
    !mission.lease_id ||
    !mission.branch_ref ||
    !mission.worker_prompt ||
    !mission.worktree_path ||
    !mission.model
  ) {
    throw new Error(
      "each mission requires mission_id, lease_id, branch_ref, worker_prompt, worktree_path, and model",
    );
  }

  return agent(
    `${mission.worker_prompt}\n\n` +
      `Claude Dynamic Workflow binding:\n` +
      `- Work only inside ${mission.worktree_path}.\n` +
      `- Mission ID: ${mission.mission_id}.\n` +
      `- Lease ID: ${mission.lease_id}.\n` +
      `- Branch ref: ${mission.branch_ref}.\n` +
      `- Plan: ${workflowArgs.plan_id} revision ${workflowArgs.plan_revision}.\n` +
      `- Plan digest: ${workflowArgs.plan_digest_sha256}.\n` +
      `- Batch base: ${workflowArgs.batch_base_sha}.\n` +
      `- Treat this prompt as the complete live task and do not reconstruct the parent transcript.\n` +
      `- Before any read, write, or shell action, enter the existing worktree at ${mission.worktree_path}.\n` +
      `- Do not create another worktree or write in the parent checkout; return blocked if the binding fails.\n` +
      `- Do not edit PLAN.md or RUN.md.\n` +
      `- Do not spawn or delegate; this workflow owns the flat orchestration.\n` +
      `- Do not wait for mid-run user input. Return REFINEMENT_REQUEST when a decision is required.\n` +
      `- Otherwise return the complete Worker Result Manifest object from your handoff.\n` +
      `- Return only one structured object accepted by the supplied schema.`,
    {
      label: mission.mission_id,
      phase: "Execute",
      schema: resultSchema,
      model: mission.model,
      ...(mission.reasoning_effort ? { effort: mission.reasoning_effort } : {}),
    },
  );
});

return results;
