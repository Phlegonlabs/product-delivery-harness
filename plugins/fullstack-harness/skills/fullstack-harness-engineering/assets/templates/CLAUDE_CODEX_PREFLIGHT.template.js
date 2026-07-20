export const meta = {
  name: "harness-codex-preflight",
  description: "Confirm that cc-codex can return a foreground Harness result.",
  phases: [
    { title: "Probe", detail: "Verify the Codex agent, authentication, and result channel" },
  ],
};

const workflowArgs = typeof args === "string" ? JSON.parse(args) : args;

if (
  !workflowArgs ||
  workflowArgs.contract_version !== "harness-node-result-v1" ||
  typeof workflowArgs.plugin_version !== "string" ||
  !workflowArgs.plugin_version
) {
  throw new Error(
    "harness-codex-preflight requires contract_version harness-node-result-v1 and plugin_version",
  );
}

const beginMarker = "HARNESS_CODEX_PREFLIGHT_V1_BEGIN";
const endMarker = "HARNESS_CODEX_PREFLIGHT_V1_END";

phase("Probe");
const rawResult = await agent(
  `--wait --fresh\n` +
    `This is a read-only Harness runtime handshake. Do not edit files, create commits, or inspect repository content. ` +
    `Return exactly these three lines and no other text:\n` +
    `${beginMarker}\n` +
    `{"status":"available","contract_version":"harness-node-result-v1"}\n` +
    `${endMarker}`,
  {
    label: "harness-codex-preflight",
    phase: "Probe",
    agentType: "codex:codex-rescue",
    isolation: "worktree",
  },
);

if (typeof rawResult !== "string") {
  throw new Error("cc-codex preflight did not return text through agent_result");
}
if (
  rawResult.split(beginMarker).length !== 2 ||
  rawResult.split(endMarker).length !== 2 ||
  rawResult.indexOf(beginMarker) > rawResult.indexOf(endMarker)
) {
  throw new Error("cc-codex preflight returned missing or duplicate markers");
}

const payloadText = rawResult
  .slice(rawResult.indexOf(beginMarker) + beginMarker.length, rawResult.indexOf(endMarker))
  .trim();
let payload;
try {
  payload = JSON.parse(payloadText);
} catch (error) {
  throw new Error(`cc-codex preflight returned malformed JSON: ${error.message}`);
}
if (
  !payload ||
  payload.status !== "available" ||
  payload.contract_version !== workflowArgs.contract_version ||
  Object.keys(payload).sort().join(",") !== "contract_version,status"
) {
  throw new Error("cc-codex preflight returned the wrong protocol payload");
}

return {
  provider: "codex",
  driver: "codex_rescue_agent",
  status: "available",
  command: "agent:codex:codex-rescue",
  version: workflowArgs.plugin_version,
  contract_version: workflowArgs.contract_version,
  completion_channel: "agent_result",
  evidence: [
    "codex-rescue-agent-invoked",
    "foreground-result-received",
    "harness-node-result-v1-confirmed",
  ],
};
