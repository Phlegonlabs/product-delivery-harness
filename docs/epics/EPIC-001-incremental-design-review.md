# EPIC-001: Incremental design and interactive review

Status: in_progress

## Problem And Baseline

An enhancement could trigger a fresh all-screen design pass even though only one
feature changed. Reviewer pages also mixed product content with review metadata,
showed token values without useful specimens, and left some controls inert.

Baseline: Harness 0.47.0, `3f6d7d2ebad2899fe4045b99a2bb4f9bfa19a12a`.
This is internal skill maintenance (`HARNESS`), not a new product PRD.

## Accepted Scope

On 2026-09-20 the owner requested usable Wireframe/HiFi review, then clarified:
enhancements add or change only affected pages and necessary connecting controls.
Existing layout, content, style and identities stay unchanged outside that scope.
Complete artifact coverage is not permission to redesign the complete product.

Record small fixes in their existing Epic or direct task. Create an Epic for an
independent accepted outcome, not for each edit or failed test. Apply this rule
across Product Definition, UI authoring, compilation and delivery.

The owner requested local commits, branch push, PR and merge for the skill bundle.
The exact main-promotion gate still applies. No force push, branch/worktree cleanup,
website deployment or overwrite of the original website is included.

## Acceptance And Dependencies

| Requirement | Expected result | Verification |
| --- | --- | --- |
| HARNESS / incremental scope | Add affected Wireframe and HiFi pages; retain unrelated screens and the existing direction | Contract tests, preservation checks and exact-head review |
| HARNESS / reviewer | Left page/target controls, one product screen, real style specimens and separate state coverage | Wireframe and HiFi contract/runtime suites |
| HARNESS / interactions | Editable local controls retain input and perform declared actions | Search, clear, language, Enter, focus and overlay regressions |
| HARNESS / history | Epic selection and per-change history cover small fixes without duplicating PRD/RUN | Template and cross-skill contract tests |
| HARNESS / release | Required suites, golden path and fixed-SHA security review pass before publication | Repository verification and PR checks |

## Document Impact

Canonical changes are under `skills/`, plus this record and the four READMEs.
The shared bounded-enhancement rule owns Epic selection. UI guidance owns the
affected-screen design scope; the compiler retains unrelated entries. Existing
product, approval, authorization and release gates remain in place.

## Change Log

| Change | Reason and scope | Commit / evidence | Result |
| --- | --- | --- | --- |
| Wireframe composition | Explicit geometry, editable fields and preserved reviewer state | `496f70f`; 75 focused tests | Superseded by the repair below; not browser evidence |
| Wireframe search/overlay repair | Review found inert search and guaranteed wide-dialog overflow | `bfa0d8e`; 79 focused tests | Review found three validator defects; repaired below |
| Wireframe input validation | Reject legacy search, malformed references and sentinel item languages | `1415a46`; 82 focused tests | Source/runtime checks pass; unified exact-head review pending |
| HiFi reviewer | Target/surface switching, specimens and source-bound evidence | `7c67abf`; initial 22 contract and 4 runtime tests | Review found four blockers; repaired below |
| HiFi evidence validation | Validate actual control variants, selectable controls and closed typed evidence rows | `b0d3e9a`; 26 contract and 4 runtime tests | Integrated; unified exact-head review pending |
| Incremental scope and Epic rules | Owner reported repeated full UI redraws | `d73b0ba`; 60 skill contract tests | Guidance and cross-skill regression pass; preserved-surface comparison remains a required review step, not an automated semantic proof |
| Release preparation | Renewed reviewer contracts are a breaking skill-bundle change | 0.48.0 version pins and four-language documentation | Complete candidate checks and main promotion pending |
| Unified review repair | Review of `7273a44` found product CSS leakage, missing anchor specimens, text fields impersonating selection, malformed group crashes and unfocusable headings | Bounded repair; 29 HiFi contract and 4 runtime tests | Removed product defaults from reviewer CSS, hardened control/evidence checks and added focus-semantic regressions; full candidate checks pending |
| Workflow forward-test | Independently plan Saved Articles addition, then a post-release contrast fix | Read-only skill evaluation at `7273a44` | New feature gets its own Epic and only UI-003/UI-004 changes; Home/Search stay preserved; contrast fix appends to the same Epic |
| Cross-skill regression repair | Full suite found stale state lists and old hybrid reviewer fixture data | `5744457`: 1,156 Harness tests, 5 failures, 16 platform/opt-in skips; sibling suites 573 tests passed with 3 platform skips | Updated state lists and two hash-bound hybrid pages with real navigation; 16 strict-authority, 2 hybrid and 1 golden-path tests pass. Validators and negative assertions unchanged; full rerun pending |

## Results And Remaining Work

PR #115's current-page review found a second blocker at `9d017fa`: the validator
looked for the navigation marker on the anchor instead of its parent chain. The
owner authorized a bounded repair and push, with a new exact-SHA merge decision
afterward. UI impact is `none`: only validation and tests change, not product HTML.
The validator now uses the same sidebar anchor collection for page coverage and
current-page checks. Three new tests cover both pages, five missing/invalid values,
markers on parents/other links/outside navigation, and valid nested links. Before
the fix, 16 negative subcases failed; afterward all 32 reviewer tests passed.
Full new-candidate verification and independent review remain pending. This is a
small fix within this Epic; previous CI PASS does not cover the repaired candidate.

At `a5b3217`, the local full suite passed (1,156 Harness tests with 16 skips,
573 sibling tests with 3 skips, and the opt-in golden path). PR #115 CI then found
one UI test fixture without the canvas measurement API. Its multiline `node -e`
launcher had hidden the failure on Windows. The bounded repair uses stdin, models
canvas width, rejects an incorrect width and asserts that execution reaches the
final check. Product runtime and validator code are unchanged. New exact-head CI
and reviews are required; the previous results remain historical.

PR: https://github.com/Phlegonlabs/product-delivery-harness/pull/115.
The canonical installer updated local skills and retained the previous seven
copies in `~/.agents/skill-backups/product-delivery-harness/20260920-125038`.
Installation is not release approval, and a fresh host session is needed to load it.

The GLM attempt failed after partial work; the owner explicitly switched to local
Codex. Existing partial work and failed reviews were retained. No old human receipt
was rewritten and no new human approval was fabricated.

The separate website worktree is a draft, not part of this skill release. Its
whole-regeneration candidate is on hold under the owner's incremental scope rule.
Its original checkout was not overwritten. Six-topic content, copy reconciliation,
navigation coverage and browser/visual verification remain unresolved there.

Skill release gates and exact-candidate main authorization remain pending. Browser
policy prevents claiming a rendered website review; source/runtime tests are not
visual approval. Each repair and release result must be recorded here before closeout.

The initial unified security review found no security vulnerability, but its result
is historical/blocked because the functional repairs changed the checkout. It does
not count as security approval for the repaired candidate. Document-sync reported
unknown loaded identity and first observation; old skill-name references are
intentional retirement/history guidance, not live installation targets.

## Readable annotations and token coverage — 2026-09-21

The owner approved local modification and verification on
`enhancement-readable-wireframes-token-coverage`, cut from observed remote main
`844701109e5bda254c3e238a6e8f3bedb775482a` (0.49.0). This is a bounded follow-up
to the reviewer outcome in this Epic. No new product PRD or managed RUN is needed.
UI impact: both, confined to the shared reviewer templates and derived preview.
The owner chose the existing grayscale direction, annotations as the formal
wireframe view, readable action destinations, and complete Wireframe/HiFi token
examples. Product flows, shipping copy, stack and existing approvals are retained.

Write scope: UI template/runtime/validator tests and guidance, the compiler's
derived preview and tests, this Epic and all four README descriptions. Local
branch creation, source edits, synthetic fixtures and verification are authorized.
The initial grant excluded commits and publication. The owner subsequently asked
to commit, push and merge after verification. This authorizes candidate commits,
branch publication and PR preparation; exact-SHA main promotion still follows the
repository contract. The required post-push canonical install is part of publication.
Cleanup remains unauthorized.
Untracked root scripts and other branches/worktrees are preserved.

Acceptance: annotations visible initially; names and page/dialog/local-result
behavior readable; actual active-target spacing measured; prototype tokens and
used action variants have samples; HiFi token samples apply source-bound values;
formal shadow/motion/type samples remain safe and reduced-motion aware. Run
focused negative/runtime tests, synthetic browser checks, all repository-required
checks and golden path. At most two repairs per root-cause family; preserve failures.

Document-sync review: no product PRD/PLAN/RUN exists in this maintenance scope;
loaded skill identity remains unknown. Source rules and templates are inspected
directly, not claimed to be the session's loaded installed version. Existing Epic
history and retired pointers remain historical. Existing .gitignore covers Python
bytecode; logs and synthetic previews use a task-specific external temp directory.
No new ignored artifact class or untracking is needed.

First focused wave: 82 wireframe tests and 5 preview tests passed. HiFi had one
failure: its blanket media-query assertion also rejected reduced-motion support.
The repair permits only that preference query and retains the viewport-query ban.
Further verification is recorded below.

The first complete wave passed: Harness 1,156 (16 skips), Product Definition 217,
UI Design 208, Design System 99 (3 skips), Activation 56, SEO 16 and golden path 1.
The new destination test initially exposed Windows stdin encoding of the em dash;
it now uses explicit UTF-8 and its assertion is unchanged. Browser scripts also
needed UTF-8 output and isolated eval scope; original logs remain in the external
evidence folder. The browser renderer checks then passed at 390/768/1200, including
page, dialog and local feedback behavior, annotation keyboard toggling, token
application and reduced-motion suppression. These are synthetic Web checks only.

Final review repair: token consumers follow declared aliases and standard dimension
shorthands; unused alias cycles do not count as use. Browser CSS validation rejects
unrenderable values, motion specimens support keyboard focus, prototype samples
share the product font, and notes show content gaps as well as region dimensions.
The four existing default-view descriptions now agree with annotation-first behavior.
New negative/runtime tests cover these boundaries. Final verification follows.

The repaired UI suite passes all 210 tests. The final synthetic browser pass checks
390/768/1200 targets, named navigation, dialogs, local feedback, retained input,
34 prototype token samples and 16 HiFi samples. Reduced-motion samples stop moving.
Release 0.50.0 records the new required HiFi preview-property contract. Three atomic
commits separate wireframe behavior, token binding and release documentation. Full
fixed-candidate checks and inline code-security review are required before promotion;
evidence stays outside the checkout so its commit remains unchanged during review.

PR #117 review found two bounded validator gaps at 0465d22: raw CSS values were
compared with normalized applied values, and min-inline-size/max-block-size were
missing. Token observations now retain raw and computed pairs separately; logical
dimension families include both bounds. Negative tests reject missing or mismatched
applied values. Browser checks cover hex/rgb, rem/px and keyword/numeric weights.
All four README descriptions explain the evidence distinction. This is one repair
of the evidence-comparison cause and the second bounded alias-family repair.

Both Linux and Windows CI passed 0465d22. Its local full run encountered temporary
Windows parent-directory locks in 12 cases across three Harness suites; all three
suites passed unchanged when rerun after installation. Original logs are retained.
The repair creates a new SHA and requires new exact-candidate checks and review.
