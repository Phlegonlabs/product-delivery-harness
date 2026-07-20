export const meta = {
  name: "design-package-builder-graph",
  description: "Draft and cross-check one design package from frozen product inputs.",
  phases: [
    { title: "Analyze", detail: "Run visual, system, icon, motion, and page roles" },
    { title: "Synthesize", detail: "Join role outputs into one design package" },
    { title: "Verify", detail: "Cross-check taste, traceability, and consistency" },
  ],
};

const workflowArgs = typeof args === "string" ? JSON.parse(args) : args;

for (const field of ["run_id", "product_name", "product_archetype"]) {
  if (!workflowArgs || typeof workflowArgs[field] !== "string" || !workflowArgs[field].trim()) {
    throw new Error(`design-package-builder-graph requires non-empty args.${field}`);
  }
}
if (!Array.isArray(workflowArgs.source_paths)) {
  throw new Error("design-package-builder-graph requires args.source_paths as an array");
}
for (const field of ["icons_in_scope", "motion_in_scope"]) {
  if (typeof workflowArgs[field] !== "boolean") {
    throw new Error(`design-package-builder-graph requires boolean args.${field}`);
  }
}
if (workflowArgs.tool_profile !== "builder_readonly") {
  throw new Error("design-package-builder-graph requires args.tool_profile builder_readonly");
}

const stringArray = { type: "array", items: { type: "string" } };
const laneSchema = {
  type: "object",
  required: ["role", "status", "decisions", "ds_ids", "assumptions", "open_questions", "evidence"],
  properties: {
    role: { type: "string" },
    status: { enum: ["complete", "blocked"] },
    decisions: { type: "array", items: { type: "object" } },
    ds_ids: stringArray,
    assumptions: stringArray,
    open_questions: stringArray,
    evidence: stringArray,
  },
  additionalProperties: false,
};
const packageSchema = {
  type: "object",
  required: [
    "design_system_markdown",
    "page_ui_matrix_markdown",
    "ui_mockups_markdown",
    "visual_acceptance_markdown",
    "motion_showcase_html",
    "trace_index",
    "assumptions",
    "open_questions",
    "unresolved_conflicts",
  ],
  properties: {
    design_system_markdown: { type: "string" },
    page_ui_matrix_markdown: { type: "string" },
    ui_mockups_markdown: { type: "string" },
    visual_acceptance_markdown: { type: "string" },
    motion_showcase_html: { type: ["string", "null"] },
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
  product_archetype: workflowArgs.product_archetype,
  source_paths: workflowArgs.source_paths,
  source_summary: workflowArgs.source_summary || "",
  builder_ux_direction: workflowArgs.builder_ux_direction || null,
  brand_constraints: workflowArgs.brand_constraints || [],
  icons_in_scope: workflowArgs.icons_in_scope,
  motion_in_scope: workflowArgs.motion_in_scope,
});

const roles = [
  {
    key: "visual-thesis-content",
    task: "Define the product-specific visual thesis, taste statement, signature decisions, anti-patterns, container/border logic, realistic content rules, and landing-page restraint.",
  },
  {
    key: "system-components",
    task: "Define tokens, typography, spacing, layout, components, states, code references, accessibility, and stable DS IDs tied to upstream traces.",
  },
  {
    key: "page-coverage",
    task: "Map every important route to breakpoints, states, components, data, mockup content contracts, asset needs, and visual acceptance evidence.",
  },
];
if (workflowArgs.icons_in_scope) {
  roles.push({
    key: "iconography",
    task: "Use current official sources to compare icon families, test semantic coverage, and define the chosen source, tokens, exceptions, implementation, and accessibility rules.",
  });
}
if (workflowArgs.motion_in_scope) {
  roles.push({
    key: "motion",
    task: "Define motion purposes, stack, tokens, patterns, hero choreography when applicable, interruption, performance, responsive behavior, and reduced-motion fallbacks.",
  });
}

phase("Analyze");
const rawLanes = await parallel(roles.map((role) => () => agent(
  `You are the ${role.key} role in a design org graph.\n` +
    `${role.task}\n\n` +
    `Frozen task context: ${sourceContext}\n\n` +
    "Read only. Do not edit, create, move, or publish files. Preserve upstream facts and exact wording, label assumptions, and return only the structured role result.",
  { label: `design:${role.key}`, phase: "Analyze", schema: laneSchema },
)));
const lanes = rawLanes.map((result, index) => (
  result && result.role === roles[index].key
    ? result
    : {
        role: roles[index].key,
        status: "blocked",
        decisions: [],
        ds_ids: [],
        assumptions: [],
        open_questions: [`The ${roles[index].key} workflow agent returned no result or the wrong role.`],
        evidence: [result ? "workflow-role-mismatch" : "workflow-agent-null"],
      }
));

phase("Synthesize");
const designPackage = await agent(
  "You are the synthesis role in a design org graph. Reconcile the role results into complete Markdown bodies for design-system.md, page-ui-matrix.md, ui-mockups.md, and visual-acceptance.md. " +
    "Return a motion showcase only when motion is in scope. Preserve upstream PRD/ARCH/UI/UX/TEST IDs, mint stable DS IDs, keep assumptions explicit, and do not claim rendered visual or usability validation. " +
    `Frozen task context: ${sourceContext}\n\nRole results: ${JSON.stringify(lanes)}`,
  { label: "design:synthesis", phase: "Synthesize", schema: packageSchema },
);
if (!designPackage) {
  throw new Error("design-package-builder-graph synthesis agent did not return a result");
}

const reviewers = [
  {
    key: "taste-verifier",
    task: "Check that the taste statement is concrete, signature decisions recur, unsupported AI-UI patterns are absent, content is realistic, and every border/elevation/media/motion choice has a purpose.",
  },
  {
    key: "trace-verifier",
    task: "Check upstream trace preservation, DS ID stability, route/breakpoint/state coverage, internal consistency, and evidence claims across all four artifacts.",
  },
];
phase("Verify");
const rawReviews = await parallel(reviewers.map((reviewer) => () => agent(
  `You are the ${reviewer.key} role in a design org graph. ${reviewer.task}\n` +
    "Read only. Return fix_required for any material issue and blocked when a human decision or missing source prevents a valid package. " +
    `Frozen task context: ${sourceContext}\n\nDraft design package: ${JSON.stringify(designPackage)}`,
  { label: `design:${reviewer.key}`, phase: "Verify", schema: reviewSchema },
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
  design_package: designPackage,
  reviews,
};
