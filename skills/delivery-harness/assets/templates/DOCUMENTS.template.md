# Documents

The manifest of every document this delivery flow produces or governs. Keep it at `docs/DOCUMENTS.md` and keep it current: add a row when a document is created, update its status when it is published or approved, and note archival instead of deleting the row. Rows labeled `when required`, `when requested`, or `managed run` are conditional; once applicability is known, fill them with the artifact status or `n/a — <reason>`. An unfilled applicable row is missing work.

| Document | Location | Stage | Owner | Canonical | Status |
| --- | --- | --- | --- | --- | --- |
| `AGENTS.md` | root | bootstrap | human + harness | shared governance | |
| `CLAUDE.md` | root | bootstrap | human + harness | imports `AGENTS.md` | |
| `PRD.md` | `docs/product/` | PRD | product-definition-builder + owner approval | product definition | |
| `ui-design.md` | `docs/design/` | Approved Product Definition (UI-bearing) | ui-design-builder + UI Design Intake / Visual Approval | UI decisions and evidence | |
| `wireframes.html` | `docs/design/` | Approved PRD UI Surface Contract | ui-design-builder + Wireframe Approval | structural projection | |
| `design-system.md` + `design-system.json` | `docs/design/` | Approved UI design when required | design-system-compiler | frozen visual contract | |
| `architecture.md` | `docs/product/` | PRD | product-definition-builder | technical definition | |
| `PRD.zh-TW.md`, `architecture.zh-TW.md` | `docs/product/` | PRD drafting and owner review | product-definition-builder | no; Chinese review copies of English sources | |
| `stack-decisions.md` | `docs/product/` | PRD | product-definition-builder | stack choices + rationale | |
| `market-research.md` | `docs/product/` | PRD (gap pass) | product-definition-builder | sourced research | |
| `implementation-plan.md` | `docs/product/` | PRD (when requested) | product-definition-builder | sequenced implementation outline | |
| `YYYY-MM-DD-<release-set>.md` | `docs/product/outcomes/` | post-release outcome (when requested) | product-definition-builder + owner | immutable outcome evidence and verdict | |
| `docs/DEPLOYMENT.md` | `docs/` | PRD seed, implementation reconciliation, deployment check | product-definition-builder + delivery-harness + owner | name-only configuration handoff + deployment record | |
| `docs/ACTIVATION.md` | `docs/` | create-once PRD seed, post-delivery activation | product-definition-builder seed + product-activation + owner | external action, measurement-source, and activation-readiness record | |
| `docs/DOCUMENTS.md` | `docs/` | PRD seed, then owner | product-definition-builder + owner edits | this manifest | |
| `document-sync.json` | `docs/` | invocation review, when retained | harness parent | byte inventory, not approval | |
| `EPIC-<id>.md` | `docs/epics/` | complete enhancement; optional for small fixes | owner + harness parent | round outcome and current-PRD references, not a second PRD or RUN | |
| `delivery-acceptance.json` | `docs/verification/` | new delivery before tests | harness parent | frozen TEST/scenario expectations | |
| `delivery-results.json` | `docs/verification/` | new delivery verification | test runner + parent | exact-candidate observations and evidence links | |
| `docs/tasks.md` | `docs/` | managed run | rendered by `render_tasks_view.py` | non-canonical view of RUN | |
| `docs/goal/PLAN.md` | `docs/goal/` | managed run | harness parent | static plan manifest | |
| `docs/goal/RUN.md` | `docs/goal/` | managed run | harness parent | coordination state | |
| `docs/goal/DECISIONS.md` | `docs/goal/` | managed run | harness parent | mid-run owner-decision log | |
| `REFINEMENT_BACKLOG.md` | `docs/goal/` | run closeout (when needed) | harness parent | deferred refinement items | |
| `docs/goal/evidence/` | `docs/goal/evidence/` | verification | workers + parent | evidence artifacts (SHA-256 bound) | |
| `docs/{product,design}/archived/` | `docs/*/archived/` | supersede | product-definition-builder / design pass | archived prior documents (move, never delete) | |
| `docs/goal/archived/` | `docs/goal/archived/` | run closeout | harness parent | moved coordination set plus closed `ARCHIVE_RECEIPT.json` (never delete) | |

Notes:

- Every skill invocation checks live document and skill drift through `delivery-harness/references/document-sync-contract.md`. Keep the current PRD as the baseline, retain links to historical revisions as references, and never rewrite archived approval or execution evidence. A sync snapshot records reviewed bytes, not approval or capability.
- Delivery acceptance uses the frozen requirement/scenario/platform matrix and evidence register from `delivery-harness/references/delivery-acceptance-contract.md`. Link its actual paths here when applicable; do not duplicate evidence rows. The direct route needs no PLAN/RUN.

- The PRD family lives under `docs/product/` with its own artifact lifecycle (staging, publish, archive); run state and evidence live under `docs/goal/`; deployment, activation, this manifest, and the rendered `tasks.md` view live under `docs/`. The repository root carries only what runtimes auto-discover — `AGENTS.md` and `CLAUDE.md` — so every discoverable-by-convention file stays where tools look for it and everything else is a flow contract.
- `PLAN.md` and `RUN.md` exist only for the managed route; small direct work creates none of the run documents.
- `tasks.md` is a rendered view: never edit it to change state — change RUN and re-render; its Update Log section is the one hand-maintained part, preserved verbatim by the renderer.
- The PRD family and the run family never mix: a run references its PRD only through the frozen content hash in PLAN's sources, nothing under `docs/product/` ever enters `docs/goal/archived/`, and the PRD stays published as the living reference for later enhancement runs.
- Harness 0.38 archival also creates one immutable `ARCHIVE_ANCHOR` at the exact absolute path supplied outside the checkout. It is not a repository document; `ARCHIVE_RECEIPT.json` records its identity, and archive-candidate publication requires the same file.
- Evidence artifacts bind to exact SHAs with lowercase SHA-256 records; they are the only accepted proof for UI and verification gates.
