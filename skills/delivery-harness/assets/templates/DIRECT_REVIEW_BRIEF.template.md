# Direct Review Brief

One independent review of one exact candidate on the direct route. Fill every `<...>` field and delete a block that does not apply. Keep the filled brief within the route's `max_message_bytes`.

## Candidate

- Repository: <repository root>
- Base SHA: <full SHA>
- Head SHA: <full SHA>
- Review input: <out>/clone/review-input/, built by `review_input.py --repo <repository root> --base <base SHA> --head <head SHA> --out <out> --scope <name>=<pathspec>`

## Identity Proof

A git failure in your sandbox is expected. The clean-checkout proof is a `tracked-files.sha256` match plus `status: clean` for this head in `parent-status.txt`; record it as "observed via manifest" under `delivery-harness/references/security-review.md#required-inputs`. A mismatch or another status returns `blocked`.

## Scope

- <path group name>: <pathspecs> (`review-input/scope-<name>.diff`)

## Lenses

- Code: apply `delivery-harness/references/architecture-method.md` to the changed boundaries.
- Security: load `delivery-harness/references/security-review.md` (sha256 <hash>) and return its result object | `security: not_applicable (<reason>; <paths>)`
- Visual: inspect with your own browser, record your own capability receipt, and follow Final UI Acceptance in `delivery-harness/references/verification-gates.md` | n/a — no UI change

## Acceptance And Instructions

- Acceptance rows: <TEST-ID or criterion> -> <evidence path>
- Read first and verify: <instruction or source path> sha256 <hash>

## Re-check

- Prior reviewed head: <full SHA>
- Prior blocking findings: F1 <finding>
- Prior notes (no verdict needed): <note | none>
- Repair range: <prior head>..<head SHA>

Give each prior finding a verdict: resolved, unresolved or superseded. Inspect the repair range and its direct consumers; anything else is a note unless it is a validated security finding or a correctness defect inside the range.

## Route Caps

- Wall-clock seconds: <observed cap>
- Tool turns: <observed cap>
- max_message_bytes: <observed cap>

## Result

Return the verdict (`pass`, `fix_required` or `blocked`), the exact head SHA, blocking findings with path and line, non-blocking notes kept apart, and the commands you ran. Do not restate this brief, matrices or hash lists.
