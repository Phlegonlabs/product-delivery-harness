# Agentic Runtime Selection

Use this guide when AI or automation is applicable. Select what the product needs; do not make every AI feature an agent.

## First Choose Execution Shape

| Shape | Choose when | Avoid when | Tradeoffs |
| --- | --- | --- | --- |
| Direct model API or fixed workflow | Inputs, tools, order, retries, and outputs are known; use one or several explicit steps | Users need the system to choose tools or reorder work | Simplest to test, inspect, and roll back |
| Single agent | One bounded role must choose tools or sequence steps from available context | A deterministic prompt/workflow meets the need | Flexible, but needs tool checks, traces, evals, and cost limits |
| Bounded multi-agent | Independent specialist roles or parallel checks have a demonstrated benefit | One role can do the job, or coordination costs exceed that benefit | Clear isolation costs coordination, duplicated context, failure surface, and review work |

Multi-agent is not better by default. Start with the least powerful shape that satisfies a written journey.

## Separate The Runtime Concerns

Record each applicable area separately:

- SDK orchestration: how the app declares tools, handoffs, prompts, retries, and routing.
- Durable execution and state: checkpoints, retries/resume, timeouts, human-in-the-loop waits, and idempotency for side effects.
- Tool and sandbox boundaries: allowlisted tools, permissions, filesystem/network isolation, output validation, dry-run, and undo.
- Retrieval: corpus ownership, freshness, permissions, chunking, reranking, citations, and denial when evidence is absent.
- Evaluation, tracing, and budget: golden/dangerous cases, quality target, trace/observability, rate/spend limits, and escalation on failure.
- Model/provider: capability, latency, price, privacy/residency, fallback, and evaluation. A provider is not the execution framework.

The owner may explicitly delegate final technology selection to the builder, but the chosen topology and controls still become architecture and stack rows. Product Definition Approval remains explicit. This does not authorize implementation.

## Candidate Directories, Not Automatic Vendors

The following are current-source starting points to verify on the PRD date. They do not imply a selection, price, or runtime limit:

- [OpenAI Agents Python](https://openai.github.io/openai-agents-python/) — tools, handoffs, and tracing in an agent SDK.
- [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) — persistence/durable execution and human-in-the-loop patterns.
- [Cloudflare Agents run-workflows](https://developers.cloudflare.com/agents/runtime/execution/run-workflows/) — durable background workflows and realtime-agent integration.
- [Temporal](https://docs.temporal.io/) — durable workflow execution for long-running or high-reliability orchestration.
- [FastAPI](https://fastapi.tiangolo.com/) — a Python API boundary; not a workflow or agent framework.
- [Hono](https://hono.dev/docs) — a JS-runtime API boundary; not a workflow or agent framework.

Where a candidate also provides a vendor's model access, separate the SDK/runtime benefit from model cost and privacy. Verify Cloudflare Workers' runtime boundary separately from a web-framework guide; a Workers web app is not a full Node.js server unless its documented APIs say so.

## Decision Output

Record the selected execution shape and every applicable runtime concern in `architecture.md` and `stack-decisions.md`, with alternatives, costs, build-vs-buy/maintenance ownership, compatibility evidence or spike, and revisit triggers. In the existing AI stack table, put execution shape, orchestration, durable state and sandbox decisions in `Tool execution and approvals`; use the separate context/retrieval, evaluation and observability rows for their own concerns. Do not invent a second approval area. Required journeys need applicable human-approval, tool-denial/no-side-effect, failure/recovery, budget/exhaustion, and output-validation tests. Keep model/provider alternatives distinct from the execution-framework alternative.
