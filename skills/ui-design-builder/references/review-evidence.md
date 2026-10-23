# Actual Review Evidence

New HiFi completeness, browser and full HiFi gates consume ui-evidence/3. Legacy Wireframe Validation and ui-evidence/2 remain historical records under their original rules. Agents must not invent a human owner, attestation or approval.

## Observation Output

An actual tool run writes ui-output/3 with check, subject, matrix and results, retaining the applicable offline sandbox, interaction, reviewer and motion transcript fields from output-contract.md. Add execution with exactly:

- startedAt and finishedAt: actual timezone-aware start/finish timestamps, never derived from a hash or invented duration;
- tool and method: the tool/method that actually performed the observation;
- environment: a nonempty map of observed runtime/platform/browser versions;
- artifacts: current path/SHA-256 identities captured for the subject and every input, including all manifest-listed HiFi children.

Each expected matrix case names surface, state and target. Results contain observed PASS, FAIL, BLOCKED or MISSING. Missing rows remain missing. A static schema check cannot emit browser, accessibility, visual quality or native PASS.

For grading, critique and audit, add assessment with scores, observations and blocks. Each observation names the exact surface/state/target, a concrete finding and its own inspected, hashed screenshot, DOM or native capture (`.png`, `.jpg`, `.jpeg`, `.webp`, `.json` or `.html`). The capture is distinct from the reviewed subject and execution input sources; reusing an input hash as case evidence fails. Synthetic tests write explicit per-case JSON captures and make no browser or native claim. Current H1–H9 scores contain every actual dimension. The UI record's overall, lowest and required dimension values must equal that assessment. Numeric thresholds do not override a block, broken interaction or missing observation. Qualitative findings remain the reviewer's judgment; hashes establish identity, not honesty or beauty.

## Receipt Assembly

From the target repository root:

    python "<ui-design-builder-skill-root>/scripts/review_evidence.py" --repo-root . --output-artifact docs/evidence/current-output.json --receipt-out docs/evidence/current-receipt.json

The tool checks recorded input identities and emits ui-evidence/3 with schema, check, result, reviewedArtifact and receipt. The receipt retains tool, method, matrix, results, outputArtifact and executedAt; executedAt is the observed finish time. It does not run a browser or create approval. It rejects stale inputs, traversal, linked paths and overwrites unless --overwrite is explicit. Missing/failed/blocked observations cannot become PASS. Collect new observations after relevant candidate changes; do not rebind old results.

Keep receipts, inspected captures and source artifacts tracked when they are required evidence. Only the final candidate's receipts and the captures they cite, including carried rows, are required evidence. Do not commit evidence of earlier attempts; cite it by SHA-256 in the defect ledger. Temporary run logs/caches belong outside the product package or under a narrow existing ignore rule. Do not hide canonical HTML, manifests, token sources or evidence with a broad generated-file pattern.

## Diagnostic Wave Completeness

Before one consolidated HiFi repair handoff, the lead confirms that the browser, critique, audit and H1–H9 receipts name the frozen candidate hash and cover every manifest surface, non-`n/a` state and that surface's responsive targets. Under the rubric's default staffing, the lead grader produces the browser and grading receipts, and the Impeccable operator produces the critique and audit receipts. `check_ui_design_contract.py` proves the same binding at Visual Approval; no separate request file or command runs earlier.

Complete observed FAIL results, low scores and fully observed defects may enter one consolidated repair batch under the existing write grant. Missing outputs, unscorable `BLOCKED` or `MISSING` rows, an absent H dimension, malformed captures or input drift block the handoff. These findings still fail strict final acceptance. None of this is a PASS or Visual Approval.

Repair re-review follows [Repair Re-review Scope](ui-grading-rubric.md#repair-re-review-scope). Every receipt still binds current candidate bytes. Rows for unchanged pages carry forward only under the output contract's carry-forward rule. Do not rebind an earlier PASS to repaired bytes.

## Frontend Design Usage

Record the `### Frontend Design Usage` table under the direction/HiFi handoff as [output-contract.md](output-contract.md) shows. The source path is a retained repository snapshot of the actually observed `frontend-design` `SKILL.md` with `name: frontend-design`. Every stage's Skill SHA-256 equals this snapshot hash. The validator checks the snapshot bytes and current artifact bindings; it cannot prove that an agent truly used the skill. Use repair-1, repair-2 for actual design repairs with their resulting artifact and applied decisions. Current direction/hifi rows bind the exact current candidates, not a convenient other file; a legacy package may retain its historical `wireframe` row. Record only work actually performed. Human direction and final Visual Approval stay in their dedicated sections of ui-design.md.

For the existing Application and task evidence, name the selected captures, font declarations, assets and visual features the author actually inspected.
Use the current source identities from [Frontend Visual Inputs](../../delivery-harness/references/frontend-visual-inputs.md); do not substitute the parent's reading or backfill an inspection.
