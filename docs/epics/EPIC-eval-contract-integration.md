# EPIC-eval-contract-integration: Freeze eval policy and verify handoff

Status: complete
Source integration complete, release pending.

## Problem And Accepted Outcome

Future AI projects need an approved rubric, fixed denominator and pass rate,
then a delivered runner, dependency lock and runbook that another executor can
rerun. The owner accepted the [research proposal](../research/eval-contract-integration.md)
on 2026-10-03: "OK，那我們開始去接入提案。"

The parent owns this checkout's writes. This is direct source maintenance,
UI impact `none`, with no consumer PRD or managed PLAN/RUN. Local atomic commits
follow the machine instructions. Publication, promotion and installation need
their separate authority.

## Baseline And Dependencies

- Repository: `product-delivery-harness`, branch `codex/eval-contract-research`.
- Entry HEAD: `1d21e596c2f6a1bccd9828c678c3cbaf233d0a80`, clean.
- Live remote main observed on 2026-10-03:
  `bdae1d82acfd24cdeb2866f5480ff4d4d73b0b61`, source `0.58.0`.
- Installed Harness: `0.59.0`, a separate local development line. It is not
  incorporated here. Loaded-at-session-start skill identity is unobserved.
- Introduction boundary: candidate `0.60.0`. Legacy packages without the new
  marker keep their checks; a present marker always validates.
- Completed research stays in [its Epic](EPIC-eval-contract-research.md).

The independent read-only assignments EVAL-I-Q1/A1 (Product), EVAL-I-Q2/A1
(delivery gate) and EVAL-I-ARCH/A1 (architecture) returned matching entry
branch/SHA without changes. The configured explorers are FlashX/max and the
architect Astra/high; independent provider/session telemetry is unobserved.
No fallback was used. These explorations are not a formal review PASS.

## Sequential Tasks And Acceptance

| Task | Outcome | Checks |
| --- | --- | --- |
| EVAL-I-01 | PRD-owned `eval-policy/1`, explicit Product checker mode, frozen dataset/rubric/judge inputs and TEST joins | Policy/parser/package regressions; legacy omission, malformed markers, artifact hashes and approval binding |
| EVAL-I-02 | Derived `eval-contract/1`, deterministic report arithmetic and delivered runbook | Fixed trial coverage, rates/slices/critical failures, identities, usage/freshness and invalid evidence |
| EVAL-I-03 | Two self-contained reports registered to required quality/handoff scenarios; exact H1/H2 proof | Git/path/byte guards, clean-checkout receipt, no transitive evidence exemption |
| EVAL-I-04 | Mandatory >=0.60 readiness joins and always-run verifier graph | Current strict source route, gate argv/hash/topology and legacy compatibility |
| EVAL-I-05 | Consistent language/version surfaces and fixed-candidate verification | Complete required suite, browser/golden path, independent code/security review, document handoff audit |

No global threshold is selected. Product owners approve their metric, repeats,
slices, critical cases, grader, data rights, freshness and spending. Required
functional TESTs retain all-pass semantics. Missing/error/duplicate trials
cannot disappear from the denominator. Checker commands never execute runners.

## Document And Artifact Impact

Product SKILL/interview/output contract, a new eval policy reference and parser;
Harness checker, templates, acceptance/verification/source references and
readiness joins; all four READMEs and version surfaces. No scheduler or RUN
schema changes. The existing evidence root and parent ownership remain intact.
New source/templates/tests are tracked. Logs and review packets stay outside
the checkout; no new ignore class is introduced.

## Change Log

| Observation | Baseline / observed head | Scope and result | Verification / remaining work |
| --- | --- | --- | --- |
| 2026-10-03 entry | `1d21e59` / same clean head | Research accepted; explicit implementation scope above. No canonical source change yet | Local Git, live main and installed version observed. Implementation and all required checks pending |
| 2026-10-03 EVAL-I-01 | `9a707dd` / working-tree | Product policy parser, explicit checker flag, approved input validation, docs and four-language description | 9 policy tests and 79 existing package tests PASS; Product pyflakes, docs weight and diff checks PASS. Runner/checker/readiness still pending |
| 2026-10-03 EVAL-I-02 | `36c6169` / working-tree | Derived contract, self-contained report shape and pure deterministic recomputation; no execution or schema migration | 8 arithmetic/report tests PASS, including 95/100 boundary, critical/prohibited override, both metrics, duplicates, fake summaries and mutable readbacks. Git/acceptance join and readiness pending |
| 2026-10-03 EVAL-I-03 | `8504ffe` / working-tree | Read-only eval CLI, two direct required evidence joins, exact source/implementation blobs and existing H1/H2 guards; filled runbook scaffold | 9 real temporary-Git evidence tests PASS; pyflakes and diff check PASS. Test dependencies, npm ci and Chromium setup completed. Mandatory readiness and full fixed-candidate verification pending |
| 2026-10-03 EVAL-I-04 | `b5e9bd3` / working-tree | Common eval adoption join before Product/UI early returns; >=0.60 explicit applicability, source/argv/hash/node/dependency guards | 8 readiness tests and 31 existing PLAN/source-join tests PASS; pyflakes/diff PASS. Legacy absent markers retained. Full suite and independent review pending |
| 2026-10-03 EVAL-I-05 candidate | `91d8205` / working-tree | 0.60.0 package/VERSION/lockfile/RUNBOOK and four-language badges/history/descriptions reconciled; index refreshed | 60 skill/version contract tests PASS after keeping the Harness core under its existing 3600-word limit via reference routing. Skill spec, full pyflakes and diff checks PASS. Independent review and complete suite pending |
| 2026-10-03 EVAL-I-01 repair | `065b365` / working-tree | Parent reproduced a policy inside the approval-excluded block: lowering its rate preserved the package digest and passed the complete package checker. Parser now rejects every overlap and malformed active approval boundary | 11 policy tests PASS, including a complete approved-package regression and non-overlapping control. Opus review A1 timed out at 900 seconds with no verdict; captured PID 35500 was confirmed exited. Logs retained; no fallback or review PASS |
| 2026-10-03 EVAL-I-04 repair | `e2442a8` / working-tree | Parent reproduced a relative checker path accepted against parent cwd while the gate would execute against consumer cwd. Require absolute installed checker paths for both gates | 9 readiness tests PASS with both relative-path substitution regressions. Refined independent review into Product/arithmetic and Git/readiness surfaces on the next clean SHA; the two confirmed authority bypasses justify bounded separate assignments. Full suite pending |
| 2026-10-03 A2 review / EVAL-I-01 structural repair | `0498df8` / working-tree | Opus Product review returned high approval-exclusion bypass plus nonblocking content/owner/import findings; Gate review returned two medium readiness bypasses. Parent independently reproduced hidden-start digest bypass. Shared raw exclusion span now drives digest removal and eval coverage without changing historical digest bytes | 12 policy tests with raw-marker/line-ending matrix and 79 existing complete-package tests PASS. Both reviews completed on Opus 5.5; effort telemetry unavailable. Old Claude processes exited (gate PID 15824 was reused by an unrelated node process, left alone). No fallback. Follow-up fixes and fresh exact-SHA review pending |

The existing large source-join module retains Product/UI authority. Eval source,
command and graph validation are isolated in one new module under 500 lines;
the public wrapper joins both checks, so early returns cannot bypass eval.

2026-10-03 A3 review / EVAL-I-01 coordinate repair, baseline `7246883`,
working-tree: Product review found a high raw/normalized-coordinate bypass and
medium double-normalization regression for repeated CR bytes. Gate review found
a medium legacy reader divergence. The same authority families recurred, so
this round requires structural matrices rather than isolated examples: one
normalization coordinate map, raw-span messages, 81 historical digest comparisons
and nine policy-prefix separators. All 14 policy tests PASS. Gate authority
selection/read safety and execution identity matrix are the next bounded repair.
A3 remains fix_required; no delivery PASS or availability fallback is claimed.

2026-10-03 EVAL-I-03 parser availability repair, baseline `9104dad`, working-tree:
missing installed sibling parser returns a clear join/CLI failure; restore the
import path after loader errors. 9 report tests, 13 readiness tests and 10
real-Git/CLI tests PASS. Pyflakes caught a shadowed test helper in the host matrix;
renamed its local variable and reran static checks successfully. Review pending.

2026-10-03 EVAL-I-04 execution repair, baseline `a31bc3a`, working-tree:
both acceptance gates require explicit host isolation, preserving the installed
checker and Git checkout in one namespace. Container, missing and malformed
execution policies fail. All 12 readiness tests PASS. Template, reference and
four README descriptions agree; stale template validator prose corrected.

2026-10-03 EVAL-I-04 adoption repair, baseline `8126610`, working-tree:
inspect every candidate PRD for opt-in policy before canonical source joins.
Extra reference rows cannot turn evaluation off; ambiguous policies fail closed.
All 11 readiness tests PASS, with 0.37/0.59/0.60 and plan-only coverage, legacy
kind aliases and common-wrapper checks. Fresh review and full suites pending.

2026-10-03 EVAL-I-01 content repair, baseline `be4f36e`, working-tree:
approved data/argv accepts JSON, markup, TODO task text and long prompts;
decision prose retains placeholder checks. Non-string owners return validation
errors. All 13 policy tests PASS. Fresh review and broad suites pending.

The large existing Product checker remains the package validation entrypoint;
eval parsing and input validation live in their own module (under 500 lines).
No new responsibility is added to its existing table/approval code.

## Handoff

2026-10-03 EVAL-I-05 local verification, exact clean candidate
`882dda69b58c615683f2a96449508beb509029c2` on
`codex/eval-contract-research`: A13's two native reviewers returned fresh
code/security PASS across all 44 changed paths, Product 11 and Harness 33.
Both have empty findings, exclusions and coverage gaps. Requested/configured
binding is GPT-6.1-Sol/xhigh/read-only; independent provider/model/effort telemetry
is unobserved. No fallback. Earlier failed, timed-out and passing receipts retain
their original identities; none was repinned. Commit `77bfaad0` records the
source-binding test repair; `882dda69` the translation wrapping repair.

Skill spec, full six-skill pyflakes, documentation weight and diff checks PASS
at this candidate. Harness core remains 3594 words under its 3600-word limit.
All required regression commands ran from the repository root and exited 0:

| Suite | Tests | Seconds | Declared skips |
| --- | ---: | ---: | --- |
| Harness | 1480 | 2778.811 | 20: platform/symlink limitations and the gated golden path |
| Explicit golden path | 1 | 4.082 | None; `HARNESS_GOLDEN_PATH=1` |
| Product Definition | 279 | 38.539 | None |
| UI Design | 311 | 94.104 | None; required Chromium browser checks enabled |
| Design System | 120 | 1.722 | 4 Windows/POSIX/symlink limitations |
| Product Activation | 56 | 0.659 | None |
| SEO Review | 21 | 0.426 | None |

This is Windows verification, not a Linux/macOS CI result. The explicit golden
run satisfies the Harness suite's one opt-in skip; remaining unavailable
platform cases retain their reasons. Browser prerequisites were installed,
`PDH_REQUIRE_BROWSER_TESTS=1` and `PLAYWRIGHT_MODULE` names this checkout's
Playwright 1.62.1. Each check had an actual finite deadline and Windows job
cleanup. The second Harness run finished under its 5400-second deadline.
Captured test roots exited. Parent rechecked clean HEAD and all reviewed source
hashes after every suite and at receipt reconciliation.

Review packets, separate code verdicts, raw logs, process receipts and
`final-882dda69-verification.json` stay in the checkout-external task directory
`C:/Users/mps19/.codex/work/eval-integration-e493a8f9c14747c4a8e75e833cb6b5d4/`.
The completion child changes only this Epic and `docs/DOCUMENTS.md`; code and
test evidence remains bound to candidate C above, not relabeled as the child.
No source, fixture or version change follows the verified candidate.

Document audit: applicable eval policy/acceptance references, templates,
four-language descriptions, version surfaces, task outcomes and index agree.
Consumer PRD/architecture, design package, PLAN/RUN and generated tasks view
are not applicable to this direct source task. No bilingual backfill is needed.
Canonical artifacts remain tracked; dependencies, caches and `.env` remain
ignored by existing rules. No new ignore class or credential read.

Installed Harness remains 0.59.0, with PROJECT_AGENTS template SHA-256
`0d5064d94c0072ad2d1f06f3b516dab328d425be79454df10b50ce6f44b2470e`.
Shared entry/checkpoint/handoff/authorization rules are current by meaning.
The source's main-only and UI2/conditionalDS3 rules intentionally differ from
that installation's dual-branch and UI3/mandatoryDS4 line. A safe cross-line
merge is unknown; `AGENTS.md` stays intact. Document-sync remains
`review_required` for unknown loaded identity and baseline. The affected
sources received semantic review; this does not invent a loaded identity or
turn document inventory into approval. Other indexed Epics retain their history.

Next owner action: separately authorize publication, exact-SHA main promotion,
release/tag and installer execution if this candidate is selected. No push,
promotion, tag, local skill update, branch deletion or worktree removal occurred.

2026-10-03 EVAL-I-05 translation structure repair, baseline
`77bfaad0a5b992e8e4ea7193dac2abdeea482839`, working-tree:
independent native assessment reproduced only physical-line count differences
in the eval readiness paragraph: English has 62 nonblank lines in its section,
the two Chinese copies 59 and Spanish 61. All headings, fence and bullet counts
match. Add three line breaks to each Chinese copy and one to Spanish, retaining
all words and decisions. All five README structure tests PASS in 0.023 seconds;
diff checks PASS. Commit `77bfaad0` records the separate seven-test source-binding
repair. No new ignore class, product UI or runtime behavior changed. A fresh
44-path code/security review and full required verification remain pending.

2026-10-03 A12 review / EVAL-I-04 source-binding test repair, baseline
`7298f182dcfcb36e921d47f8564f83192ca13999`, working-tree:
the two native reviewers returned fresh code/security PASS on all 43 changed
paths, with empty findings, exclusions and coverage gaps. They used the
configured GPT-6.1-Sol/xhigh read-only binding; independent provider/model/effort
telemetry remains unobserved. No fallback. The required Harness suite reached
its actual 2700-second deadline near the final write-path tests. Its process
tree exited; the timeout and four observed failing subtests remain external
evidence, not a complete suite result. Three failures concern translated README
structure. The other exposed a stale public-API test expectation. Independent
assessment confirmed the immutable resolver still reads the frozen Git blob,
while public validation must reject divergent working PRD authority before
interpreting marker presence or absence. The test now proves unchanged public
success, committed resolver success after branch/working-byte drift, and the
exact public authority rejection. No production guard changed. All seven
immutable-source tests PASS in 3.757 seconds. README repair, new exact-SHA
review and complete required suites remain pending. The next full Harness
deadline will allow the observed runtime without omitting tests.

2026-10-03 EVAL-I-03 protected tree repair, baseline `e11f8ede`, working-tree:
the parent reproduced Gate/A11's clean H2 mode-only PASS with an unchanged
runner blob. Keep regular captured H2 blob checks, and replace separate H1
content checks with one literal-path tree diff over every protected path.
No evidence or coordination exemption applies to those paths; mode, type,
content and existence must remain equal. Git errors fail closed. The four
READMEs and acceptance reference agree. All 17 real-Git/CLI tests PASS in
192.821 seconds, including unchanged direct-runner controls, both executable
bit directions with identical blobs, a bracket filename, four artifact
change/introduction classes, and protected-diff exit/timeout failures.
Focused pyflakes, documentation weight and diff checks PASS. Commit `e11f8ede`
records the separate exclusion scan repair and its 23 policy tests. Fresh
whole-candidate native code/security review and complete suites remain.

2026-10-03 A11 native review / EVAL-I-01 exclusion scan repair, baseline
`10079881`, working-tree: Policy, Workflow and Report code/security PASS;
Gate returns fix_required for a mode-only change on a protected artifact,
and Digest for repeated whitespace scans in the new unapproved policy route.
All five exact-SHA scope receipts cover the 43 changed paths. The parent
reproduced the blank-prefix scan exceeding a three-second child deadline;
the child was terminated and waited. Search LF-delimited marker lines once,
then retain the historical preceding blank span and trailing Unicode whitespace.
All 23 policy tests PASS in 20.648 seconds, including 5,000 seeded first-span
comparisons and million-line absent/quoted/hidden marker controls under a
60-second child deadline. Existing digest and overlap matrices still pass.
The first test run exposed an active-end fixture mistake; hiding both approval
markers corrected the fixture, without relaxing parser checks. Focused pyflakes
and diff checks PASS. Mode repair, fresh whole
candidate review and broad verification remain required.

2026-10-03 EVAL-I-03 protected candidate repair, baseline `49059be9`,
working-tree: the parent reproduced Gate/A10 in four real temporary Git
checkouts. Runner, grader, lockfile and runbook each passed valid controls and
incorrectly passed after H1 changes plus updated report/register hashes.
The checker now binds frozen PRD/contracts, approved inputs and delivered
artifacts to regular blobs at H1 independently of evidence exemptions. H2
byte, ancestry and clean-status checks remain. Overlapping reads retain their
consistency guard. Real-Git regressions cover all four artifact classes for
changed and newly introduced files, with positive controls for unchanged bytes.
The reference and four READMEs agree. All 15 real-Git/CLI tests PASS in 211.749
seconds; focused pyflakes and diff checks PASS. Fresh review and broad
verification are pending.

2026-10-03 EVAL-I-02 resource repair, baseline `06e076f1`, working-tree:
Report/A10 confirmed another full population scan per slice and a trial rescan
for `trial_pass_rate`. Aggregate passing repeats per case, then visit each
declared membership once for slice case/pass/total counters. Overall totals
stay independent of overlap. The 5,000-case/slice regression measures membership
visits deterministically, checks both metrics, overlapping membership, a failing
repeat and slice threshold rejection. Encoded inputs and reports fit 16 MiB.
All 26 report tests PASS in 0.690 seconds; focused pyflakes and diff checks PASS.
H1 binding repair and fresh review remain.

2026-10-03 A10 native review / EVAL-I-01 resource repair, baseline `450ec3f4`,
working-tree: five disjoint scopes cover all 43 changed paths. Workflow and
Digest code/security PASS; Policy, Report and Gate return fix_required for
quadratic slice work and an H1 artifact/evidence overlap. Two native reviewers
use the effective GPT-6.1-Sol/xhigh binding; actual model/effort telemetry is
unobserved. A third spawn was rejected by the thread limit, so the two instances
returned separate scope receipts sequentially. No availability fallback or
parent review substitution occurred. Reports and logs stay outside the checkout.
The Product parser now counts each validated membership once, retaining the
approved minima and population limits. A deterministic visit-count regression
and a root-bound 50,000-case/slice control with an undersized variant have a
finite child deadline. All 21 policy tests PASS in 2.089 seconds; the root-bound
control and undersized variant both ran. Focused pyflakes and diff checks PASS.
Report and H1 repairs,
fresh candidate review and broad verification remain required.

2026-10-03 EVAL-I-01 input lifecycle repair, baseline `40c59023`, working-tree:
approved inputs use new immutable repository paths outside Markdown staging;
the existing task records exact creation authority before writing. Reuse valid
grants, never overwrite live/historical input bytes, keep paths stable through
publication, include prepared paths/hashes/authority in the publication list,
and retain superseded inputs outside core-document archive moves. A contract
test covers both policy and lifecycle references. This closes A9's remaining
low workflow gap without changing runtime schemas or introducing cleanup.
The owner replaced the reviewer policy during this repair: subsequent reviews
use native reviewer / GPT-6.1-Sol / xhigh / read-only. This is a policy change,
not a provider fallback; prior Opus attempts remain immutable evidence.
All 98 Product skill-contract tests PASS. Fresh exact-SHA native review and
full suites pending.

2026-10-03 A9 workflow call-family repair, baseline `58cb3d91`, working-tree:
Report and Gate returned code/security PASS with no findings; Workflow returned
PASS with two low documentation findings. Core timed out at 901 seconds without
a verdict; PID 10196 exited, cleanup succeeded, no fallback. All attempts remain
retained. The entire new-package call family now includes root and explicit
policy mode, including AI, completeness and staging references. A contract
regression guards root on every policy-mode line and both pre-publication paths.
The existing large Product contract-test module keeps one responsibility; these
checks extend its documented-flow boundary rather than adding another module.
All 97 Product skill-contract tests PASS. Input lifecycle repair and fresh review pending;
the next Core review splits policy/tests from digest/fixture paths at the same
new candidate, preserving full union coverage without increasing the deadline.

2026-10-03 EVAL-I-01 workflow invocation repair, baseline `fbb5a062`,
working-tree: new-package approval, final publication checklist and reference
examples now all require both repository root and the explicit eval-policy
flag. The root enables approved input byte checks; rootless API inspection
remains shape-only and cannot complete this flow. Legacy omissions keep their
existing API semantics. Four READMEs agree. This closes both A8 workflow notes
through documented invocation changes, without expanding the parser API.
Diff check PASS; package and static checks follow on the frozen candidate.

2026-10-03 EVAL-I-03 Git timeout diagnostic repair, baseline `ed47747d`,
working-tree: subprocess failures at the eval CLI boundary now produce JSON
FAIL and exit 1. A passing real-Git control and independently injected entry
and final-status timeouts cover both ends. This addresses A8's low diagnostic
note without relaxing any Git guard. All 13 real-Git/CLI tests PASS, including
the actual clean H1/H2 control. Fresh review and broad suite remain pending.

2026-10-03 EVAL-I-04 current fixture repair, baseline `ff121892`,
working-tree: the synthetic ordinary-product declaration now uses the required
JSON fence before approval hashing. A direct factory/parser control rejects the
absent declaration and accepts the generated exemption. This addresses A8's
reachable current new-run/golden-path fixture failure. All 21 eval readiness
tests complete (20 PASS, one POSIX-only skip); 10 new-run and 13 tasks-view tests
PASS. Both real CLI golden spines PASS with required browser prerequisites.
The optional FlashX test worker failed at launch with 429 and produced no
evidence; its stopped attempt is retained, with no fallback. Parent performed
these operational checks. Mandatory independent review stays on Opus.

2026-10-03 EVAL-I-02 fixture isolation repair, baseline `506cb564`,
working-tree: Product fixture imports now restore the exact prior sys.path.
A fresh interpreter verifies Harness's same-named skill-contract test still
resolves to Harness after importing eval fixtures. This addresses A8's low
test-order note without changing any production boundary. All 25 report tests
PASS, including the fresh-process namespace assertion. Fresh review pending.

2026-10-03 EVAL-I-02 report intake refinement, baseline `b3ee4492`,
working-tree: A8 repeated the missing independent rejection-test family.
A fixed-input matrix now mutates one report field at a time, without changing
expected purpose, candidate, hashes, execution or artifacts. It covers report
identity/context, provenance, command receipts, trial fields and dependency
readbacks with passing controls. Existing isolated arithmetic/deadline/budget
tests remain. All 24 report tests PASS. Fresh review and full suite pending.

2026-10-03 A8 review / EVAL-I-01 visibility refinement, baseline `321c0999`,
working-tree: Core review returned a medium Markdown visibility bypass;
Report review required independent identity negatives; Gate review found an
unfenced current fixture. Workflow source review passed with two low invocation
notes. All four Opus 5.5 read-only review processes exited; no fallback. Gate's
security PASS does not override its code finding. All receipts are retained.
The parent reproduced nine accepted invisible-policy cases. The parser now
rejects Python-only line separators before the body, non-ASCII blank lines in
the prefix and Unicode padding around fences. JSON string content stays intact;
LF/CRLF/CR and ASCII blank controls remain valid. Historical digest exclusion
checks retain their precedence and bytes. This follows CommonMark's physical
line and blank-line definitions: https://spec.commonmark.org/0.31.2/#characters-and-lines.
All 19 Product policy tests PASS, including the full separator/blank/padding
matrix and existing digest/Unicode controls. Broad suites and fresh review
remain pending.

2026-10-03 EVAL-I-02 timestamp diagnostic repair, baseline `289b2b5b`,
working-tree: UTC conversion outside datetime's range raises a typed policy
failure. Unit and real-Git CLI controls cover both range ends and both report
purposes, preserving a JSON FAIL with exit 1 instead of a traceback. All 20
report tests and 12 real-Git/CLI tests PASS. This closes A7's remaining low
report diagnostic; fresh review and broad verification remain pending.

2026-10-03 EVAL-I-01 TEST authority repair, baseline `7f4be377`, working-tree:
join only the single active canonical Test Obligations section and its real
header/separator/rows. Earlier prose, subheadings and arbitrary six-cell rows
cannot override Required-Yes or AI-EVALUATION. Duplicate sections/tables/IDs and
malformed rows fail closed. All 18 policy tests and 79 existing complete-package
tests PASS. Canonical TEST ID/Required case handling and unrelated TEST IDs stay
consistent with the Product checker.

2026-10-03 EVAL-I-01 policy visibility repair, baseline `f0fefbea`, working-tree:
require a JSON code fence so rendered approval cannot hide policy fields inside
HTML comments. Read the body from exact raw offsets, retaining Unicode in valid
JSON strings. The policy reference and four README descriptions agree. All 17
policy tests PASS, including raw-offset/digest and LF/CRLF Unicode controls.

2026-10-03 EVAL-I-01 malformed-input diagnostic repair, baseline `ad48d708`,
working-tree: oversized JSON integers become typed policy errors, existing
duplicate-key diagnostics stay intact, and control characters in artifact paths
fail before filesystem calls. Generic malformed input cannot escape validation
as plain ValueError/RecursionError. All 16 policy tests PASS, including the
actual Product CLI returning exit 1 with a typed message and no traceback.

2026-10-03 EVAL-I-01 JSONL repair, baseline `4fd43240`, working-tree:
record boundaries use LF/CRLF, retaining U+0085/U+2028/U+2029 inside approved
prompts. The nine-case matrix accepts those strings unchanged and rejects the
same characters used between records. All 15 policy tests PASS. This repairs
the existing JSONL contract without changing its schema or approval bytes.

2026-10-03 A6/A7 review / EVAL-I-02 report regression repair, baseline
`cb8c373c`, working-tree: A6 Gate code/security PASS on its 21 paths; A6 Product
timed out at 900 seconds with no verdict. Its captured process exited and logs
remain. A7 split the remaining scope: Product code/security PASS on 9 paths
with four low findings, and report code/security fix_required on 11 paths for
missing discriminating regressions. Both completed on Opus 5.5, requested
xhigh, Read/Glob/Grep only, no denials or fallback. Named effort is unobserved;
numeric 40 is recorded. The three exact-SHA scopes cover all 41 changed paths.
The report repair adds valid-boundary and isolated-rejection controls for both
budgets, cost totals, currencies, separate deadline/freshness, future dates,
readback windows, retained failures, both slice metrics and subject identity.
All 19 report tests PASS. Production report code is unchanged. Product parser
findings will receive separate bounded commits; timestamp overflow remains a
low fail-closed diagnostic. Fresh candidate review and broad suites are pending.

2026-10-03 A5 review / EVAL-I-05 current-fixture repair, baseline `0b0d4f5f`,
working-tree: both 20-path Product and 16-path Gate code/security reviews PASS
at exact `0b0d4f5f8eae26696c658f4cd361c502bf4979bf`, no security findings,
Opus 5.5 / requested xhigh, read-only, no denials or fallback. Actual named
effort is unobserved; the Gate runtime reports numeric 40. Both processes exited.
Parent then found nine new-RUN fixture failures: fresh 0.60 package inputs lacked
explicit applicability. Seed a reasoned deterministic exemption before approval
hashing and before the current synthetic HiFi publication, without mocking
production checkers or changing gate requirements. New RUN and tasks-view
suites PASS; both CLI golden paths PASS. The shared fixture factory is 1545
lines and retains its one responsibility: synthetic test data construction.
These two small data helpers do not warrant a second fixture system.
Fresh security review on the resulting SHA and the full suite remain pending.

2026-10-03 A4 review / EVAL-I-04 authority refinement, baseline `2de7a56e`,
working-tree: Product code/security PASS, but Gate review returned fix_required
for a 0.37-pinned frozen-Git versus working-tree absence bypass. Both completed
on Opus 5.5 with read-only tools, no denials or fallback; captured processes
exited. This repeated family required a new bounded structural refinement:
prove one safe byte sequence against the frozen hash and any regular Git blob
before interpreting presence or absence. Reuse the hardened metadata/hash
proof; do not read an unbounded historical blob or skip unavailable authority.
The 96-case real-Git matrix covers both marker states, four pin/plan-only modes,
three source shapes and both declared-hash choices through both public joins.
19 readiness tests ran: 18 PASS, one POSIX variant skipped. A separate exact
committed-policy control passed across all four modes with complete gates.
Focused pyflakes/diff PASS. Four READMEs and reference agree. Fresh exact-SHA
review and broad suites remain required. A4's Product low integer-overflow
diagnostic note is nonblocking and retained; it fails closed.

2026-10-03 EVAL-I-03 parser diagnostic repair, baseline `1b6de68d`,
working-tree: missing, unreadable or syntactically broken installed sibling
parser returns an explicit validation/JSON failure in loader, common join and
CLI. The import path is restored after failure. All eval suites ran 37 tests:
36 PASS, one POSIX variant skipped on Windows. Product/Harness pyflakes PASS.
This completes A3's accepted structural repair scope; fresh A4 review must
inspect the full coordinate, authority-read and program-identity matrices,
including every surrounding consumer. No earlier review becomes a PASS.

2026-10-03 EVAL-I-04 interpreter authority repair, baseline `efde904`,
working-tree: both acceptance gates require the absolute interpreter resolved
to readiness's observed Python, as well as the absolute installed checker and
host isolation. Bare names, project-relative interpreters and other absolute
interpreters fail. The full readiness matrix ran 17 tests: 16 PASS, one POSIX
variant skipped on Windows. Template and four-language descriptions agree.
Fresh structural review and broad verification remain pending.

2026-10-03 EVAL-I-04 structural authority repair, baseline `78f6c42`,
working-tree: unreadable, linked, oversized or secret-like PRD authority now
fails closed before legacy Product/UI early returns. A safe read is required
to observe marker absence; no permissive fallback opens unsafe sources.
Non-frozen reference-only archive rows are ignored. The 0.37/0.59/0.60 and
plan-only matrix ran 16 tests: 15 PASS, one POSIX symlink variant skipped on
Windows; read-failure coverage ran on every version. Both A3 reviews remain
fix_required. Execution identity and parser diagnostics are still pending.

Local source integration is verified at the candidate above. Release, tag,
publication and local skill update remain unperformed.
