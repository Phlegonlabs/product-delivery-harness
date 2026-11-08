# Assignment

One bounded direct-route assignment for one executor. Fill every `<...>` field and delete a line that does not apply. Keep the filled packet within the route's `max_message_bytes`.

## Identity

- Assignment ID: <stable ID>
- Attempt ID: <new ID for each launch>
- Role: <execution role>
- Outcome: <one bounded outcome | question IDs>

## Checkout

- Repository: <repository root>
- Branch: <branch>
- Base SHA: <full SHA>
- Checkout: <worktree path>; you own it until handback

## Executor

- Requested executor: <host policy choice>; no delegation, model change or fallback
- Route caps: wall-clock <seconds>; tool turns <cap>; max_message_bytes <bytes>

## Scope

- Write paths: <exact paths or /** subtrees>
- Parent-owned paths: <paths you never edit>
- Preserve: every change you did not make

## Inputs

- Read first: <path> sha256 <hash>
- Required skills: <skill name and pinned SHA-256 | none>
- Frontend: <maximum-creativity brief per `delivery-harness/references/delegation-contract.md`, plus `visual_inputs.py` output | n/a>

## Acceptance

- <command> -> <pass signal>

## Result

- Observed identity: <executor, model and effort actually used>
- Read evidence: <each source read, and any hash mismatch>
- Commits: <SHA and subject, in order>
- Verifier results: <command, exit code>
- Cleanup receipt: <processes and services stopped, scratch area state>
