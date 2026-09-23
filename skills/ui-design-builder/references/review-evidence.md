# Actual Review Evidence

New Wireframe Validation and full HiFi gates consume ui-evidence/3. Legacy ui-evidence/2 remains a historical human-attested consistency receipt. Agents must not invent a human owner, attestation or approval.

## Observation Output

An actual tool run writes ui-output/3 with check, subject, matrix and results, retaining the applicable offline sandbox, interaction, reviewer and motion transcript fields from output-contract.md. Add execution with exactly:

- startedAt and finishedAt: actual timezone-aware start/finish timestamps, never derived from a hash or invented duration;
- tool and method: the tool/method that actually performed the observation;
- environment: a nonempty map of observed runtime/platform/browser versions;
- artifacts: current path/SHA-256 identities captured for the subject and every input, including all manifest-listed HiFi children.

Each expected matrix case names surface, state and target. Results contain observed PASS, FAIL, BLOCKED or MISSING. Missing rows remain missing. A static schema check cannot emit browser, accessibility, visual quality or native PASS.

For grading, critique and audit, add assessment with scores, observations and blocks. Each observation names the exact surface/state/target, a concrete finding and its own inspected, hashed screenshot, DOM or native capture (`.png`, `.jpg`, `.jpeg`, `.webp`, `.json` or `.html`). The capture is distinct from the reviewed subject and execution input sources; reusing an input hash as case evidence fails. Synthetic tests write explicit per-case JSON captures and make no browser or native claim. W1–W5 or H1–H9 scores contain every actual dimension. The UI record's overall, lowest and required dimension values must equal that assessment. Numeric thresholds do not override a block, broken interaction or missing observation. Qualitative findings remain the reviewer's judgment; hashes establish identity, not honesty or beauty.

## Receipt Assembly

From the target repository root:

    python "<ui-design-builder-skill-root>/scripts/review_evidence.py" --repo-root . --output-artifact docs/evidence/current-output.json --receipt-out docs/evidence/current-receipt.json

The tool checks recorded input identities and emits ui-evidence/3 with schema, check, result, reviewedArtifact and receipt. The receipt retains tool, method, matrix, results, outputArtifact and executedAt; executedAt is the observed finish time. It does not run a browser or create approval. It rejects stale inputs, traversal, linked paths and overwrites unless --overwrite is explicit. Missing/failed/blocked observations cannot become PASS. Collect new observations after relevant candidate changes; do not rebind old results.

Keep receipts, inspected captures and source artifacts tracked when they are required evidence. Temporary run logs/caches belong outside the product package or under a narrow existing ignore rule. Do not hide canonical HTML, manifests, token sources or evidence with a broad generated-file pattern.

## Frontend Design Usage

Under Wireframe Validation, record:

### Frontend Design Usage

Frontend Design source: docs/design/<folder>/SKILL.md @ sha256:<observed-source-digest>

| Stage | Skill | Artifact | Application |
| --- | --- | --- | --- |
| wireframe | frontend-design @ sha256:<observed-source-digest> | docs/design/wireframes.html @ sha256:<candidate-digest> | Concrete hierarchy, composition and interaction choices |
| direction | frontend-design @ sha256:<observed-source-digest> | docs/design/directions/round/primary.png @ sha256:<capture-digest> | Concrete alternatives evaluated for this direction |
| hifi | frontend-design @ sha256:<observed-source-digest> | docs/design/ui-references/round/index.html @ sha256:<candidate-digest> | Concrete typography, palette, layout and self-check outcomes |

The source path is a retained repository snapshot of the actually observed `frontend-design` `SKILL.md` with `name: frontend-design`. Every stage's Skill SHA-256 equals this snapshot hash. The validator checks the snapshot bytes and current artifact bindings; it cannot prove that an agent truly used the skill. Use repair-1, repair-2 for actual design repairs with their resulting artifact and applied decisions. Wireframe/hifi rows bind the exact current candidates, not a convenient other file. Record only work actually performed. Human direction and final Visual Approval stay in their dedicated sections of ui-design.md.
