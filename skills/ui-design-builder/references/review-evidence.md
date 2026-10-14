# Actual Review Evidence

New HiFi completeness, browser and full HiFi gates consume ui-evidence/3. Legacy Wireframe Validation and ui-evidence/2 remain historical records under their original rules. Agents must not invent a human owner, attestation or approval.

## Observation Output

An actual tool run writes ui-output/3 with check, subject, matrix and results, retaining the applicable offline sandbox, interaction, reviewer and motion transcript fields from output-contract.md. Add execution with exactly:

- startedAt and finishedAt: actual timezone-aware start/finish timestamps, never derived from a hash or invented duration;
- tool and method: the tool/method that actually performed the observation;
- environment: a nonempty map of observed runtime/platform/browser versions;
- artifacts: current path/SHA-256 identities captured for the subject and every input, including all manifest-listed HiFi children.

Each expected matrix case names surface, state and target. Results contain observed PASS, FAIL, BLOCKED or MISSING. Missing rows remain missing. A static schema check cannot emit browser, accessibility, visual quality or native PASS.

For grading, critique and audit, add assessment with scores, observations and blocks. Each observation names the exact surface/state/target, a concrete finding and its own inspected, hashed screenshot, DOM or native capture (`.png`, `.jpg`, `.jpeg`, `.webp`, `.json` or `.html`). The capture is distinct from the reviewed subject and execution input sources; reusing an input hash as case evidence fails. Synthetic tests write explicit per-case JSON captures and make no browser or native claim. Current H1–H9 scores contain every actual dimension; W1–W5 scores are retained only for legacy wireframes. The UI record's overall, lowest and required dimension values must equal that assessment. Numeric thresholds do not override a block, broken interaction or missing observation. Qualitative findings remain the reviewer's judgment; hashes establish identity, not honesty or beauty.

## Receipt Assembly

From the target repository root:

    python "<ui-design-builder-skill-root>/scripts/review_evidence.py" --repo-root . --output-artifact docs/evidence/current-output.json --receipt-out docs/evidence/current-receipt.json

The tool checks recorded input identities and emits ui-evidence/3 with schema, check, result, reviewedArtifact and receipt. The receipt retains tool, method, matrix, results, outputArtifact and executedAt; executedAt is the observed finish time. It does not run a browser or create approval. It rejects stale inputs, traversal, linked paths and overwrites unless --overwrite is explicit. Missing/failed/blocked observations cannot become PASS. Collect new observations after relevant candidate changes; do not rebind old results.

Keep receipts, inspected captures and source artifacts tracked when they are required evidence. Temporary run logs/caches belong outside the product package or under a narrow existing ignore rule. Do not hide canonical HTML, manifests, token sources or evidence with a broad generated-file pattern.

## Diagnostic Wave Completeness

Before one consolidated HiFi repair handoff, verify the independent browser, critique, audit and H1–H9 wave. Run the read-only CLI with installed-command resolution:

    python "<ui-design-builder-skill-root>/scripts/check_ui_diagnostic_wave.py" --repo-root . --request docs/evidence/diagnostic-request.json --request-sha256 <observed-request-digest>

`--request-sha256` is the independently read hash of the complete request bytes. The request uses `ui-diagnostic-wave-request/1`:

```json
{
  "schema": "ui-diagnostic-wave-request/1",
  "subject": {"path": "docs/design/ui-references/run/index.html", "sha256": "<64-lowercase-hex>"},
  "frozenInputs": {
    "prd": {"path": "docs/product/PRD.md", "sha256": "<64-lowercase-hex>"},
    "manifest": {"path": "docs/design/ui-references/run/index.html", "sha256": "<64-lowercase-hex>"}
  },
  "requiredCases": [{"surface": "UI-001", "state": "ready", "target": "390"}],
  "observations": {
    "browser": {"path": "docs/evidence/browser-receipt.json", "sha256": "<64-lowercase-hex>"},
    "critique": {"path": "docs/evidence/critique-receipt.json", "sha256": "<64-lowercase-hex>"},
    "audit": {"path": "docs/evidence/audit-receipt.json", "sha256": "<64-lowercase-hex>"},
    "grading": {"path": "docs/evidence/grading-receipt.json", "sha256": "<64-lowercase-hex>"}
  }
}
```

Use actual repository paths and observed hashes. `manifest` equals the HiFi HTML subject because the manifest is embedded there; the checker joins child page hashes from that manifest and execution inputs. Before each write, the author rechecks the request and all frozen-input bytes in their own context. The checker changes no bytes, approval record or evidence schema.

Exit 0 means diagnostic completeness only. Complete observed FAIL, low scores and concrete scoreable design blocks may enter one existing consolidated repair batch only under the existing write grant. Missing outputs or cases, unscorable `BLOCKED` or `MISSING`, an absent H dimension, malformed captures, or input drift blocks the dependent handoff regardless of aggregate FAIL. This is not a PASS, Visual Approval or new approval record.
The existing attempt budget and same-author ownership remain binding.

## Frontend Design Usage

Under the direction/HiFi handoff, record:

### Frontend Design Usage

Frontend Design source: docs/design/<folder>/SKILL.md @ sha256:<observed-source-digest>

| Stage | Skill | Artifact | Application |
| --- | --- | --- | --- |
| direction | frontend-design @ sha256:<observed-source-digest> | docs/design/directions/round/primary.png @ sha256:<capture-digest> | Concrete alternatives evaluated for this direction |
| hifi | frontend-design @ sha256:<observed-source-digest> | docs/design/ui-references/round/index.html @ sha256:<candidate-digest> | Concrete typography, palette, layout and self-check outcomes |

The source path is a retained repository snapshot of the actually observed `frontend-design` `SKILL.md` with `name: frontend-design`. Every stage's Skill SHA-256 equals this snapshot hash. The validator checks the snapshot bytes and current artifact bindings; it cannot prove that an agent truly used the skill. Use repair-1, repair-2 for actual design repairs with their resulting artifact and applied decisions. Current direction/hifi rows bind the exact current candidates, not a convenient other file; a legacy package may retain its historical `wireframe` row. Record only work actually performed. Human direction and final Visual Approval stay in their dedicated sections of ui-design.md.
