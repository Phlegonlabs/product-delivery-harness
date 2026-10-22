// Current graph identity barriers. Domain prose/schemas stay in product_agent_graph.
// No launcher, filesystem access, scheduler or authorization grants live here.
const {digest, frozenCopy, requireText, launchIndex, matchObserved} = require("./assignment_identity.cjs");
const {createReadonlyAssignments, joinReadonlyResults, SCHEMA_VERSION} = require("./readonly_assignments.cjs");
const GRAPH_SCHEMA = "product-graph-assignments/1";

function envelopeSchema(body) {
  return {type: "object", additionalProperties: false,
    required: ["assignment_id", "attempt_id", "input_id", "business_role", "question_id", "observed_identity", "status", "result"],
    properties: {
      ...Object.fromEntries(["assignment_id", "attempt_id", "input_id", "business_role", "question_id"].map(k => [k, {type: "string"}])),
      observed_identity: {type: "object"}, status: {enum: ["complete", "blocked", "no_sources", "skipped"]},
      result: body,
    }};
}
function validateBody(value, schema) {
  if (schema.enum && !schema.enum.includes(value)) throw new Error("invalid result enum");
  const type = value === null ? "null" : Array.isArray(value) ? "array" : typeof value;
  if (schema.type && ![].concat(schema.type).includes(type)) throw new Error("invalid result type");
  if (type === "object") {
    for (const key of schema.required || []) if (!(key in value)) throw new Error(`missing result ${key}`);
    for (const [key, item] of Object.entries(value)) {
      if (schema.properties?.[key]) validateBody(item, schema.properties[key]);
      else if (schema.additionalProperties === false) throw new Error(`unexpected result ${key}`);
    }
  }
  if (type === "array" && schema.items) value.forEach(v => validateBody(v, schema.items));
}
function createIdentityGraph(args, domain) {
  const inventory = args.research_question_inventory;
  if (!Array.isArray(inventory)) throw new Error("research_question_inventory must be an explicit array");
  if (args.market_research && !inventory.length) throw new Error("enabled research requires questions");
  if (!args.market_research) {
    requireText(args.research_skip_reason, "research_skip_reason");
    if (args.research_delegation_required === true || inventory.length) throw new Error("mandatory research cannot be disabled");
  }
  if (!Array.isArray(args.source_manifest)) throw new Error("source_manifest is required, including RA sources");
  const sourcePaths = new Set();
  for (const source of args.source_manifest) {
    requireText(source.path, "source path");
    if (!/^[a-f0-9]{64}$/.test(source.sha256) || sourcePaths.has(source.path)) throw new Error("invalid or duplicate source digest");
    sourcePaths.add(source.path);
  }
  if (args.source_paths.some(path => !sourcePaths.has(path))) throw new Error("source_manifest must cover all source_paths");
  const context = frozenCopy(args);
  let synthesisTask = null;
  let synthesisInput = null;
  let reviewTasks = null;
  let reviewedDraft = null;
  let readonlyPlan = null;
  let synthesisAttempt = 0;
  let reviewAttempt = 0;

  function binding(role) {
    const b = context.role_bindings?.[role];
    if (!b) throw new Error(`missing host role binding for ${role}`);
    for (const field of ["execution_role", "model", "effort", "authority", "runtime", "logical_role"]) requireText(b[field], `${role}.${field}`);
    if (!["native", "external"].includes(b.runtime_kind)) throw new Error(`missing runtime_kind for ${role}`);
    if (!Array.isArray(b.required_tools) || !Array.isArray(b.capability?.tools)
        || b.required_tools.some(tool => !b.capability.tools.includes(tool))) throw new Error(`required tool capability missing for ${role}`);
    const required = role.endsWith("verifier") ? "reviewer"
      : ["architecture", "frontend-platform", "backend"].includes(role) ? "code_architect"
      : role === "market-research" ? "market_researcher" : null;
    if (required && b.logical_role !== required) throw new Error(`wrong logical host binding for ${role}`);
    if (b.authorization?.delegation !== true || b.authorization?.readonly_tools !== true
        || b.capability?.launch_runtime !== true || b.capability?.readonly_tools !== true) throw new Error(`required delegation blocked for ${role}`);
    if (b.runtime_kind === "external" && b.authorization.invoke_external_runtime !== true) throw new Error(`external runtime authorization missing for ${role}`);
    return b;
  }
  function wrap(task, phase, input, attempt) {
    const role = task.label.slice(4);
    const b = binding(role);
    const requested = {execution_role: b.execution_role, model: b.model, effort: b.effort};
    const prompt = `${task.prompt}\nSource manifest (verify bytes before reading): ${JSON.stringify(context.source_manifest)}\nRead only. Do not write files or approve decisions. Return the identity envelope with the domain payload in result.`;
    const scope = {schema_version: GRAPH_SCHEMA, run_id: context.run_id, phase, business_role: role,
      requested_identity: requested, binding: b, prompt, input};
    const inputId = digest(scope);
    const assignmentId = `${context.run_id}:${phase}:${role}:${b.execution_role}:${inputId.slice(7)}`;
    return frozenCopy({...task, prompt, schema: envelopeSchema(task.schema), body_schema: task.schema,
      assignment: {...scope, assignment_id: assignmentId, attempt_id: `${assignmentId}:attempt-${attempt}`,
        input_id: inputId, question_id: role, binding_required: true,
        binding_requirements: {authority: b.authority, runtime: b.runtime}, readonly: true, required_result: true}});
  }
  const analysisTasks = domain.analyze().map(t => wrap(t, "analyze", {source_context: context, source_manifest: context.source_manifest}, 1));
  // Resolve all required bindings before any packet may be launched.
  binding("synthesis");
  for (const t of domain.review({})) binding(t.label.slice(4));

  function join(tasks, results, records) {
    if (!Array.isArray(results) || results.length !== tasks.length) throw new Error("required assignment results are missing or unexpected");
    const launches = launchIndex(tasks.map(t => t.assignment), records);
    const expected = new Map(tasks.map(t => [t.assignment.assignment_id, t]));
    const joined = new Map();
    for (const r of results) {
      const t = expected.get(r?.assignment_id);
      if (!t || joined.has(r.assignment_id)) throw new Error("unknown or duplicate assignment result");
      validateBody(r, t.schema);
      for (const field of ["assignment_id", "attempt_id", "input_id", "business_role", "question_id"]) {
        if (r[field] !== t.assignment[field]) throw new Error(`stale or wrong ${field}`);
      }
      matchObserved(t.assignment, r, launches.get(r.assignment_id));
      if (r.status !== "complete" && r.status !== "blocked") throw new Error("invalid graph result status");
      validateBody(r.result, t.body_schema);
      if (t.assignment.business_role !== "synthesis" && r.result.role !== t.assignment.business_role) throw new Error("wrong business role payload");
      joined.set(r.assignment_id, frozenCopy(r));
    }
    return tasks.map(t => joined.get(t.assignment.assignment_id));
  }
  const successful = results => {
    if (results.some(r => r.status !== "complete" || r.result.status === "blocked")) throw new Error("required graph dependency is blocked");
    return results.map(r => r.result);
  };
  function synthesize(results, records) {
    const lanes = successful(join(analysisTasks, results, records));
    synthesisInput = digest(lanes);
    synthesisTask = wrap(domain.synthesize(lanes), "synthesize", {source_context: context, source_manifest: context.source_manifest, lanes}, ++synthesisAttempt);
    reviewTasks = null;
    return synthesisTask;
  }
  function review(result, records) {
    if (!synthesisTask) throw new Error("synthesis assignment must precede review");
    reviewTasks = null;
    readonlyPlan = null;
    const [draft] = successful(join([synthesisTask], [result], records));
    reviewedDraft = frozenCopy(draft);
    const snapshot = {source_context: context, source_manifest: context.source_manifest, draft: reviewedDraft};
    const attempt = ++reviewAttempt;
    const tasks = domain.review(reviewedDraft);
    reviewTasks = tasks.filter(t => t.label !== "prd:market-research").map(t => wrap(t, "review", snapshot, attempt));
    if (context.market_research) {
      const b = binding("market-research");
      const researchPrompt = tasks.find(t => t.label === "prd:market-research").prompt;
      readonlyPlan = createReadonlyAssignments({schema_version: SCHEMA_VERSION, run_id: context.run_id,
        ...(context.research_distinct_workers === undefined ? {} : {distinct_workers: context.research_distinct_workers}),
        business_role: "market-research", execution_role: b.execution_role, phase: "post_draft_market_research",
        authorization: b.authorization, capability: b.capability, attempt_number: attempt,
        binding_required: true, binding_requirements: {authority: b.authority, runtime: b.runtime},
        requested_identity: {execution_role: b.execution_role, model: b.model, effort: b.effort},
        skip_allowed: context.research_skip_allowed === true, skip_reason: context.research_skip_reason,
        questions: inventory.map(q => ({...q, input: {...snapshot, question_input: q.input},
          prompt: `${researchPrompt}\nResearch only this assigned question: ${q.prompt}\nSource manifest: ${JSON.stringify(context.source_manifest)}\nA completed search with no useful evidence returns no_sources with searched and unresolved. Missing tools or failed searches return blocked. Return the identity envelope; no_sources/skipped/blocked use their explicit result fields.`})),
      });
      reviewTasks.push(...readonlyPlan.instances.map(a => frozenCopy({label: `prd:market_researcher:${a.question_id}`,
        phase: "Verify", prompt: a.prompt, assignment: a, schema: envelopeSchema({type: "object"})})));
    }
    return frozenCopy(reviewTasks);
  }
  function finish(laneResults, synthesisResult, results, records) {
    if (!reviewTasks) throw new Error("review must precede finish");
    const allTasks = [...analysisTasks, synthesisTask, ...reviewTasks];
    const reuseGroups = readonlyPlan?.distinct_workers === false ? [readonlyPlan.instances.map(a => a.assignment_id)] : [];
    launchIndex(allTasks.map(t => t.assignment), records, {reuseGroups});
    const recordsFor = tasks => records.filter(r => tasks.some(t => t.assignment.assignment_id === r.assignment_id));
    const lanes = successful(join(analysisTasks, laneResults, recordsFor(analysisTasks)));
    if (digest(lanes) !== synthesisInput) throw new Error("analysis snapshot changed after synthesis");
    const [draft] = successful(join([synthesisTask], [synthesisResult], recordsFor([synthesisTask])));
    if (digest(draft) !== digest(reviewedDraft)) throw new Error("reviewed draft snapshot changed");
    if (!Array.isArray(results) || results.length !== reviewTasks.length) throw new Error("review results must cover every planned assignment and reviewer exactly once");
    const verifierTasks = reviewTasks.filter(t => t.assignment.business_role !== "market-research");
    const verifierIds = new Set(verifierTasks.map(t => t.assignment.assignment_id));
    const verifierResults = join(verifierTasks, results.filter(r => verifierIds.has(r.assignment_id)), recordsFor(verifierTasks));
    const researchResults = results.filter(r => !verifierIds.has(r.assignment_id));
    const researchJoin = readonlyPlan ? joinReadonlyResults(readonlyPlan, researchResults,
      recordsFor(reviewTasks.filter(t => !verifierIds.has(t.assignment.assignment_id)))) : null;
    if (!readonlyPlan && researchResults.length) throw new Error("unexpected research result");
    const reviews = verifierResults.map(r => r.result);
    return frozenCopy({run_id: context.run_id, lanes, draft, reviews, research: researchJoin?.results || [],
      research_join: researchJoin, readonly_plan: readonlyPlan, readonly_assignment_mode: SCHEMA_VERSION,
      graph_assignment_schema: GRAPH_SCHEMA, research_skip_reason: context.market_research ? null : context.research_skip_reason,
      status: verifierResults.some(r => r.status !== "complete" || r.result.decision !== "pass") || researchJoin?.status === "blocked" ? "needs_revision" : "candidate_ready"});
  }
  return {analyze: () => frozenCopy(analysisTasks), synthesize, review, finish};
}
module.exports = {createIdentityGraph};
