export const meta = {
  name: "product-definition-builder-graph",
  description: "Draft and cross-check one PRD package from frozen discovery inputs.",
  phases: [
    { title: "Analyze", detail: "Run product, architecture, UX, platform, backend, and monetization roles" },
    { title: "Synthesize", detail: "Join role outputs into one PRD package" },
    { title: "Verify", detail: "Cross-check trace coverage and consistency, and research market gaps" },
  ],
};

const workflowArgs = typeof args === "string" ? JSON.parse(args) : args;

if (!workflowArgs || workflowArgs.multi_agent_authorized !== true) {
  throw new Error("product-definition-builder-graph requires explicit args.multi_agent_authorized=true");
}
if (workflowArgs.single_agent_only === true || workflowArgs.sequential_only === true) {
  throw new Error("product-definition-builder-graph cannot run when single-agent or sequential-only execution is required");
}
for (const field of ["single_agent_only", "sequential_only"]) {
  if (workflowArgs[field] !== undefined && typeof workflowArgs[field] !== "boolean") {
    throw new Error(`product-definition-builder-graph requires boolean args.${field} when provided`);
  }
}

for (const field of ["run_id", "product_name", "interview_summary"]) {
  if (!workflowArgs || typeof workflowArgs[field] !== "string" || !workflowArgs[field].trim()) {
    throw new Error(`product-definition-builder-graph requires non-empty args.${field}`);
  }
}
if (!Array.isArray(workflowArgs.product_archetypes) || workflowArgs.product_archetypes.length === 0) {
  throw new Error("product-definition-builder-graph requires a non-empty args.product_archetypes array");
}
if (!Array.isArray(workflowArgs.source_paths)) {
  throw new Error("product-definition-builder-graph requires args.source_paths as an array");
}
if (typeof workflowArgs.browser_frontend !== "boolean") {
  throw new Error("product-definition-builder-graph requires boolean args.browser_frontend");
}
if (typeof workflowArgs.ui_bearing !== "boolean") {
  throw new Error("product-definition-builder-graph requires boolean args.ui_bearing");
}
if (typeof workflowArgs.has_backend !== "boolean") {
  throw new Error("product-definition-builder-graph requires boolean args.has_backend");
}
if (typeof workflowArgs.deployable !== "boolean") {
  throw new Error("product-definition-builder-graph requires boolean args.deployable");
}
if (typeof workflowArgs.hosted_deployable !== "boolean") {
  throw new Error("product-definition-builder-graph requires boolean args.hosted_deployable");
}
if (workflowArgs.hosted_deployable && !workflowArgs.deployable) {
  throw new Error("product-definition-builder-graph requires args.deployable when args.hosted_deployable is true");
}
if (!Array.isArray(workflowArgs.deployable_surfaces)) {
  throw new Error("product-definition-builder-graph requires args.deployable_surfaces as an array");
}
if (!Array.isArray(workflowArgs.release_targets)) {
  throw new Error("product-definition-builder-graph requires args.release_targets as an array");
}
if (typeof workflowArgs.has_public_marketing_content !== "boolean") {
  throw new Error("product-definition-builder-graph requires boolean args.has_public_marketing_content");
}
if (typeof workflowArgs.include_implementation_plan !== "boolean") {
  throw new Error("product-definition-builder-graph requires boolean args.include_implementation_plan");
}
if (typeof workflowArgs.market_research !== "boolean") {
  throw new Error("product-definition-builder-graph requires boolean args.market_research");
}
const monetizationModels = ["none", "one_time", "subscription", "usage_based", "hybrid", "undecided"];
if (!monetizationModels.includes(workflowArgs.monetization_model)) {
  throw new Error("product-definition-builder-graph requires args.monetization_model as none, one_time, subscription, usage_based, hybrid, or undecided");
}
const partnerChannelModels = ["none", "affiliate", "referral", "reseller", "hybrid", "undecided"];
if (!partnerChannelModels.includes(workflowArgs.partner_channel_model)) {
  throw new Error("product-definition-builder-graph requires args.partner_channel_model as none, affiliate, referral, reseller, hybrid, or undecided");
}
if (workflowArgs.tool_profile !== "builder_readonly") {
  throw new Error("product-definition-builder-graph requires args.tool_profile builder_readonly");
}
if (workflowArgs.ui_bearing && (typeof workflowArgs.builder_ux_direction !== "string" || !workflowArgs.builder_ux_direction.trim())) {
  throw new Error("product-definition-builder-graph requires non-empty args.builder_ux_direction for a ui_bearing product");
}
if (workflowArgs.hosted_deployable && (typeof workflowArgs.deployment_platform !== "string" || !workflowArgs.deployment_platform.trim())) {
  throw new Error("product-definition-builder-graph requires non-empty args.deployment_platform for a hosted deployable web, API, or backend surface");
}
if (workflowArgs.deployable && workflowArgs.deployable_surfaces.length === 0) {
  throw new Error("product-definition-builder-graph requires deployable surfaces for a deployable product");
}
if (workflowArgs.deployable && workflowArgs.release_targets.length === 0) {
  throw new Error("product-definition-builder-graph requires release targets for a deployable product");
}
const deployableSurfaces = new Set();
for (const [index, surface] of workflowArgs.deployable_surfaces.entries()) {
  if (typeof surface !== "string" || !surface.trim()) {
    throw new Error(`product-definition-builder-graph requires non-empty args.deployable_surfaces[${index}]`);
  }
  const surfaceId = surface.trim();
  if (deployableSurfaces.has(surfaceId)) {
    throw new Error(`product-definition-builder-graph requires unique deployable surface ${surfaceId}`);
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
    throw new Error(`product-definition-builder-graph requires args.release_targets[${index}] as an object`);
  }
  for (const field of releaseTargetFields) {
    if (typeof target[field] !== "string" || !target[field].trim()) {
      throw new Error(`product-definition-builder-graph requires non-empty args.release_targets[${index}].${field}`);
    }
  }
  if (!["development", "production"].includes(target.stage)) {
    throw new Error(`product-definition-builder-graph requires args.release_targets[${index}].stage development or production`);
  }
  if (releaseTargetIds.has(target.id)) {
    throw new Error(`product-definition-builder-graph requires unique release target ID ${target.id}`);
  }
  releaseTargetIds.add(target.id);
  const surface = target.surface.trim();
  if (!deployableSurfaces.has(surface)) {
    throw new Error(`product-definition-builder-graph release target ${target.id} uses unexpected surface ${surface}`);
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
      throw new Error(`product-definition-builder-graph requires development and production release targets for expected surface ${surface}`);
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
    "wireframes_html_data_json",
    "architecture_markdown",
    "stack_decisions_markdown",
    "implementation_plan_markdown",
    "trace_index",
    "assumptions",
    "open_questions",
    "unresolved_conflicts",
  ],
  properties: {
    prd_markdown: { type: "string" },
    wireframes_html_data_json: { type: ["string", "null"] },
    architecture_markdown: { type: "string" },
    stack_decisions_markdown: { type: "string" },
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
const researchSchema = {
  type: "object",
  required: [
    "role",
    "status",
    "market_research_markdown",
    "mr_ids",
    "findings",
    "sources",
    "unresolved",
    "evidence",
  ],
  properties: {
    role: { type: "string" },
    status: { enum: ["complete", "blocked"] },
    market_research_markdown: { type: ["string", "null"] },
    mr_ids: stringArray,
    findings: { type: "array", items: { type: "object" } },
    sources: { type: "array", items: { type: "object" } },
    unresolved: stringArray,
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
  monetization_model: workflowArgs.monetization_model,
  partner_channel_model: workflowArgs.partner_channel_model,
  market_research: workflowArgs.market_research,
  multi_agent_authorized: workflowArgs.multi_agent_authorized,
  single_agent_only: workflowArgs.single_agent_only || false,
  sequential_only: workflowArgs.sequential_only || false,
});

const roles = [
  {
    key: "requirements",
    task: "Extract product goals, non-goals, personas, journeys, functional requirements, measurable non-functional requirements, metrics, risks, assumptions, and stable PRD/TEST trace IDs. Record each applicable quality attribute with scope, measure, target, units, population, window, and percentile where applicable; mark non-applicable categories N/A with a reason. Define a required TEST obligation with upstream trace IDs and an expected signal for every Must functional requirement and every applicable NFR.",
  },
  {
    key: "architecture",
    task: "Define implementation-ready components, data, APIs, integrations, auth, security, deployment, observability, scaling, failure handling, and stable ARCH trace IDs without inventing product scope. Cover every supplied deployable surface and preserve the supplied stable release target IDs. Keep surface identity separate from each stage's provider and name the exact branch or ref. Under the standard branch contract, development releases build from remote development after exact-SHA promotion and internal verification; production builds from remote main after separately authorized fast-forward of that same SHA. Initial delivery starts from main and enhancements start from development. Close artifact/signing, channel, release gates, availability, rollout, and rollback or forward-fix. Upload or submission is not availability. Only when hosted_deployable is true, build environment details from the resolved platform and stage providers; never substitute or invent a platform or provider, and never force native targets into the hosted two-row environment table.",
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
if (workflowArgs.monetization_model !== "none" || workflowArgs.partner_channel_model !== "none") {
  roles.push({
    key: "monetization-channel",
    task: "Apply monetization-and-partner-channel-guide.md. Keep the Monetization Infrastructure Gate separate from the Partner Channel Gate. Resolve pricing and offer rules, purchase surfaces, product/purchase/subscription/entitlement ownership, merchant-of-record and tax responsibility, and current billing/store, entitlement, and paywall options without defaulting to RevenueCat. Separately resolve affiliate, referral, reseller, or hybrid operations: attribution, lead/deal deduplication, commission or wholesale discount, reversal, payout, customer ownership, provisioning, delegated administration, support, termination, fraud controls, and reconciliation. Compare only current official sources, record retrieval dates, and leave owner decisions explicit.",
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
  "You are the synthesis role in a PRD org graph. Reconcile the role results into complete Markdown bodies for PRD.md, architecture.md, and stack-decisions.md, plus implementation-plan.md only when requested. PRD.md always records explicit Monetization Infrastructure and Partner Channel gate results; pricing never automatically selects RevenueCat, and affiliate, referral, and reseller remain distinct. Applicable architecture and stack decisions keep store/billing, entitlement, paywall/checkout, merchant-of-record/tax, and partner operations separate. For a UI-bearing product, PRD.md must include the complete UI surface contract, exactly one `responsive` anchor per UI-* entry, and the Wireframe Approval record. Also return wireframes_html_data_json as a valid JSON string using schema wireframes/3 with the same global viewports or sizeClasses, canvasWidths, and complete screens, regions, states, neverDrop lists, and per-target responsiveLayouts required by WIREFRAMES.template.html. Every visible region action must match exactly one flow with presentation page, overlay, or feedback; page and overlay target another UI-* screen in the file. When the frozen owner answers already decide a media or motion treatment, include mediaIntent with treatment, a dedicated draftPrompt, the owner decision source, and generationStatus deferred; never generate media. The parent embeds the data into the supplied self-contained HTML shell and verifies it against PRD.md. Return the HTML data field as null only when ui_bearing is false. Do not create design-system artifacts or start visual design; the parent presents wireframes.html for human approval and stops unless the owner explicitly asks to continue. " +
    "Preserve stable PRD, ARCH, UI, UX, TEST, surface, and release target IDs; do not hide conflicts or failed lanes; do not claim publication or visual/user validation. Keep Non-Functional Requirements after Functional Requirements and Test Obligations after Open Questions in PRD.md. Map every Must functional requirement and every applicable NFR to at least one required TEST row. If implementation-plan.md is requested, reuse those TEST IDs rather than creating anonymous replacements. Write provider-neutral release-target blocks for every expected surface and name the exact branch or ref. Keep surface separate from provider. Use development for the internally tested development release and main for production after same-SHA fast-forward, recording initial-versus-enhancement base rules and separate promotion authorizations/read-backs. Do not treat upload/submission as availability or force native distribution into the hosted environment table; native recovery may require a signed forward-fix. " +
    "Follow the output contract's \"How To Read This Package\": open each document with human-readable content and close it with the ID matrices and decision records, respect the per-file length budget, and keep every table at seven columns or fewer, except the mandated hosted environment contract in architecture.md, whose columns are all release-critical. " +
    `Frozen task context: ${sourceContext}\n\nRole results: ${JSON.stringify(lanes)}`,
  { label: "prd:synthesis", phase: "Synthesize", schema: draftSchema },
);
if (!draft) {
  throw new Error("product-definition-builder-graph synthesis agent did not return a result");
}

const reviewers = [
  {
    key: "trace-verifier",
    task: "Check that PRD.md contains the mandatory measurable Non-Functional Requirements and stable Test Obligations tables, every Must functional requirement and applicable NFR maps to at least one required TEST row with an expected signal, optional implementation planning reuses those TEST IDs, and every major architecture, UI, and UX obligation has stable cross-document trace coverage.",
  },
  {
    key: "consistency-verifier",
    task: "Check the complete draft package for contradictory scope, unsupported claims, missing states, hidden assumptions, and invalid implementation or usability claims. Verify both monetization and partner-channel gates are explicit; no pricing decision silently selects RevenueCat; affiliate, referral, and reseller are distinct; and provider claims cite current official sources. For UI products, verify wireframes/3 JSON maps every PRD UI-* entry, responsive set, state, never-drop region, working action flow, deferred media intent, and per-target layout without implementation code. Verify every expected surface has stable development and production targets. Confirm development builds from remote development, production from remote main only after internal exact-SHA PASS and separately authorized fast-forward, and initial versus enhancement bases are explicit. Reject missing surfaces, upload as availability, or invalid native rollback claims.",
  },
];
if (workflowArgs.has_public_marketing_content) {
  reviewers.push({
    key: "seo-copy-verifier",
    task: "Review the exact wording on public marketing, landing, or SEO-relevant screens only: headline/H1 clarity and keyword relevance without stuffing, a usable heading hierarchy for search crawlers, a meta-description-worthy summary, descriptive non-generic alt text or DISPLAY contracts for images, and internal-link or content-depth opportunities. Do not review internal-tool, dashboard, or authenticated-only screens against SEO criteria.",
  });
}
phase("Verify");
const verifyTasks = reviewers.map((reviewer) => () => agent(
  `You are the ${reviewer.key} role in a PRD org graph. ${reviewer.task}\n` +
    "Read only. Return fix_required for any material issue and blocked when a human decision or missing source prevents a valid package. " +
    `Frozen task context: ${sourceContext}\n\nDraft package: ${JSON.stringify(draft)}`,
  { label: `prd:${reviewer.key}`, phase: "Verify", schema: reviewSchema },
));
if (workflowArgs.market_research) {
  verifyTasks.push(() => agent(
    "You are the market-research role in a PRD org graph. The package is already drafted; your job is to check it against what already exists in the market and report what is missing.\n" +
      "Research the alternatives users have today (named products, in-house builds, manual process, or nothing), the feature baseline that is table stakes versus a real differentiator, this product's differentiation against those alternatives, pricing reference points when it has a commercial surface, category benchmarks for the metric targets the draft sets, and market-side risks such as incumbent response, switching cost, platform dependency, and regulatory or licensing limits. " +
      "For an internal tool, the alternatives are the current spreadsheet, the existing internal system, and doing nothing — not commercial products nobody here would buy.\n" +
      "Every factual claim carries a source with publisher, URL, and retrieval date, and prefers a primary source over a roundup. A claim you could not source is recorded in unresolved and marked UNVALIDATED with what you searched — never stated as fact. Do not invent a competitor, price, funding figure, user count, market size, or feature comparison; a plausible number with no source is the worst outcome of this role. Do not present vendor marketing copy as verified capability. When sources disagree, record both and say so.\n" +
      "Mint stable MR-* IDs for findings that could change a product decision. Each finding names the artifact and section it lands in and what should change; a finding that would widen product scope is a recommendation for the user, not a decision. Return status blocked with a null body when no web tool is available or every search failed, rather than publishing an artifact of unsourced rows.\n" +
      "Read only. Do not edit, create, move, or publish files, and do not ask the user anything. " +
      `Frozen task context: ${sourceContext}\n\nDraft package: ${JSON.stringify(draft)}`,
    { label: "prd:market-research", phase: "Verify", schema: researchSchema },
  ));
}
const verifyResults = await parallel(verifyTasks);
const rawReviews = verifyResults.slice(0, reviewers.length);
const rawResearch = workflowArgs.market_research ? verifyResults[reviewers.length] : null;
const research = workflowArgs.market_research
  ? (rawResearch && rawResearch.role === "market-research"
      ? rawResearch
      : {
          role: "market-research",
          status: "blocked",
          market_research_markdown: null,
          mr_ids: [],
          findings: [],
          sources: [],
          unresolved: ["The market-research workflow agent returned no result or the wrong role."],
          evidence: [rawResearch ? "workflow-role-mismatch" : "workflow-agent-null"],
        })
  : null;
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
  research,
};
