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
if (typeof workflowArgs.deployable !== "boolean") {
  throw new Error("prd-builder-graph requires boolean args.deployable");
}
if (typeof workflowArgs.hosted_deployable !== "boolean") {
  throw new Error("prd-builder-graph requires boolean args.hosted_deployable");
}
if (workflowArgs.hosted_deployable && !workflowArgs.deployable) {
  throw new Error("prd-builder-graph requires args.deployable when args.hosted_deployable is true");
}
if (!Array.isArray(workflowArgs.deployable_surfaces)) {
  throw new Error("prd-builder-graph requires args.deployable_surfaces as an array");
}
if (!Array.isArray(workflowArgs.release_targets)) {
  throw new Error("prd-builder-graph requires args.release_targets as an array");
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
if (workflowArgs.hosted_deployable && (typeof workflowArgs.deployment_platform !== "string" || !workflowArgs.deployment_platform.trim())) {
  throw new Error("prd-builder-graph requires non-empty args.deployment_platform for a hosted deployable web, API, or backend surface");
}
if (workflowArgs.deployable && workflowArgs.deployable_surfaces.length === 0) {
  throw new Error("prd-builder-graph requires deployable surfaces for a deployable product");
}
if (workflowArgs.deployable && workflowArgs.release_targets.length === 0) {
  throw new Error("prd-builder-graph requires release targets for a deployable product");
}
const deployableSurfaces = new Set();
for (const [index, surface] of workflowArgs.deployable_surfaces.entries()) {
  if (typeof surface !== "string" || !surface.trim()) {
    throw new Error(`prd-builder-graph requires non-empty args.deployable_surfaces[${index}]`);
  }
  const surfaceId = surface.trim();
  if (deployableSurfaces.has(surfaceId)) {
    throw new Error(`prd-builder-graph requires unique deployable surface ${surfaceId}`);
  }
  deployableSurfaces.add(surfaceId);
}
const releaseTargetFields = [
  "id",
  "surface",
  "provider",
  "stage",
  "source_policy",
  "artifact_kind",
  "signing_requirement",
  "channel",
  "release_path",
  "availability_signal",
  "rollout",
  "rollback_or_forward_fix",
];
const releaseTargetIds = new Set();
const releaseStagesBySurface = new Map();
for (const [index, target] of workflowArgs.release_targets.entries()) {
  if (!target || typeof target !== "object" || Array.isArray(target)) {
    throw new Error(`prd-builder-graph requires args.release_targets[${index}] as an object`);
  }
  for (const field of releaseTargetFields) {
    if (typeof target[field] !== "string" || !target[field].trim()) {
      throw new Error(`prd-builder-graph requires non-empty args.release_targets[${index}].${field}`);
    }
  }
  if (!["development", "production"].includes(target.stage)) {
    throw new Error(`prd-builder-graph requires args.release_targets[${index}].stage development or production`);
  }
  if (!["pr_head", "integration_head", "merged_main"].includes(target.source_policy)) {
    throw new Error(`prd-builder-graph requires args.release_targets[${index}].source_policy pr_head, integration_head, or merged_main`);
  }
  if (target.stage === "development" && !["pr_head", "integration_head"].includes(target.source_policy)) {
    throw new Error(`prd-builder-graph requires development source_policy pr_head or integration_head for ${target.id}`);
  }
  if (target.stage === "production" && target.source_policy !== "merged_main") {
    throw new Error(`prd-builder-graph requires production source_policy merged_main for ${target.id}`);
  }
  if (releaseTargetIds.has(target.id)) {
    throw new Error(`prd-builder-graph requires unique release target ID ${target.id}`);
  }
  releaseTargetIds.add(target.id);
  const surface = target.surface.trim();
  if (!deployableSurfaces.has(surface)) {
    throw new Error(`prd-builder-graph release target ${target.id} uses unexpected surface ${surface}`);
  }
  if (!releaseStagesBySurface.has(surface)) {
    releaseStagesBySurface.set(surface, new Set());
  }
  releaseStagesBySurface.get(surface).add(target.stage);
}
if (workflowArgs.deployable) {
  for (const surface of deployableSurfaces) {
    const stages = releaseStagesBySurface.get(surface) || new Set();
    if (!stages.has("development") || !stages.has("production")) {
      throw new Error(`prd-builder-graph requires development and production release targets for expected surface ${surface}`);
    }
  }
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
  deployable: workflowArgs.deployable,
  hosted_deployable: workflowArgs.hosted_deployable,
  deployable_surfaces: workflowArgs.deployable_surfaces,
  release_targets: workflowArgs.release_targets,
  include_implementation_plan: workflowArgs.include_implementation_plan,
  has_public_marketing_content: workflowArgs.has_public_marketing_content,
});

const roles = [
  {
    key: "requirements",
    task: "Extract product goals, non-goals, personas, journeys, functional requirements, measurable non-functional requirements, metrics, risks, assumptions, and stable PRD/TEST trace IDs. Record each applicable quality attribute with scope, measure, target, units, population, window, and percentile where applicable; mark non-applicable categories N/A with a reason. Define a required TEST obligation with upstream trace IDs and an expected signal for every Must functional requirement and every applicable NFR.",
  },
  {
    key: "architecture",
    task: "Define implementation-ready components, data, APIs, integrations, auth, security, deployment, observability, scaling, failure handling, and stable ARCH trace IDs without inventing product scope. Cover every supplied deployable surface and preserve the supplied stable release target IDs. Keep stable surface identity separate from each stage's provider, which may differ between development and production. Use only PLAN-v5 source policies: pr_head or integration_head for development and merged_main for production. Close artifact kind, signing requirement, exact channel/track, submission/promotion/review or manual-approval path, actual availability signal, rollout, and rollback or forward-fix. Upload or submission is not availability, and native recovery may require rollout halt plus a signed forward-fix. Only when hosted_deployable is true, build hosted web/API/backend environment details from the resolved deployment_platform and the stage-specific target providers. The target provider is authoritative for that stage and may differ between development and production; never substitute or invent a platform or provider, and never force native targets into the hosted two-row environment table.",
  },
  {
    key: "ux-wireframe",
    task: "Define UX obligations, routes, states, exact wording or bounded display contracts, low-fidelity wireframe structure, Builder UX Direction consequences, and stable UX/UI trace IDs.",
  },
];
if (workflowArgs.browser_frontend || workflowArgs.mobile_desktop_platform) {
  roles.push({
    key: "frontend-platform",
    task: "Recommend or preserve one explicit browser stack and rendering/platform strategy, separate technology layers, and record Selection, Status, cited Authority/evidence, Why it fits, and Constraint/follow-up per layer; sections may mix statuses. Identify official-source checks and leave unresolved decisions explicit. When a mobile or desktop target is in scope, apply the same row contract to the Mobile/Desktop Technology Decision layers — platform, toolchain, distribution, backend/API integration, push/offline sync, testing — on the supplied mobile_desktop_platform; never substitute or invent a platform.",
  });
}
if (workflowArgs.has_backend) {
  roles.push({
    key: "backend",
    task: "Decide service topology first (monolith versus named services and monorepo versus polyrepo), then recommend or preserve one explicit backend runtime/framework, database category and engine, and auth strategy and provider. Keep these as separate ordered layers and record Selection, Status, cited Authority/evidence, Why it fits, and Constraint/follow-up per row; sections may mix statuses. Map data entities to stores, identify official-source checks, and leave unresolved decisions explicit for the Backend and Data Technology Decision section.",
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
    "Preserve stable PRD, ARCH, UI, UX, TEST, surface, and release target IDs; do not hide conflicts or failed lanes; do not claim publication or visual/user validation. Keep Non-Functional Requirements after Functional Requirements and Test Obligations after Open Questions in PRD.md. Map every Must functional requirement and every applicable NFR to at least one required TEST row. If implementation-plan.md is requested, reuse those TEST IDs rather than creating anonymous replacements. Write provider-neutral development and production release-target blocks for every expected deployable surface in the frozen inventory. Keep surface identity separate from provider, permit different providers by stage, and use only PLAN-v5 source policies. Do not treat upload/submission as availability or force native distribution into the hosted environment table. " +
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
    task: "Check that PRD.md contains the mandatory measurable Non-Functional Requirements and stable Test Obligations tables, every Must functional requirement and applicable NFR maps to at least one required TEST row with an expected signal, optional implementation planning reuses those TEST IDs, and every major architecture, UI, and UX obligation has stable cross-document trace coverage.",
  },
  {
    key: "consistency-verifier",
    task: "Check all four documents for contradictory scope, unsupported claims, missing states, hidden assumptions, and invalid implementation or usability claims. Verify that every expected deployable surface has stable development and production target IDs and complete provider-neutral release fields. Confirm surface identity is separate from provider, different stage providers are allowed, and source policies use the PLAN-v5 vocabulary. Reject missing expected surfaces, upload/submission/approval as the availability signal, and web-style rollback claims for native channels that require staged-rollout halt and forward-fix.",
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
