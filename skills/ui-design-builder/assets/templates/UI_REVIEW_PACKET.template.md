# UI Review Packet: <assignment ID> — <role>

One packet per lead grader, Impeccable operator or scoped re-review dispatch. Link rule sections; do not copy their values. Check the filled packet's UTF-8 size against `max_message_bytes` before launch.

```text
Assignment:
- Assignment ID: <id>
- Attempt: <attempt id>
- Role: <lead grader | Impeccable operator | scoped re-review>
- Route caps: time <seconds> / turns <n> / max_message_bytes <n>

Frozen inputs (path @ sha256):
- PRD: <path @ sha256:hash>
- Architecture: <path @ sha256:hash>
- Stack: <path @ sha256:hash>
- ui-design.md: <path @ sha256:hash>
- HiFi entry: <docs/design/ui-references/<run-id>/index.html @ sha256:hash>
- HiFi pages: <every manifest page path @ sha256:hash>
- Selected direction: <VD-* and its study path @ sha256:hash>
- Journey map: <docs/design/directions/<round>/journeys.html @ sha256:hash>
- Impeccable authorization: <where the explicit workflow authorization is recorded; Impeccable operator only>

Read:
- <ui-design-builder-skill-root>/references/ui-grading-rubric.md
- <ui-design-builder-skill-root>/references/output-contract.md#reviewer-navigation-and-design-specifications
- <ui-design-builder-skill-root>/references/output-contract.md#connected-hifi-package
- <ui-design-builder-skill-root>/references/output-contract.md#hifi-review
- <ui-design-builder-skill-root>/references/ui-design-pass.md#browser-and-human-visual-approval
- Impeccable SKILL.md: <path @ sha256:hash; Impeccable operator only>

Do not read:
- ui-design-intake.md, design-translation.md, design-reference-guide.md, motion-and-media-routing.md, page-design-profiles.md, enhancement-recommendations.md

Write scope:
- docs/design/evidence/<run-id>/ only

Scoped re-review only:
- Defect ledger: <docs/design/evidence/<run-id>/defect-ledger.json @ sha256:hash>
- Prior candidate: <SHA-256 of the last reviewed candidate>
- Source diff: <diff path or commit range>
- Direct consumers: <pages and states that render a changed source>
- Closure cases: <the ledger families' acceptance cases>
- Tolerance source: <ui-design.md Approved target `tolerance`>

Return:
- Verdict: <PASS | FAIL | BLOCKED>
- Candidate SHA-256: <the reviewed candidate>
- Findings: <each with its capture path @ sha256:hash; blocking findings apart from non-blocking notes>
- ui-output/3: <path @ sha256:hash>
- Receipt: <ui-evidence/3 path @ sha256:hash>
- Commands run: <exact commands>
```
