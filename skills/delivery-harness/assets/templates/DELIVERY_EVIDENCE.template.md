# Delivery Evidence

One evidence file per runner command under `docs/verification/evidence/`. It carries each scenario's row status, each assertion's status and the observations; `scripts/build_delivery_results.py` reads these headings and copies the row identity from the frozen register.

## Run

- Candidate: <full SHA>
- Command: <exact command> -> exit <code>
- Runner: <name> <version>
- Device / OS: <device or simulator>, <OS and version> | n/a
- Date: <RFC3339>
- Build read-back: <observed build ID and config digest> | n/a
- Fixtures: namespace <synthetic-...>; owned <owned:...>; setup read-back <observation>; cleanup read-back <observation> | none
- Raw log sha256: <64 lowercase hex> (<log path>)

## <scenario_id> (<TEST-ID>) — row status: <pass|fail|blocked|skipped|unvalidated>

fixture_cleanup: <cleaned|not_required|pending|failed>

### ASSERT-001 — <pass|fail>

observed: <what the run showed>

```text
<raw runner lines for this assertion>
```

## <not-run scenario_id> (<TEST-ID>) — row status: <blocked|unvalidated>

reason: <why it did not run, for a blocked or unvalidated row>

The next action for a not-run row goes in the round's handoff record (`delivery-harness/references/bounded-enhancement.md`).
