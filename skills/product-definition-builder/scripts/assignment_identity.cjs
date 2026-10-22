// Pure identity checks. Only the host can supply trustworthy launch observations.
const {createHash} = require("node:crypto");
function canonical(value) {
  if (Array.isArray(value)) return value.map(canonical);
  if (value && typeof value === "object") return Object.fromEntries(Object.keys(value).sort().map(k => [k, canonical(value[k])]));
  return value;
}
function digest(value) {
  return `sha256:${createHash("sha256").update(JSON.stringify(canonical(value))).digest("hex")}`;
}
function frozenCopy(value) {
  const copy = JSON.parse(JSON.stringify(value));
  function freeze(item) {
    if (item && typeof item === "object") { Object.values(item).forEach(freeze); Object.freeze(item); }
    return item;
  }
  return freeze(copy);
}
function requireText(value, name) {
  if (typeof value !== "string" || !value.trim()) throw new Error(`${name} must be non-empty`);
}
function identityTracker(reuseGroups = [], label = "reused parent launch") {
  const groups = reuseGroups.map(ids => new Set(ids));
  const workers = new Map();
  const sessions = new Map();
  return (assignmentId, identity) => {
    for (const [field, paired, seen] of [["worker_id", "session_id", workers], ["session_id", "worker_id", sessions]]) {
      const prior = seen.get(identity[field]);
      if (prior && (prior[paired] !== identity[paired]
          || !groups.some(group => group.has(prior.assignment_id) && group.has(assignmentId)))) {
        throw new Error(`${label} ${field} ${identity[field]}`);
      }
      seen.set(identity[field], {...identity, assignment_id: assignmentId});
    }
  };
}
function launchIndex(instances, records, {reuseGroups = []} = {}) {
  if (!Array.isArray(records) || records.length !== instances.length) throw new Error("required parent launch records are missing or unexpected");
  const expected = new Map(instances.map(a => [a.assignment_id, a]));
  const index = new Map();
  const reservations = new Set();
  const observeIdentity = identityTracker(reuseGroups);
  for (const record of records) {
    const a = expected.get(record?.assignment_id);
    if (!a || index.has(record.assignment_id)) throw new Error("unknown or duplicate parent launch assignment");
    for (const field of ["assignment_id", "attempt_id", "input_id"]) {
      if (record[field] !== a[field]) throw new Error(`parent launch ${field} mismatch`);
    }
    for (const field of ["authority", "runtime", "reservation_id", "execution_role", "model", "worker_id", "session_id"]) requireText(record[field], `parent launch ${field}`);
    for (const field of ["authority", "runtime"]) {
      if (record[field] !== a.binding_requirements[field]) throw new Error(`wrong launch ${field}`);
    }
    for (const field of ["execution_role", "model"]) {
      if (record[field] !== a.requested_identity[field]) throw new Error(`wrong launch ${field}`);
    }
    if (a.requested_identity.effort !== undefined && record.effort !== a.requested_identity.effort) {
      throw new Error("wrong launch effort");
    }
    if (reservations.has(record.reservation_id)) throw new Error("reused parent launch reservation_id");
    reservations.add(record.reservation_id);
    observeIdentity(a.assignment_id, record);
    index.set(a.assignment_id, record);
  }
  return index;
}
function matchObserved(instance, result, launch) {
  for (const field of ["execution_role", "model", "worker_id", "session_id"]) {
    if (result.observed_identity?.[field] !== launch[field]) throw new Error(`launch observation conflicts with the child observed ${field}`);
  }
  if (instance.requested_identity.effort !== undefined && result.observed_identity?.effort !== launch.effort) {
    throw new Error("launch observation conflicts with the child observed effort");
  }
}
module.exports = {digest, frozenCopy, requireText, launchIndex, matchObserved, identityTracker};
