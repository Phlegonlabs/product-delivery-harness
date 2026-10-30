# Documents

The manifest of the stable documents this delivery flow produces or governs, plus one row per directory of generated records. Keep it at `docs/DOCUMENTS.md` and keep it current: update a row's status when the document is published or approved, and note archival instead of deleting the row. Do not add one row per Epic or per run — those records live in the directories below, and their own records carry the per-item detail. Rows labeled `when required` or `when requested` are conditional; once applicability is known, fill them with the artifact status or `n/a — <reason>`. An unfilled applicable row is missing work.

| Document | Location | Stage | Owner | Canonical | Status |
| --- | --- | --- | --- | --- | --- |
| `AGENTS.md` | root | bootstrap | human + harness | shared governance | |
| `CLAUDE.md` | root | bootstrap | human + harness | imports `AGENTS.md` | |
| `PRD.md` | `docs/product/` | PRD | product-definition-builder + owner approval | product definition | |
| `architecture.md` | `docs/product/` | PRD | product-definition-builder | technical definition | |
| `stack-decisions.md` | `docs/product/` | PRD | product-definition-builder | stack choices + rationale | |
| `ui-design.md` | `docs/design/` | Approved Product Definition (UI-bearing) | ui-design-builder + UI Design Intake / Visual Approval | UI decisions and evidence | |
| `design-system.md` + `design-system.json` | `docs/design/` | Approved UI design when required | design-system-compiler | frozen visual contract | |
| `docs/DEPLOYMENT.md` | `docs/` | PRD seed, implementation reconciliation, deployment check | product-definition-builder + delivery-harness + owner | name-only configuration handoff + deployment record | |
| `docs/DOCUMENTS.md` | `docs/` | PRD seed, then owner | product-definition-builder + owner edits | this manifest | |
| `docs/tasks.md` | `docs/` | managed run | rendered by `render_tasks_view.py` | non-canonical view of RUN | |
| `docs/goal/PLAN.md` | `docs/goal/` | managed run | harness parent | static plan manifest | |
| `docs/goal/RUN.md` | `docs/goal/` | managed run | harness parent | coordination state | |

Generated records — one row per directory, never one row per record:

| Document | Location | Stage | Owner | Canonical | Status |
| --- | --- | --- | --- | --- | --- |
| `docs/epics/` | `docs/epics/` | complete enhancement | owner + harness parent | one round-outcome record per Epic with current-PRD references, not a second PRD or RUN | |
| `docs/product/deltas/` | `docs/product/deltas/` | PRD delta pass (when required) | product-definition-builder | requirement deltas that amend the frozen PRD baseline | |
| `docs/design/ui-references/` | `docs/design/ui-references/` | Visual Approval (UI-bearing) | ui-design-builder | approved connected HiFi package per run | |
| `docs/verification/` | `docs/verification/` | new delivery verification | harness parent + test runner | frozen acceptance expectations and exact-candidate delivery results | |
| `docs/product/outcomes/` | `docs/product/outcomes/` | post-release outcome (when requested) | product-definition-builder + owner | immutable outcome evidence and verdict | |
| `docs/goal/evidence/` | `docs/goal/evidence/` | verification | workers + parent | evidence artifacts (SHA-256 bound) | |
| `docs/product/archived/` | `docs/product/archived/` | supersede | product-definition-builder | archived prior product documents (move, never delete) | |
| `docs/design/archived/` | `docs/design/archived/` | supersede | design pass | archived prior design documents (move, never delete) | |
| `docs/goal/archived/` | `docs/goal/archived/` | run closeout | harness parent | moved coordination set plus closed `ARCHIVE_RECEIPT.json` (never delete) | |

Notes:

- The PRD family lives under `docs/product/` with its own artifact lifecycle (staging, publish, archive); run state and evidence live under `docs/goal/`; deployment, this manifest, and the rendered `tasks.md` view live under `docs/`. The repository root carries only what runtimes auto-discover — `AGENTS.md` and `CLAUDE.md` — so every discoverable-by-convention file stays where tools look for it and everything else is a flow contract.
- `PLAN.md` and `RUN.md` exist only for the managed route; small direct work creates none of the run documents.
- `tasks.md` is a rendered view: never edit it to change state — change RUN and re-render; its Update Log section is the one hand-maintained part, preserved verbatim by the renderer.
- The PRD family and the run family never mix: a run references its PRD only through the frozen content hash in PLAN's sources, nothing under `docs/product/` ever enters `docs/goal/archived/`, and the PRD stays published as the living reference for later enhancement runs.
