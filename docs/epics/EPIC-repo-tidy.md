# Repository Tidy

Status: in_progress

## Problem And Baseline

At `bf56ab27` (0.64.0) the repository mixed current guidance with history and machine-local state:

- Research reports sat in a top-level `research/` folder beside `docs/`.
- The installers copied each skill's tests and CI data into `~/.agents/skills`, and Skill Binding pins hashed them. A test-only release therefore moved every consumer pin, while the contract digest already skipped tests.
- Epic files used more than twenty free-form status texts, and about 120 places pointed at one machine's absolute paths.
- Every release added a translated history entry to four READMEs.
- The retired Wireframe guide and templates sat beside current guidance.

## Accepted Outcome

On 2026-10-17 the owner accepted four tidy items on branch `codex/repo-tidy`: move research into docs, keep tests out of installs, tidy Epics and local links, and shorten the READMEs while moving legacy material. Later that day the owner asked to finish them and open the PR.

## Requirements

| ID | Outcome |
| --- | --- |
| RT-01 | Research reports live under `docs/research/`. |
| RT-02 | Installed skills contain no `tests` directory, `ci-test-timings.json` or `requirements-test.txt`. The installers, `hash_skill` and `contract_digest` share one rule. |
| RT-03 | Every Epic has one `Status:` line with a template value, and the `docs/DOCUMENTS.md` status cells agree. |
| RT-04 | Epics, audits and research reports contain no local machine paths. |
| RT-05 | Release notes live once in an English `CHANGELOG.md`, and each README links to it. |
| RT-06 | The retired Wireframe guide and templates live in `legacy/` folders, and every current reference uses the new paths. Epic, audit and release-note records keep their historical paths. |

## Document Impact

| Source | Affected artifact |
| --- | --- |
| `install.ps1`, `install.sh`, `check_skill_bindings.py`, `harness_contract.py` | Installed tree, Skill Binding hash and contract digest |
| `CHANGELOG.md`, the four READMEs, `source-maintenance.md`, `docs/WORKFLOW.zh-TW.md` | Release notes and release rules |
| `docs/epics/`, `docs/DOCUMENTS.md`, `docs/audits/`, `docs/research/` | Status lines, the index and local paths |
| `skills/ui-design-builder/references/legacy/`, `skills/ui-design-builder/assets/templates/legacy/` | Wireframe guide and templates |

## Change Log

| Change | Commit | Verification |
| --- | --- | --- |
| Research reports under `docs/research/` (RT-01) | `3bf25c0d` | Ten renames with no content change. |
| Tests and CI data stay out of installs and hashes (RT-02) | `f491442c` | Installer 21, skill binding 9 and harness contract 8 tests pass. |
| One status line per Epic and a shorter index (RT-03) | `ba0ce946` | A script finds one allowed status line in each of 45 Epics, and every Epic row in the index starts with its Epic's status. |
| Release history in `CHANGELOG.md` (RT-05) | `7f898c0f` | All 108 entries match README.md in text and order. |
| Wireframe material in `legacy/` folders (RT-06) | `5e8618c4` | UI suite 367, cross-skill 18 and Product Definition contract 102 tests pass. No current reference keeps an old path. |
| Local machine paths removed (RT-04) | `75a531b5` | No drive path is left in Epics, audits or research, and the 107 changed lines keep their table structure. |
| Version 0.65.0 | `af4dc502` | Skill contract 65, README structure 5 and document sync 27 tests pass. |
| Review of the documents and moves (`3bf25c0d` to `af4dc502`) | — | GPT-6.1 Sol: PASS with no findings. It checked the 108 release entries, byte-identical moves, 45 Epic statuses and 390 path references. |
| Review of the install change (`f491442c`) | — | GPT-6.1 Sol: FIX_REQUIRED with three medium findings. PowerShell matched case-insensitively, the digest skipped directories named like the excluded files, and the runtime trust guide still pointed at the uninstalled test requirements. |
| Review fixes | `56d8f929`, `1d96dc18`, `dcb892ae` | Each fix has a test. A new installer test runs both installers on case variants. Focused checks on `dcb892ae` pass: installer 22, UI suite 367 and Product Definition 304 tests, plus the skill spec, docs weight and pyflakes. |
| Follow-up review of the fixes | — | GPT-6.1 Sol confirmed the three findings closed. It found one older mismatch: the digest skipped a regular file named `tests` and kept `.pytest_cache`. |
| Digest follows the same rule | `fd58127b` | Harness contract 11, skill binding 10 and skill contract 65 tests pass. |
| Review of `fd58127b` | — | GPT-6.1 Sol: the `tests` finding is closed. It found an older cache-rule gap: bash ships a regular file named `.pytest_cache` or `__pycache__`, which PowerShell and both hashes leave out. The rules also differ on letter case. |
| One cache rule in both installers | `cfb7f548` | A new installer test runs both installers on cache-name variants. The installer suite of 23 tests passes in 356 s. |
| Review of `cfb7f548` | — | GPT-6.1 Sol: closed. Two older suffix gaps remained: the digest skipped directories ending in `.pyc`, and both hashes kept a file named exactly `.pyc`. |
| Compiled files matched by name | `3f7ef22e` | Each included test path now proves itself on its own. The installer suite of 23 tests passes in 352 s, along with harness UI 50, the skill spec and pyflakes. |
| Final review of the shared rule | — | GPT-6.1 Sol: PASS. It compared 4,668 tricky paths across both installers, `hash_skill` and `contract_digest` and found no disagreement. |

Four GLM workers timed out on this work. In each case the parent checked the partial result, finished or corrected it, and verified it before integration.

## Remaining Work

- When 0.64.1 to 0.64.5 land first, merge `main` into this branch: move their README history entries into `CHANGELOG.md`, give their Epics and index rows the status form, and move the installer tests from this branch into the split installer test files.
