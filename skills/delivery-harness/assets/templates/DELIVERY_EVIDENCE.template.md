# Delivery Evidence

One evidence file per runner command under `docs/verification/evidence/`. It holds only what the register cannot: row status, assertion status, expected text and `fixture_cleanup` stay in `delivery-results.json`. Fill every `<...>` field; never record a secret, cookie or token.

## Run

- Candidate: <full SHA>
- Command: <exact command> -> exit <code>
- Runner: <name> <version>
- Device / OS: <device or simulator>, <OS and version> | n/a
- Date: <RFC3339>
- Build read-back: <observed build ID and config digest> | n/a
- Fixtures: namespace <synthetic-...>; owned <owned:...>; setup read-back <observation>; cleanup read-back <observation> | none
- Raw log sha256: <64 lowercase hex> (<log path>)

## <scenario_id>

### ASSERT-001

observed: <what the run showed>

```text
<raw runner lines for this assertion>
```

## <not-run scenario_id>

reason: <why it did not run, for a blocked or unvalidated row>

The next action for a not-run row goes in the round's handoff record (`delivery-harness/references/bounded-enhancement.md`).
