# Motion, 3D And Reference Quality In UI Design

Status: complete
Committed on `codex/review-fixes` for the 0.55.0 release (`d0c3320e`, `2fb4b973`, `f094299c`); push, main promotion, tag and install follow under the owner's 2026-09-27 commit/push/merge instruction and are reported in the handoff.
Design workflow: enhancement
UI impact: none (skill guidance and one checker rule; no product UI)

## Scope And Accepted Outcome

The owner said Wireframe/HiFi output often lacks motion, Higgsfield media and template references, and asked to add Motion (motion.dev) and Three.js. The rules already allowed these, but every rule defaulted to deferral and gave no craft guidance. Make them the normal path inside the existing gates. No new gate, schema or approval.

Owner decisions (2026-09-27 conversation):

- HiFi media stays embedded as `data:`. A sibling resources folder is not part of this change.
- When the owner states no motion posture, propose one from what each page actually shows.
- A library that cannot run inside HiFi is marked during the process, not exempted in the checker.
- Work continues on `codex/review-fixes`.
- Commit, push and PR merge authorized by the owner after implementation.

| Requirement | Acceptance |
| --- | --- |
| MQ-1 | Option library lists Motion (JS and React) and Three.js / React Three Fiber with fit, avoid, license and cost, from inspected sources. |
| MQ-2 | Motion router has a lowest-route ladder: CSS/WAAPI, Motion, GSAP, Three.js; Higgsfield for generated media, including GLB for Three.js. Libraries need the approved stack. |
| MQ-3 | Silent owner gets a content-based motion proposal; provider use, regions and cost limit are asked once in intake; unanswered means unauthorized. |
| MQ-4 | Direction studies play proposed or selected expressive landing/portfolio motion live. Authorized provider rows generate after direction selection. |
| MQ-5 | HiFi embedding limits: short compressed `data:` clips with poster; libraries that fail the offline scan use a deterministic approximation marked for implementation verification; never obfuscate library code. |
| MQ-6 | H6 judges motion craft (tokens, rhythm, interruption, no layout shift, reduced-motion meaning) as repair findings. |
| MQ-7 | Confirmed references keep a capture with hash; adapted template code records source, license and changes. |
| MQ-8 | Checker treats `Motion` and `Three.js` as code-only routes (no media asset required); regression test covers it. |
| MQ-9 | Four README descriptions updated. |

## Baseline

Observed 2026-09-27: repository `product-delivery-harness`, branch `codex/review-fixes`, HEAD `f904183c` (two commits past the session-start snapshot `27ea4979`: `9c281836`, `f904183c`, both Epic/index docs from the review-fix work). Working tree clean at entry.

Found during research: `check_ui_design_contract.py` treated any route other than `css-waapi`, `gsap`, `native-framework` as a provider, so a `Motion` or `Three.js` route would have required a generated asset and blocked Visual Approval. The offline surface scan (`NETWORK_SCRIPT_RE` in `check_wireframe_html.py`) rejects inlined code containing `fetch`, `Worker` or `import`; Three.js source contains `fetch`, which is why MQ-5 routes it to an approximation.

Sources inspected 2026-09-27: motion.dev quick-start, React docs and examples; github.com/mrdoob/three.js; r3f.docs.pmnd.rs introduction; gsap.com/showcase; threejs.org/examples. The three.js manual page did not render and was not used.

## Change Log

### 2026-09-27 — working-tree

Paths: option-library `motion.md` and `sources.md`; `ui-design-builder` `SKILL.md`, `motion-and-media-routing.md`, `ui-design-pass.md`, `ui-design-intake.md`, `ui-grading-rubric.md`, `design-reference-guide.md`, `output-contract.md`, `WIREFRAMES.template.html` (route placeholder only), `check_ui_design_contract.py`, `test_ui_design_contract.py`; four READMEs.

Scoped diff fingerprint (`git diff -- skills README*.md | sha256sum`, before Epic/index edits): `288dd7b140af14c0f2cef32c59ec4cea8b3fb704844d6e2cf8a802305114ac93`.

Verification (from repository root, `PDH_REQUIRE_BROWSER_TESTS=1`):

- New test `test_code_motion_routes_need_no_media_asset` fails on the HEAD checker (Motion, Three.js) and passes with the change.
- Skill spec, pyflakes, `git diff --check`: passed. Docs weight: ui-design-builder +888 words vs v0.54.5 (this change about +770).
- UI Design 293 OK; Product Definition 240 OK; Design System Compiler 116 OK (4 skipped); Product Activation 56 OK; SEO Growth Review 21 OK.
- Harness: 1,318 tests, 1 failure, 16 skipped (1,933 s). The failure was `test_reference_library` pinning the old SKILL phrase `CSS/WAAPI and GSAP routes`; fixed in `f094299c`, then `test_reference_library`, `test_skill_contract` and `test_cross_skill_pipeline` rerun OK on final bytes. Golden path: 1 OK.
- Later edits (enhancement-recommendations route list, router markers in `test_skill_contract`, 0.55.0 history lines) were followed by a full UI rerun: 293 OK. CI runs the full set on the pushed SHA before main moves.
- Handoff audit: repo `AGENTS.md` matches the source 0.55.0 `PROJECT_AGENTS.template.md`; installed copy is 0.54.5 (template sha256 `1677220a…`), so repo rules are ahead of installed, not stale. No AGENTS edit.

- Branch pushed; PR #128 CI on `a3da039d` failed only in review-fixes work (see that Epic). Owner chose to fix Linux and keep macOS non-blocking; fixes in `7db24835` and `221bac00`.
- Local skills installed from `a3da039d` with `install.ps1` after the first push (backup `~/.agents/skill-backups/product-delivery-harness/20260927-143326`); installed VERSION 0.55.0.

Remaining: a resources-folder option for larger HiFi media is deferred.
