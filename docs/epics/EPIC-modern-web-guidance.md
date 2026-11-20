# EPIC-modern-web-guidance: pinned Modern Web Guidance for frontend authors

Status: in_progress (0.97.0 on branch `modern-web-guidance`; pilot not started)
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

Baseline for the pilot: in the ten-repository sidecars of 2026-11-19, 623 of 1,293 interaction operations failed, 2,791 attempts in all. Measured per repository, focus failures ("product focus did not land on the control alone", 1,734 attempts) sit mostly in ticketradar (609 attempts, 153 of 190 operations) and ticketradar-en-app (555, 139 of 175). hk-car-care has 306 (78 of 119), agentkiosk 184 (23 of 38) and jolvex-platform 80 (8 of 604). They are nearly all `state` interactions and look like one project-level cause per repository, so MWG may not move them; the pilot decides. dilution-radar, hardwareprices and agentic-commons-site fail on destinations and missing controls instead.

## Accepted Scope

Owner decision, 2026-11-20, in reply to the evaluation: "照這個方向做" (go this way) for the proposed 0.97.0:
- Do not install MWG globally. A project binds it in Skill Bindings with an exact version.
- Telemetry off. The HiFi output contract's markers win inside HiFi; MWG applies to how production code is built.
- The PRD's browser target becomes a Baseline level.
- Pilot on one consumer, compare interaction failures with the matrix capture, then decide on wider use.
- Do not copy guides into this repository. Do not make `legacy-scan` a gate.

Delivered in 0.97.0:
- `delivery-harness/scripts/modern_web_guidance.py` pins `modern-web-guidance@1.0.1` (registry tarball SHA-256 `713d3d34…38a3`, npm integrity `sha512-5ztUh5F1…`). It always sets `DISABLE_TELEMETRY=1` and runs only `search`, `list` and `retrieve`. `retrieve` needs `--baseline` with the PRD value and runs in an empty temporary directory whose `.mwgrc` holds only that target; no project or user `.mwgrc` applies. `--pin` prints the binding row.
- Skill Bindings gain the optional `web_platform_guidance` row, seeded `pending`. `check_skill_bindings.py` accepts `pending`/`pending` or exactly the wrapper's package and pin, at the `ui-design` and full stages, and ignores the row at other stages.
- Frontend Visual Inputs says when `hifi` and `implementation` authors consult MWG, that the HiFi output contract wins inside HiFi, and that authors record the guide IDs that changed their work. The UI design stage points there.
- The PRD's Frontend Delivery Requirements open with `Browser support:` and one of `Baseline Widely available`, `Baseline Newly available` or `Baseline <year>`. Discovery asks for it. The checker does not require it, so existing PRDs stay valid; the MWG rule uses `Baseline Widely available` when the line is missing.

Pilot, written before it runs: one web consumer adopts 0.97.0 between rounds, binds the row, and runs its next HiFi round with MWG. Compare that round's first matrix capture with the consumer's 2026-11-19 capture, failing operations by reason. The binding is worth wider use when failing operations fall by at least a third and no new failure reason appears. Fewer than that is within what differences between rounds alone can produce. Which consumer and when is the owner's call, because the owner paused the running UI rounds on 2026-11-19.

## Change Log

| Change | Commits |
| --- | --- |
| Pinned wrapper, optional binding row, author rule | `d58f4b0d` |
| PRD browser support as one Baseline target | `938507ea` |

## Verification

- A real run of the wrapper: `search "light dismiss dialog"` returned ten guides in 1.6 s from the npm cache; `--baseline "Baseline 2024" retrieve "dialog,menu"` returned 44,837 bytes headed by the CLI's "Project Baseline Target: Baseline 2024" banner; `retrieve` without `--baseline` and `install` exited 2 without running npx. No telemetry watchdog process was left running. The tarball's sha512 equals the registry integrity.
- Focused modules: the wrapper, bindings, project context, CLI inventory and dependency tests, 62 passed; install script 13 passed after the commit (before it, the installer refused the untracked new script, as designed). Twelve broken variants of the wrapper and the checker each failed a test.

## Consumer Impact

Nothing changes until a project fills the new row. `--check --merge-agents` lists the new template row as a Skill Bindings difference until the project adopts it. Rounds keep their recorded Harness version.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / modern-web-guidance / the commit that adds this file / task/ (untracked)
Stage and skill: source maintenance of the skill suite; direct work, no PLAN/RUN
Inputs consumed (path + hash or revision): main 09941dde (v0.96.0); modern-web-guidance 1.0.1 tarball 713d3d34…38a3; the ten-repository sidecars of 2026-11-19
Template audit (current | stale | unknown; template sha256, VERSION, bundle digest, loaded identity or unknown; differences, or the reused audit's matching hashes): pending; rerun after 0.97.0 is installed
Approvals in force (gate, owner, date, candidate): owner, 2026-11-20: "照這個方向做" for the proposed 0.97.0 (pinned per-project binding, telemetry off, HiFi markers first, Baseline target, one-consumer pilot)
Done and verified (command, exit code): see Verification
Remaining: release 0.97.0 (entries, review, pull request, CI, merge, tag, install); the pilot
Blocked / waiting (gate name or owner decision): pilot consumer and round (owner)
Next action (one command or one owner decision): write the 0.97.0 entries and run prepare_release.py
Next owner (skill or human): parent session
```
