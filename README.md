<p align="center">
  <img src="./assets/readme-cover-en.png" alt="Product Delivery Harness — define, design, deliver, and verify" width="100%">
</p>

<p align="center">
  <strong>English</strong> | <a href="README.zh-TW.md">繁體中文</a> | <a href="README.zh-CN.md">简体中文</a> | <a href="README.es.md">Español</a>
</p>

<p align="center">
  <a href="https://github.com/Phlegonlabs/product-delivery-harness/actions/workflows/harness-ci.yml"><img alt="CI" src="https://github.com/Phlegonlabs/product-delivery-harness/actions/workflows/harness-ci.yml/badge.svg?branch=main"></a>
  <img alt="Version" src="https://img.shields.io/badge/version-0.65.2-059669?style=flat-square">
</p>

# Product Delivery Harness

Skills repository for turning a product idea or change request into a verified delivery flow with Codex, Claude Code, Pi, or any host that discovers a user skills directory.

It is not a prompt collection. The skill suite separates product definition, visual design, engineering execution, code-security review, activation, and post-release organic-growth review so each stage has one source of truth, a bounded handoff, and its own verification.

> Define the product. Compile the design. Deliver verified software.

**Use it:** [Install](#install) | [Start here](#start-here) | [Typical prompts](#typical-prompts) | [What is included](#what-is-included) | [Standalone skills](#standalone-skills)<br>
**Understand it:** [How the system fits together](#how-the-system-fits-together) | [Operating reference](#operating-reference)<br>
**Maintain it:** [Maintain the skills](#maintain-the-skills) | [Releasing](#releasing) | [Version history](#version-history)

## Install

The repository is public, so no access permission is needed. You need Python 3.10 or newer, Git, and at least one host that discovers a user skills directory such as `~/.agents/skills/` — Codex, Claude Code, Pi, or any other.

To confirm public repository access before cloning, run:

```bash
git ls-remote https://github.com/Phlegonlabs/product-delivery-harness.git HEAD
```

### Fastest setup

Clone the repository and run the installer. It takes one destination-wide lock, stages only Git-index-tracked files from the seven skills, moves current and legacy managed IDs to one timestamped backup under `~/.agents/skill-backups/product-delivery-harness/`, installs the staged trees, and verifies every path and byte before releasing the lock:

```bash
git clone https://github.com/Phlegonlabs/product-delivery-harness.git
cd product-delivery-harness
./install.sh             # macOS / Linux / Git Bash
# Windows PowerShell: powershell -ExecutionPolicy Bypass -File install.ps1
```

Install the pinned Python test/runtime dependencies, including Pillow, before validation:

```bash
python -m pip install -r skills/delivery-harness/requirements-test.txt
```

There is no safe raw-copy equivalent for updates: it would bypass the tracked-file manifest, destination lock, ownership markers, complete verification, and rollback. If neither installer can run, stop and repair that environment instead of copying over an existing install.

<details>
<summary><b>Installer safeguards, legacy migration, cross-skill checks and dependencies</b></summary>

The installer ignores reproducible Python caches and refuses every other untracked or ignored source artifact, including local `.env` and `.dev.vars` values; tracked example files remain allowed. Its lock serializes Bash and PowerShell updaters. Both installers reject tracked symlink/gitlink modes and junction/reparse components in source, destination, backup, staging, and managed targets before and immediately around mutation. Each created target carries an attempt owner marker until full-tree verification finishes, so rollback removes only paths created by that attempt and restores the prior backup. A foreign or concurrently created path is preserved. Re-running the installer is the update path and still requires explicit authorization plus quiesced skill-using sessions. Start a fresh host session only after success. Each run prints the source HEAD SHA and whether tracked `skills/` files have uncommitted changes; a successful install writes that line to `<backup>.source` next to its backup. Uncommitted bytes still install, but the record makes them traceable.

When upgrading from 0.23 or earlier, let the installer archive the legacy directories under their original IDs in the same backup and install all seven current skills: `delivery-harness`, `product-definition-builder`, `ui-design-builder`, `design-system-compiler`, `code-security-review`, `product-activation`, and `seo-growth-review`. The migration is `full-harness` → `delivery-harness`, `prd-builder` → `product-definition-builder`, and `product-design-builder` → `design-system-compiler`; the installer verifies that every legacy ID is no longer discoverable.

The seven bundled skills can be invoked independently; their cross-skill modes validate the approved Product package and exact source identities. A retained `ui-design/2` package checks direct PRD-to-HiFi coverage, copy, CSP and offline/browser evidence, plus a conditional `design-system/3` pair; `ui-design/3` adds the required `design-system/4` package, and Harness 0.59+ RUNs freeze its derived HTML too, while older pins cannot consume `ui-design/3`. The Harness dispatches `design-system/4` to the design-system compiler's checker. Under a 0.59 pin, only a validated frozen maintenance record retains `ui-design/2`; an enhancement requires `ui-design/3`. Hybrid `surfaceContracts` match every approved UI surface, capture mode and responsive set. Legacy contracts keep their original joins. Deployment, Activation, Outcome Review and saved SEO reports share the production identity.

New project Skill Bindings are deliberately unresolved until the session observes installed candidates and the owner confirms one skill per slot. Pins cover each complete skill tree, not only `SKILL.md`. The public dependency manifest pins the source locator and install route for both required UI dependencies: use the host's skill installer to install `frontend-design` from the recorded Anthropic path, and install Impeccable with `npx impeccable install` (its current npx route requires Node.js 22.18+). Then run `check_external_skill_dependencies.py`; a changed upstream tree must not silently replace the pinned bytes. The Harness owns conformance and compilation contracts. Impeccable is never a default read-only Harness reviewer: using its pinned workflow needs separate authorization for subagents, browser/server work, snapshot writes, and any optional binary download.

Managed local build/test uses the project toolchain without Docker or Podman by default. Only explicitly selected container verifiers require an administrator-installed runtime and machine trust policy (`runtime-trust.md`). Archive publication still requires its separate machine trust policy and signing setup (`branch-promotion-contract.md`); the installer creates neither privileged policy.

</details>

<details>
<summary><b>Zero-to-one flow from product idea to measured outcome</b></summary>

### Zero-to-one flow

This is the **v0.65.2** default flow for a new product. Install the seven skills using the setup above and start a fresh host session. Continue only the stages the owner authorized. Enhancements and maintenance reuse approved inputs and inspect the accepted delta; headless products skip UI stages.

```mermaid
---
config:
  flowchart:
    wrappingWidth: 420
    nodeSpacing: 24
    rankSpacing: 30
---
flowchart TD
  subgraph ENG["Product and engineering"]
    direction TB
    P["Researcher + product author + conditional architect<br/>PRD, architecture, stack; reconcile research<br/>Plan AEO, deployment, analytics and access"]
    S["Original author: 1 complete PRD package self-review<br/>Include architecture, stack and Chinese copies<br/>Repair and recheck affected scope"]
    A["Owner: Stack Decision → affected-scope recheck<br/>→ Product Definition Approval"]
    U["Bound frontend author: 3 rendered directions by default<br/>Author checks each; owner selects direction"]
    H["Complete HiFi: preflight + author self-check<br/>1 diagnostic + at most 1 repair/re-review<br/>Each pass: Impeccable critique + audit, browser, H1-H9<br/>Overall ≥85; every dimension ≥80"]
    V["Owner: Visual Approval → design-system compiler<br/>Technical validation + rendered showcase<br/>0 added aesthetic review waves"]
    W["Parent: choose Direct or freeze managed PLAN/RUN<br/>Resolve roles, tasks, TESTs and shared contracts<br/>Isolate parallel writers; integrate serially"]
    T["Before build: toolchain, app IDs, devices/signing<br/>Before repo/CI connection: protection readback"]
    B["First fixed usable build + SHA/artifact<br/>Authorized isolated deployment + Activation preparation<br/>Analytics hooks; retrieve dynamic errors/crashes"]
    J["Prove untested real core journey before dependent expansion<br/>Scoped frontend/backend tasks + focused checks<br/>Risk-based failure, load, cost, migration/restore proof"]
    N["Independent review under the chosen route<br/>Direct: author diff check + 1 exact-SHA security review<br/>Managed: each ready mission/surface before integration<br/>Then fresh unified applicable-surface + security reviews"]
    Q["Applicable UI: 1 read-only Final UI Acceptance<br/>Parity + page quality; consolidated findings, targeted recheck<br/>Stop after 2 failed repairs; stricter lineage wins → final regression"]
    F["Before external trials: tested feedback route to owner<br/>Before unattended Preview/beta: useful alert received<br/>Preparation grants no trial or deployment action"]
    C["Isolated candidate Preview: exact-build acceptance<br/>Managed: local C → archive A; Direct: fixed candidate<br/>Separate publication/readback if Preview uses remote branch"]
    R["Separately authorized main/production release<br/>Verify actual released SHA/artifact<br/>Server-created main: tree equality + fresh full checks/security"]
    ACT["Activation: reuse setup, rebind actual release<br/>Configuration + independent readback + behavior proof<br/>Verify feature events and measurement sources"]
    O["After real measurement window: requested Outcome Review<br/>Per target; aggregate when applicable<br/>Delivery does not wait for adoption"]
    Z["Second failed HiFi review → blocked<br/>Exceptional successor needs explicit owner decision<br/>Changed strategy + acceptance matrix"]
    P --> S --> A
    A -->|"UI scope"| U
    U --> H
    H -->|"Pass"| V
    H -->|"Second failure"| Z
    V --> W
    A -->|"Headless"| W
    W --> T --> B --> J --> N --> Q --> F --> C --> R --> ACT --> O
  end
  subgraph GTM["Optional parallel GTM"]
    direction TB
    G["During PRD: go-to-market: audience, positioning, channels, outcome<br/>Current owner context: Instagram + Threads active<br/>Evaluate Facebook Pages; X optional"]
    CD["gtm-content: selected-channel drafts, assets and CTA<br/>Can start early; label missing proof and availability"]
    CR["Existing content review + owner approval of exact revision<br/>Use truthful planned / Preview / beta / released claims<br/>Verify public-safe destination and actual availability"]
    PUB["Separately authorized publication or scheduling<br/>Read back actual post ID/URL and visibility"]
    M["Existing campaign measurement<br/>Separate engagement, clicks, sessions and verified actions<br/>Missing access or sources stays unknown"]
    G --> CD --> CR --> PUB --> M
  end
  P -. "Audience and task clear" .-> G
  J -. "Verified demo" .-> CD
  R -. "Actual availability evidence" .-> CR
  ACT -. "Verified sources" .-> M
  M -. "Applicable signals" .-> O
```

Solid arrows show stage dependencies; dashed arrows show optional GTM inputs and parallel handoffs. Neither grants actions or adds a review wave. The parent dispatches sibling roles throughout; each checkout has one writer. Freeze shared contracts before dependent parallel work. The review table below retains the full limits: managed runtime review allows one initial review and one repair re-review per cumulative lineage. Changed code needs fresh security review. The current owner uses Instagram and Threads; evaluate Facebook Pages and keep X optional. Each product still selects channels by audience, account access and capacity. GTM and Outcome Review do not block delivery. Enhancements and maintenance keep their scoped routes and pinned rules. For Facebook Pages, confirm Page identity and access, audience fit, and content and reply capacity before selecting it.

The arrows show dependencies, not action grants. `product-definition-builder` owns PRD, architecture and stack decisions; `ui-design-builder` owns directions, HiFi and Visual Approval. New full UI uses `ui-design/3` followed by the `design-system/4` Markdown/JSON/HTML package from `design-system-compiler`. Retained packages and maintenance keep their versioned rules.

#### MultiAgent responsibilities

Roles are delivery responsibilities, not fixed models or mandatory staffing at every stage. The host resolves its actual bindings.

| Role | Responsibility and handoff |
| --- | --- |
| Owner | Existing research, product, stack, direction, visual and action decisions. Agents never supply these approvals. |
| Parent / integrator | Scope, dependencies, authorization, sibling dispatch, result reconciliation, serial integration and handoff. |
| Researcher / explorer | Read-only sourced research or file/symbol evidence for distinct unanswered questions. |
| Architect, when needed | Propose interface, state, trust or migration contracts. Parent reconciles and freezes them within approved decisions. |
| Product / frontend author | Write assigned product artifacts. The bound frontend author owns UI directions, HiFi, frontend implementation and visual repairs. |
| Backend / general author | Implement scoped service or integration work and focused tests. It cannot substitute for the frontend binding. |
| Test executor, when useful | Return actual command, environment and outcome evidence. Testing does not grant approval. |
| Independent reviewer | Read-only findings at existing review points, bound to the exact candidate and required tools. |

Every delegate is a parent-dispatched sibling. With capability and authorization, two independent substantive research questions require two distinct researchers/explorers. Launch dependency-ready work together. One writer owns each checkout; parallel writers need isolated checkouts and nonconflicting scopes after shared interfaces are frozen. Workers never spawn children, approve decisions or integrate their own results. See the [collaboration contract](skills/delivery-harness/references/delegation-contract.md#delivery-collaboration-overview).

#### When foundations happen

Use the existing PRD/architecture/stack, `docs/DEPLOYMENT.md`, `docs/ACTIVATION.md`, TEST rows and task evidence. These steps add no approval gate or review wave.

| Time | Work and required evidence |
| --- | --- |
| Product Definition | Plan AEO/public discovery, deployment targets and isolation, analytics/events/privacy, build access and named owners. Record approved alternatives or explicit non-applicability. |
| Before the first artifact | Observe toolchain, local/CI build route, owned app/bundle IDs, device/emulator and needed signing access. Necessary external provisioning uses a separate operator/provider grant. |
| Before repository connection, CI bootstrap or workflow enablement | A person with authorized host access configures and reads back actual repo/ref protection, host capability, review rules, required checks and checked time. No push/force/delete protection test. |
| First fixed usable build, before dependent features | Implement the approved scaffold, metadata, config and measurement hooks; bind its SHA and actual artifact. Invoke authorized Activation preparation. For approved Cloudflare projects, verify an isolated Preview deployment and smoke through the separate deployment route. |
| First dynamic build | Provide environment/build-bound error or crash retrieval with redaction and applicable symbols/source maps. Existing provider logs may suffice. |
| Before external trials / unattended Preview or beta | Before trials, test one feedback route to its owner and retain a build/context-linked report. Before unattended operation, prove a useful health/error alert reaches its response owner. |
| Actual release | Read existing objects before creating anything. Reuse setup, then rebind and reverify the actual released SHA/artifact, feature events, privacy controls and readiness. |

Public AEO/search work uses approved public surfaces; native screens alone cannot satisfy an AEO outcome. Preserve private surfaces. Web uses its intended GA4 stream and one tag owner; applicable iOS/Android builds use Firebase/native SDKs. Respect approved alternatives and no-collection decisions. Search Console setup is applicable public-discovery preparation; indexing, citations and rankings are later observations, never setup guarantees.

Property creation is configuration. Verify an implemented event in the intended debug/realtime destination before claiming collection. Deployment/bootstrap stays on its separately authorized operator/provider route, outside Harness/RUN. Unavailable native artifacts remain pending; never borrow a web build. Only dependent work waits. See [Initial Product Foundations](skills/delivery-harness/references/initial-product-foundations.md).

#### Engineering evidence within existing work

PRD defines outcomes and measurable quality. Architecture assigns responsibilities, state, interfaces and recovery. Existing tasks define ownership, dependency order and executable acceptance.

For an unproven cross-layer dependency, first verify one real core journey before expanding dependent features. Keep approved platform order, small layer tasks, shared contracts, frontend ownership and visual quality. Independent work continues; unchanged boundaries reuse evidence only under existing freshness rules. A usable scaffold alone does not prove the journey.

Choose load, latency, cost, migration, restore and failure-recovery checks from applicable approved NFRs and TESTs. Record the owner, workload, environment, exact SHA/artifact and actual result at the existing checkpoint with the required prerequisites. Preserve real-sandbox obligations and separate external-action grants. Use existing task, Deployment and Activation evidence; missing proof remains blocked. Do not impose universal targets or another review wave. Early proof does not replace final candidate or release checks.

See [engineering evidence](skills/delivery-harness/references/execution-task-decomposition.md#early-journey-and-engineering-evidence) and [PRD author self-review](skills/delivery-harness/references/pre-delivery-self-review.md#prd-self-review). HiFi retains 85/80; required functional, security and data-correctness checks must each pass.

#### Review counts and stopping rules

An author self-check, independent review, machine check and human decision are different events. Three direction studies are not three independent review waves.

| Stage | Default review / verification and limit |
| --- | --- |
| Research and Product Definition | After drafting and research reconciliation, the original author performs **one complete package self-review**. Review PRD, architecture, stack and Chinese copies together: journeys, requirements, interfaces, risks and TEST coverage. Repair findings, then recheck changes and shared consumers after Stack Decision before Product Definition Approval. Unchanged content retains its verified review identity. No new independent wave. |
| Direction studies | Three rendered studies by default; the same author checks each. Owner selects the direction. A mix/rejection needs a revised complete set and another explicit decision. A single recommended direction needs an explicit owner choice. |
| Complete HiFi | Cheap completeness check and author self-check first. Then **one complete diagnostic wave**; if needed, **one consolidated repair batch and one re-review**. |
| HiFi checks within each pass | Required Impeccable `critique` **and** `audit`, complete required browser coverage and current H1-H9 assessment. Rounded overall mean **at least 85**, every dimension **at least 80**, no block or dispute; then **one Visual Approval**. |
| Design-system compilation | One coherent source/pair/coverage/contrast/type/HTML validation sequence and rendered showcase inspection. Recheck affected technical repairs; no new direction-selection or aesthetic grading wave. |
| Direct code delivery | One writer, focused checks, author complete-diff check and one exact-candidate `code-security-review`. A changed code candidate needs fresh security review. Small UI uses the consolidated UI acceptance below and stops after two failed repair attempts. |
| Managed code delivery | One reviewer per applicable surface at each mission head before integration, then fresh applicable-surface reviews at the unified head, including unified security. The frozen PLAN declares the nodes. Runtime review permits an initial review and one repair re-review; budgets stay cumulative across the same lineage. |
| Implementation UI acceptance, when applicable | **One independent read-only Final UI Acceptance** combines the Final Visual Parity Loop and page-quality checks on the exact candidate. One reviewer shares current evidence and consolidates defects. Recheck original defects and affected consumers; retain the required matrix and stop after **two failed repair rounds**, subject to the stricter existing lineage budget. Impeccable requires separate authorization and does not replace the reviewer. |
| Candidate and production | Verify isolated candidate Preview, then the actual promoted production build separately. Earlier Preview evidence cannot prove production. A server-created main SHA needs tree equality, fresh full verification and security review. These are release checks, not HiFi taste waves. |
| Activation | Per target/action: configuration or manual evidence, independent readback and applicable behavior proof. Verify early preparation and actual release separately; action count depends on required targets. |
| Outcomes | After the real measurement window, perform the owner-requested per-target Outcome Review and the multi-target aggregate when applicable. History is append-only. Applicable `seo-growth-review` is optional; delivery does not wait for adoption. |

HiFi uses one lead grader by default; up to two specialist siblings require an owner request or recorded high-impact risk. Browser, Impeccable and H1-H9 checks share one frozen candidate and diagnostic wave. The lead consolidates the assessment before repair; no separate aesthetic or scoring wave follows. Re-review follows original defects and affected consumers while retaining mandatory Impeccable scope, complete browser coverage and current scores. After a second failed review, stop at `blocked`. One exceptional successor re-review requires explicit owner approval of a changed strategy and acceptance matrix. A generic instruction to continue is insufficient. See the [HiFi rubric](skills/ui-design-builder/references/ui-grading-rubric.md#repair-re-review-scope). Frontend dispatch includes source-bound direction studies, screens, fonts, assets and visual-feature sources. Direction exploration permits explicitly pending captures; recorded identities remain checked. The author inspects them before editing.

Reusing an earlier visual PASS requires evidence for both acceptance components and complete scope coverage; tree identity alone is insufficient.
The counts describe Harness stage passes. Impeccable still follows its complete pinned workflow and internal assessments; its native totals do not replace H1-H9 grading.

Stop on PASS; do not chase 100. Do not repeat same-scope review on an unchanged candidate. A changed SHA/input requires applicable fresh evidence. Managed node counts and repair allowances remain governed by the PLAN and original lineage; renaming a wave never creates another budget. See the [implementation verification gates](skills/delivery-harness/references/verification-gates.md#final-visual-parity-loop).

Reuse only under existing exact-execution or qualifying non-security byte-identical rules. Security review never uses that skip.

Managed's exceptional successor generation also needs the quoted owner decision, its decision ID and user-turn reference, changed structural strategy and acceptance matrix. It grants exactly one extra review, not a reset of earlier attempts. See [review lineage](skills/delivery-harness/references/graph-orchestration.md#root-cause-repair-escalation).

#### Delivery and release handoff

`delivery-harness` keeps one bounded writer and one verification sequence direct. Managed work follows its [stage routes](skills/delivery-harness/references/stages/managed-delivery.md), frozen source joins and `record-observation` preflight before isolated missions. Run the planned broad cross-cutting regression after reviews and repairs converge.

Managed closeout keeps candidate C local, then archives A with exact main evidence and an external immutable anchor. When Preview builds from the remote branch, separately authorized trusted-host publication/readback precedes its isolated candidate gates. Otherwise follow the approved candidate-verification route. Separately authorized main promotion precedes production verification. A post-A failure uses the existing continuation route. Direct work skips RUN archival and retains its fixed candidate. Follow [publication](skills/delivery-harness/references/trusted-host-publication.md) and [promotion](skills/delivery-harness/references/branch-promotion-contract.md) contracts.

`product-activation` reuses early setup and verifies the actual release; Outcome Review consumes its verified measurement sources later. Optional `go-to-market` and `gtm-content` prepare project-fit strategy and reviewable drafts alongside the appropriate stage. They grant no publication, scheduling or messaging authority.

**Skill-source release exception:** this repository uses reviewed PRs directly to protected main. If the provider creates a new main SHA, [source release rules](skills/delivery-harness/references/governance/source-maintenance.md#required-verification) require fresh full verification and security review before tagging. Tree equality does not replace them. This is exact-release verification, not another product UI review wave.

</details>

<details>
<summary><b>Running installed skills and publication checks</b></summary>

### Running installed skills and publication checks

Resolve each `<skill-name-skill-root>` to its installed absolute directory (normally `~/.agents/skills/<skill-name>`), quote the script path, and keep the working directory and `--repo-root` at the target project. Reference paths such as `skills/<name>/scripts/` are logical installed paths, not a requirement to copy skills into that project. Source-repository maintenance commands below retain their repository-relative paths.

Skill Bindings checks default to all slots. Product Definition uses `--stage product-definition` and may retain `pending`/`pending` future rows. UI authoring and compilation use `ui-design` and `design-compilation`; `backend` is limited to a proven headless or backend-only scope. Each stage rechecks required installed full-tree pins; no earlier result grants a later stage.

Approve UI artifacts at final logical paths in a separately authorized publication checkout at the source HEAD with complete Git history. `check_ui_publication.py` compares upstream bytes and runs the approved Product and final UI gates; after authorized publication, `--published` checks exact transferred bytes. `.ui-staging` is for unapproved drafts. Compiler `sourceBindings.uiDesign.sha256` uses `ui_approval_digest.py`, excluding derived pair/replacement linkage and, for `ui-design/3`, the Package action and pair disposition lines, so an unchanged package can switch to `reuse`; other bindings use raw-file hashes. Homogeneous responsive sets stay global, while hybrids use exact per-surface `surfaceContracts` and approved stack semantics.

Design System Compiler changes in 0.55.0: `stylingMechanism` stays a closed enum but only has to name the verbatim Stack styling approach kept in `stackSemantics.stylingMechanism` (for example `plain CSS` for `modern vanilla CSS`, or `platform theme` for native styles). The pair-less preflight has no separate command; it runs inside `check_design_system_pair.py --repo-root`. `tokenSources` and `primitiveSources` must be exact repo-relative paths. `check_color_contrast.py` accepts `#RGBA` and `#RRGGBBAA` foregrounds over an opaque background, and `check_type_scale.py` accepts rem and em sizes with `--root-font-size` (default 16px). Its 1.5 text and 1.1 heading line-height limits are house readability floors, not WCAG AA rules. The legacy Harness join now checks design-system/2 pairs against the repository root.

Private HTTPS publication may use the administrator's exact-endpoint credential-helper policy from `trusted-host-publication.md`. Requests bind policy/helper hashes; prepare, trusted-host push, and recovery reject drift and never inherit arbitrary repository/user helpers. No credentials enter evidence. Activation may prepare separately authorized deployment prerequisites at a fixed implementation SHA; readiness and verified measurement handoff still require exact deployment evidence. Activation checker commands include PRD, architecture, deployment, stack decisions, activation path, and repository root.

Trusted-host publication and the legacy pre-0.38 run-branch push both run isolated from repository hooks, fsmonitor and askpass: `core.hooksPath` points at a fresh empty directory, `core.fsmonitor` is off and askpass is empty. The Git config preflight treats a linked worktree's shared config and `config.worktree` as repository config, and rejects a repository `core.askPass`; URL-scoped TLS, header and cookie settings are rejected for remote access and publication, while local reads in a CI checkout still work. Git and verifier output is read as UTF-8. A short window remains between the remote recheck and the no-force push, in which another actor could fast-forward the run branch to an ancestor of A, so keep run-branch push access limited to the trusted host. Run-branch publication uses the trusted host because its signed evidence is archive state; `main` promotion is a separately authorized plain no-force push and does not require A to be published to its run branch first.

</details>

A `deployment/2` record adds Release Source Provenance. Each target binds a bounded retained observation JSON by hash: repository, source and resolved refs, source SHA, artifact, observation time, and actual command or provider output. The caller supplies `repo-root` and `expected_repository` independently; a symbolic candidate/1 ref also needs a concrete `candidate_ref`. The validator reads bytes only, never executes commands or fetches providers, and treats a hash as integrity rather than authenticity. Pending preparation and historical inspection stay valid. Full Deployment checks, including resource isolation and record validity, gate ready closeout, verified sources, SEO, and Outcome. Explicit target subsets do not replace complete inventories; blocked and all-n/a records retain compatibility.

For strict symbolic-candidate proof:

```bash
python "<delivery-harness-skill-root>/scripts/check_deployment.py" --deployment docs/DEPLOYMENT.md --architecture docs/product/architecture.md --require-source-provenance --repo-root <actualFrozenRepo> --expected-repository <owner/repository> --candidate-ref <candidate-ref>
```

## Start here

| If you have... | Start with | What you get |
| --- | --- | --- |
| A product idea | `product-definition-builder` | An owner-approved Product Definition with complete frontend/backend architecture, stack choices, UI behavior, release targets, and tests |
| An approved Product Definition that needs UI design | `ui-design-builder` | PRD preflight, intake, direction selection, connected HiFi, completeness checks, Impeccable/H1–H9, Visual Approval and the design-system decision |
| A scoped change in an existing repository | `delivery-harness` | Direct implementation for small work, or a managed PLAN/RUN flow for large work |
| A fixed integrated code candidate | `code-security-review` | A read-only, exact-SHA security review with validated source-to-sink findings and explicit coverage gaps |
| A delivered release that needs external setup | `product-activation` | Exact authorized console actions, verified measurement sources, and target-by-target activation readiness |
| A public production site that needs SEO or organic-growth analysis | `seo-growth-review` | A read-only technical and measurement review, evidence-ranked keyword/page opportunities, and routed follow-ups |

Each bundled skill can be invoked on its own; the full pipeline is optional. Each mode still enforces its declared inputs and dependencies.

<details>
<summary><b>Optional reference library and technology, design and Cloudflare catalogs</b></summary>

A shared optional reference library compares 19 technology and design domains without choosing a default stack. The [selection rule](skills/delivery-harness/references/reference-selection.md) starts from the need and reads only the relevant domain under [option-library](skills/delivery-harness/references/option-library/README.md). It preserves an existing stack and never makes CSS/Tailwind, icons, Cloudflare, Expo/React Native, GSAP, or any provider mandatory. Adopted choices go into existing product, architecture, stack, UI, or task records; no new gate, registry, runtime, or approval authority is added.

The frontend catalog includes TanStack Start/Router and the supporting ecosystem as separate choices. Architecture examples compare complete managed React, portable React, content, realtime, Python and business-app stacks. They also cover server-driven HTML, local-first sync, durable workflows, tenant data isolation, headless content/conditional commerce and independent typed APIs, with failure checks and exit costs. Maturity observations carry dates; each project's existing stack checkpoint still decides adoption.

Design references include component foundations, eight visual directions and manual discovery with Mobbin, Dribbble, Awwwards, Refero and MotionSites. Owners share selected case/original-site links or screenshots; no design-reference MCP connection is added. React Bits supplies effect components and Anime.js supplies an animation engine; source reuse and dependencies still follow the existing stack and license decisions.

The docs-weight visibility report includes nested optional reference Markdown and adds no gate.

The Cloudflare catalog separates compute, data, agents/search, browser/sandbox, media/email and analytics roles. Basin, K2, Artifacts, framework adapters, CLI and skill candidates include dated maturity or migration checks; catalog coverage does not establish local installation, account availability or deployment readiness.

Void appears as an optional full-stack SDK/CLI path. Native or framework routing is a stack decision, direct Cloudflare stays `cloudflare`, and a team Void platform remains a separate deployment decision. Void Preview needs a proven build/config path or an approved isolated deployment through Void.

</details>

<details>
<summary><b>Design translation, motion, platform targets and design freshness</b></summary>

### Design translation and reusable patterns

App + companion Web products use one PRD with separate iOS, Android and public-showcase surfaces; authenticated Web apps are included only when scoped. React Native + Expo is a reference option, not a required or default stack; choose technology from product needs and preserve existing approved decisions. Native phone targets, Web widths, shared-code boundaries and platform-specific design, tests and release paths follow the [App and companion Web contract](skills/product-definition-builder/references/mobile-stack-selection.md#app-and-companion-web-contract). Choosing Expo for mobile does not select the website stack or approve paid EAS services.

Internal HiFi rules require measured checks for compressed controls, alignment, clipped content and open layers, plus product-specific anti-slop review. Inspect long copy, text scaling and widths between Web targets; retain element-level evidence and repair shared causes. Hiding overflow or increasing a score cannot clear a broken layout. These rules use the existing review gates and do not require Hallmark.

The [modern design source guide](skills/ui-design-builder/references/modern-design-sources.md) maps Web accessibility, Apple/Android platform guidance and recent Anthropic/Google Labs AI-design practices into the existing handoff and review. It separates standards from aesthetic advice and preserves platform choices, review widths and bounded repair limits. [Page design profiles](skills/ui-design-builder/references/page-design-profiles.md) adapt Taste ideas by purpose: landing/portfolio pages can select distinctive font roles, one- or two-line desktop heroes and required expressive motion; dashboards, data pages and forms prioritize readable density and functional feedback. Record choices and mobile/localization/reduced-motion exceptions in the existing brief; retain approved decisions.

Motion now has a clear ladder in the [motion and media router](skills/ui-design-builder/references/motion-and-media-routing.md): CSS/WAAPI, then Motion, GSAP and Three.js, each only when the approved stack includes it. Higgsfield supplies generated media, including GLB models for an approved Three.js region. When the owner states no motion posture, the proposal follows what the page actually shows and plays live in the direction study. Provider use, regions and cost limit are asked once in the design intake. HiFi embeds media as `data:`; a library that cannot run there gets a deterministic approximation and is marked for verification in the first implementation slice. H6 also judges motion craft, and inspected references keep a screenshot or recording plus the license of any adapted template code.

Direction studies and HiFi use the exact approved PRD responsive targets. The retained legacy Wireframe template offers 390, 768, 1024 and 1440 px examples; these are review widths, not mandatory breakpoints or a new authoring stage.

Design prompts read the PRD UI Surface Contract directly. Record constraints and creative freedom in the existing Design Brief Page-purpose mapping; do not duplicate per-page requirements. Compare primary and stress cases, then expand the selected direction into complete HiFi. The PRD owns required behavior and content; the designer chooses composition and visual expression.

Incremental changes preserve unnamed scope. An explicit **full design rebuild with retained PRD** instead starts fresh composition and direction under the observed skill contract, preserving product/stack/copy constraints and known usability failures. Old design files and approvals remain history; replacement, archival and installation keep their own authorization. New iOS scope defaults to iPhone with smaller/larger phone review targets and Dynamic Type checks; iPad remains opt-in and existing PRD requirements stay binding. Native HTML never proves native behavior.

The seven [composition recipes](skills/ui-design-builder/assets/templates/composition-patterns.json) remain optional references for direction/HiFi work: four Web and three iPhone patterns. Select, adapt or reject them to suit the product. Preserve bilingual copy, language/direction tags, long-content checks and the PRD language matrix. No recipe imposes a hero/features/CTA layout.

After applicable skill updates and before implementation, [design freshness](skills/ui-design-builder/references/design-freshness.md) checks inventoried artifact and input hashes, skill provenance and downstream dependencies. Unknown identity remains unknown; a changed skill requires semantic review, not automatic redesign. `check_design_freshness.py` is read-only and never approves a design. Include every HiFi sibling and still run the full package validators. Resolve affected gaps before coding when implementation is demonstrably not started.


</details>

## Typical prompts

Codex accepts the `$skill-name` form below. In Claude Code or any other host, ask for the skill by name, such as `product-definition-builder`. In Pi, use its discovered project skill or pass the skill directory with `--skill`, then ask for `delivery-harness` by name.

```text
Use $product-definition-builder to define this product, including complete frontend/backend architecture, data/auth/deployment choices, coherent stack options, UI behavior, release targets, tests, and Product Definition Approval. Stop before UI design.
```

```text
The Product Definition is approved. Use $ui-design-builder with the `ui-design/3` contract and mandatory $frontend-design. Run the product preflight, read the PRD UI Surface Contract directly, and show three materially different directions over the same representative cases for my selection.
```

```text
I selected a direction. Continue $ui-design-builder with $frontend-design: build the complete connected HiFi, run the HiFi completeness preflight, then run separately authorized $impeccable critique and audit plus H1-H9 grading. Ask for one full Visual Approval covering copy, structure, product menus, tabs, visuals and tokens, then use $design-system-compiler for the required `design-system/4` pair and frozen derived HTML.
```

```text
Use $delivery-harness to implement the approved plan, building each page from its approved HTML reference in docs/design/ui-references/ within the recorded tolerance.
```

```text
Use $delivery-harness to review the existing app, plan the required work, and stop before implementation.
```

```text
Use $delivery-harness to implement the approved plan. Create a branch and commit the verified change, but do not push or open a PR.
```

```text
Use $delivery-harness only if the size gate selects the direct route: implement this bounded change, verify one fixed candidate, and push that non-default branch under this exact authorization. Stop if PLAN/RUN managed delivery is required; managed publication needs a new post-archive request.
```

```text
The delivery is complete. Use $product-activation for the production release targets, configure only the exact external actions I approve, verify each result by read-back, and stop after recording activation readiness and the measurement-window handoff.
```

```text
The RUN is complete on its non-default branch. Use $delivery-harness to dry-run and archive the completed coordination set on that same branch, verify the archive-only candidate, and stop before any push or main promotion.
```

```text
The archive-only candidate A is verified. Prepare its immutable trusted-host publication request from the external anchor and stop. Do not execute the emitted publication command locally; wait for separate trusted-host evidence and recovery.
```

```text
The production measurement window has closed. Use $product-definition-builder to validate the Outcome Review against the exact PRD metrics, TEST signals, deployment, Activation hash, and verified MS sources.
```

```text
Use $seo-growth-review to audit this production website, reconcile Search Console visibility with GA4 on-site outcomes, prioritize evidence-backed keyword and page opportunities, and route every proposed change without modifying the site or external accounts.
```

```text
Use delivery-harness on this host to execute this plan. Observe native capabilities and preserve installed roles, models and fallbacks.
```

For a multi-mission delivery, state the intended local and remote outcome. Branch creation, commits, integration, each push, deployment, worktree removal, and deletion remain separate actions. Post-RUN promotion may update only `main`, with exact action-time authorization, fast-forward proof, read-back, and complete candidate testing.

## What is included

| Skill | Use it for | Main output |
| --- | --- | --- |
| `product-definition-builder` | Discovery, research, security requirements, measurable product/UI behavior, complete frontend/backend architecture, coherent stack choices, release targets, tests, and Product Definition Approval | Approved `PRD.md`, `architecture.md`, `stack-decisions.md`, and research artifacts |
| `ui-design-builder` | PRD preflight, intake, three-direction default, connected HiFi, completeness checks, Impeccable/H1–H9, Visual Approval and Design System Need Gate; mandatory stage reads own authoring and routing detail | `docs/design/ui-design.md`, direction studies and the approved complete HiFi package |
| `design-system-compiler` | Compiling an approved `ui-design.md` target into the frozen design-system pair after Visual Approval when required, plus its derived source-bound HTML specimen book; mandatory stage reads own compile, validation, publication and routing detail | `docs/design/design-system.md`, `docs/design/design-system.json`, `docs/design/design-system-preview.html` |
| `delivery-harness` | Shared size gate, security-aware task gates, PLAN/RUN, authorization, local verification, and integration, plus the runtime adapter reference (`references/runtime-adapters.md`) holding one general capability contract mapped to observed native tools | Direct work or `PLAN.md` + `RUN.md` |
| `code-security-review` | Read-only security review after implementation and unified integration, preferably in a fresh sibling agent; active penetration testing and remediation stay outside this skill; mandatory stage reads own inputs, workflow and handoff detail | Exact-SHA decision, trust-boundary coverage, validated findings, and remediation tests |
| `product-activation` | Initial-build external setup and final release verification: exact authorization, capability routing, read-back, behavior evidence and measurement handoff | `docs/ACTIVATION.md` |
| `seo-growth-review` | Read-only post-release technical SEO, measurement integrity, keyword research, organic-traffic diagnosis, and query-to-page opportunity prioritization; mandatory stage reads own inputs, review method and reporting detail | Inline review by default; optional dated report on explicit request |

<details>
<summary><b>How the delivery core sizes work: direct or managed</b></summary>

The delivery core makes one size decision before it invokes managed orchestration:

- Small work stays direct without PLAN/RUN, but resolves required roles before choosing its executor. UI authoring uses the host-bound frontend worker, not the parent. Read-only delegation alone does not require a managed run.
- The [parent-owned delegation contract](skills/delivery-harness/references/delegation-contract.md) applies across Product Definition, UI Design and delivery. Two independent substantive research/exploration questions require distinct researcher/explorer instances when authorized and capable. Capacity limits use bounded waves. The pure `readonly-assignments/1` API joins by assignment, attempt and frozen input identity, accepts reordered results, and rejects missing, duplicate, stale or reused-worker results. Parent launch evidence remains separate from child claims. Required role bindings and external-runtime grants must be checked before launch; a missing mandatory delegate never silently becomes parent work. Availability-only fallback preserves host policy, termination checks and partial work. One writer owns each checkout, including the parent; independent review still requires its actual tools.
- Architecture assignments start with a caller example, then define state ownership and failure recovery. Code reviews apply this method to affected boundaries. Local repairs reuse accepted decisions.
- Large work enters managed planning. It may use `PLAN.md` and `RUN.md` for a managed-sequential delivery or for multiple missions and durable handoff; `new_run.py` writes the initial `docs/tasks.md` with `--out` and `--repo-root`, and guarded `accept-wave`, `record-worker-result`, `reject-worker-result`, `record-integration`, `reconcile-candidate-head`, `reconcile-coordination-head`, `reconcile-interrupted`, `reconcile-interrupted-reviews`, and `close-wave` transitions with `--repo-root` refresh it while preserving the Update Log. Projection failure never rolls back RUN; the standalone `render_tasks_view.py` repairs or checks that non-canonical view. This source repository does not keep a separate root `Tasks.md` flow log.

Each required integration or wave-close checkpoint can commit its exact coordination files as one ordinary direct child, then freshly observe and bind that head with `reconcile-coordination-head`. The guard accepts only supported exact coordination/generated-view paths, keeps product and frozen design sources out, checks live/observed identity and clean product bytes, preserves old evidence, and re-arms current exact-head reviews and gates; isolated mission workers may continue while parent-side reviewers and checks are quiescent.

- The selector derives `managed_sequential` for fewer than two actually selected safe write missions and `parallel_graph` for two or more. Scheduler fan-out starts only for the latter; the runtime driver remains a separate transport fact. The core applies one general capability contract; the agent maps current native tools without a provider-specific section.
- RUN execution never waits for remote CI. Branch promotion is a separate closeout stage: exact candidate and applicable isolated preview-environment verification must finish before `main` can move.

Only RUN and its declared generated tasks view are clean-checkout exceptions; verifier hashes still protect both. Product dirt and hand-authored views still block. Routine RUN operations use guarded transitions, while formal revisions preserve history and need exact new authorization. For a package containing only `Selected`/`Required` layers with no approved new option, keep `Approved option map: None` and skip the optional generator. The checker accepts case-insensitive `None` without an options table only when no layer or option is newly approved.

Size means coordination scope and blast radius, not a raw file or line count. If small work grows, the Harness preserves completed work and plans only the remainder.

</details>

Runtime timing can retain parent-observed dispatch and backoff intervals through the guarded `record-runtime-observation` command.
It uses existing reservations and metrics, rejects conflicting replay, and never advances execution or infers total delivery time.
See [host interval recording](skills/delivery-harness/references/runtime-performance.md#parent-observed-host-intervals).

## Standalone skills

[Go To Market](standalone-skills/go-to-market/SKILL.md) selects channels and experiments from the project's audience, positioning, voice and capacity.
[GTM Content](standalone-skills/gtm-content/SKILL.md) prepares X posts/threads and other channel-specific copy, asset briefs and proposed calendars for owner review.
Both reference existing product pages, success metrics and measurement sources when available. Missing records do not block drafting.
X guidance covers [channel fit](standalone-skills/go-to-market/references/channel-selection.md#channel-hypotheses) and a [content playbook](standalone-skills/gtm-content/references/channel-playbooks.md#x-twitter).
Reuse verified demos and availability claims in the existing campaign package, then join published post IDs to destinations and product outcomes.
Keep public engagement, authorized clicks, destination sessions and verified actions separate; missing analytics access remains an explicit gap.
These handoffs reuse existing records and review points without adding a review wave.
Content approval, publication, scheduling and measurement setup remain separate actions.
After separately registering both complete skill directories, invoke `$go-to-market` for strategy and `$gtm-content` for drafts.

[README Studio](standalone-skills/readme-studio/SKILL.md) helps other projects write a distinctive, brand-first GitHub README with real demonstrations, a useful quickstart and renderer-specific checks. Its [dated case library](standalone-skills/readme-studio/references/case-library.md) draws on Starship, Bruno, Transformers, tldraw and Vite. Visual work follows the target project's frontend route and includes before/after evidence.

Registry images need a working destination URL; including an image in a package alone does not prove that it renders there.

[Release Packager](standalone-skills/release-packager/SKILL.md) prepares applicable artifacts for Node/Bun, Python, Go/Rust, containers and desktop/mobile apps using the project's native tooling. It tests actual package contents and consumer paths, then reconciles README/release facts. Builds, signatures, installation tests and publication retain separate evidence; missing runners or signing material remain explicit gaps. It adds no automatic CI pipeline.

These sources are independent of the seven-skill bundle and are not installed by `install.sh` or `install.ps1`. Open the linked `SKILL.md` with its references in your host, or register the complete skill directory using that host's supported discovery mechanism. Registration is a separate local action; this repository does not automatically install it. Once available, invoke `$readme-studio` to improve a README or `$release-packager` when preparing a release. Keep the project's language, license and supported channels; publishing follows its existing authorization.

## How the system fits together

```mermaid
flowchart LR
  Idea["Product idea or change request"] --> PRD["Product Definition candidate\nPRD + architecture + stack"]
  PRD --> Market["Post-draft market reconciliation"] --> ProductGate{"Stack Decision + PRD self-review +\nProduct Definition Approval"}
  ProductGate -->|"approved UI product, explicit request"| UIDesign["ui-design-builder\nintake + directions + UI self-review"]
  UIDesign --> UIReview["selected direction + complete HiFi\ncompleteness + self-review + Impeccable + H1–H9"]
  UIReview --> Design["approved HiFi target\ndesign-system-compiler when required"]
  ProductGate -->|"approved headless product"| Harness["delivery-harness\nShared delivery core"]
  ProductGate -->|"approved scoped enhancement or maintenance; no affected design gate"| Harness
  Design -->|"approved all-pages HTML reference or design-system pair"| Harness
  Harness --> Runtime["Observed native capabilities\nOne general contract"]
  Runtime --> Security["code-security-review\nfresh unified exact-SHA review"]
  Security --> Evidence["Broad final tests and UI evidence"]
  Evidence --> Close["RUN closes on exact integration head"]
  Close --> Archive["Archive coordination on run branch\ncommit + reverify archive-only candidate"]
  Archive --> Push["External request/attempt/receipt\nfor exact candidate push"]
  Push --> Candidate["Verify exact candidate SHA\nlocal + isolated preview gates"]
  Candidate --> Main["Separately authorize fast-forward\nexact SHA to main"]
  Main --> Activate["product-activation\nExternal setup + read-back"]
  Activate --> Outcome["Verified measurement sources\nLater outcome review"]
  Activate -.-> SEO["seo-growth-review\nOptional organic-growth review"]
  SEO -.-> Outcome
```

<details>
<summary><b>Design-system binding, token evidence and pre-delivery self-review</b></summary>

A retained `ui-design/2` package has no grayscale Wireframe or W1–W5 stage. Layout, typography, hierarchy and responsive behavior are explored directly in representative visual studies and verified in HiFi. Historical Wireframe tools remain available for read-only inspection and validation.

HiFi supplies the complete source-derived Design Tokens view. A `ui-design/3` package always compiles `design-system/4`: its `showcase` binds every primitive variant, component state and motion variant to an approved HiFi element, and `design-system-preview.html` renders them as a specimen book without inventing styles. For `ui-design/2`, when the Need Gate requires a formal pair, the compiler creates `design-system/3`. Both bind the approved PRD, architecture, stack, UI contract and HiFi package, without a Wireframe binding.

HiFi copy provenance uses embedded `ui-hifi-copy/1` metadata and product DOM bindings. Static text, dynamic display contracts and paired languages remain checkable. Tokens show actual values, purposes and control variants; reviewer text cannot satisfy product coverage.

Impeccable critique and audit remain mandatory. HiFi requires an overall score of at least 85 and every H1-H9 dimension at least 80. Blocking findings and required evidence checks still apply.
The `ui-design/3` completeness CLI reports unresolved static animation provenance before approval. These advisory diagnostics create no registry or compile-readiness verdict.
One complete diagnostic wave allows one repair batch and one re-review of original defects and affected consumers. Keep current receipts and required browser coverage; do not restart broad qualitative discovery.

Token observations retain raw source/display values separately from browser-normalized source/applied values, so hex colors, rem dimensions and keyword weights compare correctly.

Resume at a stage only when its prerequisites remain current. Follow the [pre-delivery self-review contract](skills/delivery-harness/references/pre-delivery-self-review.md): after post-draft market reconciliation and accepted revisions, review the PRD package; review UI structure/directions before direction selection; review the connected HiFi before independent review and Visual Approval. Keep candidate identities, findings, repairs and unresolved blockers in the existing task record. Self-review does not replace required independent review or owner approval. UI-bearing initial delivery enters Harness execution only after the applicable checks pass; a deferred UI phase cannot bypass them. Headless products record UI checks as not applicable, and enhancements/maintenance review their accepted scope. These are parent semantic checks; validator success alone does not prove self-review.

Harness 0.57.0 removes the UI-deferred shortcut for UI-bearing initial delivery, including backend-first slices. A backend binding check does not waive this handoff. When a new task consumes earlier approvals, perform present-day catch-up self-reviews of the applicable scope; record the approval and candidate identities without backdating or reopening unchanged owner decisions. Earlier pinned RUNs keep their contracts.

</details>

<details>
<summary><b>Full skill lifecycle diagram, approval gates, deployment, Activation, SEO and commerce rules</b></summary>

### Full skill lifecycle

The complete lifecycle across all seven skills, with every gate and the cross-cutting mechanisms:

```mermaid
flowchart TB
    user([User idea or change request])

    subgraph PRD["product-definition-builder — product definition"]
        direction TB
        interview[Structured interview<br/>3 free-text segments + AskUserQuestion]
        pkg["Core package candidate<br/>PRD.md + architecture.md<br/>+ stack-decisions.md"]
        mr["market-research.md<br/>(reconcile candidate, skippable)"]
        rchoice{{"Platform optimization recommendations<br/>owner accepts / revise / defer / reject"}}
        revision["Apply accepted changes only"]
        sgate{{"Stack Decision Checkpoint<br/>Required | Selected | Approved"}}
        pgate{{"Product Definition Approval<br/>all products"}}
        ra["research-first assessment<br/>research-assessment.md (skippable)"]
        rgate{{"Research Gate<br/>go | clarify | stop"}}
        interview --> ra --> rgate --> pkg --> mr --> rchoice
        rchoice -->|accepted| revision --> sgate --> productself["PRD author self-review"] --> pgate
        rchoice -->|revise proposal| mr
        rchoice -->|none, deferred, or rejected; no blockers| sgate
    end

    subgraph DESIGN["ui-design-builder — UI design (explicit owner request)"]
        direction TB
        intake{{"UI Design Intake<br/>style + motion + media; wait for owner"}}
        preflight["PRD preflight<br/>operations + states + responsive + copy"]
        studies["frontend-design<br/>three directions by default"]
        style["frontend-design<br/>Style Integration + HiFi target"]
        hifi_review["Impeccable critique + audit<br/>H1–H9 grading"]
        vgate{{"Human Visual Approval"}}
        dgate{{"Design System Need Gate"}}
        pending["Approved required/pending marker<br/>bound to Visual Approval digest"]
        pair["design-system-compiler preflight + compile<br/>design-system.md + design-system.json"]
        linked["Owner links pair hashes<br/>final UI validation"]
        intake --> preflight --> studies --> directionself["UI structure/direction self-review"] --> directionChoice{{"Direction selection"}} --> style --> completeness["HiFi completeness preflight"] --> hifiself["HiFi author self-review"] --> hifi_review --> vgate --> dgate
        dgate -->|required| pending --> pair --> linked
        dgate -->|not_required| target[Approved page-faithful target]
    end

    subgraph HARNESS["delivery-harness — delivery core"]
        direction TB
        route["System Review And Route<br/>(parent-only, read-only)"]
        size{{"Project Size Gate"}}

        subgraph DIRECT["Direct route (small)"]
            direct_impl["Implement directly -> local verify<br/>-> code-security review -> authorized Git actions"]
        end

        subgraph MANAGED["Managed route (large)"]
            direction TB
            plan["PLAN v6<br/>typed graph: missions / reviews / gates<br/>allowed_providers + atomic task commits"]
            newrun["new_run.py generates<br/>RUN v11 + the 12-key authorization ledger"]

            subgraph LOOP["Execution loop (per wave)"]
                direction TB
                lock["--session-id acquire-run-lock<br/>(run lock + heartbeat)"]
                obs["record-observation<br/>live-Git snapshot"]
                sel["select_ready_nodes.py<br/>deterministic frontier selection"]
                accept["accept-wave<br/>(batch base binding)"]
                adapters["resolve the available agent driver<br/>under the shared contract"]
                lease["lease-worker<br/>(worktree + lease + graph binding)"]
                workers["fresh bounded agent workers"]
                record["record-worker-result<br/>revalidate evidence + atomic RUN update"]
                review["exact-head review<br/>(reserve -> reviewer -> record)"]
                integ["record-integration<br/>(serial; unified candidate SHA)"]
                lock --> obs --> sel --> accept --> adapters --> lease --> workers --> record --> review --> integ
            end

            plan --> newrun --> LOOP
            security["code-security-review<br/>fresh sibling; all missions; exact SHA"]
            gates2["Broad final validation<br/>(E2E / regression / UI evidence matrix)"]
            LOOP --> security --> gates2
        end

        route --> size
        size -->|small| DIRECT
        size -->|large| MANAGED
    end

    subgraph DEPLOY["Deployment (git-connected platform)"]
        direction TB
        handoff["Managed: refresh docs/DEPLOYMENT.md<br/>(typed targets + secret names + console tasks)"]
        archive["Close RUN, archive coordination<br/>commit + reverify candidate"]
        push["Checkout-external request/attempt/receipt<br/>for the exact run-branch candidate"]
        directhandoff["Direct: refresh deployment record<br/>retain one fixed verified candidate"]
        directpush["Separately authorized direct<br/>candidate publication"]
        preview["Preview builds automatically<br/>(platform builds per push)"]
        merge([Separately authorized exact-SHA<br/>fast-forward to main])
        prod["Production deployment<br/>(platform builds from main)"]
        check["Post-deploy verification (read-only)<br/>check_deployment.py"]
        status["Reconcile deployment record<br/>(status + pending human actions)"]
        handoff --> archive --> push --> preview --> merge --> prod --> check --> status
        directhandoff --> directpush --> preview
    end

    subgraph ACTIVATE["product-activation — setup and release verification"]
        direction TB
        profiles["Select core + surface profiles<br/>docs/ACTIVATION.md"]
        capability["Probe connector / API / CLI<br/>Browser / Computer Use / manual"]
        actions["Exact ACT-* actions<br/>authorization + read-back"]
        ready["Per-target activation readiness<br/>verified MS-* sources"]
        profiles --> capability --> actions
        actions -->|"final release evidence"| ready
    end

    subgraph SEO["seo-growth-review — optional post-release review"]
        direction TB
        seo_sources["Production pages + verified sources<br/>Search Console / GA4 / estimates"]
        seo_review["Technical SEO + measurement integrity<br/>query-to-page opportunities"]
        seo_route["Prioritized routed follow-ups<br/>no direct mutation"]
        seo_sources --> seo_review --> seo_route
    end

    subgraph OUTCOME["Post-release outcome review"]
        outcome["docs/product/outcomes/YYYY-MM-DD-release-set.md<br/>(owner-requested, post measurement window)"]
        verdict{{"Verdict: no_change | enhancement | incident"}}
        outcome --> verdict
    end

    subgraph CROSS["Cross-cutting mechanisms (all stages)"]
        bindings["Skill Bindings<br/>(AGENTS.md slot table + SHA-256 pins)"]
        ledger["Authorization ledger<br/>12 independent action keys"]
        ver["Version gate + contract digest<br/>(compatible_old wave boundary)"]
        watch["watchdog + reconcile<br/>(interruption recovery)"]
    end

    user --> interview
    pgate -->|approved UI product and explicit UI request| intake
    pgate -->|approved headless product| HARNESS
    pgate -->|"approved scoped enhancement or maintenance; no affected design gate"| route
    linked --> route
    target --> route
    DIRECT --> directhandoff
    gates2 --> handoff
    direct_impl -.->|"parent-owned initial-build preparation"| profiles
    workers -.->|"parent-owned initial-build preparation"| profiles
    status --> profiles
    ready --> outcome
    ready -.-> seo_sources
    seo_route -.-> outcome
    verdict -.->|next enhancement request| interview
```

Product Definition Approval, UI Visual Approval, and the merge to `main` are separate human gates. Publication authorization is also separate: accepting product content never authorizes overwriting or moving files.

Product Definition and UI approval/handoff responses list every current document individually in chat, with a verified absolute Markdown link, purpose and status. Include Chinese review copies and English sources, research, direction studies, all HiFi pages, review evidence, required design-system Markdown/JSON/HTML and applicable project/operational documents. Once both packages are complete, present one combined list for whole-package review before implementation. Keep existing approvals and mark missing or later-stage outputs explicitly; a preview panel or document-index link does not replace this list.

For every deployable release, `docs/DEPLOYMENT.md` is the operator handoff. Product Definition seeds typed `Surface class` and `Public discoverability` fields; Delivery Harness joins every development/production target to those fields, its exact provider/channel, endpoint or typed native disposition, expected/deployed SHA, artifact identity, availability evidence, and checked time. Production uses canonical `<product-slug>-<surface-suffix>` with no `-prod`; development adds `-dev`. The record lists secret and variable names plus external-console tasks, never secret values.

From a fixed initial build, `product-activation` prepares authorized prerequisites before dependent features. After production deployment, it reuses existing resources and re-verifies the actual release. Capabilities, action digests and behavior evidence remain bound to each exact target, environment, SHA and artifact. Final readiness, verified measurement sources and outcome review retain their release requirements.

Activation is execution by default: inventory the real delta, continue ready authorized actions through mutation/read-back/behavior, and use the closeout checker at the end; documentation-only work requires an explicit owner request. `--require-closeout` rejects a required action left ready, configured, pending, uncertain, or stale. Only verified work or an explicit concrete blocker closes the action; either blocked state keeps the record blocked. A true no-op needs no synthetic action, but every target must have a concrete n/a disposition, while verified handoff still requires verified sources and target readiness. Generate action digests with an explicit staged `--activation` path before requesting authorization.

After activation, `seo-growth-review` can run as an independent read-only pass for a typed public hosted-web production target. Its dated report must match the Review date, deployment hostname, exact release and Activation hash, verified source roles, data cutoff, and PASS integrity checks. It audits crawl/index behavior, separates Search Console visibility from GA4 behavior, ranks evidence-labeled opportunities, and routes follow-up without changing the site or external accounts.

A saved lifecycle SEO review needs only its reviewed production target to be `ready` in Activation; other targets, such as an app still in store review, may stay pending. `check_seo_review.py` validates the Product Definition package and Deployment once, prints those findings on stdout with the other review findings, and reports a date-only Data cutoff instead of crashing. For `code-security-review`, the review packet's Contract JSON lists each PLAN `security_review.required_checks` ID with the execution key of its PASS at the reviewed head, and the result copies that list into `checks`. The reviewer returns no reason codes: a blocked result names its cause in `coverage.gaps` or `evidence`, and dispatch blockers are recorded by the parent's selector.

The loop closes at both ends. Research-first evidence gates drafting and supplies applicable baselines; the complete candidate receives post-draft reconciliation and owner decisions on evidence-based recommendations before any revision, Stack Decision Checkpoint, or Product Definition Approval. Metrics now carry baseline, target/guardrail, measurement window, source/method, and owner so the later outcome review has a real contract.

Enhancements record impact across product behavior, UI structure/style, data/integrations, architecture/stack, data trust/AI, commercial channels, and release/operations. Changed product content reopens Product Definition Approval; UI keeps its `none`/`structure`/`style`/`both` gate and refreshes only affected artifacts.

Product Definition checks changed in 0.55.0. Package and Stack Checkpoint digests now cover the raw file text, including fenced code, indented lines and HTML comments; only the approval or checkpoint marker block is removed, and CRLF reads as LF. Digests recorded by earlier releases may no longer match, so re-run finalize and re-record Product Definition Approval and the Stack Decision Checkpoint. A Mobile/Desktop stack needs a `Styling approach` layer row (for example `platform theme`). In the Enhancement Impact Record, a UI `structure` or `both` row names Wireframe Validation and Visual Approval, and a `style` row names Visual Approval; Copy Freeze, Wireframe Approval and Impeccable/H1–H9 are no longer required names. `check_product_package.py` prints `complete and owner-approved` only when both `--require-filled` and `--require-approved` ran. The Product Definition agent graph accepts only the two closed release source policies: development from the run's integration head and production from the verified `main` SHA; tags and other refs are rejected. The `--prior-outcome` digest is the SHA-256 of the prior record's raw bytes, so it matches `sha256sum` or `Get-FileHash`.

Gitignore hygiene also applies to both direct and managed work. The scope scan records whether a task changes a local-only artifact class, then derives the narrowest rules from the observed toolchain. Value-bearing environment and credential files, reproducible build output, dependency directories, caches, logs, and local platform state are ignored; source, tests, lockfiles, migrations, tracked configuration examples and schemas, and canonical product or delivery artifacts stay visible. A new environment-variable read updates the tracked example and ignore rule in the same task. Harness verifies representative paths with `git check-ignore`, `git status --ignored`, and `git ls-files`; it never reads a secret value or hides a dirty worktree, and a likely secret already tracked by Git stops the run for owner action.

Commercial products now pass two separate Product Definition decisions. The Monetization Infrastructure Gate resolves the model, pricing/offer rules, purchase surfaces, entitlement source, and merchant-of-record/tax ownership before comparing current options such as native store billing, RevenueCat, Qonversion, Adapty, Superwall, Stripe Billing, Paddle, or Lemon Squeezy; pricing never makes RevenueCat the default. The Partner Channel Gate independently resolves `none`, affiliate, referral, reseller, or hybrid. It compares link/commission tools such as Rewardful or FirstPromoter, broader partner platforms such as PartnerStack, an integrated Lemon Squeezy affiliate route, or a custom reseller service. Billing, entitlement, paywall, tax, attribution, commission/payout, and reseller operations remain separate PRD, architecture, stack, UI, mission, and test contracts.

</details>

Each assignment gets private scratch and a finite deadline. Before cleanup or retry, the parent confirms the process tree exits and inspects partial work, prior operations, and evidence gaps. A 403 or a finding that research produced no useful sources is not a launch failure; it is never permission to synthesize evidence.

## Operating reference

These groups hold the complete operating rules. Open a group to read its requirements in full.

<details>
<summary><b>Acceptance, workflow map, bilingual review and handoff checkpoints</b></summary>

Acceptance runs focused checks per atomic task, affected integration checks per mission, then the complete required matrix and one independent security review per fixed candidate. Resource-safe regression and review may overlap only when declared dependencies permit it; managed selection and required-check prerequisites remain binding. Reuse retains the original exact-SHA evidence; repairs require fresh review, and local tests never prove external state.

The workflow's template map names where every existing template is used, including optional views and historical Wireframe templates; it does not create unnecessary artifacts to use them all.

CI regression parses the complete source workflow and consumer CI template as YAML, including multiline candidate and diff-base expressions. Text assertions alone do not prove GitHub can load a workflow.

Consumer workflows keep their approved branch policy. This skills source repository is maintained for our own use: temporary work branches target main through reviewed PRs. It needs no development branch. Historical consumer runs keep their pinned contracts.

The [step-by-step workflow](docs/WORKFLOW.zh-TW.md) maps every applicable stage to its owner, existing templates and verification boundary. A section may have several isolated frontend/backend writers after shared interfaces are frozen; each executable task retains its atomic commit. Use observed host capacity, bounded packets and completion events, streaming review and serial integration. Do not remove precondition or postcondition validation as duplicate work, or claim rolling writer scheduling before it is implemented.

Product Definition drafts canonical English `PRD.md` and `architecture.md` together with complete Traditional Chinese `PRD.zh-TW.md` and `architecture.zh-TW.md` review copies. The owner reviews Chinese; implementation and approval digests use English. Accepted feedback updates both views. The [bilingual review contract](skills/product-definition-builder/references/bilingual-review.md) requires source hashes, matching IDs and semantic comparison before review and paired publication. When an existing English-only PRD or architecture is found at a task checkpoint, the agent adds a complete Chinese review copy in the same directory, preserving the English source and approvals. A PRD-only project can validate its pair without creating an architecture. Read-only tasks report the missing copy; archives are not translated automatically.

`AGENTS.md` requires local repository checks at task start, significant changes and completion, even without Harness or PLAN/RUN. Record meaningful committed and uncommitted changes in the matching Epic, including external changes labeled observed/unverified, and update `docs/DOCUMENTS.md`. Missing baselines stay explicit; unchanged checks create no duplicate entry. Read-only tasks report proposed records. No background watcher or new action authority is implied.

Before every handoff, repeat the repository checkpoint and reconcile affected live documents, the matching Epic and index, and the task record. For managed runs, compare PLAN/RUN with the generated `docs/tasks.md` view using the renderer's `--check`; RUN remains authoritative, and generated content is not hand-edited. Compare shared `AGENTS.md` rules by meaning with the observed installed project template and version, then update only stale shared instructions within existing document-write authority while preserving local rules. Authorized bootstrap proposes missing shared sections and same-heading differences; apply only after a reviewed merge plan binds the observed hashes and heading selection. Before append, recheck the opened file against reviewed bytes; require the exact original-plus-block result. Concurrent drift fails while preserving every byte. Proposed additions are not proof that contradictions are absent. Reconcile by meaning without overwriting intentional stricter local rules; the later `--check --require-resolved` gate checks placeholders, not template byte equality. If the template or semantic merge is unknown, report the gap. This is a handoff checkpoint, not a timed scan or new action grant.

Audit corrections align installed command paths, required CLI flags, the 500-line responsibility checkpoint, schema-5 Wireframe Validation and reviewer shell v3. Activation uses the exact release-surface profile; security PASS requires complete coverage. Product Definition review checks operation completeness; the schema-5 UI approval gates enforce the declared PRD-to-Wireframe/HiFi joins. Current RUNs are local-only; publication and main promotion keep separate authorization.

</details>

<details>
<summary><b>Core guarantees for recovery, approvals, design packages, isolation, evidence and release policy</b></summary>

## Core guarantees

- **Recovery preserves identity and evidence.** Launch recording separates the parent `--session-id` lock from `--worker-session-id`. Additional historical-review admission matches the retained attempt; old PASS never covers a new head. A blocked sibling without an interrupted-review reconciliation receipt prevents candidate movement. Current role-bound interrupted missions need a stopped failure receipt before reconciliation and retry. Dual-branch archives prove frozen-base ancestry while retaining their main observation; legacy pins keep their original rules. Review packets can retain a complete external diff with SHA-256 and name-status inventory. Truncated previews require full inspection, and security integration reviews always cover the full scope. New UI entry uses `/3`; retained `/2` packages keep their approval semantics.

- **Recommendations before implementation.** When owners have no stack preference, propose a product-fit default and alternatives covering frontend, hosting, backend/runtime and agent orchestration, with compatibility, cost assumptions and revisit triggers. Enhancements inspect the current UI and show affected before/after cases. Research templates and CSS references with license and stack checks; preserve native platform conventions. Explicit hero and motion requests remain traceable through delivery. Visual Approval requires typed, hash-bound normal and reduced-motion observations for every motion intent; HTML evidence proves only the review projection.
- **Small work stays small.** One bounded change uses a direct inspect, implement, verify, and review loop.
- **Large work is explicit.** PLAN v6 defines the typed graph; RUN v11 records authorization, attempts, and evidence.
- **Product definition is approved before UI design.** Research-first evidence, applicable baselines, a complete candidate, explicit recommendation choices, and any accepted delta precede the final approvals. Every release surface selects its required architecture and stack areas from one closed applicability matrix: hosted UI needs frontend, native UI needs mobile/desktop, services and agents need backend/data/interface decisions, and CLI delivery needs an explicit toolchain. Product and Stack approvals carry canonical content digests, a structured revision, a non-future decision time, and exact acceptance references for every retained open item. At a human review gate, the agent proactively links the complete actual candidate and waits for explicit approval. UI-bearing products enter `ui-design-builder` only on an explicit request. CLI and `other_nonpublic` share the canonical `Toolchain` approval area (`CLI/toolchain` is an alias), with language, toolchain, distribution mechanism, and testing layers.
- **Security starts in Product Definition.** Executable software — including static sites, clients, CLI tools, and agents — records a human-owned Security Requirements Gate. Each required row traces an existing PRD requirement and security TEST, then Harness task gates implement controls plus denial/no-side-effect negative tests before commit; the fresh exact-SHA code-security review remains final.

Security exemptions also require a documentation-only product description and Product Archetype, plus explicitly absent executable architecture surfaces. Required security TEST signals and Harness criteria use `denial: rejected (<signal>); no unauthorized side effects: unchanged (<state evidence>)`, with concrete observations for both assertions.
- **Recommendations are not implementation authority.** Product Definition presents two or three coherent technology bundles per applicable area. New accepted choices are `Approved`, existing choices remain `Selected`, and hard constraints are `Required`; `Recommended` and `Provisional` block delivery. The checkpoint's closed area set must equal the applicable resolved areas, and the approved option's layer map must equal the executable stack rows. `render_stack_option_map.py` prints a candidate map from existing rows for owner review; it cannot approve or rewrite the package. Explicit option maps are wrapped as `||...||`; legacy comma-only maps remain readable, and commas in layer names or selections require the explicit form. A frontend component foundation may be one headless React primitive layer, Base UI or Radix Primitives, plus custom components; pick one per product. Radix Themes counts as a packaged suite. HiFi draws that layer's states and focus behavior without changing the stack.
- **Full UI packages ship a complete design system.** New initial and full-redesign packages select `UI contract: ui-design/3`: three rendered direction studies by default in `docs/design/directions/<round>/`, each self-checked by the same author, owner select/mix/modify, full HiFi checked at every approved target and each intermediate web width, and a required `design-system/4` Markdown/JSON/HTML package (`Package action: compile|update|reuse`). The HTML specimen book shows every token, range, registered component variant, state, responsive size and motion copied from the approved HiFi in sandboxed plates, with replay/stop and reduced motion. Every required state, including default, has an explicit treatment row. Animation evidence follows the specimen’s winning CSS declaration and named keyframes, including importance, specificity and resolved custom properties. Unsupported animation CSS, including escaped declarations and invalid shorthands, is a finding. Retained `ui-design/2` compiles `design-system/3` only when required; its `not_required` approvals keep their meaning. A single recommendation requires the owner's explicit intake choice, human Decision owner and Decided on; its studies must match that choice. Validated `none`/`style` maintenance retains historical design artifacts; it grants no fresh pair or preview approval. Without adjacent approved web widths, record the exact `Intermediate width check: not_applicable — no adjacent approved web viewport widths`; native size-class and ordinary HiFi evidence remain required.
- **Retained design packages go directly from PRD to HiFi.** `UI contract: ui-design/2` explicitly selects the retained flow; new initial and full-redesign packages use `ui-design/3`. Product preflight validates operations, states, responsive targets and copy status; HiFi checks actual copy provenance and product-control coverage before Impeccable. Three directions are the default, followed by selection and one complete Visual Approval. Native HTML remains design evidence. Legacy schemas and pinned RUNs keep their original meanings; a missing Wireframe never selects a weaker check.
- **HiFi pages must connect through product controls.** New or revised `ui-hifi/2` references use an `index.html` manifest with hash-bound sibling HTML pages and explicit control destinations. Current `ui-output/3` observations check click and keyboard outcomes at every responsive target; missing pages, stale hashes, dead controls, wrong destinations, and undeclared navigation block approval. Each page renders exactly its assigned surfaces. Publish and retain the complete package. Schema-1 references remain inspection-only; every current Visual Approval requires HiFi schema 2. Historical output/2 and evidence/2 retain their original meaning. A frozen Git revision must contain every listed child page with the same bytes.
- **Visual quality has its own floor.** HiFi H5 (visual slop), H7 (creative distinction), and H9 (design consistency) each require 80; an overall 85 cannot average away a weak visual dimension. Reviews cite inspected screenshots and confirmed direction principles. Numeric validation does not prove beauty or human inspection.
- **Select directions from rendered representative cases.** Each direction uses the same primary/stress cases and content across the applicable platforms. Keep captures and hashes. Bounded playable motion studies show normal/reduced motion; they are selection evidence, not final motion proof or provider authorization. Only the selected direction expands into the full connected HiFi.
- **Platforms share a brand, not control defaults.** Platform rules cover each approved platform separately. iOS addresses system text styles, Dynamic Type, SF Symbols and native input/layout; Web libraries are not forced onto it. HTML remains a review projection. Native implementation proves the representative cases with platform tooling before expanding, then completes the final full matrix.
- **Workers are isolated.** Write missions use dedicated worktrees and bounded scopes. The parent validates every returned commit and diff.
- **Every graph attempt is durable; local verification defaults to the host.** New PLANs explicitly use `execution.isolation: "host"` for build, lint, and test with the project toolchain. Results retain exact SHA, command identity, cwd, exit status, logs, and source/Git guards. Host verification ends its owned child processes before the final source/Git check, including after a timeout. Host commands run fresh and serially with current user permissions; worktrees are not OS sandboxes. Optional `container` declarations retain machine-approved Docker/Podman, pinned images and all isolation checks, with no automatic host fallback. Attempts still reserve before execution and the inspector never infers process liveness from a phase. Independent workers launch in separate worktrees before the parent waits for results; host verification does not cap mission concurrency. Re-observe actual capacity instead of keeping seeded one-slot defaults.
- **Runtime bindings are explicit.** `lease-worker` derives the provider, driver, model, effort, and portable runtime axes from the selected directive, accepts `--task-thread-id` only for app tasks, accepts an existing exact target, and materializes a new exact target only from an active wildcard grant without widening authority.
- **Capability is not permission.** A runtime may be able to push or clean up, but each action still needs exact authorization.
- **Activation is read back.** Activation, Outcome, and SEO first revalidate the approved Product/Stack bytes and the full Deployment contract. External setup stays outside PLAN/RUN, binds approval to an exact action digest and typed release target, and becomes verified only after independent read-back and behavior evidence. Outcome coverage preserves the PRD method and owner plus an exact target-to-source map; measurement windows begin after each target is available. Multi-target reviews use one closed mode, bind their primary fields to the first ordered target, preserve earlier rows append-only, and derive the aggregate verdict and required follow-up.
- **SEO growth is evidence-led.** Saved lifecycle SEO reviews are limited to an exact public, discoverable hosted-web production target. Their mode-specific record fixes market, language, outcome, timezone, comparison windows, and segmentation. Per-source verification time remains separate from the review's common data-coverage boundary. Search Console visibility stays separate from GA4 on-site behavior, and every change routes to its owning workflow.
- **Evidence follows the SHA.** A new commit invalidates earlier gate and UI evidence for the old head.
- **UI evidence proves layout, not pixels.** Runs pinned to harness 0.34.0 or later record a `layout_check` on every route-breakpoint-state evidence row from a real-browser geometry scan, every UI task classifies its impact (`none`/`style`/`structure`/`both`) before acceptance, accepted parity deviations land in a cited deviation ledger, and shipped motion traces to `ui-design.md`'s Motion and Media Intent. Runs pinned to 0.35.0 or later also machine-check the `deviation_ledger` and a per-mission `ui_impact_summary`.
- **Completed managed runs fold away before promotion.** `archive_run.py` verifies C, current `main`, every coordination path, evidence, and the move list under no-follow handles, then journals a durable C→A transaction, writes the closed receipt plus immutable checkout-external anchor, and preserves concurrent user data during recovery. Archive-only A is revalidated against that anchor before any separately authorized publication. `push_archived_candidate.py` binds the exact canonical push URL, machine policy, verifier, immutable request/attempt/receipt, and detached trusted-host evidence; the local agent prepares the handoff but never executes its publication argv. Direct work keeps its fixed verified candidate and does not invent a PLAN/RUN archive.
- **Parity is captured, not remembered.** Hosted-browser surfaces use `parity_capture.py` at every route×viewport×state. Extensions, native apps, and desktop apps use platform tooling or labeled manual captures and never substitute a hosted URL. Any unsupported required group makes the result partial and non-gating. Every row binds accepted Git blobs, authority paths/hashes, baseline image/hash, capture method, trusted launcher identity, and layout result. Screenshot filenames include the full SHA-256 of the surface/route/breakpoint/state tuple, so token normalization and case-insensitive paths cannot merge distinct evidence pairs.
- **Reading the rules is mandatory.** The seeded project `AGENTS.md` requires every session to read the installed `delivery-harness` SKILL.md before managed work and the affected PRD sections before product-affecting direct work; skipping it is a blocking review finding.
- **Code security is a fresh final review.** Every code PLAN requires `code-security-review`; `not_applicable` is accepted only for narrowly scoped documentation-only work. Actual candidate paths must stay inside mission/security scope and may never include parent coordination files. Project-required security commands are graph-ordered host or container verifiers whose exact current-head execution keys are checked before review. A PASS is exact-SHA, complete, exclusion-free, and cannot reuse earlier tree-identical evidence.
- **Release sources use branch Preview before main.** New 0.63+ work uses `main-preview/1`. Ordinary work and hotfixes freeze remote main, use a temporary branch, pass exact-candidate review and isolated PR/branch Preview acceptance, then separately land on protected main and verify production. No permanent development branch is required. Managed RUNs remain local-only at C; archive A, trusted-host publication and protected-main authorization stay separate. Historical RUNs and correction lineages retain their original pins. Existing branches are never deleted by this change.

Cloudflare uses native Workers Previews with project Wrangler 4.135.0+ and `wrangler preview` when supported. Record a fixed deployment URL/ID and exact SHA. D1/KV/R2, secrets, auth and payments need explicit non-production isolation. Unsupported service-binding, Workflow, Queue, Cron or route journeys need an isolated alternative or remain blocked. Pages Preview remains an owner-selected route.

Frontend release sources use the explicit `main-preview/1` marker for candidate Preview and verified main for production. Historical dual-branch/1 and markerless candidate/1 keep their recorded semantics.

Before RUN creation, plan-only validation checks an explicit branch policy and architecture marker together. An absent RUN does not imply a legacy pin or grant execution.

</details>

<details>
<summary><b>Unified design review: HiFi reviewer, design intake and PRD refinement</b></summary>

New assembled studies use `assemble_ui_review.py --mode direction` and the closed `ui-direction-review/1` profile. `--mode hifi` remains the default and HiFi contracts do not change. The profile gives every case its own surface, platform, approved target family, and exact pixel widths. The assembler reuses the shared reviewer CSS and HiFi runtime, shows only one case's approved targets, and carries that case and target across studies.

## Unified design review

HiFi uses a neutral reviewer shell isolated from product CSS, with App, Web front and administration groups, one product canvas, platform-specific sizes/states, and a source-derived Design Tokens view. Historical Wireframe packages retain their reviewer and original checks.

Reviewer controls and panels use Shadow DOM while the product canvas stays in normal DOM. Real state controls switch state/target content; reviewer selections persist by package and platform without crossing packages.

`frontend-design` reads the PRD directly, proposes three comparable directions by default, then builds connected HiFi after owner selection. An explicit owner direction may use one study; unchanged enhancements retain their direction. Product preflight precedes authoring, and cheap HiFi completeness checks precede Impeccable and H1–H9. One Visual Approval covers copy, structure, working menus/tabs, interactions, visuals and tokens. Required Home/back/cancel, keyboard, Escape and focus return follow PRD operations.

Before direction or HiFi authoring, verify UI-stage bindings and load the complete pinned `frontend-design` in the actual writer context. Parent reads and shell assembly are not design authorship. Managed authoring requires both `ui-design-builder` and `frontend-design`.

Initial design uses the full flow. Enhancements author only affected pages and connecting flows, with preserved-page comparisons. Routine maintenance edits and verifies the current product and effective requirements without rebuilding historical HiFi. Source, installed and actually loaded skill identities stay separate. New `ui-output/3` / `ui-evidence/3` preserve real observations, time, tool, environment and candidate hashes; machine results never invent human approval. Legacy formats retain their historical meaning. See [review workflow](skills/ui-design-builder/references/review-workflow.md) and [evidence](skills/ui-design-builder/references/review-evidence.md).

UI Design Builder rules tightened in 0.55.0. Impeccable critique and audit are required before Visual Approval; their side effects still need separate authorization, and if the owner declines it the HiFi review is `blocked`. The old Wireframe Approval heading does not keep old HiFi evidence rules. A legacy Visual Approval decided on or after 2026-09-27, or with any HiFi Review or motion-effect receipt run from that date, always needs `ui-evidence/3`, reviewer shell v3 and direction/hifi Frontend Design Usage rows; committing or backdating it does not make it historical, and its Decided on date must not predate that evidence. An earlier approval keeps its `ui-evidence/2` HiFi receipts only while its Approved target equals the one committed at HEAD. Publication, the design-system compiler preflight and Harness UI and pair joins for runs that require 0.55.1 or later enforce the dated rule; only `check_ui_publication.py` also compares the target with HEAD. Schema-5 wireframe receipts use one check name derived from the architecture Release Targets (`wireframe-browser`, `-extension`, `-desktop`, `-native`, or `-mixed` for hybrids) and the wireframe's own case order, so the same receipts pass both the structure gate and Visual Approval. A Visual Approval dated before the newest HiFi, Impeccable, grading or motion receipt is rejected.

The existing design intake explicitly asks whether the owner has reference images, screenshots, websites, Figma views or products, what to learn from them and what to avoid. Text questions collect links and preferences; image attachments use the conversation's attachment support. Supplied answers are reused, and no references is a valid answer that leads to relevant research and proposals. A concise Design Brief inside `ui-design.md` maps approved UI IDs to page purposes/profiles, then links typography/density/headline constraints, motion intent, inspected references, visual constraints and avoid rules to existing REF/RP, Style Integration and motion records. Reference roles and avoid examples are optional; their reasons must be concrete. Selected brief decisions carry through direction, HiFi, H1–H9 and later compiler/implementation authority. It adds no separate file or approval gate and does not require historical briefs to be backfilled. See [intake](skills/ui-design-builder/references/ui-design-intake.md).

The PRD is refined throughout delivery. Before first-delivery approval, UI and technical perspectives review the same candidate for complete user journeys, cross-feature dependencies, data, permissions, failure recovery and operational readiness. Findings identify required coverage, explicitly deferred scope and owner decisions. Later design, implementation, tests and release observations feed evidence and stable IDs back through the existing product flow. Keep one current PRD and its Chinese review copy; do not silently expand scope, weaken acceptance or rewrite frozen approvals. These checks use existing roles and checkpoints, not an extra design phase or approval gate. See [PRD refinement](skills/product-definition-builder/references/prd-refinement.md).

</details>

<details>
<summary><b>Delivery model: Epics, acceptance and eval contracts, managed waves and repair routes</b></summary>

Source authority is separate from availability evidence. Every target's provenance ref comes from its architecture source policy. Strict checks keep that ref, the observed source SHA, expected SHA, deployed SHA, and artifact hash joined. Target-review subsets remain explicit; Activation still inventories every active target, while a concrete n/a can replace an unavailable target only by owner rule.

Strict Outcome Review requires stack-decisions.md and validates the Product Definition package once. It forwards that validated context to Activation, requires provenance on Deployment, and checks only the review's production-target subset. A saved SEO review forwards the same source context and checks only its reviewed target.

## Delivery model

Acceptance rejects embedded identity placeholders and requires checkout-relative evidence paths, so retained results remain portable between checkouts.

Document checks now report each changed source, affected artifacts and required rechecks. The parent owns the global inventory; a child names its complete scope and never replaces the parent snapshot. A parent reviews the semantic delta; hashes and routing hints never grant approval. Existing `document-sync/1` snapshots remain readable. Unknown loaded identity stays unknown.
The child checks source hashes and reports its own loaded/read evidence.

Repository governance uses a short entry with mandatory trigger routes. Complete task, development, product-contract, source-maintenance, and managed-delivery rules live in `skills/delivery-harness/references/governance/`; consumer paths resolve from the observed installed Harness root.

Complete enhancements use one indexed Epic in `docs/epics/`, referencing the current PRD instead of duplicating it. Small fixes append to the relevant Epic and may link detailed direct-task evidence. The goal, write scope, design source, dependencies and checks are derived into that record or existing PLAN/RUN; no extra coordination specification is required.

Choose the record before implementation: a new accepted outcome gets an Epic; same-outcome fixes append to its Change Log; an isolated small fix gets a bounded Epic entry with linked direct-task evidence. Log the reason, affected scope, commit, tests and remaining work without rewriting closed history. UI enhancements are incremental: add or patch only named HiFi pages and necessary entry/return controls. Preserve unrelated product layout, content, style and IDs, and reuse the approved direction. List shared-component consumers before changing them. Complete package coverage and full regression are not instructions to redraw every screen.

Project AGENTS keeps entry, reading, ownership, routing, synchronization, authorization and completion rules. Conditional commerce, activation and managed-run details live in a required reference. The consumer AGENTS template requires KISS, first-principles reasoning, responsibility-based module splitting and no speculative compatibility code. New consumer code/test modules have a 500-physical-line hard cap; this does not impose a cap or a refactor on Harness source.

New or changed documentation uses core [ASD-STE100 Issue 9](https://www.asd-ste100.org/about_STE.html) writing rules: active voice, one idea per sentence and consistent terms. Procedures use one instruction per step, with necessary conditions first. English procedural sentences have at most 20 words; descriptive sentences have at most 25. Code and literal strings are outside prose counts. Other languages use natural phrasing and consistent terms without English word limits. Preserve technical meaning, requirement strength, approvals and history. This STE-informed guideline uses existing document review; it adds no delivery gate or full-conformity claim.

HiFi review starts on the primary product page. The sidebar opens Overview, every page and design specifications. Product interactions, reviewer navigation and source-derived tokens need separate evidence. Historical bundles remain readable.

HiFi keeps one product canvas visible, sets actual review widths and retains applicable inputs and state. Product controls and state variants are verified in the browser; token specimens stay bound to their source pages.

The HiFi validator checks `aria-current="page"` on each page's own sidebar link, including nested links. A marker on a parent or another link cannot substitute for it.

Reviewer evidence also covers unknown links, browser Back from each review view, and final restoration of the primary product page at every target.

Full-stack delivery follows complete user flows through UI, API, permissions, persistence and feedback. Use agent-browser for Web exploration and retain important journeys as local/CI tests. Actual login, denied access, retry and side effects need evidence. Deployment checks include migrations, health, monitoring, cost alerts and recovery; delivery, release, activation and product results are reported separately. SEO applies only to relevant public surfaces.

Upgrade to 0.50.0 with the canonical installer after active skill-using sessions reach a safe boundary. Keep its backup and start a fresh session; installed bytes do not update a loaded worker. Review the document-sync impact report, preserve local AGENTS rules and historical evidence, and patch only affected live sources. Existing document-sync/1 and ui-hifi/2 files remain inspectable. A fresh HiFi approval adds the reviewer shell and page-bound ui-output/2 reviewer observations; regenerate only affected evidence, not old approvals. Small fixes reuse a matching Epic without PLAN/RUN; create a bounded Epic only when none fits. Re-run the affected owner gates plus mandatory final verification. For 0.49.0, inspect design freshness before implementation and supply region-bound motionSpec in strict schema-5 authoring checks; preserve historical approvals. For 0.50.0, retain existing product layouts and approved artifacts. New wireframes open with annotations. Add a supported data-token-preview property and a matching source consumer for each HiFi token, then regenerate affected reviewer observations; preserve historical approvals.

Every skill invocation starts with the shared [document-sync contract](skills/delivery-harness/references/document-sync-contract.md): review changed live instructions, skill/runtime identity and product documents, without rewriting historical approvals or runs. The current PRD stays the next enhancement's baseline; superseded PRDs remain linked references. [Bounded enhancement](skills/delivery-harness/references/bounded-enhancement.md) reuses one accepted scope for repairs, same-scope module replacement and retesting instead of repeated approval prompts. Stop at the repair budget and hand unresolved requirements to the next round; ending a round is not a delivery PASS or permission to publish.

The [Generate, Verify, Correct guide](skills/delivery-harness/references/gen-verify-correct.md) maps each stage to its author, verifier, and corrector. It starts with the shortest meaningful focused check, broadens at mission, feature, platform, and integration scope, and stops on PASS. Read-only findings return to the owning flow with expected and actual evidence; exact-candidate proof and existing budgets stay binding.

The [delivery-acceptance contract](skills/delivery-harness/references/delivery-acceptance-contract.md) joins required PRD TEST IDs to a frozen scenario/platform matrix and exact-version evidence. Prepare isolated synthetic accounts and owned test data only under the declared test-environment authority. Mock login proves mocked behavior, not real authentication; Web, native iOS and agent-tool outcomes need their own evidence. No production login bypass, secret-bearing fixture, skipped required test, stale build or deferred blocker can count as PASS. The checkers validate retained evidence and coverage, not whether a human attestation or external observation is truthful.

The [eval policy](skills/product-definition-builder/references/eval-policy-contract.md) freezes rubric, population, repeats, pass rate, slices, critical rules and judge inputs in the approved PRD. Its required `json` fence keeps every field visible during review. Prefix line endings and blank lines must follow Markdown rules. Approved input paths stay fixed through staging/publication; retain superseded versions. New-package approval and publication use `--repo-root <root> --eval-policy eval-policy/1` to verify approved input bytes; ordinary products give a reasoned exemption. Required functional TESTs still all pass. Legacy packages without the marker keep their checks; a present marker always validates.

New authoring with an owner-selected whole-platform order adds `--platform-delivery platform-delivery/1`. The checker reads the active architecture sequence, exact release inventory, shared API/interface ARCH rows, human decision, and Required-Yes PRD tests; only approved status is executable. Draft, duplicate, hidden, malformed, omitted, or shared-label bypass cases fail. Absent legacy sections stay readable.

Harness joins that contract to PLAN v6. Architecture order defines stage sequence. Explicit UI owners map once by release surface, shared ARCH work starts first, and pass-only dependencies reach each completion mission and next platform. A single-mission pre-integration runtime review cannot carry that path. Fresh completion integration and final gates cover platform TESTs; retained integration PASS is historical handoff only. Unmarked plans stay legacy.

In a marked flow, every planned `PRD-*` must trace names fresh acceptance gates. Their TEST IDs come from canonical Required-Yes PRD obligations and may include extra required regressions; unmarked legacy plans stay optional.

The [eval acceptance contract](skills/delivery-harness/references/eval-acceptance-contract.md) derives its execution contract from that policy and recomputes every planned trial. Quality failures remain in the denominator; prohibited or critical failures override the rate. Two full reports retain output, judge/tool observations, identity, timing and usage; the handoff report repeats the run from a clean checkout.

`check_eval_acceptance.py` joins those two reports to the existing delivery register at clean H2, verifies frozen hashes and H1 equivalence, then precedes delivery acceptance. Frozen contracts, approved inputs and delivered artifacts must already match H1 content, type and Git mode, even when registered as evidence. The delivered [eval runbook](skills/delivery-harness/assets/templates/EVAL_RUNBOOK.template.md) covers setup, full/quick commands, limits, failed-case replay and owned-fixture cleanup. Checkers execute no runner commands; review still verifies provenance.

For RUN pins >=0.60.0, readiness requires explicit eval applicability and, when required, frozen eval/delivery sources plus always-run checker gates in dependency order: broad final checks → eval acceptance → delivery acceptance → closeout. Wrong hashes, substituted commands or disconnected gates fail. Older pins without the marker retain their contract; a present marker opts in.
Both acceptance checkers use absolute installed paths, the observed absolute
Python executable and explicit host execution,
so an image cannot replace the checker at the same path.
An unsafe or unreadable PRD authority is a validation gap, including on older
pins; it cannot establish that a policy is absent.
Policy presence and absence both require the read bytes to match the frozen
hash and any declared Git revision before parsing.

The Harness is built around explicit boundaries:

1. Inspect the current project and identify the required work.
2. Freeze the relevant contracts, sources, scope, and verification steps.
3. Plan dependencies before starting implementation when the task is large enough to need it.
4. Use parallel workers only when at least two safe write missions are actually selected, the work is independent and isolated, and every action is explicitly authorized; managed-sequential still proves its isolated writer, scope/head, and review gates.
5. Verify task results and integrations, run a fresh unified code-security review, then verify UI journeys where relevant and the final diff. A single mission has no invented cross-mission batch gate.
6. Close the Harness 0.38+ RUN local-only at C. Archive and commit exact A, then use a new action-time instruction plus checkout-external request/attempt/receipt for any run-branch publication. Verify A before separately promoting it to `main` and verifying production.

For plan-backed work, it records task scope, dependencies, worker ownership, verification commands, and action-specific authorization. Harness 0.38+ keeps RUN push false. The post-archive protocol derives C and the branch from the archive, verifies exact C→A relocation and remote pre-state, binds an exact canonical URL plus observed trust policy/verifier, prepares a URL-only no-force handoff, and leaves publication to a trusted host; recovery verifies detached execution evidence and reads back A. Legacy pinned runs keep their older path only for recovery.

Before a wave is accepted, the Harness rechecks the observed clean product tree on the non-default integration branch, binds the batch to that exact head, reruns the selector, and accepts only its complete current frontier. The clean-tree gate excludes only the exact tracked RUN file that transitions necessarily update; every other change still blocks. A linked integration checkout is recorded as the parent while Git's clean primary checkout remains a recognized sibling. The durable run lock owns dispatch; a short operating-system lock serializes each RUN read/validate/write transaction. Frozen PRD, complete approved HiFi, and design-system sources are byte-hash-bound in both standalone validation and the transition write path. Every frozen PRD is parsed even when PLAN claims zero UI surfaces. Every structured PRD surface owns one literal route; a UI-bearing localized PRD keeps exactly one language-neutral boundary pair and one `route` and `states` anchor per entry; IDs, routes, and states agree exactly across artifacts. The design-system pair keeps separate Markdown and JSON source rows, its generated contract and compiler namespaces must agree, and every PLAN `DS-*` trace resolves through the same globally unique JSON registry. product-definition-builder batches every applicable closed decision to the question tool's actual per-call capacity; it has no Codex-specific call target and drops no decision to fit a host count.

Rules added in 0.55.0 apply only to runs that require Harness 0.55.0 or later; older runs keep the rules they were recorded under. Cleanup lifecycle nodes (`archive_worker_tasks`, `remove_worktrees`, `delete_branches`) need an exact PLAN target even under a run-wide `*` grant: PLAN validation rejects a node without one, the selector defers it as `action_not_authorized`, and `delete_branches` never covers `main`, `development` or the observed default branch. A subagent reviewer gets an exact `worker:<id>` `spawn_subagents` receipt, like a mission worker. At every RUN-v11 version, mission launches and `app_threads` reviewers need exact `mission_ids` in their launch grants: the selector defers a `*` mission scope as `action_not_authorized`, and `lease-worker` refuses it. RUN-v11 `integration.coordination_paths` may list only run coordination files (`docs/tasks.md`, `docs/DOCUMENTS.md`, PLAN/RUN/DECISIONS/REFINEMENT_BACKLOG/tasks under `docs/goal/`, and `docs/epics/*.md`); product and frozen design sources are rejected. This check and the protected `delete_branches` grant check also apply when `required_harness_version` is null or malformed; only a pin below 0.55.0 skips them. Closeout accepts dormant edges and unused repair nodes on routes the run never took; everything on the taken path must still finish. `record-integration` refuses a new head when a gate or integration review it would re-arm has no attempt budget left. Incoming routes are OR and dependencies are AND, so fan-in from several reviewers uses one gate per review joined by dependency edges. The PLAN and RUNBOOK templates include the delivery-acceptance entries a delivery PLAN adds: source `SRC-004`, the `delivery-acceptance` final gate between `final-check` and `final-closeout`, node `N-ACCEPTANCE-GATE` and edges `E-FINAL-ACCEPTANCE` and `E-ACCEPTANCE-CLOSEOUT`; legacy pins without an eval marker do not mandate them; applicable eval adoption enforces these joins. When a PLAN declares that gate, worker-result validation refuses a worker change to the register or evidence paths in every workspace mode, shared checkout included. The scripts never dispatch cross-provider runtimes; `invoke_external_runtime` stays for schema compatibility and for processes the parent starts itself. RUN transitions, `archive_run.py --apply` and `check_design_system_pair.py --write` keep their atomic exchange commit and now also run on macOS (`renameat2` `RENAME_EXCHANGE` on Linux, `renameatx_np` `RENAME_SWAP` on macOS).

```mermaid
flowchart TB
  Intake["Intake: request, repo, instructions"] --> Size{"small or large?"}
  Size -->|small| Direct["Direct parent work<br/>no PLAN/RUN, no scheduler"]
  Size -->|large| Plan["PLAN v6 + RUN v11<br/>frozen contracts, authorization ledger"]
  Plan --> Observe["Record observed git + batch_base_sha<br/>(the selector returns an empty frontier without it)"]
  Observe --> Frontier["Ready frontier<br/>dependencies, scope/resource conflicts, permission gates<br/>bounded by observed slots x isolation x conflicts"]
  Frontier --> Host["One general capability contract<br/>maps observed native tools to app_threads, subagents or sequential_parent"]
  Host --> Work["Isolated mission worktree<br/>attempt + lease, worker tests + commits"]
  Work --> Review["Exact-head read-only review<br/>required before integration"]
  Review -->|pass| Integrate["Serial integration into the resolved branch"]
  Review -->|fix_required| Work
  Integrate --> Security["Fresh unified code-security review<br/>all missions; exact integration SHA"]
  Security -->|pass| Gates["Applicable integration, E2E and UI evidence gates"]
  Security -->|fix_required| Repair["Bounded repair route"]
  Gates -->|fix_required| Repair
  Repair --> Rereview["Re-review on the new head"]
  Rereview --> Security
  Gates -->|pass| Local["Local verification complete"]
  Direct --> Local
  Local --> ArchiveCandidate["Managed: archive C and commit A<br/>Direct: keep fixed commit"]
  ArchiveCandidate --> Remote{"exact candidate publication authorized?"}
  Remote -->|no| Done["Stop with verified local evidence"]
  Remote -->|yes| Push["External request/attempt/receipt<br/>publish exact candidate branch"]
  Push --> Candidate["Verify exact candidate<br/>local + isolated preview gates"]
  Candidate --> Main["Separate exact-SHA authorization<br/>fast-forward to main"]
  Main --> Prod["Production read-back<br/>and smoke"]
```

</details>

<details>
<summary><b>General runtime adapter: host capabilities, contract adoption and host handoff</b></summary>

Required reviewer browser capability must match the reviewer's binding. A native reviewer proves the host provider and driver. An external bridge additionally proves the model provider and reserved probe session. Host-specific models stay in host policy; shared skills retain configured roles and authorized fallbacks. Resolve the frontend model by design or implementation stage from effective host policy. Pass its exact effort explicitly. Keep requested settings separate from runtime observations.

## General runtime adapter

Resume keeps the same RUN and completed missions when an authorized repair advances the candidate. Historical verifier receipts retain their original SHA and attempt; current PASS results still require the current exact SHA. Candidate reconciliation re-arms stale gates within their remaining attempt budgets and requires fresh integration and security reviews. It does not authorize repairs, reset budgets or reopen a completed RUN. Resume checks the parent and currently bound workspaces; unrelated linked worktrees do not block it. Changed-file paths such as `[slug]` are literal paths, separate from write-scope patterns.

One capability contract in `delivery-harness/references/runtime-adapters.md` serves every host. The agent reads the current native tool descriptions, observes capabilities and maps actual calls to `app_threads`, `subagents` or `sequential_parent`. There are no provider-specific adapter sections, fixed model defaults or bundled native workflow scripts.

Hosts that expose skills as lazy filesystem references may not know which seven-skill bundle was loaded at session start. At an owner-authorized quiet boundary, RUN-v11 can instead record an `adopted` receipt after the parent supplies the reviewed digest, owner source and reading evidence; the transition checks the executing Harness version and refuses to record when a fresh installed digest differs. The historical loaded digest stays null. Runtime-worker selection rechecks the live digest once, drift blocks dispatch, and each fresh worker or reviewer must independently recompute, read and report the fixed contract. Owner and reading evidence are attestations, not cryptographic proof of model ingestion. From 0.55.1, under an adopted contract, each worker and reviewer returns `contract_adoption_check` (`digest`, `matched`, `reading_evidence`). The worker-result and review recording transitions reject a passing worker result or non-blocked review whose check is missing, names a different digest or has `matched` other than `true`. `record-review-attempt` takes it with `--contract-adoption-check`, as the bare object or the wrapped reply; a security reviewer returns it beside the security result, never inside it. A blocked review may report a mismatch, which the attempt log keeps as `contract_adoption_mismatch:<digest>`. The check is a child attestation; the live-bundle comparison happens at dispatch.

Provider identity controls only explicit PLAN eligibility. Available drivers are ordered from observed suitability; a host name proves no capability. Delegated drivers require evidence for task creation/result delivery and any managed workspace. Unknown capability cannot dispatch. Null model and effort preserve installed defaults and role/fallback routing; unsupported explicit choices block without substitution.

The parent keeps all authorization, PLAN/RUN, leases, isolated writes, exact-SHA result checks and serial integration. Reviewers start fresh and prove required tools inside their own session. Native completion, retries and caches never replace those gates. Explicitly requested independent app tasks cannot silently become direct subagents.

Product Definition uses a bounded read-only analysis graph only when authorized. `product_agent_graph.cjs` validates frozen inputs and produces packets; it launches no agents. The parent dispatches the assigned roles and retains the existing decision and publication gates. If the required read-only boundary cannot be enforced, block the affected assignment. Capacity of one serializes distinct delegates; it does not substitute parent work.

Managed role-bound results use [parent-retained execution receipts](skills/delivery-harness/references/agent-execution-receipts.md): exact host session, retained source bytes and accepted payload must agree. Explicit failed-start receipts allow configured availability recovery without inventing a successful launch. These hashes bind evidence; they do not authenticate an untrusted parent adapter.

The former native workflow driver, launch templates and `workflow_runs` compatibility path are removed. Historical user files remain unchanged. Unfinished work with those bindings needs explicit replanning and fresh capability/authorization evidence; do not silently migrate it.

The runtime performance path removes repeated work without moving a gate. `docs_weight.py` reads a resolved baseline's blobs in one `cat-file --batch`; verifier results expose read-only setup, guard, snapshot, command, and postcheck timings; review packets remove only duplicated diff material, and a new launch checks the complete parent-visible UTF-8 message against an explicit byte budget before writes; same-batch immutable archive bytes are reused while each verifier gets its own checked extraction; verifier slots refill with conflict-free work instead of waiting for a wave; and only a deterministic opted-in PASS from the same runner may reuse a container result after fresh guard and runtime/image trust checks. No container result enters a durable cache. New reuse must include its origin in the current parent-observed batch; RUN history alone cannot authorize it.

Workers and reviewers never delegate. The parent keeps one writer per isolated worktree, integrates serially, and dispatches fresh reviewers for exact-head review. Read-only and write scopes stay separate; profile labels never prove permission-level tool removal. A PLAN host mismatch defers with `runtime_unavailable` and never launches another runtime.

One run has one active host. A same-repository handoff is allowed only after Host A closes its wave and `RUN.active_wave.status` is neither `active` nor `proposed`; the `active_wave` object remains in RUN, so its absence is not a handoff signal. Host B preserves PLAN/RUN and graph state, re-probes its runtime, and reviews the current exact SHA before selecting the next wave. A repair routes back to Host A and invalidates the old review; cross-machine handoff is unsupported until a future schema adds portable repository/state identity.

</details>

<details>
<summary><b>Native execution on the current host</b></summary>

## Native execution

Choose native calls from the current session, not a runtime name. Use independent app tasks only when their task/worktree/result contract is observed and authorized; use fresh sibling agents when their launch and terminal-result contract is observed; otherwise perform eligible work sequentially in the parent. An independent review still needs a fresh reviewer and blocks when none is available.

Preserve requested topology, installed roles, model choices and effective repository instructions. Resolve deferred tools, bind actual identities, launch selected siblings before waiting and prefer terminal events or cursor waits. Reconcile ambiguous creation before retrying; never create duplicate tasks automatically.

</details>

## Repository layout

```text
skills/                                              Canonical skill sources
skills/delivery-harness/references/option-library/   Optional cross-domain reference catalog
assets/                                              README covers
.github/workflows/harness-ci.yml                     Contract, unit, and E2E checks
install.sh / install.ps1                             One-command installers into ~/.agents/skills/
```

## Maintain the skills

Edit only the canonical sources in `skills/`, then run the core verification suite:

```bash
python -m pip install -r skills/delivery-harness/requirements-test.txt
python skills/delivery-harness/scripts/check_skill_spec.py
python -m pyflakes skills/delivery-harness/scripts skills/product-definition-builder/scripts skills/ui-design-builder/scripts skills/design-system-compiler/scripts skills/product-activation/scripts skills/seo-growth-review/scripts
python skills/delivery-harness/scripts/docs_weight.py
python -m unittest discover -s skills/delivery-harness/scripts/tests -v
python -m unittest discover -s skills/product-definition-builder/scripts/tests -v
python -m unittest discover -s skills/ui-design-builder/scripts/tests -v
python -m unittest discover -s skills/design-system-compiler/scripts/tests -v
python -m unittest discover -s skills/product-activation/scripts/tests -v
python -m unittest discover -s skills/seo-growth-review/scripts/tests -v
git diff --check
```

CI also runs the end-to-end spine check. In a POSIX shell use `HARNESS_GOLDEN_PATH=1 python -m unittest discover -s skills/delivery-harness/scripts/tests -p "test_golden_path.py" -v`. In PowerShell use `$env:HARNESS_GOLDEN_PATH='1'; python -m unittest discover -s skills/delivery-harness/scripts/tests -p "test_golden_path.py" -v; Remove-Item Env:HARNESS_GOLDEN_PATH`. It walks the real CLI spine (`new_run.py` → frozen joins including the sibling skill's full wireframe checker → `validate_result.py --repo-root`) over one synthetic product package. On macOS, first run `export TMPDIR="$(cd "$TMPDIR" && pwd -P)/"` so test repositories avoid the `/var` link, and keep `/usr/bin` ahead of Homebrew on `PATH` so Harness finds a root-owned Git.

<details>
<summary><b>Verification and measured execution: CI, browser suite, timing and acceptance evidence</b></summary>

`check_ui_diagnostic_wave.py` joins browser, critique, audit, grading, PRD, manifest, and subject identities. Every request and role must cover the frozen manifest’s complete surface, non-n/a state and per-surface target matrix. Fully observed FAIL rows remain complete and repair-eligible under existing authority, while strict final approval still fails. Missing, blocked, partial, stale, or out-of-scope evidence blocks handoff; a partial report never gains repair approval. Direction `--overwrite` rejects hardlinks after comparing destinations with author sources and the manifest, preserving inputs. Outcome and SEO checkers carry the required Product/Stack context into strict Activation checks.

## Verification and measured execution

CI installs the pinned Node/Playwright packages and Chromium before the required reviewer browser suite. Missing browser prerequisites fail that suite. For the same local check, run `npm ci` and `npx playwright install chromium`, set `PDH_REQUIRE_BROWSER_TESTS=1` and `PLAYWRIGHT_MODULE` to this checkout's `node_modules/playwright`, then run the UI suite. Ordinary local checks may still skip unavailable browsers.

Source CI verifies a feature branch once through its pull request. Pushes to `main`, merge-queue candidates, and manual releases run separately. Every suite job checks out and verifies one full candidate SHA; a manual release names that SHA plus a full ancestor `base_sha` and is grouped by the candidate, so a later branch push cannot cancel it. The resolver fails an unresolved or unrelated base and uses the verified merge base for PR and merge-group checks, so base-only changes made after the fork are excluded. For a missing or all-zero push base, it compares the candidate tree with Git's derived empty tree instead of an empty self-diff. The seeded consumer template uses equivalent inline Git checks and does not require a skills checkout. The final `validate` job requires every dependency to be `success`, including matrix shards.

The Harness suite runs in four deterministic shards per POSIX platform; Windows runs its explicit native files in four shards. `ci-test-timings.json` records a Windows scheduling sample, not passing-suite or release evidence. Reusing those weights to split macOS and Linux is a scheduling choice. An unmeasured discovered file is scheduled at the largest measured weight only with `--allow-unmeasured`, and is reported as a fallback. These observations do not establish a hosted speedup.

Required browser mode launches Playwright's bundled Chromium directly. A timed-out HiFi scenario reports its last completed phase. Browser operations keep their own time limits, and every product assertion remains active.

`design_workflow.py` includes canonical goal PLAN/RUN paths and reports file presence separately from live execution. Maintenance needs UI impact `none` or `style`; structural or unknown impacts require the affected design checks. The shared schema-5 lifecycle test uses real compiler, Harness, Activation and SEO checks. The UI checker loads its own dependencies before Harness removes its temporary import path, and SEO forwards the stack and repository context to Activation.

Gate checks changed in 0.55.0. A Deployment Environment Status row with a status or Checked value needs a URL, an RFC3339 Checked time with a timezone (a bare date fails), full SHAs, and Expected equal to Deployed for PASS. `check_ui_contract.py` lets only a bare `:root` rule (attribute selectors allowed) and an exact `@media (prefers-reduced-motion: reduce)` block hold raw values; `--token-source` or `--primitive-source` prints `NOT CONTRACT-CLEAN` and exits 1. Verifier PASS is exit code 0 alone; `pass_signal` is a label written `exit 0`. There is no disk verifier cache, and a request's `cache_root` is ignored. `check_delivery_acceptance.py` reads the register and evidence from the working tree. From 0.55.1 it needs `--candidate-sha <sha>` or `--candidate-from-head`; in a Git checkout the register's `candidate_sha` must be HEAD or an ancestor of it, and later commits may change only the register, the evidence files it lists and run coordination files. Run the scenarios at candidate H1, commit only the register and its evidence to get H2, then run the reviews and every final gate at H2 from a clean checkout. In a managed run, H1 is the last mission's merged head, and `record-integration --integrated-sha H2` runs before the unified reviews; the register paths go in that mission's `write_scope` and the security review scope, not in coordination paths. Rerunning acceptance after H2 needs a PLAN revision.

Successful mutating Harness transitions record their measured preparation phase. `inspect_harness_run.py` summarizes those observations separately from verifier timings. Final validation, persistence and later output work are outside the preparation interval. Unknown run time, critical path, waits and model usage remain unknown; a synthetic CLI benchmark is not a model or full-delivery speed claim.

Document sync ignores bare old names only in explicit retirement catalogs. Actionable references remain visible, as does an unknown loaded skill identity. Reuse a reading only in the same session, with matching current file bytes, the full prior content still available and the same applicable rule; rerun invocation checks. No persistent reading cache or approval database is introduced.

Chinese review checks now detect missing heading-level counts, table shapes/rows and numeric literals as well as stale source hashes and trace IDs. Translated labels may differ. The checker does not prove meaning or section order; the required complete semantic comparison remains a human responsibility.

### Acceptance evidence in Git checkouts

When `--repo-root` is the Git checkout root, the delivery-acceptance gate compares the register, every listed evidence file and candidate tree against one fixed `HEAD` SHA; it fails unless HEAD still names that SHA when the check finishes. Submodule changes cannot be hidden by Git diff settings. This root requirement also applies to the H1/H2 check above. Ignored, untracked and edited evidence fails even when its recorded hash matches the working copy. Add and commit `-text -filter` attributes for the register and evidence paths before candidate H1, so Windows line endings or Git filters cannot change their committed bytes. After running at H1, commit only the register and evidence as H2, then run the final gate.

</details>

## Keeping the READMEs current

The READMEs are documentation-of-record: every change that adds or alters a skill, rule, table, diagram, or documented flow updates the README's descriptive sections in the same change, in all four languages. The version badge and version-history entries are the release-time part and follow Releasing below.

## Releasing

Source maintenance uses focused checks per atomic task, followed by the full required matrix on a fixed release candidate. Reuse compatible installed test dependencies and cite unchanged exact-SHA deterministic results with their origin; never cache PASS or reuse stale security, browser, live-state or migration evidence. Consumer product interviews, UI approvals and Activation execution are not source-repository release steps. After a verified formal release, update local skills once only when the bundle digest changed, using the official installer at a quiescent boundary with backup and verification. Feature/development pushes do not replace the installed release; restart the relevant host only after successful installation when needed.

CI runs Linux, macOS and Windows jobs against one exact candidate SHA. Aggregate regressions execute the public CLI with successful, failed, skipped, cancelled and missing job results. A failed or zero-coverage shard fails, and the stable `validate` aggregate also fails any skipped or cancelled job. Feature branches verify once by pull request; `main`, merge queue and exact-SHA release runs stay separate. Browser tests run on Linux, while macOS retains its non-browser UI suite. Windows keeps native Harness, installer and Design System checks. Test fixtures resolve temporary paths before binding executable or repository identities, including Windows 8.3 aliases. On macOS, sandboxed container verifiers and browser parity capture fail closed, because macOS cannot execute a bound file descriptor. Trusted-host signature verification runs there only with the SIP-protected `/usr/bin/ssh-keygen`.

Byte-bound HiFi examples retain LF line endings across checkouts. Wireframe Node tests read multiline scripts from stdin so Windows launchers cannot silently truncate assertions.

Every flow that lands on `main` is one release, and the version bump rides in the same change — patch by default, minor for a breaking skill-bundle change. Update all of these together:

1. The `version` field in `package.json` and the copied-skill version in `skills/delivery-harness/VERSION`.
2. The version badge and the version-history entry in all four READMEs (`README.md`, `README.zh-TW.md`, `README.zh-CN.md`, `README.es.md`).
3. The RUNBOOK `required_harness_version` default in `skills/delivery-harness/assets/templates/MISSION_RUNBOOK.template.md`.
4. No test literals: `skills/delivery-harness/scripts/tests/test_skill_contract.py` reads `VERSION` and fails when any surface above differs from it.

Then run the full verification above, review the entire diff, and land this source candidate through a reviewed PR directly to `main`. Consumer promotions still follow `branch-promotion-contract.md`. Use a PR when repository protection requires it. If the provider creates a new main SHA, require tree equality with the verified candidate and immediately rerun the full suite plus security review on that exact main SHA before tagging or claiming release completion. After landing, tag the release commit on `main` with the matching `v<version>` tag (for example `v0.30.0`); the tag is part of the release, not an optional extra. Every released version has its tag — `git tag` and `package.json` must tell the same story.

## Security and data safety

- Keep GitHub tokens and other credentials out of this repository.
- Do not delete old installed skill copies until the new ones are confirmed to load correctly.
- The orchestration skill requires explicit authorization for every state-changing Git or lifecycle action.
- `code-security-review` is read-only by default. It does not install scanners, enable network access, remediate code, or probe a live target without separate explicit authorization.

## License

This repository is licensed under the MIT License — see [LICENSE](LICENSE).

## Version history

Update this section with each release, as part of the version bump and tag described in Releasing above.

- **0.65.2** — Publish the complete four-language delivery flowchart. Mark PRD self-review, foundation timing, MultiAgent handoffs, existing review counts and parallel GTM inputs. Record Instagram and Threads as the current owner context, evaluate Facebook Pages and keep X optional. Preserve 85/80 and existing review budgets.

- **0.65.1** — Clarify one complete PRD package author review and affected-scope rechecks before approval. Order core-journey proof and applicable load, cost, migration and recovery evidence within existing engineering tasks. Add X channel selection, content guidance and draft-to-measurement handoffs to the optional GTM skills. Explain roles, foundation timing and review limits in all four READMEs. Reuse existing records and review budgets; no new schema or review wave.

- **0.65.0** — Require HiFi overall 85 and every H1-H9 dimension 80, with mandatory Impeccable and bounded repair review. Move build access, repository-protection readback, AEO/search, deployment, analytics, feedback, errors and alerts into existing startup stages. Explain parent-owned MultiAgent collaboration. Add guarded runtime observations, advisory compiler-source diagnostics and optional GTM strategy/content handoffs. Current HiFi acceptance changes; historical approvals and evidence retain their meaning.

- **0.64.0** — Match native reviewer browser identity to the host while keeping bridge checks. Assemble direction studies in the shared reviewer with per-case targets and widths. Join complete diagnostic waves to PRD, manifest, and evidence identities. Require release source provenance in strict Activation, SEO, and Outcome handoffs, including main-preview/1 packages. Write CLI output as UTF-8 so Chinese findings no longer crash on Windows. Clarify frontend-only authoring, version-3 navigation, worker recovery, measured widths, and honest partial research.

- **0.63.1** — Add optional Void full-stack SDK/CLI guidance. Preserve owner-approved stacks, isolated deployment resources, migration recovery and exact-version evidence.

- **0.63.0** — Use main-based delivery with exact-candidate PR/branch Preview acceptance. Add current Cloudflare Workers Previews and preserve historical RUN pins.

- **0.62.3** — Bound complete dispatch messages before durable writes. Load required stage rules through smaller skill and governance entries. Keep parent inventories and scoped child checks separate. Repair owner assertions and archive fixture cleanup.

- **0.62.2** — Put purpose, installation and navigation first in all four READMEs. Refresh the three generated covers. Keep detailed contracts and history in expandable sections. Correct the Spanish generic-host prompt and installation command order.

<details>
<summary><b>Release notes from 0.62.1 back to 0.2.0</b></summary>

- **0.62.1** — Require an integrated-mission dependency path for platform handoffs and feature gates. Single-mission pre-integration runtime reviews cannot witness either platform barrier; deterministic verifiers, approvals, direct mission paths and integration reviews remain valid.

- **0.62.0 (unreleased preparation; included in 0.62.1)** — Apply Generate, Verify, Correct across seven skills. Adopted platform contracts enforce approved Web/iOS order, TEST coverage and feature acceptance gates. Preserve legacy packages and explicit action grants. Maintain this owner-use source through reviewed PRs directly to main.

- **0.61.0** — Require complete Product Definition and UI document links in chat, add STE core writing rules, caller/state architecture methods and finite experiment loops. Add standalone README and runtime packaging skills outside the seven-skill bundle. Preserve existing approvals and action grants; remote execution remains pending.

- **0.60.0** — Freeze eval rubric, population, repeats, pass rate and judge inputs in approved PRD eval-policy/1. Recompute quality and independent clean-checkout reports, deliver runner/grader/lockfile/runbook, and join exact H1/H2 evidence. Applicable >=0.60 plans require frozen sources and always-run eval/acceptance gates; legacy absent markers retain their contract. Includes the unreleased 0.59 workflow modernization.

- **0.59.0** — Modernize AGENTS template merging, protected development/main flow, host-neutral parallel writers, full design-system HTML, Activation execution closeout and exact-candidate verification. Preserve historical pins and atomic task commits. See the numbered workflow and modernization Epic for implementation and validation status. Source milestone included in 0.60; no separate release.

- **0.58.0** — Parent-owned role routing and multi-instance research/exploration, identity-bound result joins and mandatory frontend delegation with a maximum-creativity brief. App-thread role bindings require observed app capabilities, per-binding workspaces drive isolation, conflict and budget checks, completed research requires sourced findings, and omitted effort accepts the host default. The consumer AGENTS template sets a 500-line hard cap for new code/test modules, KISS, first principles, module splitting and no speculative compatibility code; Harness source is outside this cap. Preserve legacy pinned runs and owner approval gates.

- **0.57.0** — Require author self-review after PRD market reconciliation, before UI direction selection and before independent HiFi review. Record current evidence and block dependent Harness execution on unresolved findings. Preserve independent review, owner decisions, scoped maintenance and historical RUNs. Web review keeps 390/768/1024/1440 px plus intermediate widths; approved targets and native size classes remain authoritative.

- **0.56.1** — In a Git checkout root, bind delivery-acceptance results and evidence to the exact committed `HEAD` bytes. Ignored, untracked and edited files cannot produce a gate PASS; byte-preserving Git attributes are required.

- **0.56.0** — Remove the new-package Wireframe stage. Explicit ui-design/2 reads PRD directly, defaults to three directions and validates HiFi copy/operations before review. Harness 0.56 freezes the complete HiFi package; design-system/3 drops the Wireframe binding. Legacy contracts retain their original checks. Follow-ups to the 0.55.0 review fixes. `check_delivery_acceptance.py` now needs `--candidate-sha` or `--candidate-from-head`, and in a Git checkout it requires the register's candidate to be HEAD or an ancestor with only the register, its listed evidence and run coordination files changed after it. The checker has no RUN version, so an in-flight 0.55.0 run fails the gate if its register commit holds other files or it passes a stale `--candidate-sha` after a repair. Under an adopted runtime contract, runs that require 0.55.1 or later need every worker's and reviewer's `contract_adoption_check`. The PLAN and RUNBOOK templates include the delivery-acceptance rows and the register commit order. Mission launches and `app_threads` reviewers under a `*` mission scope are deferred instead of stalling. The 0.55.0 `coordination_paths` and protected-branch checks skip only runs pinned below 0.55.0. The legacy current-HiFi rule is dated by the approval and its receipts and is enforced in UI and design-system pair joins for runs that require 0.55.1 or later, with receipts compared against 2026-09-27T00:00:00Z. Acceptance evidence must sit under `evidence/` next to the register, and workers can never write the register or its evidence. A crashed or timed-out review can be recorded as `retryable_failure` again. Exchange-commit races keep concurrent bytes in a named recovery file. Product Definition adds Base UI and Radix Primitives as headless component-foundation options. Correct audited skill instructions, prompts and command examples; retain historical approvals and compatibility pointers. Clarify product-operation review and automated approval joins, container-only verifier reuse and optional motion skills. Includes macOS CI and SIP-protected signature-verifier fixes.

- **0.55.0** — Fixes from a multi-agent review of all seven skills. Breaking changes and what consumers must do: re-run finalize and re-record Product Definition Approval and the Stack Decision Checkpoint, because their digests now cover the raw text including fenced code, indented lines and HTML comments; add a `Styling approach` row to Mobile/Desktop stacks; write Environment Status Checked values as RFC3339 with a timezone; give cleanup lifecycle nodes (`archive_worker_tasks`, `remove_worktrees`, `delete_branches`) an exact target in runs that require 0.55.0; complete Impeccable critique and audit before Visual Approval; name Wireframe Validation and Visual Approval in enhancement UI rows. Also isolates trusted-host and legacy pushes from repository hooks and askpass, keeps atomic RUN, DOCUMENTS and design-system commits on macOS, records each install's source commit and adds a macOS CI job. UI Design Builder also adds Motion and Three.js motion routes, a content-based motion proposal when the owner is silent, HiFi media embedding limits and captured references.

- **0.54.5** — Publish the missing 2026-09-24 handoff-audit record and the 2026-09-26 branch reconciliation. Removed local and remote branches only after tree checks proved their content was already released on main.

- **0.54.4** — Add an optional 19-domain reference library and stage-specific pointers across all seven skills. Compare choices from product needs, retain adopted decisions, and keep source refresh, design, runtime and authorization boundaries in the existing workflow.

- **0.54.3** — Polish the shared Wireframe and HiFi sidebar with quieter navigation, a clear active page, a two-column target picker, wrapping labels and reduced-motion-aware feedback. Preserve reviewer isolation, canvas sizes and runtime behavior.

- **0.54.2** — Wireframes now default to four Web review widths: 390, 768, 1024 and 1440 px. App + companion Web products use one technology-neutral PRD across iOS, Android and public-showcase surfaces. The page-purpose Design Brief and playable motion studies carry into HiFi and implementation. HiFi review adds measured layout-integrity checks for compressed controls, alignment and clipped content. Tests isolate the missing-worktree fixture and explicitly synchronize a waiting retry before releasing its failed origin.

- **0.54.1** — Preserve the same RUN after authorized candidate repairs, retain historical verifier identities, revalidate exact current heads, accept literal dynamic-route filenames and report parent/worktree drift. Require the actual Wireframe and HiFi writer to load frontend-design, with action-time skill checks and explicit handoffs. Includes the previously unpublished 0.54.0 design-intake, PRD refinement and handoff-audit work.

- **0.54.0 (unreleased preparation; included in 0.54.1)** — Ask for product and visual references in design intake and record a concise Design Brief. Review first-delivery UI and technical completeness before product approval, then refine the same PRD from evidence through delivery without changing frozen approvals. Every task handoff also audits affected live documents, Epic/index and task state, checks `docs/tasks.md` against PLAN/RUN when applicable, and compares shared `AGENTS.md` rules with the observed installed template before refreshing stale shared instructions in place.

- **0.53.1** — Use bundled Chromium for required browser verification. Keep the long HiFi scenario bounded, preserve all assertions and report completed phases on timeout. This repairs repeated post-merge browser deadline failures in 0.53.0.

- **0.53.0** — Browser CI requires provisioned prerequisites. Shared schema-5 lifecycle checks cover the compiler/Harness/Activation/SEO joins and repair missing dependency/context handoffs. Maintenance summaries, runtime preparation metrics, document reading reuse and translation structure/literal checks make verification more reliable. Stronger required checks are a breaking skill-bundle change.

- **0.52.0** — Wireframe and HiFi review share a shell with platform-specific canvases and working product controls. Schema-5 wireframes require sourced copy and operation coverage; HiFi review requires source-bound tokens, independent evidence and one consolidated owner approval. Design routing distinguishes initial work, enhancements and routine maintenance without rewriting historical artifacts. The changed review and approval contract is a breaking skill-bundle change.

- **0.51.0** — General capability-based runtime adaptation replaces provider-specific drivers and legacy workflow templates. English PRD and architecture sources gain synchronized Chinese review copies, including same-directory backfill for existing English-only documents. AGENTS records repository changes in Epics at task checkpoints, even without a Harness run. This is a breaking skill-bundle change.

- **0.50.0** — Annotated wireframes are the default, with measured layout notes and readable destinations. Wireframe and HiFi token galleries apply their displayed values; formal previews include safe typography, shadow and motion samples. Required HiFi preview properties and fresh observations make this a breaking skill-bundle change.

- **0.49.0** — Design translation and explicit full rebuilds with retained PRDs; bilingual reading, motion boundaries, responsive navigation, Web/iPhone recipes and source-aware design freshness checks. New review obligations make this a breaking skill-bundle change.

- **0.48.0** — Enhancements preserve unaffected Wireframe and HiFi screens and reuse the approved direction. Epic change logs distinguish new outcomes from small fixes. Reviewers gain exact-width responsive canvases, usable local search and source-bound component specimens. Fresh HiFi evidence validates actual variants, selection retention and malformed rows. Breaking skill-bundle change.

- **0.47.0** — Indexed Epics and derived execution summaries keep one current PRD. Document sync reports source impacts. Project guidance routes conditional rules; 500 lines is a split checkpoint. Wireframe defaults to the primary page; fresh HiFi approval requires sidebar Overview, page-bound Design Tokens and separate product/reviewer browser evidence. Full-stack E2E and recovery handoffs use existing records. Breaking skill-bundle change.

- **0.46.0** — Product-fit stack and agent-runtime recommendations, researched design references and scoped enhancement guidance. Required motion now needs approved intent and typed normal/reduced-motion projection evidence. Native implementation keeps its separate platform checks. Breaking skill-bundle change.
- **0.45.0** — Mid-fidelity wireframes include a reviewer-only Design System Draft view with shared prototype values and live specimens. Generate formal design-system HTML from the validated pair and reject missing, stale or edited previews at publication. Preserve approved wireframe bytes and keep formal component appearance tied to HiFi. Required-pair publication now needs the derived preview. Breaking skill-bundle change.

- **0.44.0** — Neutral grayscale wireframes show product content by default, with review annotations available separately. Add task-fit navigation, editorial, table, list, and form presentation plus explicit primary-action emphasis. Review representative cases before full coverage and require W5 composition quality of at least 80. Existing approval records need the new W5 score before revalidation. Breaking skill-bundle change.

- **0.43.0** — Every skill invocation reviews live document and runtime drift. Preserve the current PRD as the enhancement baseline and link historical references. Add frozen requirement-to-scenario acceptance, isolated synthetic fixtures, and separate Web/native/agent evidence. Bound repair and module replacement without repeated same-scope approval; unresolved requirements never become PASS. Harden bounded contract reads. New delivery workflows require these checks; legacy RUNs are not migrated.

- **0.42.0** — Executable product packages require a human-owned Security Requirements Gate: required rows trace existing `PRD-*` requirements to Required-Yes security `TEST-*` IDs, and Harness task gates enforce controls plus denial/no-side-effect tests before commit. Existing product packages require renewed Product Definition Approval. PLAN-v6 requires each deterministic batch/final verifier node to reference `batch_verifiers`/`final_gates`, and every declared gate to have a node. Breaking skill-bundle change.

- **0.41.1** — Stop Windows CI at the first failed Python suite and normalize temporary fixture paths before strict identity checks. This fixes failures hidden by later successful commands.

- **0.41.0** — Default new managed build/lint/test checks to explicit host execution with executable and source evidence; keep Docker/Podman optional and existing container declarations unchanged. Record actual worker/worktree capacity and launch independent missions before waiting. Present complete PRD, wireframe and HiFi review links, and derive PRD improvement recommendations from prior market research. UI browser review needs no container. New host declarations require this bundle version.

- **0.40.1** — Fix strict stack validation for existing Selected/Required choices with `Approved option map: None`, including packages without an options table. Newly approved choices still require an exact option map.

- **0.40.0** — Visual quality now requires H5, H7, and H9 scores of at least 80 independently. Direction selection uses comparable primary/stress screenshots with validated scope, platform coverage, image files, and hashes. Platform rules separate Web and native typography, icons, layout, and input; iOS explicitly assesses system text styles, Dynamic Type, and SF Symbols. HTML is review-only; native representative cases are verified before implementation expands. Existing visual contracts need the new comparison, platform, and score records plus renewed affected approvals. Breaking skill-bundle change; no legacy approval is silently upgraded. This release also adds guarded checkpoint task-view refreshes, a read-only stack option-map renderer, retained dispatch evidence inspection, batched documentation reads, smaller review packets, verifier timings, and exact same-batch container reuse with independent guards.

- **0.39.0** — Connected HiFi packages use `ui-hifi/2` with hash-bound sibling HTML pages, declared product-control destinations, and `ui-output/2` click/keyboard evidence. Frozen Git revisions must include every child page. Schema-1 references remain inspection-only; Visual Approval requires the new contract. Also fixes CLI/nonpublic Toolchain approval, parity filename collisions, and Windows executable-file ACL checks. Adds final-path UI publication checks, stage-aware skill bindings, installed command paths, approved HTTPS credential helpers, canonical UI digests, hybrid responsive guidance, and predeployment Activation preparation.

- **0.38.0** — Full zero-to-one contract hardening. Release-surface applicability, canonical Product/Stack approval digests, exact `PD-Rn@sha256` revisions, closed approval-reference/option sets, exact product identity, full Deployment revalidation, target-specific measurement provenance/windows, typed append-only Outcome/Verdict History, and mode-specific SEO records close the Product→Activation→Outcome chain. Required design systems use a pending→compile→owner-link handshake; Stack styling and platform choices bind through UI and schema-2 `surfaceContracts`. PLAN-v6 commands run only through a machine-approved OS-protected native Docker/Podman executable whose path/hash/owner-DACL/version/RepoDigest are retained; fake PATH runtimes and Windows script wrappers are rejected. Parity is non-gating for unsupported groups and binds trusted launcher identities. Archive C→A uses complete no-follow inventories, a durable recovery journal, canonical paths/modes, isolated Git filtering, and closed recovery mappings. Authority-file writers atomically exchange or retain a displaced backup before accepting new bytes, so concurrent data is restored or preserved. Trusted-host policy setup and signed publication evidence are executable and remain outside the local agent boundary. Git, transition, design-system, and installer writes reject link/reparse swaps; Windows has a targeted CI lane; public external UI dependencies and Python/Pillow prerequisites are explicit. RUN closes local-only at C, direct work skips managed archival, and failed A enters a fresh C2/A2 continuation without rewriting history. Breaking skill-bundle change.
- **0.37.0** — UI design is now a separate approved skill boundary. `product-definition-builder` freezes product scope plus complete frontend/backend architecture and stack decisions, then stops. New `ui-design-builder` owns human UI/style/motion/media intake, `wireframes/4` typed image/motion placeholders, W1–W5 structural scoring, `frontend-design` Style Integration, connected HiFi HTML, Impeccable critique/audit, H1–H9 scoring, Visual Approval, conditional GSAP routing, optional exactly authorized Higgsfield MCP motion generation, and the Design System Need Gate. Schema-4 wireframes now freeze exact static, action, feedback, and alternate-state copy plus bounded dynamic display contracts before grading or structural approval; the copy owner, locale, and date are recorded in `ui-design.md`, and later wording changes reopen Product Definition, Copy Freeze, responsive review, and Wireframe Approval. Formal tokens compile only after visual approval, canonical UI artifacts live under `docs/design/`, and Harness 0.37.0+ requires a frozen approved `ui-design.md` for UI delivery while retaining legacy design paths for read compatibility. Product Definition's read-only analysis graph now uses the current host's native sibling-agent runner with the same role and parent-ownership contract across Codex, Claude Code, Pi, and generic hosts. The seventh bundled skill, `seo-growth-review`, adds an optional read-only post-release pass over production crawl/index evidence, verified Search Console and GA4 sources when available, current Trends or Keyword Planner estimates, and user-provided exports. It keeps search visibility distinct from on-site behavior, labels claims as observed, estimated, or hypothesis, ranks query-to-page opportunities, and routes every follow-up without changing the site or external accounts. Breaking skill-bundle change.
- **0.36.0** — Product-first decisions now have an approval spine. Post-draft market research reconciles the core candidate before a human Stack Decision Checkpoint and Product Definition Approval; UI wireframes start only from that approved revision, while headless products still require product approval. New technology choices are presented as coherent bundles and become executable only as `Required`, `Selected`, or `Approved`; `Recommended` and `Provisional` block Harness. Frontend separates language, package manager, component foundation such as shadcn/ui, and styling; mobile destinations are separate from native/cross-platform and framework decisions. PRDs add Data & Trust and AI/Automation gates, measurable metric ownership, structured assumptions/open questions, and enhancement-wide impact records. The new `check_product_package.py` validates the three core files and is reused by the Harness frozen join when the approval marker is present. Breaking skill-bundle change.
- **0.35.5** — New `scripts/parity_capture.py`: the Final Visual Parity Loop becomes executable — it enumerates the route×breakpoint×state matrix from PLAN `ui_surfaces`, drives the agent-browser CLI to capture the design-reference render and the implemented page at the same viewport (`-target.png`/`-actual.png` pairs under `docs/goal/evidence/parity/`), runs a DOM geometry probe per app page (horizontal overflow plus visible overlap findings) for the `layout_check` attestation, and writes `manifest.json` plus a self-contained `parity-board.html` for the judgment; a small per-run route map supplies reference selectors and optional state triggers, the ready state captures without a trigger, and manual capture remains the no-CLI fallback. Production smoke gets its first content definition: UI-bearing candidates re-capture parity at the production URL into `docs/goal/evidence/production/` (promotion contract condition 7, deployment contract, seeded AGENTS.md), so a deploy that drifted from the design reference is a recorded finding instead of a post-deploy surprise.
- **0.35.4** — Direct small work now commits with the structured subject too: the seeded `AGENTS.md` and `commit-convention.md` require `<type>(<scope>): <imperative summary>` for every commit outside a managed run — including plan-mode edits made in place without a branch — with trailers optional and a shipped example pair (`fix(dashboard): correct save-button copy`, `chore(deps): bump playwright to 1.49`). The subject is the record: small changes between runs leave a searchable, typed trail in git history.
- **0.35.3** — Added `scripts/docs_weight.py`: a read-only complexity-ratchet report that counts the normative words in every skill's SKILL.md plus its references and prints the per-file, per-skill, and grand-total deltas against the most recent `v*` tag. It runs in CI and in the Required Verification suite so documentation growth is visible at every release; it reports and never gates.
- **0.35.2** — Hardening pass over the 0.34/0.35 gate stack. The harness version gate now uses one strict parser (`harness_schema.version_at_least`) everywhere, so pre-release pins such as `0.35.1-rc.1` enable gates consistently and short or malformed pins disable them consistently — closing the fork where the layout/ledger gates and the impact-summary/security gates disagreed. Runs pinned to harness 0.34.0+ now get the three-viewport web floor enforced at the harness joins too (design-system pair and PRD anchors); legacy and unpinned runs keep two-target readability. `archive_run.py` runs the real PLAN/RUN pair validation before archiving, refusing hand-edited or invalid "complete" runs. The tasks view's generated header scopes its never-edit warning to the generated part; coordination-path seeds now include `docs/tasks.md` and `docs/goal/REFINEMENT_BACKLOG.md`, so documented closeout rewrites no longer trip the stale-head check; the Required Reading rule names the orchestration skill truthfully; activation is ordered after promotion and before archival, with its findings logged by the parent; UI-impact classifications travel in the worker payload's integration notes and aggregate strongest-impact-first into `ui_impact_summary`; and layout_check, deviation_ledger, and ui_impact_summary values are labeled as recorded attestations — validated for completeness and shape, verifiable by lookup — with `inspect_harness_run.py` surfacing their counts and gaps.
- **0.35.1** — The seeded project `AGENTS.md` gains a Required Reading section: managed harness work reads the bound `delivery-harness` SKILL.md and product-affecting direct work reads the affected `docs/product/PRD.md` sections plus the documents `DOCUMENTS.md` names, with skipping treated as a blocking review finding; the repository's own `AGENTS.md` carries the maintainer-side mirror. `docs/tasks.md` gained a hand-maintained Update Log fenced by `update-log` markers — `render_tasks_view.py` rewrites everything above the markers, preserves the fenced rows verbatim, and `--check` ignores log edits — where every owner or agent update after a completed plan lands as one dated row until archival; product-affecting updates also follow Keep Product Contracts Current into the PRD. The PRD/run separation is now stated across archival: the archived set references its PRD only through the frozen `content_sha256` in PLAN's sources, nothing under `docs/product/` ever enters `docs/goal/archived/`, and the PRD stays published as the living reference for later enhancement runs. `archive_run.py` also gained `--stamp` to pin the archive timestamp for deterministic re-runs.
- **0.35.0** — UI alignment became machine-enforced: RUN-v11 files pinned to harness 0.35.0 or later carry a `deviation_ledger` — every accepted parity deviation needs one cited row, and an uncited row is rejected — and a `ui_impact_summary` that classifies every mission on a UI run as `none`/`style`/`structure`/`both`, with `structure` or `both` naming its accepted upstream doc delta; both are validated at closeout. New `scripts/archive_run.py` folds a completed run's whole coordination set — PLAN.md, RUN.md, DECISIONS.md, REFINEMENT_BACKLOG.md, evidence/, and the rendered tasks view — into `docs/goal/archived/<YYYYMMDD-HHMMSS>-<run-id>/` behind a dry-run move list, records the row in DOCUMENTS.md, and never deletes; the completion flow makes post-promotion archival the mandatory next step, the archival commit rides the run branch to `main` through the same promotion path, and new_run points a completed run at the archiver instead of a bare overwrite refusal. Breaking skill-bundle change, version-gated to 0.35.0+ runs.
- **0.34.0** — Renamed the fidelity vocabulary end to end: the high-fidelity HTML review is now the design reference and wireframes are explicitly structural; frozen PRD bytes are unaffected. Web responsive sets now require at least three ascending viewports from PRD authoring through the wireframe checker and the design-system pair, while historical `wireframes/2` files keep two-target readability and a legacy two-target web set must be raised through a design-input delta before its next re-validation. The harness PRD join now requires exactly one `responsive` anchor per `UI-*` entry instead of silently skipping the breakpoint comparison. RUN-v11 files pinned to harness 0.34.0 or later record a `layout_check` on every UI evidence row — a real-browser DOM geometry scan (overlap, clipping, occlusion, horizontal overflow), a labeled manual or native basis, or a recorded reason — and a PASS row with a failed check never closes. UI tasks classify their impact (`none`/`style`/`structure`/`both`) before acceptance, structural changes integrate only behind their doc delta, accepted parity deviations land in a deviation ledger with citations, direct and open-ended refinement work carries the same doc-sync duty, and shipped motion must trace to the PRD Motion Need Gate decision. Breaking skill-bundle change.
- **0.33.0** — Moved the five canonical skills from `.agents/skills/` to a top-level `skills/` folder for the public mono-repo layout, and added one-command installers. `install.sh` (bash) and `install.ps1` (PowerShell) move any existing copies to one timestamped backup under `~/.agents/skill-backups/product-delivery-harness/`, copy `skills/` into `~/.agents/skills/` excluding `__pycache__`, and verify each copied `SKILL.md`; re-running the installer is the update path. `package.json`'s Pi skills pointer, CI, the contract tests' repo-root detection, and every documented repo-internal path follow the move; the user-side `~/.agents/skills/` install convention is unchanged, so existing installs keep working. Breaking skill-bundle layout change.

- **0.32.0** — Bounded Product Definition UI grading to one complete diagnostic wave, one consolidated root-cause ledger, one repair batch, and one re-review. One lead grader is now the default; at most two non-overlapping specialists require an owner request or recorded high-impact risk. Numeric scores describe visual quality, while explicit PRD and Technical Hard Gate failures remain binary; design-reference output needs an overall score of 90 with `H2`, `H4`, and `H8` also at 90, non-critical 60–79 scores are advisory, and passing candidates are not reworked to chase 100. PRDs now include a Motion Need Gate, design-reference HTML may demonstrate required local UI motion with a reduced-motion path, and generated motion remains deferred until separately authorized.

- **0.31.0** — Standardized release-unit naming across Product Definition and Deployment. Production uses the canonical `<product-slug>-<surface-suffix>` name without `-prod`; development adds `-dev`, and distinct surfaces cannot reuse one release name. The normal suffixes are `web`, `api`, and `extension`, while native artifacts and separately released units use explicit surface suffixes and keep provider/store identity separate. The Product Definition workflow now requires and validates `surface_suffix`/`release_name` pairs, `docs/DEPLOYMENT.md` records every release unit, and its checker enforces the same naming contract. This is a breaking change for workflow inputs and deployment records.

- **0.30.0** — Replaced the persistent `development` branch with a permanent main-only flow. Initial delivery and enhancements both start from observed remote `main`; a non-default candidate branch carries implementation, exact-SHA review, complete tests, and any isolated preview-environment verification before separately authorized fast-forward promotion to `main`. The retired `development` name remains refused as a RUN target and can be deleted only after ancestry and dependency checks. This release also adds interactive `wireframes/3`, PRD-bound multi-agent UI grading from 0–100, the 80-point refinement loop, element-level responsive/layout checks, accessibility, design consistency, creative distinction, deferred MCP media/motion handoffs, and backward read compatibility for `wireframes/2`.

- **0.29.1** — Added `README.es.md` as the fourth README language. The language switchers, the Keeping-the-READMEs-current rule, the Releasing checklist, the repository AGENTS.md, and the pinned README contract tests now cover all four languages in the same change. No skill behavior changed.

- **0.29.0** — Added development-first promotion and living product-governance gates. Initial delivery starts from `main`; enhancements start from persistent `development`. A RUN still pushes only its own branch. After RUN close, the exact candidate is separately promoted to `development`, read back, and internally tested before production promotion. RUN guards reject `development` and `main` as integration or push targets, including mixed-case spellings. A required PR may create a different merge SHA; its tree and checks must be verified and the protected refs reported honestly. Product Definition now keeps existing PRDs and affected wireframes current for direct follow-up work, records monetization and partner-channel gates, compares RevenueCat with current alternatives instead of defaulting it, and separates affiliate, referral, and reseller operations. Gitignore hygiene is toolchain-specific, keeps examples tracked, and stops on already tracked likely secrets.

- **0.28.0** — Added `code-security-review` as the fifth bundled skill. Every new managed PLAN records security as `required` or `not_applicable` with a non-code reason. Required review dispatches one fresh sibling after serial integration and before broad final validation; `security` must cover every mission, contain every mission write scope, and cannot be skipped or superseded. `record-review-attempt --security-result` validates the other agent's structured decision, exact SHA and base, scope, trust boundaries, tools, coverage, findings, and empty PASS exclusions. Security reserve and completion recheck live Git. Interrupted security reviewers reconcile through an exact receipt; a later current PASS can close the run while retaining that history. PASS needs at least one tool or manual review recorded as `passed` or `findings`, and malformed reviewer identities return errors instead of crashing. Local verifiers protect the tracked RUN dirty exception with byte and file-identity snapshots plus a record-time hash check. Design-system atomic writes reject symlink destinations. The release also includes guarded non-runtime node transitions, exact runtime bindings, CSS-escape-aware self-contained artifact checks, and five-skill installation and contract digests.
- **0.27.0** — Added `product-activation` as the fourth bundled skill. It starts after delivery, records exact post-delivery actions and verified measurement sources in `docs/ACTIVATION.md`, routes work through connector/API/CLI/Browser/Computer Use/manual handoff, and binds authorization and evidence to the exact target, environment, action digest, source SHA, and artifact identity. Product Definition creates the Activation seed only when absent; Delivery closes before the Activation handoff; later outcome reviews use only matching verified `MS-*` sources. The release also makes browser extensions first-class release-target surfaces and updates four-skill installation, contract digests, CI, and cross-skill tests.
- **0.26.0** — Responsive UI contracts are now blocking from product definition through delivery. Every `UI-*` entry declares one shared set of at least two web viewports or native/desktop size classes; `wireframes/2` projects each target with explicit region order, visibility, grid spans, reflow, interaction rules, and never-drop regions. Wireframe and design-reference HTML approval require a real-browser page-target-state matrix with no unintended overlap, clipping, occlusion, or horizontal overflow, while intentional overlays document stacking, focus, safe-area, and dismissal behavior. The design-system pair and PLAN use the same responsive set, and Harness rejects missing, duplicate, one-target, unsorted, extra, or drifting coverage while keeping legacy schemas readable.
- **0.25.7** — Removed the source repository's root `Tasks.md` flow log and its local logging rule. Managed target projects still render the non-canonical `docs/tasks.md` view on demand; no target-project skill behavior changed.
- **0.25.6** — Documented the scripted transition flag surfaces (`pause`/`resume`/`cancel`, review-attempt, wave, lease, and validation flags) in the state-model reference, added direct tests for the wireframe HTML and PRD contract checkers, and noted bytecode exclusion in the install docs. No skill behavior changed.
- **0.25.5** — `Tasks.md` flow-log updates now stay local and land with the next real change's branch and PR instead of getting a log-only release.
- **0.25.4** — Added the repository flow log `Tasks.md`: one line per minimal step, checked off as each completes. No skill behavior changed.
- **0.25.3** — The repository is now licensed under the MIT License: a LICENSE file was added, all three READMEs gained a License section, and the package.json `license` field is set to MIT. No skill behavior changed.
- **0.25.2** — Repository renamed from `fullstack-goal-dev` to `product-delivery-harness` to match the product name. README badges, clone commands, and install paths now use the new name, and the install note now describes the repository as public; no skill behavior changed.
- **0.25.1** — Managed-run correctness and evidence recording. `new_run.py` now binds graph revision to the actual PLAN revision, reads release identity from a skill-local `VERSION` file that survives directory-copy installation, and validates its generated RUN before writing. `record-worker-result` observes the bound worktree's live branch, head, dirty state, diff, and ancestry before atomically recording accepted or validator-rejected evidence; `reject-worker-result` records a parent-rejected current candidate without hand-editing RUN. The transition rechecks both worker HEAD and PLAN before replacement. Attempt and lease identities now fail closed on ambiguous reuse. The real cross-skill golden path is a required CI step, and installation text now distinguishes independently invocable stages from their explicit dependencies.

- **0.25.0** — Research-first gating, outcome review, and one wireframe checker. `delivery-harness`'s frozen wireframe join now runs `product-definition-builder`'s full `check_wireframe_html.py` on the frozen bytes — reviewer shell, self-containment, filled data, approved status, and the PRD-to-wireframe join — instead of a reduced reimplementation, with `validate_harness_plan.py --wireframes` routed through the same checker and a missing sibling skill reported as an explicit error. `validate_result.py` gains `--repo-root`, re-running the frozen-source byte and semantic joins inside its single manifest walk. `product-definition-builder` gains a pre-draft research-first assessment (workflow step 4, before any closed-set decision) with a human `go | clarify | stop` Research Gate recorded in `PRD.md`, a published `research-assessment.md` with stable `RA-*` IDs, and a post-draft market-research pass that reconciles the assessment instead of researching cold; plus a post-deploy `outcome-review.md` — deployed SHA, per-metric baseline/target/actual, and a `no_change | enhancement | incident` verdict — that the next enhancement run reads in full. Deployable packages also seed a names-only `docs/DEPLOYMENT.md` operator handoff (Required Secrets and Variables plus External Console Setup) that `delivery-harness` reconciles before the first deployable push and against observed status after deployment via `check_deployment.py`. An opt-in golden-path E2E (`HARNESS_GOLDEN_PATH=1`, outside CI) walks the real CLI spine over one synthetic package so cross-skill drift surfaces as one red test.

- **0.24.0** — Renamed the complete skill suite to Product Delivery Harness. `prd-builder` is now `product-definition-builder`, `product-design-builder` is now `design-system-compiler`, and `full-harness` is now `delivery-harness`. Canonical folders, skill frontmatter, UI metadata, templates, CI, tests, setup commands, cover art, and all three READMEs use the new names. Existing installs now have a recoverable migration: quiesce active sessions, archive legacy and existing destination directories outside the discovery root, copy and byte-verify the three current skills, confirm the legacy IDs are no longer discoverable, and restore the backup on failure. The package id is now `product-delivery-harness`; the existing GitHub repository slug remains unchanged until it is renamed separately.

- **0.23.0** — Write-path hardening and cross-artifact validation. `close-wave` records durable wave tombstones and preserves `run_complete` authorization for validated `worker_passed` closeout while `wave_closed` grants still require resolution first. `accept-wave` now runs only while control is `running`, requires a live clean non-default integration checkout at `observed.git.parent_head_sha`, reruns the selector, and accepts exactly its complete dispatchable mission frontier; `lease-worker` refuses overlapping write scopes and serialized or exclusive resources, and only explicit retryable failures or interrupted-worker reconciliation can re-arm a blocked mission. `record-integration` proves the observed integration checkout and branch, clean product tree, batch-base and prior-integration-head ancestry, and worker-head containment, so integration cannot move onto a fork that drops earlier work. These clean-tree gates exclude only the exact tracked RUN file that transitions necessarily update; linked integration checkouts select themselves as the parent while retaining Git's clean primary checkout as a recognized sibling. Every mutation refuses foreign locks regardless of staleness or heartbeat parseability; the five dispatch commands require the held durable lock, and an operating-system lock plus exact-text comparison serializes the full RUN read/validate/write transaction. prd-builder now uses a stable closed-decision inventory and the question tool's actual per-call capacity, asks every applicable decision, and has no Codex-specific total-call target. The design-system registry accepts optional primitive `dsId` values and enforces one global namespace for every exact `DS-[A-Z]+-\d+` token, while PLAN traces must all resolve; the frozen Markdown generated block, filled values, and exact compiler namespaces must also agree with JSON. Frozen PRD, wireframe, and separate design-system Markdown/JSON rows require matching byte hashes in standalone and transition validation; every frozen PRD is parsed even when PLAN claims no UI, every UI contract has one matched boundary pair and one `route`/`states` anchor per entry, and PRD/PLAN/wireframe IDs, routes, and states join exactly. CI and the three-language documentation are pinned to the same behavior.

- **0.22.0** — The private marketplace and plugin bundle are retired. `plugins/`, `.claude-plugin/marketplace.json`, `.agents/plugins/marketplace.json`, and `scripts/sync_plugin_skills.py` are gone; `.agents/skills/` is the only source, and installing or updating means copying the three harness skills into your user skills directory (`~/.agents/skills/`), exactly as the Fastest setup already described. The READMEs drop the marketplace badge, the per-host plugin install commands, and the local-marketplace section; `runtime-upgrades.md` now names the skills sync as the only Harness update surface and trims the per-host update notes to host-owned installers plus restart. The same release widens the run record and the deployment contract: mid-run modifications — extra fixes, follow-up edits, or user-reported changes — are recorded as their own missions through a plan revision (`execution-state-model.md`'s "Mid-Run Modification Recording"), and `docs/tasks.md` renders newest mission first so the view ends the run listing every modification the run made. Deployment gains a per-platform "Adding A Binding" runbook in the seeded `docs/DEPLOYMENT.md`: create the resource before writing the declaration on both sides, verify preview before the default-branch landing, secrets never in the wrangler config, D1 migrations preview-first — the wrangler steps scoped to cloudflare, and the named Wrangler environments renamed `env.development`/`env.production`. The READMEs also document the release flow itself: the version-bump checklist, the `v<version>` tag after landing, and the rule that any change to a skill, rule, or documented flow updates the READMEs' descriptive sections in all three languages in the same change.

- **0.21.12** — SEO metadata is now part of the PRD surface contract. Every `UI-*` entry records its route's unique `<title>` and meta description plus canonical URL, Open Graph/social, robots, and structured-data decisions (or an explicit `n/a — <reason>`); site-level SEO (indexing strategy, sitemap and robots policy, canonical policy, default structured data) is recorded in Frontend Delivery Requirements with its own `TEST-*` traces. The harness side binds it through: implementation must render the recorded `<head>` exactly, a missing SEO record is a PRD contract gap routed to `prd-builder`, and UI evidence includes a rendered-head check where `<title>` and meta description must match the PRD record on the integration head. The retired `update-private-skills.ps1` one-command updater is also removed in this change: per-runtime copies were deliberately dropped on 2026-09-03, so setup and updates are now the plain skills sync — copy the three harness skills from `.agents/skills/` into `~/.agents/skills/` — and the READMEs no longer teach the script. Running on a host outside the three named runtimes is now detection-free: a session that is not evidently Codex, Claude Code, or Pi records `provider: generic` outright with no probing for another runtime's CLI, and the version gate no longer defers a generic host for lacking an observable own-version — the loaded Harness release and the selected driver's live capability probe complete the observation. The seeded `AGENTS.md` also gains a Commit Messages section stating the message shape (`<type>(<scope>): <imperative summary>` with `Task`/`Trace`/`Verified` trailers), the one-kind-of-change-per-commit rule, and the mission-level integration form, so every runtime writes commits the same way at commit-and-push time.
- **0.21.11** — UI runs now close with a Final Page-Quality Pass. After the Final Visual Parity Loop, the skill bound to the new `ui_quality_verification` slot — `impeccable` by default — runs one `critique` and one `audit` per delivered design-reference page on the exact integration head. Blocking findings enter the ordinary repair budget; a finding that conflicts with the frozen PRD, wireframes, or visual sources routes to `prd-builder` as a design-input delta instead of a local change; the pass uses evaluate commands only and creates no competing product authority; an unavailable bound skill records the gate `UNVALIDATED` and blocks closeout unless the user accepts the descope. The seeded `AGENTS.md` Skill Bindings table carries the new slot.
- **0.21.10** — The rendered tasks view now lives at `docs/tasks.md`, not `docs/goal/tasks.md`. `docs/goal/` keeps only canonical run state (PLAN, RUN, DECISIONS, evidence); the non-canonical human view sits under `docs/` beside `DOCUMENTS.md` and `DEPLOYMENT.md`. SKILL routing, the DOCUMENTS manifest row, the renderer's help text, the stray-checklist wording, and the pinned contract tests all follow the new path. The seeded project `AGENTS.md` now states the goal-complete archival rule directly: once the owner declares the goal complete and the Closeout Bar has passed, the finished plan runtime (`PLAN.md`/`RUN.md` plus its evidence) archives into `docs/goal/archived/<YYYYMMDD-HHMMSS>-<initiative-slug>/` — a move, never a delete, and never touching `docs/product/`.
- **0.21.9** — Review-hardening cleanup from a four-lens architecture review. A real bug fix: the RUN-v11 head cross-check's follow-up git calls (merge-base, diff) now degrade into error entries instead of crashing the validator. `CURRENT_SCHEMA_PAIR`/`is_current_pair` replace eight hand-typed `(6, 11)` literals; fake test-patch seams and a stale `__all__` are gone. The selector's "exactly these deferral codes" list is complete again (it was missing eleven codes plus the reviewer-tool prefixes) and a new test binds the doc list to the emitted codes. The sequential-parent binding is defined once under an anchored heading (it was restated seven times) and the review-attempt budget once in Root-Cause Repair Escalation; contract tests pin the single definitions plus pointers instead of freezing the restatements. The integration/bookkeeping commit split is settled (merge commit, then paired bookkeeping commit) and parity repairs are stated to be ordinary candidate-changing repairs under the existing budget. The ~1200-line fixture library moved from test_harness_manifest.py into manifest_fixtures.py with re-exports, canonical fixtures read schema versions from harness_schema, and contract_digest's CRLF/LF normalization and tests/__pycache__ exclusion gained direct tests.
- **0.21.8** — Atomicity is now a run-wide commit contract, not only a worker rule. Every commit any participant creates holds exactly one kind of change: a task commit carries one verified outcome, a repair commit carries one root-cause fix attributed to one task, an integration commit carries reviewed mission heads and coordination state only (never an unrelated fix or cleanup), and a bookkeeping commit carries `PLAN.md`/`RUN.md` files only, never product code. No run layer — task, repair, integration, wave close, or closeout — lands a catch-all or mixed commit; two kinds of change land as two commits in dependency order.
- **0.21.7** — UI runs now close with a Final Visual Parity Loop. At the final gate, every route-breakpoint-state screenshot is compared against the run's visual authority: the approved HTML reference rendered side by side in target-conformance mode, or a clean `check_ui_contract.py` run plus the full screenshot matrix in system-conformance mode. Each RUN-v11 `ui_evidence` row records a `target_comparison` (baseline, baseline artifact, verdict) validated by the harness; differences outside tolerance enter a repair cycle capped at two rounds, and an unresolved difference is reported instead of relabeled.
- **0.21.6** — Production/preview resource separation is now recorded and checked, not just stated. The deployment record gains a Resource Isolation table — every stateful binding class (D1 database, KV namespace, R2 bucket, Durable Objects) with its production and preview resource IDs — and `check_deployment.py` fails a record whose two columns share one ID. The contract requires the preview environment's declared bindings to be cross-checked read-only against the recorded production IDs before the first preview push serves traffic, the seeded project `AGENTS.md` states the full-separation rule, and the frontend stack decisions record two ID sets per binding class.
- **0.21.5** — Workers preview binding isolation is configured, not assumed. The contract now records that a version preview URL serves a new version of the same Worker and shares its live bindings — a version preview of the production Worker writes to production D1/KV/R2 — so stateful preview traffic goes to a separately named preview Worker created through a named Wrangler environment whose full binding set is declared explicitly, because named environments do not inherit bindings. The non-production D1/KV/R2 resources are created at project setup, before the first preview push; a preview bound to a production resource is a blocker, not a configuration preference, and the boundary must not depend on an experimental flag.
- **0.21.4** — Enhancement runs no longer carry superseded CSS or previous-version visuals into the updated result. A style-impacting enhancement that updates a retained HTML reference must regenerate the affected screens' style layer — appending to the previous file's CSS is not approvable, orphaned, duplicate, or overridden style blocks are removed before owner review, and an in-place edit refreshes the handoff's recorded SHA-256 and archives the pre-edit copy. Harness implementation now removes the styles and classes the new reference no longer contains, never grafts a new reference onto the previous implementation's CSS, and the refinement flow gains a stale-carryover check: the after state must show nothing the accepted delta supersedes, and the delta record names every superseded style and its call sites. The same discipline covers backend and app surfaces — superseded endpoints, business rules, queries, flags, and jobs are removed or carry an explicit recorded compatibility retention; silently keeping the old path beside the new one is a contract violation.
- **0.21.3** — Deployment gains a third recorded mode, `ci_connected`: the repository's own CI workflow deploys on push instead of a platform Git connection. On Cloudflare this is the Wrangler bootstrap — `wrangler pages project create` plus a push-triggered workflow running `wrangler pages deploy --branch` — with the same branch split as git-connected (production branch to production, every other branch to a preview URL) and the same boundary: a CI deployment adds no authorization keys, and the Harness never triggers it. On Workers the same workflow runs `wrangler deploy` for the production branch and `wrangler versions upload` for every other branch, each version serving its own preview URL, with preview versions never touching production traffic. The contract also records the hard limit that a Wrangler-created Direct Upload project can never be converted to git-connected afterwards, and states the standing default: Workers with Static Assets is the Cloudflare route; Pages enters only by an explicit owner decision. Post-deploy verification now also reports the pushed head's preview URL in the conversation — observed read-only from the workflow output or platform listing, never constructed or guessed.
- **0.21.2** — Native surfaces get the same wireframe and HTML-preview treatment as web. `wireframe-guide.md` states explicitly that a native mobile or desktop app ships the same single `wireframes.html` review projection, with its own size classes as the viewport toggle, and the UI Preview Gate now defaults every UI-bearing surface — web, native or cross-platform mobile, and desktop — to a design-reference HTML mock at the surface's size class, with image generation as the fallback only where HTML cannot represent the surface. A native surface goes further: one self-contained design-reference HTML containing every `UI-*` screen with a screen switcher — the same single-file principle as `wireframes.html` — so the owner reviews the whole app in one file. The visual phase's opening recipe is now stated explicitly: work from the approved PRD package with both skills combined — `design-taste-frontend` leading the overall design direction and `frontend-design` executing the surfaces Taste excludes.
- **0.21.1** — Wireframe Reference Pass and enhancement UI-impact classification. Before drafting `wireframes.html`, prd-builder fetches the structures of two to four mainstream live products in the category and pulls Dribbble-style gallery composition references, recording every consulted source or the skip reason in `PRD.md`'s `### Wireframe Approval`; references inform structure only. Enhancement runs now classify the delta's UI impact (`none` / `structure` / `style` / `both`) with the owner before drafting instead of assuming none: structure impact regenerates the affected wireframe pages and re-runs the approval gate, and style impact requires a recorded owner decision to re-run the UI Design Pass or keep the existing direction — a stale visual contract no longer publishes silently. The UI Design Pass now also chooses iconography through an online lookup over a closed candidate set — Lucide, Phosphor, Heroicons, and Tabler — recording one primary set plus a named fallback with cited official sources in the handoff's `Iconography:` line, instead of silently defaulting to a remembered library. Typography gets the same lookup discipline — display/body pairing with Latin plus CJK coverage and a loading strategy recorded in a `Typography:` line — and the handoff gains a `Color & dark mode:` line for palette derivation and dark-mode scope. The frontend stack gains a styling-approach layer (Tailwind utilities, CSS Modules, vanilla modern CSS) recorded with the same per-row status and cited authority as every other layer.
- **0.21.0** — Browser-extension archetype support end to end. prd-builder covers the browser-extension archetype across the interview, architecture, and stack selection, and full-harness gains the matching platform archetype. Market-research findings can now land in `stack-decisions.md`; `architecture.md` gains Frontend/Backend Architecture sections; provisional stack rows now gate publication; and `implementation-plan.md` sequencing intent is a mandatory PLAN input.
- **0.20.2** — Added the full skill lifecycle diagram to all three READMEs: one mermaid covering prd-builder → optional visual design → the full-harness routing and per-wave execution loop (lock, observe, select, accept, adapters, lease, workers, validate, review, integrate) → git-connected deployment, with the cross-cutting mechanisms (skill bindings, authorization ledger, version gate, watchdog) and the two human stop points called out.
- **0.20.1** — Review hardening. lease-worker accepts the real failure phases (`worker_failed`, `blocked`) and clears stale `last_outcome`/`blockers`, so a failed or reconciled mission can retry without hand edits; `reconcile-interrupted` no longer dead-ends. A malformed verifier in `verifier_executions` reports key errors instead of crashing the validator. `reserve-review-dispatch --packet-out` renders only after the post-transition validation gate. The run lock refreshes its heartbeat on the holder's own successful transitions, fails closed on naive/unparseable heartbeats, and a non-dict `run_lock` now fails schema. `record-integration` resolves the mission node from the PLAN graph instead of a naming convention; `accept-wave` refuses a live wave even with the same id; `record-observation` tolerates dead worktrees and derives `managed_by` from recorded workspace modes. Docs/gates: AGENTS.md's verification list gains the pyflakes step; the seeded-record checkers cover their own templates' placeholders; the lock doc shows the correct `--session-id` position; the driver ladder regains its Pi line; `cursor_wait` becomes the schema label `thread_poll`; the worker-report heading, File-Size-Limit pointers, seeded-document checklist coverage, and E2E/CI template routing are fixed. Six regression tests pin the fixes.
- **0.20.0** — Structural decomposition with behavior preserved (550 tests unchanged throughout). The four near-identical verifier-group loops merge into one `_validate_verifier_group` helper; `validate_plan` (~680 lines) decomposes into nine section helpers; `validate_run` sheds its first ~700 lines into five helpers (`observed`, `attempt_log`, `waves`, `workers` at ~400 lines, `review_lineages`) with shared locals threaded explicitly — the remaining `review_workers` and `runtime_capabilities` sections stay inline for a dedicated future pass. The selector builds its per-pass indexes (`nodes_by_id`, workers-by-mission, review-workers-by-node) once per selection instead of per node. Every step was gated on the full suite staying green.
- **0.19.1** — Code simplification pass, behavior-preserving (550 tests unchanged). Dead code removed (TOOL_PROFILES, unused helpers/imports/locals); `new_run.py` imports the 12-key ledger instead of re-declaring it; the pass-through wrapper and an inverted guard are gone; the source-path quartet merges into two parameterized helpers; git blob readers consolidate into `harness_core.read_git_blob`; `changed_files_digest` is shared by both validators; test git plumbing moves into `manifest_fixtures`; `harness_manifest` declares its re-export API via `__all__`; and a pyflakes step (45 findings cleaned to zero) joins CI so dead code cannot silently return.
- **0.19.0** — Runtime speedup: the write path is scripted. `record-observation` writes the live-Git observed snapshot, `accept-wave` records the wave plus batch base, `lease-worker` binds graph/mission/task/worker/attempt in one atomic validated write, and `record-integration` closes a mission against live Git — replacing the hand-authored RUN JSON edits that made parent output grow quadratically. `reserve-review-dispatch --packet-out` renders the reviewer packet from the in-memory reserved run (one command, one validation, no separate render pass), and the selector accepts `manifest_already_validated` from callers that just validated the identical pair; `plan_digest` is hoisted out of the workflow-run and review-worker loops.
- **0.18.1** — The seeded operational documents moved under `docs/`: `DEPLOYMENT.md` and `DOCUMENTS.md` now publish to `docs/` (the checker's default path follows), and the repository root carries only what runtimes auto-discover — `AGENTS.md` and `CLAUDE.md`. The artifact lifecycle's root-publication exception is gone with them; the root rule now stands unqualified.
- **0.18.0** — Final debt batch. The PRD artifact lifecycle now inventories, stages, publishes, and reports the seeded root `DEPLOYMENT.md`/`DOCUMENTS.md`; `configure_project_context.py --check --require-resolved` fails while a seeded `AGENTS.md` still carries unresolved placeholders and runs as the publish's final move; `docs/goal/DECISIONS.md` is defined (parent-owned mid-run decision log) and the DOCUMENTS manifest gains the `implementation-plan.md`, archived-documents, and DECISIONS rows; the contract-digest deferral branches (mismatch, unobserved) are tested; `check_deployment.py` structurally validates the deployment record read-only; and `render_tasks_view.py` emits a state fingerprint (plan revision/digest, graph revision, wave) with a `--check` staleness mode.
- **0.17.1** — Second debt sweep. `watchdog --reclaim` now honors `--stale-after-minutes` and a lockless RUN no longer rewrites the document; `--session-id` moved to one documented position (before the subcommand) with a clear refusal message; `inspect_harness_run.py` shows the run lock and control state; the DOCUMENTS manifest locates the design-system pair under `docs/product/` and matches the lowercase `tasks.md`; `skip-integration-review`, `--tree-sha`, and the lock/watchdog commands are named in the canonical docs and the runbook subcommand list; skill-binding pins are verified at the resume gate; `check_skill_spec` folds frontmatter continuation lines; the required verification set begins with the test-dependency install CI performs; dedicated providers have one source of truth (`RUNTIME_DRIVER_PRIORITY`).
- **0.17.0** — Hardening and standards pass. Tier-1 debt fixed: the DOCUMENTS manifest and TASKS wording now match the canonical `docs/goal/` placement, the byte-identical-tree integration-review skip gained its tooling path (`record-review-attempt --tree-sha`, `skip-integration-review` verifying against live Git), and stale adapter phrasing left the seeded templates. New: `check_skill_spec.py` enforces the Agent Skills open specification in CI; Skill Bindings pin bound skills by SKILL.md SHA-256 with `check_skill_bindings.py` recomputing them (a skill change is a deliberate, reviewed pin update); and durable execution gains a run lock (`acquire/release/heartbeat-run-lock`; foreign sessions are blocked, stale locks taken over after 15 minutes) plus a `watchdog` transition reporting interrupted-work candidates.
- **0.16.0** — When the PRD flow seeds a new `AGENTS.md` at publication, it now fills the Skill Bindings table from the locally installed skills visible to the session: slot candidates are listed, the owner confirms the bindings in one question, and slots without a local candidate stay at the bundled default. An established `AGENTS.md` is never reopened for this — a binding update is its own explicit edit.
- **0.15.0** — Skill selection is now a project setting, not a harness edit: the seeded `AGENTS.md` gains a Skill Bindings table mapping stage slots (design_direction, design_compilation, frontend_implementation) to installed skills, with the bundled skills as defaults. The PRD UI Design Pass and the harness UI contract resolve skills from the binding — adopting a new taste or frontend skill is a one-table project edit, and bound skills inherit the same modes, frozen sources, and review gates.
- **0.14.0** — The PRD flow now seeds two root documents: `DEPLOYMENT.md` (platform record, human setup checklist for git connection and Cloudflare/Vercel/AWS wiring, environment status table) and `DOCUMENTS.md` (the manifest of every flow document, its location, owner, and canonical status). `TASKS.md` renders at the repository root when a run starts and after each accepted wave. Root carries the operational documents; the PRD family stays under `docs/product/`.
- **0.13.0** — Added the deployment contract: a git-connected, platform-abstracted stage where preview tracks the pushed run branch and production tracks the default branch, with per-platform sections (cloudflare, vercel, aws, generic — any lowercase id), read-only post-deploy verification bound to the deployed SHA, a migration path that changes the record rather than the flow, and a Deployment section seeded into project `AGENTS.md`/`CLAUDE.md`. The 12-key ledger is unchanged; deployment adds no authorization keys.
- **0.12.1** — Added the Re-Orchestrate contract to the runtime upgrade gate: after an update, the fresh session runs Resume Reconciliation, re-derives the frontier, and binds every not-yet-succeeded node to the new runtime through new attempts (succeeded nodes are never re-executed); a provider change goes through an explicit replan of `allowed_providers`, never an inferred bridge.
- **0.12.0** — The integration-review skip now keys on byte-identical trees, not just the same commit: a single-mission wave integrated as a merge commit with the same tree as its already-passed review records `integration.integration_tree_sha` and `review_workers[].tree_sha` and skips the unified dispatch. A dispatched unified reviewer gets a seam-scoped packet listing the already-reviewed mission heads and focusing on merge seams, conflict resolutions, and cross-mission interaction.
- **0.11.0** — Provider ids are open: any lowercase id (a market runtime such as `gemini_cli` or `cursor`) is schema-valid in `allowed_providers` and RUN `runtime_adapter`, runs the generic route and driver ladder, and needs no schema change; a dedicated section and `RUNTIME_DRIVER_PRIORITY` entry are optional refinements. Market host names in the generic section are illustrations, not a support list.
- **0.10.1** — The generic provider section is now a complete route for any unlisted agent host — driver selection, version gate, model pass-through, context discovery, and chrome_devtools deferral — and the marketplace and README descriptions present the harness as adapting any coding agent rather than the three named runtimes.
- **0.10.0** — Merged the three runtime adapter skills into one shared reference, `full-harness/references/runtime-adapters.md`, with per-provider sections and an add-a-provider path; `fullstack-harness-codex`, `fullstack-harness-claude-code`, and `fullstack-harness-pi` are removed from the bundle (breaking). Reviews may declare required tools, RUN records per-tool reviewer probe evidence under `runtime_capabilities.reviewer_tools`, and the selector defers unprobed or unavailable tools instead of substituting the parent's browser. Missions pass a cohesion gate and every task maps to one ordered atomic commit boundary.
- **0.9.0** — Made design-skill-rendered design-reference HTML the default web preview route in the UI Design Pass. Approved HTML references are retained under `docs/design/ui-references/<run-id>/`, superseded sets archive under `docs/design/archived/`, and target-conformance implementation builds each page from its approved HTML reference with per-file frozen hashes.
- **0.8.0** — Added the wireframe stage to prd-builder: every UI-bearing package projects its UI surface contract into one self-contained interactive wireframes.html behind a human Wireframe Approval Gate, and visual design became a separate explicitly requested phase (UI Design Pass, provider-neutral preview gate, Design System Need Gate). product-design-builder now compiles only an approved UI Design Handoff. Also fixed the design-system pair-check command path, unified the wireframe approval vocabulary, made sync --check ignore runtime bytecode, and added git diff --check to CI.
- **0.7.0** — Upgraded managed work to PLAN v6 / RUN v11 with durable pause/cancel control, cross-revision review lineages and owner grants, candidate-head tolerance for coordination-only commits, loaded/installed contract digests, guarded transition commands, and bounded review packets.
- **0.6.0** — Added a shared runtime upgrade gate for Codex, Claude Code, and Pi. RUN-v10 records host/Harness versions, lets only an already-active compatible-old wave reach its boundary, blocks incompatible or restart-pending sessions, and resumes unfinished work with a fresh attempt after update and re-probe. The updater now supports Pi packages; host binary updates and standalone Pi skill migration stay explicit.
- **0.5.0** — Reduced managed-run overhead across Codex, Claude Code, and Pi with bounded fresh context, event-driven completion, active-wave streaming review, resource-safe parallel verifier batches, exact session caching, effort routing, smaller task slices, and RUN-v10 runtime telemetry. The measured target is 75% less wall time, with 85% as the stretch target; authorization and exact-SHA gates are unchanged.
- **0.4.0** — Added repository-local design-image discovery and connected Impeccable concept generation to the Product Design Builder visual-direction gate. Creation mode now requires `product-design-builder`, `impeccable`, and `frontend-design`, while the existing PRD and three-file design package remain the only canonical product and design sources.
- **0.3.0** — Removed the GitHub landing adapter and the whole deployment/release model. The harness now ends at a push to the run's own branch; landing on the default branch is the user's own step. Authorization ledger cut from 19 actions to 12; `landing` reduced to `mode`, `remote`, `pushed_head_sha`, `continuity`; `integration.branch` is the only branch field. Dropped branch-protection evidence, `target_sources`, the three contract markers, `post_merge_cleanup`, `plan.release`, and `run.targets`.
- **0.2.0** — Worktree-per-mission default; PLAN v5 / RUN v10 typed graph with multi-reviewer fan-out; Cloudflare dispatched-deploy and Auto-Deploy (native Git auto-deploy) release models; persistent integration branches; per-page generic HTML prototypes replacing the retired page UI matrix; mobile/desktop platform support including a dedicated mobile stack-selection guide (native iOS/Android, Flutter, React Native/Expo); environment-secret scaffolding via `.env.example`; a Haiku cost tier for bounded/mechanical delegated work.

</details>
