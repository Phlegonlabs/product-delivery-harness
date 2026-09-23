# Design Freshness Before Implementation

After a skill update and before implementation, apply the shared document-sync check, then inspect the design dependency chain: PRD/architecture/stack → wireframe → every HiFi page → required design-system pair/preview. A newer version or file date alone does not invalidate a design. A disk update is not a session reload; unknown loaded identity remains unknown.

Record in the existing task or UI handoff: actual loaded/installed skill digests, relevant artifact paths/hashes and upstream inputs, implementation status (`not_started`, `started`, `unknown`) with evidence, changed rule, affected scope, required rechecks, retained decisions and result. Do not infer `not_started` merely from an absent RUN. No new approval registry is needed.

Use `scripts/check_design_freshness.py` with a retained observation manifest to detect byte drift. Its report is read-only and never grants approval or regenerates files. The manifest is observation evidence, not a second editable specification. Unknown provenance requires inspection, not a fabricated old digest. Include every manifest-listed HiFi sibling, not just index.html. The existing full UI checker remains mandatory and establishes completeness; this helper can only assess inventoried paths.

| Changed source | Next action |
| --- | --- |
| Unrelated docs or wording in skill guidance | Inspect semantic impact; retain unaffected design |
| Applicable checker | Rerun checks on unchanged artifacts first |
| Wireframe geometry, controls, language or motion rules | Inspect affected wireframe cases and downstream HiFi |
| Visual-direction or native guidance | Review affected HiFi/platform cases; preserve valid structure |
| Product requirements or copy | Return to Product Definition and renew affected gates |
| Unknown loaded skill or source identity | Observe/restart as appropriate; do not claim latest-rule verification |

When implementation has not started, resolve applicable design gaps before coding. When it has started, route the accepted delta through the existing enhancement workflow; never restart completed execution nodes solely because a skill changed. Rerun required validation, not all authoring by default. Present a short affected/retained/blocked list before repairs. Existing authorization covers same-scope design repairs, not installation, publication, archive, provider calls or invented human approval.

Retain historical receipts; a changed candidate receives fresh evidence and affected human decisions. A check-only rerun on identical design bytes does not require reselecting brand direction. Explicit full redesign follows `design-translation.md` and overrides incremental preservation only for its authorized design scope.

## Observation Input

From the target repository root:

```text
python "<ui-design-builder-skill-root>/scripts/check_design_freshness.py" --repo-root . --baseline <existing-task-evidence/design-observation.json> --skills-root <installed-sibling-skills-root> [--loaded-digest <observed-session-digest>]
```

Input shape: `{ "schema": "design-observation/1", "skillDigest": "<sha256 or null>", "implementation": "not_started|started|unknown", "implementationEvidence": "<observed evidence>", "artifacts": [{ "path": "docs/design/wireframes.html", "sha256": "<sha256 or null>", "inputs": [{"path": "docs/product/PRD.md", "sha256": "<sha256 or null>"}] }] }`. Use one artifact entry per current design file, including HiFi siblings and compiled outputs. Inputs can name other design files. Null means unknown, never current. Store only non-secret product/design paths. Exit 0 means inventoried bytes and observed skill identities match, not design approval; 1 means review required; 2 means invalid input. The helper propagates stale upstream inputs to dependent artifacts even when their own bytes match.

## After Delivery

Routine maintenance is not a fresh design round. Pass `--task-record docs/epics/<current-epic>.md` when its existing record declares `Design workflow: maintenance`. The report labels old design drift `historical`; it does not claim those bytes are current, reuse browser proof or approve the product. Verify current requirements and accepted changes separately. Skill changes are classified as shell, format, rule or product-design changes before applying them; none automatically revokes all prior design decisions.
