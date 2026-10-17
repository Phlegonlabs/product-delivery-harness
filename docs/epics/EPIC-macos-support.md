# macOS Support

Status: complete
Integrated on `main` in the 0.56 release line. PR #129 was superseded by PR #131.
Design workflow: maintenance
UI impact: none

## Scope And Accepted Outcome

The owner asked (2026-09-27) to make the skill bundle run on macOS and to test on the Mac mini. The macos CI job added in 0.55.0 is non-blocking because it failed 353 tests. Outcome: every required suite passes on macOS, and the macos job blocks again.

Owner decisions (2026-09-27):

- The macos CI job uses Apple's `/usr/bin/git`; the trusted-Git policy (root-owned, no links) is unchanged.
- The Mac mini uses its existing Homebrew Python 3.14 (`/opt/homebrew/bin/python3.14`) in a venv outside the repo (`~/.cache/pdh-venv`), with `/usr/bin` ahead of Homebrew on PATH.

| Requirement | Acceptance |
| --- | --- |
| MAC-1 | CI macos job uses a root-owned Git and blocks again once suites pass. |
| MAC-2 | Test temp roots do not traverse macOS `/var` → `/private/var`; the no-link path policy is unchanged. |
| MAC-3 | Descriptor-bound executable launch fails closed with its own error on macOS instead of EACCES at exec; any macOS alternative binding needs an owner decision and security review. |
| MAC-4 | Four READMEs state how to run the suites on macOS. |

## Baseline

Observed 2026-09-27: branch `codex/macos-support` cut from `origin/main` `2fa9b343` (v0.55.0). Pushed only to the Mac mini checkout (`macmini:Documents/GitHub/product-delivery-harness`, previously clean at `1c7939d`). Mac mini: macOS 26.6.2 arm64, `/usr/bin/git` 2.54.0 (Apple Git-157), Python 3.14.7.

Mac baseline at `2fa9b343` (default `TMPDIR`): Harness 1321 run, 98 failures, 26 errors, 28 skipped; UI Design 35 failures, 39 errors; Design System Compiler 9 failures; golden path 1 failure; Product Definition, Product Activation, SEO passed.

Same code with `TMPDIR` resolved to `/private/var/...`: UI Design, Design System Compiler and golden path pass; Harness has 4 failures and 18 errors. None of the unresolved-run rejections name a product-created temp dir (`harness-verifier-snapshot-`, `harness-git-isolated-`, `trusted-host-challenge-`, `harness-no-hooks-`, `harness-filtered-objects-`, `harness-trusted-host-`), so the `/var` failures come from test fixtures placing repositories under the symlinked temp root.

Remaining 22: descriptor-bound exec through `/dev/fd/N` returns EACCES on macOS (`verifier_runtime._RuntimeExecutableBinding`, `parity_capture` launcher, `push_archived_candidate` signature verifier); 4 `parity_capture` capture failures likely downstream; 1 cross-device link in `test_push_archived_candidate`.

## Change Log

### 2026-09-27 — branch `codex/macos-support`

- `20a43c01` ci(harness): macos job puts `/usr/bin` on `GITHUB_PATH` before setup-python; test asserts the step and order. Verified locally with `test_install_script.py -k macos` (OK); not yet run in CI.
- `74a048ab` ci(harness): macos job sets `TMPDIR` to its real path through `GITHUB_ENV`; four READMEs give the macOS test setup. Product temp dirs were not involved (see Baseline), so the no-link policy is unchanged.
- `c1dc379f` fix(harness): descriptor-bound exec refuses `/dev/fd` on darwin and raises the existing binding error in `verifier_runtime`, `parity_capture` (executables only) and `push_archived_candidate` (the signature verifier only; bound data files still read through `/dev/fd`). 26 tests that need descriptor exec skip on darwin with a stated reason; three darwin tests assert the fail-closed errors.
- Mac mini at `c1dc379f` (resolved `TMPDIR`, `/usr/bin/git`): Harness 1324 OK (54 skipped), Product Definition 240 OK, UI Design 293 OK (3 skipped), Design System Compiler 116 OK (2 skipped), Product Activation 56 OK, SEO 21 OK, golden path OK, skill spec and pyflakes pass.
- Windows: `test_push_archived_candidate` 35 OK, `test_verifier_runtime` 46 OK. `test_parity_capture` failed once (4 failures, 4 errors, 721 s, details not kept), then passed twice (17 OK, ~22 s); treated as a flaky browser timeout, not a regression.

Owner decision (2026-09-27): allow path launch only for SIP-protected files; keep container verifiers and parity capture fail-closed on macOS; push the branch and open a PR.

- `7395efce` feat(harness): the trusted-host signature verifier runs by path on macOS when `csr_check` shows SIP filesystem protection enforced and the path names the hash-verified inode of a restricted file. Mac mini: `test_push_archived_candidate.py` 36 OK (the 10 formerly skipped tests run again); Windows 36 OK, 1 skipped.
- Security review of `7395efce` against `2fa9b343`: PASS, three informational notes. Note 1 (check the restricted flag on every path component) fixed in `9039decb`; Mac mini 36 OK.
- PR #129 CI on `7395efce` (run 36386171742): macos success, windows-hardening success, validate failed because `test_install_script` could not import after the `pwsh` probe hit its 10 s timeout on a cold runner. Fixed in `94c8a21a` (60 s, timeout means unavailable).
- The macos job is blocking again and the READMEs state the macOS limits (`ci(harness): make the macos job blocking again`).

Still fail-closed on macOS: sandboxed container verifiers and browser parity capture.

### 2026-09-28 — 0.56.0 integration

- `daac7206` on `codex/macos-support` was integrated into `codex/release-0.56.0` by merge `412db6b4`, together with the review follow-ups and Wireframe-stage removal. PR #131 carries the combined release; PR #129 remains historical review evidence.
- At `7fa1e935`, PR #131's `validate`, `macos` and `windows-hardening` CI jobs passed. The release and exact-`main` verification remain pending.
