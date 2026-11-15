# UI compiler evidence scope

Status: development patch; verification and owner-authorized installation pending

AgentKiosk's approved Shop talk package exposed two checker mismatches. Declared
`:n/a` states entered the expected capture matrix, and intermediate-width receipts
were required to repeat reviewer measurements from the approved-width surface run.

The patch excludes declared n/a states and limits that repeated reviewer check to
ordinary surface evidence. Intermediate receipts still require the typed output,
current source bindings, browser transcript, interactions and interval coverage.
New regression tests preserve those rejection paths and per-surface derived cases.

The owner authorized this 0.80.0 development installation on 2026-11-15. It does
not authorize a release, main landing, push or changes to other consumers' pins.
The approved AgentKiosk design remains unchanged. The official installer must
retain the previous installed bundle and record the source commit.

## Handoff

Focused regression tests pass. Run the source verification matrix on the committed
candidate, then install through `install.sh`, update AgentKiosk's pins and run its
official compiler preflight. The four-hunk checker patch already has protected
read-only review in AgentKiosk's `compiler-reconciliation-002/protected-review.txt`.
Full verification and installed preflight results are not yet claimed.
