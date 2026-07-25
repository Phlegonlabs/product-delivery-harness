export const meta = {
  name: "prd-builder-graph",
  description: "Draft and cross-check one PRD package from frozen discovery inputs.",
  phases: [
    { title: "Analyze", detail: "Run product, architecture, UX, platform, and backend roles" },
    { title: "Synthesize", detail: "Join role outputs into one PRD package" },
    { title: "Verify", detail: "Cross-check trace coverage and consistency" },
  ],
};

const workflowArgs = typeof args === "string" ? JSON.parse(args) : args;

for (const field of ["run_id", "product_name", "interview_summary"]) {
  if (!workflowArgs || typeof workflowArgs[field] !== "string" || !workflowArgs[field].trim()) {
    throw new Error(`prd-builder-graph requires non-empty args.${field}`);
  }
}
if (!Array.isArray(workflowArgs.product_archetypes) || workflowArgs.product_archetypes.length === 0) {
  throw new Error("prd-builder-graph requires a non-empty args.product_archetypes array");
}
if (!Array.isArray(workflowArgs.source_paths)) {
  throw new Error("prd-builder-graph requires args.source_paths as an array");
}
if (typeof workflowArgs.browser_frontend !== "boolean") {
  throw new Error("prd-builder-graph requires boolean args.browser_frontend");
}
if (typeof workflowArgs.ui_bearing !== "boolean") {
  throw new Error("prd-builder-graph requires boolean args.ui_bearing");
}
if (typeof workflowArgs.has_backend !== "boolean") {
  throw new Error("prd-builder-graph requires boolean args.has_backend");
}
if (typeof workflowArgs.has_public_marketing_content !== "boolean") {
  throw new Error("prd-builder-graph requires boolean args.has_public_marketing_content");
}
if (typeof workflowArgs.include_implementation_plan !== "boolean") {
  throw new Error("prd-builder-graph requires boolean args.include_implementation_plan");
}
if (workflowArgs.tool_profile !== "builder_readonly") {
  throw new Error("prd-builder-graph requires args.tool_profile builder_readonly");
}
if (workflowArgs.ui_bearing && (typeof workflowArgs.builder_ux_direction !== "string" || !workflowArgs.builder_ux_direction.trim())) {
  throw new Error("prd-builder-graph requires non-empty args.builder_ux_direction for a ui_bearing product");
}
if (workflowArgs.browser_frontend && (typeof workflowArgs.deployment_platform !== "string" || !workflowArgs.deployment_platform.trim())) {
  throw new Error("prd-builder-graph requires non-empty args.deployment_platform for a browser_frontend product");
}

const stringArray = { type: "array", items: { type: "string" } };
const laneSchema = {
  type: "object",
  required: ["role", "status", "sections", "trace_ids", "assumptions", "open_questions", "evidence"],
  properties: {
    role: { type: "string" },
    status: { enum: ["complete", "blocked"] },
    sections: { type: "array", items: { type: "object" } },
    trace_ids: stringArray,
    assumptions: stringArray,
    open_questions: stringArray,
    evidence: stringArray,
  },
  additionalProperties: false,
};
const draftSchema = {
  type: "object",
  required: [
    "prd_markdown",
    "architecture_markdown",
    "stack_decisions_markdown",
    "wireframes_markdown",
    "implementation_plan_markdown",
    "trace_index",
    "assumptions",
    "open_questions",
    "unresolved_conflicts",
  ],
  properties: {
    prd_markdown: { type: "string" },
    architecture_markdown: { type: "string" },
    stack_decisions_markdown: { type: "string" },
    wireframes_markdown: { type: "string" },
    implementation_plan_markdown: { type: ["string", "null"] },
    trace_index: { type: "array", items: { type: "object" } },
    assumptions: stringArray,
    open_questions: stringArray,
    unresolved_conflicts: stringArray,
  },
  additionalProperties: false,
};
const reviewSchema = {
  type: "object",
  required: ["role", "decision", "findings", "evidence"],
  properties: {
    role: { type: "string" },
    decision: { enum: ["pass", "fix_required", "blocked"] },
    findings: stringArray,
    evidence: stringArray,
  },
  additionalProperties: false,
};

const sourceContext = JSON.stringify({
  run_id: workflowArgs.run_id,
  product_name: workflowArgs.product_name,
  product_archetypes: workflowArgs.product_archetypes,
  source_paths: workflowArgs.source_paths,
  source_summary: workflowArgs.source_summary || "",
  interview_summary: workflowArgs.interview_summary,
  builder_ux_direction: workflowArgs.builder_ux_direction || null,
  ui_bearing: workflowArgs.ui_bearing,
  browser_frontend: workflowArgs.browser_frontend,
  deployment_platform: workflowArgs.deployment_platform || null,
  mobile_desktop_platform: workflowArgs.mobile_desktop_platform || null,
  has_backend: workflowArgs.has_backend,
  include_implementation_plan: workflowArgs.include_implementation_plan,
  has_public_marketing_content: workflowArgs.has_public_marketing_content,
});

const roles = [
  {
    key: "requirements",
    task: "Extract product goals, non-goals, personas, journeys, requirements, acceptance signals, metrics, risks, assumptions, and stable PRD/TEST trace IDs.",
  },
  {
    key: "architecture",
    task: "Define implementation-ready components, data, APIs, integrations, auth, security, deployment, observability, scaling, failure handling, and stable ARCH trace IDs without inventing product scope. Build the deployment and environment contract on the supplied deployment_platform; never substitute or invent a platform.",
  },
  {
    key: "ux-wireframe",
    task: "Define UX obligations, routes, states, exact wording or bounded display contracts, low-fidelity wireframe structure, Builder UX Direction consequences, and stable UX/UI trace IDs.",
  },
];
if (workflowArgs.browser_frontend || workflowArgs.mobile_desktop_platform) {
  roles.push({
    key: "frontend-platform",
    task: "Recommend or preserve one explicit browser stack and rendering/platform strategy, separate technology layers, identify official-source checks, and leave unresolved decisions explicit. When a mobile or desktop target is in scope, also cover the Mobile/Desktop Technology Decision layers — platform, toolchain, distribution, backend/API integration, push/offline sync, testing — on the supplied mobile_desktop_platform; never substitute or invent a platform.",
  });
}
if (workflowArgs.has_backend) {
  roles.push({
    key: "backend",
    task: "Recommend or preserve one explicit backend runtime/framework, database category and engine, and auth strategy and provider, separate technology layers, map data entities to stores, identify official-source checks, and leave unresolved decisions explicit for the Backend and Data Technology Decision section.",
  });
}

phase("Analyze");
const rawLanes = await parallel(roles.map((role) => () => agent(
  `You are the ${role.key} role in a PRD org graph.\n` +
    `${role.task}\n\n` +
    `Frozen task context: ${sourceContext}\n\n` +
    "Read only. Do not edit, create, move, or publish files. Preserve supplied facts, label assumptions, and return only the structured role result.",
  { label: `prd:${role.key}`, phase: "Analyze", schema: laneSchema },
)));
const lanes = rawLanes.map((result, index) => (
  result && result.role === roles[index].key
    ? result
    : {
        role: roles[index].key,
        status: "blocked",
        sections: [],
        trace_ids: [],
        assumptions: [],
        open_questions: [`The ${roles[index].key} workflow agent returned no result or the wrong role.`],
        evidence: [result ? "workflow-role-mismatch" : "workflow-agent-null"],
      }
));

phase("Synthesize");
const draft = await agent(
  "You are the synthesis role in a PRD org graph. Reconcile the role results into complete Markdown bodies for PRD.md, architecture.md, stack-decisions.md, and wireframes.md, plus implementation-plan.md only when requested. " +
    "Preserve stable PRD, ARCH, UI, UX, and TEST IDs; do not hide conflicts or failed lanes; do not claim publication or visual/user validation. " +
    "Follow the output contract's \"How To Read This Package\": open each document with human-readable content and close it with the ID matrices and decision records, respect the per-file length budget, and keep every table at seven columns or fewer. " +
    `Frozen task context: ${sourceContext}\n\nRole results: ${JSON.stringify(lanes)}`,
  { label: "prd:synthesis", phase: "Synthesize", schema: draftSchema },
);
if (!draft) {
  throw new Error("prd-builder-graph synthesis agent did not return a result");
}

const reviewers = [
  {
    key: "trace-verifier",
    task: "Check every must-have requirement and major architecture, UI, UX, and test obligation for stable cross-document trace coverage.",
  },
  {
    key: "consistency-verifier",
    task: "Check all four documents for contradictory scope, unsupported claims, missing states, hidden assumptions, and invalid implementation or usability claims.",
  },
];
if (workflowArgs.has_public_marketing_content) {
  reviewers.push({
    key: "seo-copy-verifier",
    task: "Review the exact wording on public marketing, landing, or SEO-relevant screens only: headline/H1 clarity and keyword relevance without stuffing, a usable heading hierarchy for search crawlers, a meta-description-worthy summary, descriptive non-generic alt text or DISPLAY contracts for images, and internal-link or content-depth opportunities. Do not review internal-tool, dashboard, or authenticated-only screens against SEO criteria.",
  });
}
phase("Verify");
const rawReviews = await parallel(reviewers.map((reviewer) => () => agent(
  `You are the ${reviewer.key} role in a PRD org graph. ${reviewer.task}\n` +
    "Read only. Return fix_required for any material issue and blocked when a human decision or missing source prevents a valid package. " +
    `Frozen task context: ${sourceContext}\n\nDraft package: ${JSON.stringify(draft)}`,
  { label: `prd:${reviewer.key}`, phase: "Verify", schema: reviewSchema },
)));
const reviews = rawReviews.map((result, index) => (
  result && result.role === reviewers[index].key
    ? result
    : {
        role: reviewers[index].key,
        decision: "blocked",
        findings: [`The ${reviewers[index].key} workflow agent returned no result or the wrong role.`],
        evidence: [result ? "workflow-role-mismatch" : "workflow-agent-null"],
      }
));

return {
  run_id: workflowArgs.run_id,
  status: lanes.some((lane) => lane.status !== "complete") || reviews.some((review) => review.decision !== "pass")
    ? "needs_revision"
    : "candidate_ready",
  lanes,
  draft,
  reviews,
};
