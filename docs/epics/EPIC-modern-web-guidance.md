# EPIC-modern-web-guidance: pinned Modern Web Guidance for frontend authors

Status: in_progress (0.97.0 reviewed on branch `modern-web-guidance`, not yet published; pilot not started)
Design workflow: enhancement
UI impact: none (author rules, a binding row, a wrapper script and a PRD field; no product UI)

## Problem And Baseline

On 2026-11-20 the owner asked whether Google's Modern Web Guidance (MWG, https://github.com/GoogleChrome/modern-web-guidance-src) should join the suite. MWG is a skill plus an npm CLI (`modern-web-guidance`, Apache-2.0, stewarded by Chrome, Edge, Firefox and MDN). An agent searches about 210 guides and retrieves one before writing a web control, layout or script. Its own evals report Claude Code opus-5-5 at 57% to 88% and Codex gpt-6.1-sol at 54% to 82% on its own tasks and graders.

As shipped, it conflicts with this suite in five ways:
- Its skill and every guide call `npx modern-web-guidance@latest`, so content changes under a running round. Skill Bindings pin every bound skill by full-tree SHA-256.
- Telemetry is on by default. It sends the agent's search queries, guide IDs and agent name, and a query can carry product terms.
- Its tabs guide drops `aria-controls`, and its menu guide relies on `commandfor` and sets `aria-expanded` in a `toggle` listener. The HiFi output contract requires `data-product-*`, `aria-controls` and `aria-expanded` or `aria-selected` on menu, tab and disclosure buttons.
- Its fallback advice depends on a Baseline browser target. Our PRD had only free text ("target devices and browsers").
- Its SKILL.md says it is mandatory for every HTML, CSS and client JS task. Installed globally, it would trigger in every repository and every running round.

Baseline for the pilot: in the ten-repository sidecars of 2026-11-19, 623 of 1,293 interaction operations failed, 2,791 attempts in all. The evaluation said MWG aims at the largest class, focus failures ("product focus did not land on the control alone", 1,734 attempts). Split by target, that was wrong. 1,490 of them are at native size classes: ticketradar 603, ticketradar-en-app 549, hk-car-care 306 and jolvex-platform 32. Those pages are HiFi projections of native app screens, and the MWG rule covers web surfaces only. Web widths hold 244: agentkiosk 184 (23 of its 38 operations), jolvex-platform 48, ticketradar and ticketradar-en-app 6 each. The other web failures, in dilution-radar, hardwareprices and agentic-commons-site, are destinations that did not load or apply and missing controls. They come from the HiFi contract's wiring, not from platform knowledge. MWG mainly changes production code, which the matrix capture does not measure.

## Accepted Scope

Owner decision, 2026-11-20, in reply to the evaluation: "照這個方向做" (go this way) for the proposed 0.97.0:
- Do not install MWG globally. A project binds it in Skill Bindings with an exact version.
- Telemetry off. The HiFi output contract's markers win inside HiFi; MWG applies to how production code is built.
- The PRD's browser target becomes a Baseline level.
- Pilot on one consumer, compare interaction failures with the matrix capture, then decide on wider use.
- Do not copy guides into this repository. Do not make `legacy-scan` a gate.

Delivered in 0.97.0:
- `delivery-harness/scripts/modern_web_guidance.py` pins `modern-web-guidance@1.0.1` (registry tarball SHA-256 `713d3d34…38a3`, npm integrity `sha512-5ztUh5F1…`). It always sets `DISABLE_TELEMETRY=1` and `ENABLE_FILE_LOGGING=false` and runs only `search`, `list` and `retrieve`. npx comes from absolute PATH directories only, and queries and guide IDs take letters, digits, spaces and `,.:_/'+-` only, so `cmd.exe` cannot reinterpret them when npx is a `.cmd` script. `retrieve` needs `--baseline` with the PRD value and runs in an empty temporary directory whose `.mwgrc` holds only that target; no project or user `.mwgrc` applies. `--pin` prints the binding row.
- Skill Bindings gain the optional `web_platform_guidance` row, seeded `pending`. `check_skill_bindings.py` accepts `pending`/`pending` or exactly the wrapper's package and pin, at the `ui-design` and full stages, and ignores the row at other stages.
- Frontend Visual Inputs says when `hifi` and `implementation` authors consult MWG, that the HiFi output contract wins inside HiFi, and that authors record the guide IDs that changed their work. The UI design stage points there, and `visual_inputs.py` puts the PRD's Browser support value and the rule's location into `hifi` and `implementation` packets.
- The PRD's Frontend Delivery Requirements open with `Browser support:` and one of `Baseline Widely available`, `Baseline Newly available` or `Baseline <year>`. Discovery asks for it. The checker does not require it, so existing PRDs stay valid; the MWG rule uses `Baseline Widely available` when the line is missing.

Pilot, written before it runs: one web consumer adopts 0.97.0 between rounds, binds the row, and runs its next HiFi round with MWG. agentkiosk is the candidate, with the most focus failures at web widths. Compare that round's first matrix capture with the consumer's 2026-11-19 capture, failing operations by reason. The binding is worth wider use when failing operations fall by at least a third and no new failure reason appears. Fewer than that is within what differences between rounds alone can produce. Which consumer and when is the owner's call, because the owner paused the running UI rounds on 2026-11-19.

## Change Log

| Change | Commits |
| --- | --- |
| Pinned wrapper, optional binding row, author rule | `d58f4b0d` |
| PRD browser support as one Baseline target | `938507ea` |
| This Epic; release 0.97.0 | `01aaf56f`, `099c88b4` |
| npx from absolute PATH directories only; cmd-safe arguments | `05d0697d` |
| Pilot baseline split into native and web targets | `f12a9aa6` |
| Review notes: CLI file logging off; Browser support and the rule in generated packets; the optional row in Installed Commands; README entries | `b605766f`, `78c54090`, `d1d77d72`, this commit |

## Verification

- A real run of the wrapper: `search "light dismiss dialog"` returned ten guides in 1.6 s from the npm cache; `--baseline "Baseline 2024" retrieve "dialog,menu"` returned 44,837 bytes headed by the CLI's "Project Baseline Target: Baseline 2024" banner; `retrieve` without `--baseline` and `install` exited 2 without running npx. No telemetry watchdog process was left running. The tarball's sha512 equals the registry integrity.
- Focused modules: the wrapper, bindings, project context, CLI inventory and dependency tests, 62 passed; install script 13 passed after the commit (before it, the installer refused the untracked new script, as designed). Twelve broken variants of the wrapper and the checker each failed a test.
- Before review: release, document, template and bindings modules (401 passed, 5 skipped), the product-definition suite (16 modules), `check_skill_spec.py`, pyflakes over the four script trees, `prepare_release.py --check` and `git diff --check` passed. A planted `npx.cmd` in the current directory and arguments with `&`, `|`, `%`, `^`, `<` or `"` became two more caught variants (14).
- Review point, gpt-6.1-sol xhigh read-only, on `f12a9aa6` (a first run on `05d0697d` was cut off when the T3 server restarted): no blocking defect. Four notes. R1: an inherited `ENABLE_FILE_LOGGING=true` let the CLI append `modern-web.log` to `MODERN_WEB_LOG_DIR`, fixed in `b605766f`. R2: the generated author packet lacked the Browser support value and the rule, fixed in `78c54090`. R3: Installed Commands described every deferred row as a skill and a full-tree hash, fixed in `d1d77d72`. R4: this handoff was stale, fixed here. The reviewer noted that the tarball SHA-256 is binding metadata; the wrapper does not verify executed bytes against it, and npm, its configuration and its cache stay trusted.
- After the notes: the wrapper, generator, bindings and document modules passed (33 and 82 tests, plus 116 README and release tests), and four more broken variants (logging left on, the Browser support line dropped, a commented-out line counted, the lines added at the direction stage) each failed a test.

## Consumer Impact

Nothing changes until a project fills the new row. `--check --merge-agents` lists the new template row as a Skill Bindings difference until the project adopts it. Rounds keep their recorded Harness version.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / modern-web-guidance / the commit that adds this block / task/ (untracked)
Stage and skill: source maintenance of the skill suite; direct work, no PLAN/RUN
Inputs consumed (path + hash or revision): main 09941dde (v0.96.0); modern-web-guidance 1.0.1 tarball 713d3d34…38a3; the ten-repository sidecars of 2026-11-19
Template audit (current | stale | unknown; template sha256, VERSION, bundle digest, loaded identity or unknown; differences, or the reused audit's matching hashes): pending; rerun after 0.97.0 is installed
Approvals in force (gate, owner, date, candidate): owner, 2026-11-20: "照這個方向做" for the proposed 0.97.0 (pinned per-project binding, telemetry off, HiFi markers first, Baseline target, one-consumer pilot)
Done and verified (command, exit code): see Verification; review point without a blocking defect on f12a9aa6, its four notes fixed
Remaining: a targeted re-check of f12a9aa6..HEAD; pull request, CI, merge, tag v0.97.0, install; the pilot
Blocked / waiting (gate name or owner decision): pilot consumer and round (owner)
Next action (one command or one owner decision): run the targeted re-check of f12a9aa6..HEAD
Next owner (skill or human): parent session
```
