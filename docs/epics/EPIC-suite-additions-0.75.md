# Suite Additions, Program Profile And Thinner Reading (0.74.2 to 0.75.3)

Status: complete; v0.75.3 released, installed and adopted in 19 consumer repos, all pushed
Design workflow: enhancement
UI impact: none (skill rules, templates and scripts; no product UI in this repository).

## Problem And Baseline

The 0.74.1 review left six findings, Linux desktop was not an accepted target, and the suite had no guidance for GA4 setup, design-first exploration, AI features, cost budgets, native build cleanup or ERP-scale products. Each addition grew the reading load, so the owner also asked for a thinner Harness. The 0.75.2 consumer adoption then found three template defects that every consumer had copied.

Baseline: `9e9280a7` (v0.74.1 on `main`).

## Accepted Scope

Owner instructions, 2026-11-02: fix review findings 1 to 6 including Linux; a general GA4 admin setup with funnels; fold the design-first video process into the UI flow; a full suite review with additions (native cleanup on the Mac mini, AI, runtime, ERP program profile, module structure), all by Sonnet 5.5; thinning items 1 and 3; commit, push, merge, install and update every consumer to the new flow; then release the template fixes and update the docs.

Not in scope: owner decisions listed under Handoff.

## Acceptance

| ID | Expected outcome | Verification |
| --- | --- | --- |
| FR-1 | Six 0.74.1 findings fixed; Linux desktop accepted across the nine affected scripts | PR #168 CI; `test_markdown_anchor_links.py` |
| FR-2 | `references/ga4-admin-setup.md` covers streams, retention, key events, reports, funnels and the launch checklist | PR #169 CI; live GA4 walkthrough in the session |
| FR-3 | UI flow has optional R0 exploration, journey maps before HiFi, font pairing and journey missions | PR #170 CI |
| FR-4 | AI feature contract, performance and cost budgets, compliance jurisdiction, native build cleanup and modular-monolith guidance exist and are routed | PR #171 CI |
| FR-5 | `program` delivery profile with `PROGRAM_PRD`, `MODULE_PRD` and `PROGRAM_MIGRATION` templates and `program_package.py` | PR #172 CI |
| FR-6 | `docs_duplicates.py` and `docs_reading_budget.py`; pin-only guides moved to `references/legacy/`; seven references compressed with no rule removed | PRs #173 and #174 CI; counted total below v0.74.1 |
| FR-7 | `PROJECT_AGENTS.template.md` names the real managed-run rule owner; the DEPLOYMENT presence example is not a placeholder; the GA4 guide names the pre-verification `MS-*` status | `test_documented_commands.py` (both new tests fail on the old templates); PR #175 CI |
| FR-8 | 19 consumers pin the released contract, their shared rules match the templates, and every `main` equals `origin/main` | per-repo `check_skill_bindings.py`, `check_document_sync.py`, `git rev-parse` |

## Change Log

- 2026-11-02: PRs #168 to #174 merged as v0.74.2 (`0ae26cca`), v0.74.3 (`08b3422d`), v0.74.4 (`57977845`), v0.74.5 (`4d10aa77`), v0.75.0 (`e0ba4530`), v0.75.1 (`1b20eeb6`) and v0.75.2 (`d70347f8`). Workers were Claude Sonnet 5.5 (xhigh) through `delegate_task`; the stack was collapsed into its top PR so `main` took one CI run.
- 2026-11-02: `install.sh` from v0.75.2; installed contract `9ffdddab`. 19 consumers re-pinned by one parent script; bound `ui-design-builder` and `design-system-compiler` pins moved only where they equalled the 0.74.1 tree (hk-car-care keeps its owner-approved C4 tree).
- 2026-11-02: a handoff audit per consumer (one Sonnet 5.5 worker each, about seven at a time) compared AGENTS.md and CLAUDE.md with the project templates and the live docs. 17 of 19 had stale shared rules; all were updated, baselines refreshed, and every consumer pushed.
- 2026-11-02: the audit found three Harness template defects; fixed in PR #175, merged at `645b4335` and tagged v0.75.3. `install.sh` exit 0; installed contract `a191bfa0`. One parent script re-pinned the 19 consumers and rewrote their copy of the managed-run pointer (no consumer had copied the old presence example). One Sonnet 5.5 (xhigh) worker per repo then rewrote the Epic `## Handoff` block for 0.75.3 and moved live docs that named 0.75.2 as current. The parent restored three worker-manager Change Log rows the 0.75.2 audit had deleted or truncated, refreshed 17 document-sync baselines (hk-car-care's inventory belongs to its live session; jolvex-platform's re-seed is an owner decision) and pushed all 19 `main` branches.

## Handoff

```text
Repository / branch / HEAD / dirty paths: product-delivery-harness / main / 645b4335 (v0.75.3) / none
Stage and skill: source maintenance; 0.75.3 released and adopted
Inputs consumed (path + hash or revision): tag v0.75.3 645b4335; installed contract a191bfa0
Approvals in force (gate, owner, date, candidate): owner "全部的內容都停下來吧。 然後更新上去。" and "OK 更新到全部，然後裏面的那些文檔都更新一下。" 2026-11-02
Done and verified (command, exit code): PR #175 CI pass; install.sh exit 0; check_skill_bindings.py no mismatch in 19 consumers; 19 consumers pushed with main equal to origin/main
Remaining: none in this repository
Blocked / waiting (gate name or owner decision): GA4 internal IP filters and the three manual funnels; jolvex-platform stale RUN and baseline re-seed; hk-car-care C4 pin exception and its document-sync baseline; clouldflare-bifu daily cap 12 or 15; deployment owner facts in phlegon-web, social-auto-reply and agent-bridge
Next action (one command or one owner decision): owner decides the blocked items above
Next owner (skill or human): owner
```
