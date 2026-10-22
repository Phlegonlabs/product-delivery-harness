// Versioned, pure packets for read-only research and exploration assignments.
// This module validates parent classifications and joins observed results. It
// launches no worker, creates no branch, writes no checkout state, and grants
// no authorization.

const { createHash } = require("crypto");
const {frozenCopy, launchIndex, matchObserved, identityTracker} = require("./assignment_identity.cjs");

const SCHEMA_VERSION = "readonly-assignments/1";
const ASSIGNMENT_PHASES = new Set([
  "pre_draft_research",
  "post_draft_market_research",
  "ui_research",
  "code_exploration",
]);
const RESULT_STATUSES = new Set(["complete", "no_sources", "skipped", "blocked"]);

function hasResearchEvidence(result) {
  return Array.isArray(result.findings) && result.findings.length > 0
    && Array.isArray(result.sources) && result.sources.length > 0;
}

function isPlainObject(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function nonEmptyString(value) {
  return typeof value === "string" && value.trim().length > 0;
}

function stableJson(value) {
  if (Array.isArray(value)) {
    return value.map(stableJson);
  }
  if (isPlainObject(value)) {
    return Object.fromEntries(
      Object.keys(value).sort().map((key) => [key, stableJson(value[key])]),
    );
  }
  return value;
}

function reject(message) {
  throw new Error(`readonly-assignments: ${message}`);
}

function deepFreeze(value) {
  if (Array.isArray(value)) {
    value.forEach(deepFreeze);
    Object.freeze(value);
  } else if (isPlainObject(value)) {
    Object.values(value).forEach(deepFreeze);
    Object.freeze(value);
  }
  return value;
}

function inputIdentity(instance) {
  return `sha256:${createHash("sha256")
    .update(JSON.stringify(stableJson({
      business_role: instance.business_role,
      execution_role: instance.execution_role,
      input: instance.input,
      phase: instance.phase,
      prompt: instance.prompt,
      question_id: instance.question_id,
      requested_identity: instance.requested_identity,
      run_id: instance.run_id,
      schema_version: SCHEMA_VERSION,
      ...(instance.distinct_workers === undefined ? {} : {distinct_workers: instance.distinct_workers}),
    })))
    .digest("hex")}`;
}

function createReadonlyAssignments(args) {
  const request = typeof args === "string" ? JSON.parse(args) : args;
  if (!isPlainObject(request) || request.schema_version !== SCHEMA_VERSION) {
    reject(`schema_version must be ${SCHEMA_VERSION}`);
  }
  for (const field of ["run_id", "business_role", "execution_role"]) {
    if (!nonEmptyString(request[field])) {
      reject(`${field} must be a non-empty string`);
    }
  }
  if (request.distinct_workers !== undefined && typeof request.distinct_workers !== "boolean") {
    reject("distinct_workers must be a boolean when provided");
  }
  const staffing = request.distinct_workers === undefined ? {} : {distinct_workers: request.distinct_workers};
  if (!ASSIGNMENT_PHASES.has(request.phase)) {
    reject("phase must be pre_draft_research, post_draft_market_research, ui_research, or code_exploration");
  }
  if (!isPlainObject(request.authorization)) {
    reject("authorization must be an object");
  }
  if (request.authorization.delegation !== true || request.authorization.readonly_tools !== true) {
    reject(
      "mandatory delegation is blocked: authorization.delegation and authorization.readonly_tools must both be true",
    );
  }
  if (!isPlainObject(request.capability)) {
    reject("capability must be an object");
  }
  if (request.capability.readonly_tools !== true || request.capability.launch_runtime !== true) {
    reject(
      "mandatory delegation is blocked: capability.readonly_tools and capability.launch_runtime must both be true",
    );
  }
  if (typeof request.skip_allowed !== "boolean") {
    reject("skip_allowed must be a boolean");
  }
  if (request.skip_allowed && !nonEmptyString(request.skip_reason)) {
    reject("skip_reason must be a non-empty string when skip_allowed is true");
  }
  if (typeof request.binding_required !== "boolean") {
    reject("binding_required must be a boolean");
  }
  if (request.binding_required) {
    if (!isPlainObject(request.binding_requirements)) {
      reject("binding_requirements must be an object when binding_required is true");
    }
    for (const field of ["authority", "runtime"]) {
      if (!nonEmptyString(request.binding_requirements[field])) {
        reject(`binding_requirements.${field} must be a non-empty string when binding is required`);
      }
    }
  }
  if (!Number.isInteger(request.attempt_number) || request.attempt_number < 1) {
    reject("attempt_number must be an integer of at least 1");
  }
  if (!Array.isArray(request.questions) || request.questions.length === 0) {
    reject("questions must be a non-empty array");
  }
  if (!isPlainObject(request.requested_identity)) {
    reject("requested_identity must be an object");
  }
  if (request.requested_identity.execution_role !== request.execution_role) {
    reject("requested_identity.execution_role must match execution_role");
  }
  for (const field of ["model", "effort"]) {
    if (field in request.requested_identity && !nonEmptyString(request.requested_identity[field])) {
      reject(`requested_identity.${field} must be a non-empty string when provided`);
    }
  }
  if (!nonEmptyString(request.requested_identity.model)) {
    reject("requested_identity.model must be a non-empty string");
  }

  const questionIds = new Set();
  const inputIds = new Set();
  const instances = request.questions.map((question, index) => {
    if (!isPlainObject(question)) {
      reject(`questions[${index}] must be an object`);
    }
    for (const field of ["question_id", "prompt"]) {
      if (!nonEmptyString(question[field])) {
        reject(`questions[${index}].${field} must be a non-empty string`);
      }
    }
    if (!/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(question.question_id)) {
      reject(`questions[${index}].question_id must use letters, numbers, dots, underscores, or hyphens`);
    }
    if (question.substantive !== true || question.independent !== true) {
      reject(
        `questions[${index}] needs parent classification substantive=true and independent=true`,
      );
    }
    if (!isPlainObject(question.input)) {
      reject(`questions[${index}].input must be an object`);
    }
    if (questionIds.has(question.question_id)) {
      reject(`question_id ${question.question_id} is duplicated`);
    }
    questionIds.add(question.question_id);

    const identitySource = stableJson({
      business_role: request.business_role,
      execution_role: request.execution_role,
      input: question.input,
      phase: request.phase,
      prompt: question.prompt,
      question_id: question.question_id,
      requested_identity: request.requested_identity,
      run_id: request.run_id,
      schema_version: SCHEMA_VERSION,
      ...staffing,
    });
    const inputId = `sha256:${createHash("sha256").update(JSON.stringify(identitySource)).digest("hex")}`;
    if (inputIds.has(inputId)) {
      reject(`input identity for question ${question.question_id} is duplicated`);
    }
    inputIds.add(inputId);

    const assignmentId = `${request.run_id}:${request.phase}:${request.business_role}:${request.execution_role}:assignment:${question.question_id}:${inputId.slice(7)}`;
    const attemptId = `${assignmentId}:attempt-${String(request.attempt_number).padStart(3, "0")}`;
    return {
      assignment_id: assignmentId,
      attempt_id: attemptId,
      binding_required: request.binding_required,
      binding_requirements: request.binding_required ? { ...request.binding_requirements } : null,
      business_role: request.business_role,
      execution_role: request.execution_role,
      independent: true,
      input: question.input,
      input_id: inputId,
      phase: request.phase,
      prompt: question.prompt,
      requested_identity: { ...request.requested_identity },
      run_id: request.run_id,
      question_id: question.question_id,
      readonly: true,
      required_result: true,
      substantive: true,
      ...staffing,
    };
  });

  if (instances.length >= 2 && new Set(instances.map((instance) => instance.assignment_id)).size !== instances.length) {
    reject("independent questions require unique assignments");
  }

  const plan = {
    attempt_number: request.attempt_number,
    authorization: { ...request.authorization },
    binding_required: request.binding_required,
    binding_requirements: request.binding_required ? { ...request.binding_requirements } : null,
    capability: { ...request.capability },
    business_role: request.business_role,
    execution_role: request.execution_role,
    instances,
    requested_identity: { ...request.requested_identity },
    run_id: request.run_id,
    schema_version: SCHEMA_VERSION,
    skip_allowed: request.skip_allowed,
    skip_reason: request.skip_allowed ? request.skip_reason : null,
    ...staffing,
  };
  // Callers cannot mutate the frozen canonical inputs after hashing.
  return frozenCopy(plan);
}

function readonlyResult(instance, payload) {
  if (!isPlainObject(instance) || instance.schema_version !== undefined) {
    reject("readonlyResult requires an assignment instance");
  }
  if (!isPlainObject(payload)) {
    reject("readonlyResult requires a payload object");
  }
  if (!RESULT_STATUSES.has(payload.status)) {
    reject("status must be complete, no_sources, skipped, or blocked");
  }
  if (!isPlainObject(payload.result)) {
    reject("result must be an object");
  }
  if (payload.status === "complete" && !hasResearchEvidence(payload.result)) {
    reject("a complete result requires non-empty findings and sources");
  }
  if (payload.status === "no_sources") {
    for (const field of ["searched", "unresolved"]) {
      if (!nonEmptyString(payload.result[field])) {
        reject(`a no_sources result requires non-empty result.${field}`);
      }
    }
  }
  if (payload.status === "skipped" && !nonEmptyString(payload.result.reason)) {
    reject("a skipped result requires non-empty result.reason");
  }
  if (payload.status === "blocked" && !nonEmptyString(payload.result.reason)) {
    reject("a blocked result requires non-empty result.reason");
  }
  const observed = payload.observed_identity;
  if (!isPlainObject(observed)) {
    reject("observed_identity must be an object");
  }
  for (const field of ["execution_role", "model", "worker_id", "session_id"]) {
    if (!nonEmptyString(observed[field])) {
      reject(`observed_identity.${field} must be a non-empty string`);
    }
  }
  if (instance.requested_identity.effort !== undefined && !nonEmptyString(observed.effort)) {
    reject("observed_identity.effort must be a non-empty string when effort was requested");
  }

  return {
    assignment_id: instance.assignment_id,
    business_role: instance.business_role,
    attempt_id: instance.attempt_id,
    input_id: instance.input_id,
    observed_identity: { ...observed },
    question_id: instance.question_id,
    result: { ...payload.result },
    status: payload.status,
  };
}

function joinReadonlyResults(plan, rawResults, parentLaunchRecords) {
  if (!isPlainObject(plan) || plan.schema_version !== SCHEMA_VERSION) {
    reject(`join requires a ${SCHEMA_VERSION} plan`);
  }
  if (!Array.isArray(rawResults) || rawResults.length !== plan.instances.length) {
    reject("required results are missing or unexpected results were supplied");
  }

  const byAssignment = new Map(plan.instances.map((instance) => [instance.assignment_id, instance]));
  if (plan.distinct_workers !== undefined && typeof plan.distinct_workers !== "boolean") reject("invalid staffing policy");
  for (const instance of plan.instances) {
    if (instance.distinct_workers !== plan.distinct_workers) reject("assignment staffing policy differs from plan");
  }
  const reuseGroups = plan.distinct_workers === false ? [plan.instances.map(a => a.assignment_id)] : [];
  const launches = plan.binding_required ? launchIndex(plan.instances, parentLaunchRecords, {reuseGroups}) : null;
  const resultIds = { assignment_id: new Set(), attempt_id: new Set(), input_id: new Set(), question_id: new Set() };
  const observeIdentity = identityTracker(reuseGroups, "reuses observed");
  const joined = rawResults.map((rawResult, index) => {
    if (!isPlainObject(rawResult)) {
      reject(`results[${index}] must be an object`);
    }
    if ("launch_observation" in rawResult) reject("launch_observation belongs in separate parent launch records, not child results");
    for (const field of Object.keys(resultIds)) {
      if (!nonEmptyString(rawResult[field])) {
        reject(`results[${index}].${field} must be a non-empty string`);
      }
      if (resultIds[field].has(rawResult[field])) {
        reject(`results[${index}] has duplicate ${field} ${rawResult[field]}`);
      }
      resultIds[field].add(rawResult[field]);
    }
    const instance = byAssignment.get(rawResult.assignment_id);
    if (!instance) {
      reject(`results[${index}] names unknown assignment ${rawResult.assignment_id}`);
    }
    if (inputIdentity(instance) !== instance.input_id) {
      reject(`plan input identity changed for ${instance.assignment_id}`);
    }
    for (const [field, expected] of [
      ["attempt_id", instance.attempt_id],
      ["input_id", instance.input_id],
      ["question_id", instance.question_id],
      ["business_role", instance.business_role],
    ]) {
      if (rawResult[field] !== expected) {
        reject(`results[${index}] has stale or mismatched ${field} for ${instance.assignment_id}`);
      }
    }
    if (!RESULT_STATUSES.has(rawResult.status)) {
      reject(`results[${index}] has invalid status ${rawResult.status}`);
    }
    if (!isPlainObject(rawResult.result)) {
      reject(`results[${index}].result must be an object`);
    }
    if (rawResult.status === "complete" && !hasResearchEvidence(rawResult.result)) {
      reject(`results[${index}] complete requires non-empty findings and sources`);
    }
    if (rawResult.status === "skipped" && !plan.skip_allowed) {
      reject(`results[${index}] skips an assignment that has no authorized skip`);
    }
    if (rawResult.status === "no_sources") {
      for (const field of ["searched", "unresolved"]) {
        if (!nonEmptyString(rawResult.result[field])) {
          reject(`results[${index}] no_sources requires non-empty result.${field}`);
        }
      }
    }
    for (const field of ["skipped", "blocked"]) {
      if (rawResult.status === field && !nonEmptyString(rawResult.result.reason)) {
        reject(`results[${index}] ${field} requires non-empty result.reason`);
      }
    }

    const observed = rawResult.observed_identity;
    if (!isPlainObject(observed)) {
      reject(`results[${index}].observed_identity must be an object`);
    }
    for (const field of ["execution_role", "model", "worker_id", "session_id"]) {
      if (!nonEmptyString(observed[field])) {
        reject(`results[${index}].observed_identity.${field} must be a non-empty string`);
      }
    }
    observeIdentity(instance.assignment_id, observed);
    if (observed.execution_role !== instance.requested_identity.execution_role) {
      reject(`results[${index}] has the wrong observed execution role`);
    }
    if (observed.model !== instance.requested_identity.model) {
      reject(`results[${index}] has the wrong observed model`);
    }
    if (instance.requested_identity.effort !== undefined && observed.effort !== instance.requested_identity.effort) {
      reject(`results[${index}] has the wrong observed effort`);
    }
    if (instance.binding_required) {
      matchObserved(instance, rawResult, launches.get(instance.assignment_id));
    }
    return rawResult;
  });

  const blockers = joined
    .filter((result) => result.status === "blocked")
    .map((result) => ({
      assignment_id: result.assignment_id,
      reason: result.result.reason,
      reason_code: "blocked_result",
    }));
  const output = {
    blockers,
    instances: [...plan.instances],
    results: joined,
    run_id: plan.run_id,
    schema_version: SCHEMA_VERSION,
    status: blockers.length > 0 ? "blocked" : "ready",
  };
  return deepFreeze(output);
}

module.exports = {
  SCHEMA_VERSION,
  createReadonlyAssignments,
  joinReadonlyResults,
  readonlyResult,
};
