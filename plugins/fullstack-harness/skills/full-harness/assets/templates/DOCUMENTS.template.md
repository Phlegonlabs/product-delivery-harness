# Documents

The manifest of every document this delivery flow produces or governs. Keep it at the repository root and keep it current: add a row when a document is created, update its status when it is published or approved, and note archival instead of deleting the row. An unfilled row means the document has not been created yet — not that it is optional.

| Document | Location | Stage | Owner | Canonical | Status |
| --- | --- | --- | --- | --- | --- |
| `AGENTS.md` | root | bootstrap | human + harness | shared governance | |
| `CLAUDE.md` | root | bootstrap | human + harness | imports `AGENTS.md` | |
| `PRD.md` | `docs/product/` | PRD | prd-builder + owner approval | product definition | |
| `wireframes.html` | `docs/product/` | PRD (UI-bearing) | prd-builder + Wireframe Approval | low-fidelity projection | |
| `architecture.md` | `docs/product/` | PRD | prd-builder | technical definition | |
| `stack-decisions.md` | `docs/product/` | PRD | prd-builder | stack choices + rationale | |
| `market-research.md` | `docs/product/` | PRD (gap pass) | prd-builder | sourced research | |
| `design-system.md` / `design-system.json` | `docs/design/` | design (when required) | product-design-builder | frozen design pair | |
| `DEPLOYMENT.md` | root | PRD seed, then owner | human setup + read-only verification | deployment record | |
| `PLAN.md` | root | managed run | harness parent | static plan manifest | |
| `RUN.md` | root | managed run | harness parent | coordination state | |
| `TASKS.md` | root | managed run | rendered by `render_tasks_view.py` | non-canonical view of RUN | |
| `REFINEMENT_BACKLOG.md` | root | run closeout (when needed) | harness parent | deferred refinement items | |
| `docs/goal/evidence/` | `docs/goal/evidence/` | verification | workers + parent | evidence artifacts (SHA-256 bound) | |

Notes:

- The PRD family lives under `docs/product/` with its own artifact lifecycle (staging, publish, archive); root carries the operational documents a person or agent needs during delivery: governance, deployment, plan/run state, tasks, and this manifest.
- `PLAN.md` and `RUN.md` exist only for the managed route; small direct work creates none of the run documents.
- `TASKS.md` is a rendered view: never edit it to change state — change RUN and re-render.
- Evidence artifacts bind to exact SHAs with lowercase SHA-256 records; they are the only accepted proof for UI and verification gates.
