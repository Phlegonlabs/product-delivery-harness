export const meta = {
  name: "harness-runtime-preflight",
  description: "Confirm that Claude Code can execute a Harness Dynamic Workflow.",
};

if (!args || args.protocol_version !== 1) {
  throw new Error("harness-runtime-preflight requires protocol_version 1");
}

const probeSchema = {
  type: "object",
  required: ["status"],
  properties: {
    status: { const: "available" },
  },
  additionalProperties: false,
};

const probe = await agent(
  "This is a read-only runtime handshake. Use no tools and return only the structured status available.",
  { label: "harness-runtime-probe", schema: probeSchema },
);

if (!probe || probe.status !== "available") {
  throw new Error("harness runtime probe agent did not return the expected status");
}

return {
  provider: "claude_code",
  driver: "dynamic_workflow",
  protocol_version: 1,
  status: "available",
};
