export const meta = {
  name: "harness-runtime-preflight",
  description: "Confirm that Claude Code can execute a Harness Dynamic Workflow.",
  phases: [
    { title: "Probe", detail: "Verify arguments, pipeline fan-out, and structured results" },
  ],
};

const workflowArgs = typeof args === "string" ? JSON.parse(args) : args;

if (!workflowArgs || workflowArgs.protocol_version !== 1) {
  throw new Error("harness-runtime-preflight requires protocol_version 1");
}

const probeSchema = {
  type: "object",
  required: ["label", "status"],
  properties: {
    label: { type: "string" },
    status: { const: "available" },
  },
  additionalProperties: false,
};

const labels = ["probe-a", "probe-b"];
phase("Probe");
const probes = await pipeline(labels, (label) => agent(
  `This is a read-only runtime handshake for ${label}. Use no tools and return only the structured label and status available.`,
  { label: `harness-runtime-${label}`, phase: "Probe", schema: probeSchema },
));

if (
  probes.length !== labels.length ||
  probes.some((probe, index) => !probe || probe.status !== "available" || probe.label !== labels[index])
) {
  throw new Error("harness runtime probe agents did not return the expected ordered results");
}

return {
  provider: "claude_code",
  driver: "dynamic_workflow",
  protocol_version: workflowArgs.protocol_version,
  status: "available",
  probe_count: probes.length,
  probe_labels: probes.map((probe) => probe.label),
};
