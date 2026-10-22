# EPIC-architecture-loop-remote-execution: Integrate architecture and remote execution methods

Status: in_progress

## Problem And Baseline

The owner wants pstack's architecture methods in the existing Harness and its
loop methods available for automation. Future workers should run error-report
checks and technical feature acceptance on a Mac Mini, other computers or servers.

- Observation: 2026-10-04 02:39 UTC-7.
- Repository: `product-delivery-harness`.
- Branch: `codex/harness-flow-modernization`.
- Baseline: `1782fa000b107396fd36787c7df7fad8a2141c82`, clean at entry.
- Source and observed installed Harness: `0.60.0`; loaded identity unobserved.
- No consumer PRD, product architecture or managed PLAN/RUN applies to this round.
- Current runtime contracts do not support arbitrary cross-machine dispatch.

## Accepted Scope

Decision source: the owner's acceptance, "我覺得可以。", and subsequent pilot
choice, "mac mini", and connection method, "tailscale", on 2026-10-04. These
accept the direction, first machine type and network; the execution channel
and executable target still need observation.

This first task records the agreed split, proposed integration and acceptance
checks in the linked document and its index. UI impact is `none`. One parent
writer owns this checkout. Effective machine instructions require atomic local
commits; there is no push, branch creation, installation or remote mutation here.

The document is a derived implementation proposal. It does not grant actions,
replace product approvals, add RUN fields or change installed skill behavior.

On 2026-10-04, the owner authorized source implementation:
"依整合方案修改 skills，受影響文件採用新準則（建議）".
T2 and T3 now proceed as separate direct tasks in this checkout.
The parent remains the sole writer. UI impact remains `none`.
Affected prose follows the accepted STE core writing rules.

T2 updates the shared architecture method, worker template, Product Definition
guidance and technical packets, code-review packets, focused tests and four READMEs.
T3 updates the bounded-loop method and four READMEs after T2 verification and commit.
Both update this Epic, its index and the proposal's current status.
Acceptance uses packet-routing tests, existing authority negatives, specification
and documentation checks, plus independent review of the fixed candidate.
Runtime schemas, release version, installed skills and remote capabilities stay unchanged.

## Acceptance And Dependencies

| Scope | Expected outcome | Verification | Dependency |
| --- | --- | --- | --- |
| T1: Decision record | Separate product architecture, implementation design, execution, loop and remote responsibilities | Source references, Markdown links, diff and independent document review | Existing source/review evidence |
| Core integration | Caller-first design and scoped review methods in existing packets | Technical-role and code-review routing; accepted repair and approval boundaries | T2 implemented, 193 focused tests passed, independent source/security review passed at `2e34d526` |
| Loop methods | Finite metrics, budgets, reconciliation and retained rejected experiments | Pause, uncertainty, exhaustion and candidate-change negatives | T3 implemented; 68 focused tests passed; no schedule created |
| Remote boundary | Versioned host/workspace/transport/result identity | Capability, duplicate, mismatch, disconnect and provenance negatives | T4; current schema remains unchanged |
| Mac Mini pilot | Fixed task with verifiable result/evidence return | Actual transport and platform checks, then technical acceptance | Tailscale peer observed online; execution channel, capabilities and target case pending |

## Document Impact

| Path | Impact | Recheck |
| --- | --- | --- |
| `docs/research/architecture-loop-remote-execution.md` (deleted; recover from Git history) | Accepted direction, future work and explicit gaps | Source links, review boundary and pilot scope |
| `docs/DOCUMENTS.md` | Discoverable proposal and Epic | Paths and pending status |
| Canonical skills and four READMEs | No change in T1 | Update together when an actual skill/rule/flow changes |

## Change Log

| Change / request | Reason and affected scope | Commit / evidence | Verification and remaining work |
| --- | --- | --- | --- |
| 2026-10-04 owner acceptance, Mac Mini and Tailscale choice | Preserve the agreed architecture/loop/remote split; T1 documents only | `working-tree` at baseline `1782fa000b107396fd36787c7df7fad8a2141c82`; linked proposal | Seven local Markdown links and whitespace checks passed. Native Sol/xhigh document review DR-1 attempt 1 found no blockers. Source implementation and remote execution remain pending. |
| 2026-10-04 implementation entry | T1 landed as `4cef4f4`; writing rules landed as `f717221`. Owner authorized T2/T3 source changes. | Clean `codex/harness-flow-modernization` at `f717221368bb81afc4061c621c88559505f9ca3b`; scoped history observed | INT-E1 and INT-E2 returned separate read-only source assessments. Loaded identity remains unknown. Document sync reports `review_required` for loaded identity and first baseline. T4-T7 need the versioned remote contract and actual execution channel. |
| 2026-10-04 T2 architecture method | Add caller-first conceptual and implementation methods, state/side-effect checks and conditional alternatives. Route guidance to technical analysis and code reviews. | `working-tree` against `f717221`; scoped diff; existing packet/result schemas preserved | 193 tests passed: Product graph identity 7, review packets 9, Product contract 100, cross-skill 17 and Harness contract 60. Node syntax, focused pyflakes, skill specification, docs weight and diff checks passed. Initial fixture-name and context-length failures were corrected. Independent exact-SHA review pending. T3 and T4-T7 remain pending. |
| 2026-10-04 T2 review checkpoint | Fixed source candidate and clean checkout; clarify historical T1 observations in the live documents | `2e34d526398e2fe801d8cf34d653f29eb4d27d23`; INT-R1 attempt 1 | Independent source/security review passed with no blockers or exclusions. Manual source review covered all 16 changed files and required dependencies. Configured native reviewer binding: Sol/xhigh; actual model/session identity unobserved. T3 proceeds; remote and release work remain pending. |
| 2026-10-04 T3 bounded-loop method | Fixed measurements, one hypothesis, finite limits, retained rejected work and reconciled wake behavior; four-language descriptions | `working-tree` against `2e34d526`; graph reference and SKILL routing; runtime schemas unchanged | 68 tests passed: Harness contract 60 and eight existing authority negatives. Skill specification, docs weight and diff checks passed. No prose-mirroring test or new engine added. The final handoff supplies the fixed-candidate review verdict. T4-T7 remain pending. |

## Results And Remaining Work

Detailed scope and ordered tasks: [integration proposal](../research/architecture-loop-remote-execution.md).

T2/T3 source methods are implemented and locally verified.
The task handoff names their atomic commits and final exact-candidate review.
The Epic remains open for T4-T7; no release, installation or remote acceptance is claimed.

T3's source diff against `2e34d526`, excluding this Epic and its index, has SHA-256
`dc37a93b56366ed6bb0022d009d2b7da05f1fa5d21b54ea26f99f1742355597f`.
It covers SKILL routing, the graph method, four READMEs and the proposal update.

DR-1 reviewed the proposal at SHA-256
`ab9a2d7d37be11508891f33da011b76d926929e0c0abe3a27b5b16570977705b`,
the index at `8aefbeddb77181acbbbe49165594614d7ef54bae6e1b233dd0a276cd248b88cf`,
and the pre-results-update Epic at
`e7c854684688c7216b12920acd4a3a3c97714a35258fb6ca956cd35c8239d549`.
At T1 closeout, the proposal and index remained byte-identical to that review.
The hashes above identify historical evidence, not later source changes.

Document sync returned `review_required` for unobserved loaded identity and
the first-observation baseline. No snapshot or loaded digest was invented.
At T1, observed installed template 0.60.0 matched the source template hash
`0d5064d94c0072ad2d1f06f3b516dab328d425be79454df10b50ce6f44b2470e`;
shared rules are current by meaning with the repository's explicit overrides.

At the T2 checkpoint, installed template 0.60.0 retained that hash.
The source template is now
`feed8dcc70b3691d9822a1b05641d4502dae452fd1926954f09db3fc78fff62f`.
The difference is the accepted writing guideline in `f717221`.
Existing shared rules remain current by meaning; release and installation remain pending.

Codex project inventory observed only local projects. The owner selected
Tailscale, whose local status is Running and whose peer inventory shows one
matching Mac Mini online with OS macOS. Device endpoints stay out of tracked
documents. This proves neither remote execution nor platform capability.
Remote capabilities, skill identity, execution channel, target acceptance
scenario and actual execution remain unverified. Do not mark the Epic complete from this
documentation checkpoint or treat a transport smoke as feature acceptance.

No new artifact class requires an ignore rule. The proposal and Epic are tracked
source documents; no credentials, logs, caches or temporary process records are added.

T2 retains `product_agent_graph.cjs` above 500 lines because it owns one Product
graph facade. This prompt change adds no new module responsibility.
Test logs stay in a unique temporary directory outside the checkout.
Existing Python cache patterns apply; no new ignore rule is needed.
