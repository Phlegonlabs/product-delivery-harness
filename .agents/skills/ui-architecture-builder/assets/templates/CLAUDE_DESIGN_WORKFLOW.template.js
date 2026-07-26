export const meta = {
  name: "ui-architecture-builder-graph",
  description: "Draft and cross-check one UI architecture specification from frozen product inputs.",
  phases: [
    { title: "Analyze", detail: "Run visual, contract, system, primitive, icon, motion, recipe, and page roles" },
    { title: "Synthesize", detail: "Join role outputs into one UI architecture and its registry" },
    { title: "Verify", detail: "Cross-check taste, traceability, and registry/recipe consistency" },
  ],
};

const workflowArgs = typeof args === "string" ? JSON.parse(args) : args;

for (const field of ["run_id", "product_name", "product_archetype"]) {
  if (!workflowArgs || typeof workflowArgs[field] !== "string" || !workflowArgs[field].trim()) {
    throw new Error(`ui-architecture-builder-graph requires non-empty args.${field}`);
  }
}
if (!Array.isArray(workflowArgs.source_paths)) {
  throw new Error("ui-architecture-builder-graph requires args.source_paths as an array");
}
for (const field of ["icons_in_scope", "motion_in_scope"]) {
  if (typeof workflowArgs[field] !== "boolean") {
    throw new Error(`ui-architecture-builder-graph requires boolean args.${field}`);
  }
}
if (workflowArgs.tool_profile !== "builder_readonly") {
  throw new Error("ui-architecture-builder-graph requires args.tool_profile builder_readonly");
}
const visualDirectionPass = workflowArgs.visual_direction_pass || { status: "not_used" };
if (
  typeof visualDirectionPass !== "object"
  || visualDirectionPass === null
  || !["not_used", "selected", "rejected"].includes(visualDirectionPass.status)
) {
  throw new Error(
    "ui-architecture-builder-graph requires args.visual_direction_pass status not_used, selected, or rejected; a candidate awaiting selection is not a frozen input",
  );
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
const mockupPageSchema = {
  type: "object",
  required: ["route", "html"],
  properties: {
    route: { type: "string" },
    html: { type: "string" },
  },
  additionalProperties: false,
};
const packageSchema = {
  type: "object",
  required: [
    "ui_architecture_markdown",
    "ui_registry",
    "page_recipes_markdown",
    "design_system_markdown",
    "mockup_html_pages",
    "catalog_html",
    "visual_acceptance_markdown",
    "motion_showcase_html",
    "trace_index",
    "assumptions",
    "open_questions",
    "unresolved_conflicts",
  ],
  properties: {
    ui_architecture_markdown: { type: "string" },
    ui_registry: { type: "object" },
    page_recipes_markdown: { type: "string" },
    design_system_markdown: { type: "string" },
    mockup_html_pages: { type: "array", items: mockupPageSchema },
    catalog_html: { type: "string" },
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
  visual_direction_pass: visualDirectionPass,
  brand_constraints: workflowArgs.brand_constraints || [],
  icons_in_scope: workflowArgs.icons_in_scope,
  motion_in_scope: workflowArgs.motion_in_scope,
  styling_engine: workflowArgs.styling_engine || null,
  animation_runtime: workflowArgs.animation_runtime || null,
  registry_enforcement: workflowArgs.registry_enforcement || null,
  adoption_mode: workflowArgs.adoption_mode || null,
  required_viewports: workflowArgs.required_viewports || [390, 768, 1200, 1440],
});

const roles = [
  {
    key: "visual-thesis-content",
    task: "Define the product-specific visual thesis, taste statement, signature decisions, anti-patterns, container/border logic, realistic content rules, and landing-page restraint.",
  },
  {
    key: "content-contracts",
    task: "Turn the product rules into content contracts: per recurring product object, the required fields, length limits, date and number formats, image ratios, CTA count, empty handling, long-content handling, mobile truncation, and the fields that may never be dropped for layout reasons. Then define the route and state contracts and the state matrix — for every important component and route, cover ready, loading, empty, error, disabled, permission denied, stale, expired, long content, reduced motion, and mobile reflow, or mark a cell n/a with a reason. Own no visual values.",
  },
  {
    key: "system-components",
    task: "Define tokens, typography, spacing, and the layered component architecture — layout primitives, surface primitives, control primitives, then product components — with one inventory row per component stating its layer, what it composes, variants, and states. Composition runs downward only. Include states, code references, accessibility, and stable DS IDs tied to upstream traces.",
  },
  {
    key: "primitive-contracts",
    task: "Give every primitive a closed variant set, never a free value. Per primitive, list the variant names, what each is for, and what it must not be used for; a variant with no stated purpose is deleted, not documented. Bind each product component to its content contract. Define the guardrail checks that must fail when a page leaves the set — raw colors, unapproved dimensions, inline layout styles, page-local controls or surfaces, unregistered motion — and the definition of done for a route.",
  },
  {
    key: "page-recipes",
    task: "For each route, fix the section order top to bottom, the container size, the section density, the allowed surfaces, the required product components with their content contracts, the forbidden patterns this route must never grow into, the required states, and what must still render with no JavaScript. Derive forbidden patterns from the anti-slop review and the route's known failure modes. A route with no recipe is a blocker, not an invitation to improvise. Introduce no new visual treatment.",
  },
  {
    key: "page-coverage",
    task: "Map every important route to breakpoints or size classes, states, components, data, mockup content contracts, asset needs, and visual acceptance evidence. Plan the component catalog page that shows every token, primitive variant, and component state at once under realistic content, and the route → mockup → trace ID → DS ID → TEST ID index.",
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
    task: "Define motion purposes (feedback, continuity, processing, storytelling — no fourth category), the split across style-layer transitions, the animation runtime, and route-level transitions, motion tokens as the only place durations/distances/easings/springs live, the registered variants call sites may reference, hero choreography when applicable, interruption, performance, responsive behavior, and one global reduced-motion policy rather than a per-call-site check.",
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
  "You are the synthesis role in a design org graph. Reconcile the role results into complete Markdown bodies for ui-architecture.md (layer model, source-of-truth precedence, content contracts, primitive contracts with closed variant sets, product components, motion architecture, state matrix, guardrail requirements, definition of done, adoption sequence), page-recipes.md (the per-route recipe plus the route → mockup → trace IDs → DS IDs → TEST IDs index), design-system.md, and visual-acceptance.md; one real dependency-free HTML mockup body per important page/route/screen (styled to the resolved platform's own conventions, never web styling by default for a native or desktop product); and one catalog HTML body showing every token, primitive variant, and component state under realistic content. Do not produce a ui-mockups.md or page-ui-matrix.md body; both files are retired for every platform. " +
    "Derive ui_registry from the same primitive contracts, product components, registered motion variants, and page recipes you write into ui-architecture.md and page-recipes.md, so the allowlist cannot describe a different system: carry every primitive with its closed variant sets, every product component with its content contract, every registered motion variant, every page recipe, and the flags for what is not allowed. " +
    "Return a motion showcase only when motion is in scope. Preserve upstream PRD/ARCH/UI/UX/TEST IDs, mint stable DS IDs, keep assumptions explicit, and do not claim rendered visual or usability validation. " +
    `Frozen task context: ${sourceContext}\n\nRole results: ${JSON.stringify(lanes)}`,
  { label: "design:synthesis", phase: "Synthesize", schema: packageSchema },
);
if (!designPackage) {
  throw new Error("ui-architecture-builder-graph synthesis agent did not return a result");
}

const reviewers = [
  {
    key: "taste-verifier",
    task: "Check that the taste statement is concrete, signature decisions recur, unsupported AI-UI patterns are absent, content is realistic, and every border/elevation/media/motion choice has a purpose.",
  },
  {
    key: "trace-verifier",
    task: "Check upstream trace preservation, DS ID stability, route/breakpoint-or-size-class/state coverage, internal consistency, and evidence claims across the UI architecture, the page recipes and their route index, the design system, every mockup page, the catalog, and visual acceptance.",
  },
  {
    key: "registry-verifier",
    task: "Check that the registry, the primitive contracts, the page recipes, the state matrix, and the catalog describe one system. Every registry primitive and variant exists in the architecture document and the catalog, and every catalog and architecture entry exists in the registry. Every component, surface, and motion variant a page recipe requires is registered, and every recipe in the architecture appears in the registry. Every route and important component in the state matrix covers the required states or marks them n/a. Every primitive prop is a closed set with no free value. Return blocked when the registry and the recipes disagree — a contract check run against a stale allowlist proves nothing.",
  },
];
phase("Verify");
const rawReviews = await parallel(reviewers.map((reviewer) => () => agent(
  `You are the ${reviewer.key} role in a design org graph. ${reviewer.task}\n` +
    "Read only. Return fix_required for any material issue and blocked when a human decision or missing source prevents a valid package. " +
    `Frozen task context: ${sourceContext}\n\nDraft UI architecture: ${JSON.stringify(designPackage)}`,
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
