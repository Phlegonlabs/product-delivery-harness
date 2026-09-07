# Documents

The manifest of every document this delivery flow produces or governs. Keep it at `docs/DOCUMENTS.md` and keep it current: add a row when a document is created, update its status when it is published or approved, and note archival instead of deleting the row. An unfilled row means the document has not been created yet — not that it is optional.

| Document | Location | Stage | Owner | Canonical | Status |
| --- | --- | --- | --- | --- | --- |
| `AGENTS.md` | root | bootstrap | human + harness | shared governance | |
| `CLAUDE.md` | root | bootstrap | human + harness | imports `AGENTS.md` | |
| `PRD.md` | `docs/product/` | PRD | product-definition-builder + owner approval | product definition | |
| `wireframes.html` | `docs/product/` | PRD (UI-bearing) | product-definition-builder + Wireframe Approval | low-fidelity projection | |
| `architecture.md` | `docs/product/` | PRD | product-definition-builder | technical definition | |
| `stack-decisions.md` | `docs/product/` | PRD | product-definition-builder | stack choices + rationale | |
| `market-research.md` | `docs/product/` | PRD (gap pass) | product-definition-builder | sourced research | |
| `implementation-plan.md` | `docs/product/` | PRD (when requested) | product-definition-builder | sequenced implementation outline | |
| `design-system.md` / `design-system.json` | `docs/product/` | design (when required) | design-system-compiler | frozen design pair | |
| `docs/DEPLOYMENT.md` | `docs/` | PRD seed, implementation reconciliation, deployment check | product-definition-builder + delivery-harness + owner | name-only configuration handoff + deployment record | |
| `docs/ACTIVATION.md` | `docs/` | create-once PRD seed, post-delivery activation | product-definition-builder seed + product-activation + owner | external action, measurement-source, and activation-readiness record | |
| `docs/DOCUMENTS.md` | `docs/` | PRD seed, then owner | product-definition-builder + owner edits | this manifest | |
| `docs/tasks.md` | `docs/` | managed run | rendered by `render_tasks_view.py` | non-canonical view of RUN | |
| `docs/goal/PLAN.md` | `docs/goal/` | managed run | harness parent | static plan manifest | |
| `docs/goal/RUN.md` | `docs/goal/` | managed run | harness parent | coordination state | |
| `docs/goal/DECISIONS.md` | `docs/goal/` | managed run | harness parent | mid-run owner-decision log | |
| `REFINEMENT_BACKLOG.md` | `docs/goal/` | run closeout (when needed) | harness parent | deferred refinement items | |
| `docs/goal/evidence/` | `docs/goal/evidence/` | verification | workers + parent | evidence artifacts (SHA-256 bound) | |
| `docs/{product,design}/archived/` | `docs/*/archived/` | supersede | product-definition-builder / design pass | archived prior documents (move, never delete) | |

Notes:

- The PRD family lives under `docs/product/` with its own artifact lifecycle (staging, publish, archive); run state and evidence live under `docs/goal/`; deployment, activation, this manifest, and the rendered `tasks.md` view live under `docs/`. The repository root carries only what runtimes auto-discover — `AGENTS.md` and `CLAUDE.md` — so every discoverable-by-convention file stays where tools look for it and everything else is a flow contract.
- `PLAN.md` and `RUN.md` exist only for the managed route; small direct work creates none of the run documents.
- `tasks.md` is a rendered view: never edit it to change state — change RUN and re-render.
- Evidence artifacts bind to exact SHAs with lowercase SHA-256 records; they are the only accepted proof for UI and verification gates.
