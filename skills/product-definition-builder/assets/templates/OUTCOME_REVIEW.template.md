# Outcome Review

This strict post-deployment record is written only after the real measurement window closes. A single-target record binds one production architecture target, release SHA/artifact, deployment PASS, and Activation SHA. A multi-target record adds an ordered target set plus immutable per-target reviews and target-bound measurements; its top-level verdict is a deterministic aggregate and no target identity overwrites another.

## Record

- Schema: outcome-review/1
- Product: <fill>
- Outcome owner: <human owner>
- Production release target: <architecture release-target-id>
- Production release targets: <omit for single target; otherwise `target-set: <id>, <id>, ...` in review order>
- Release SHA: <full lowercase Git SHA>
- Artifact / build identity: <exact artifact, build, or deployment identity>
- Deployment identity: <release-name;exact-channel;artifact/build-identity>
- Deployment checked: <RFC3339>
- Deployment status: PASS
- Activation record: docs/ACTIVATION.md
- Activation sha256: <lowercase SHA-256 of current docs/ACTIVATION.md>
- Reviewed on: <YYYY-MM-DD>
- Verdict: <no_change / enhancement / incident>

## Activation Sources

List every verified `MS-*` source from Activation whose target, SHA, and artifact/build identity match this release. A configured, blocked, stale, or mismatched source cannot support this review.

| MS ID | Release binding | Owner | Verified at | Evidence |
| --- | --- | --- | --- | --- |
| MS-001 | <target>@<sha>#<artifact> | <human owner matching Activation> | <latest PASS evidence RFC3339> | <Activation EVID-* IDs and bounded non-secret evidence> |

## Measurements

| Signal | Baseline | Target | Window start | Window end | Actual | Source ID |
| --- | --- | --- | --- | --- | --- | --- |
| <PRD metric or required TEST-ID> | <exact PRD baseline or none recorded> | <exact PRD target / expected signal> | <YYYY-MM-DD> | <YYYY-MM-DD> | <measured value> | MS-001 |

## Target Reviews

Include this section when `Production release targets` names more than one target. Keep one row per production target in the declared order. Each row must use its own SHA, artifact, deployment identity, verified Activation source IDs, and per-target verdict.

| Release target | Release SHA | Artifact / build identity | Deployment identity | Deployment checked | Deployment status | Activation sources | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <production target> | <full lowercase Git SHA> | <artifact> | <release-name;channel;artifact> | <RFC3339> | PASS | <MS IDs> | <no_change / enhancement / incident> |

## Target Measurements

Include this section for a multi-target review. Repeat every PRD metric and required `TEST-*` signal for every target; each row names the exact target and matching `MS-*` source.

| Signal | Release target | Baseline | Target | Window start | Window end | Actual | Source ID |
| --- | --- | --- | --- | --- | --- | --- | --- |
| <PRD metric or required TEST-ID> | <production target> | <exact baseline> | <exact target / expected signal> | <YYYY-MM-DD> | <YYYY-MM-DD> | <measured value> | MS-001 |

## Feedback

| Fact | Source ID | Observed |
| --- | --- | --- |
| <post-deployment fact> | MS-001 | <bounded non-secret observation> |

For a multi-target record use `Fact | Release target | Source ID | Observed` and bind each fact to a verified source for that exact target.

## Incident Response

Leave one `none` row for a non-incident verdict. An incident must use one typed containment (`rollout halted`, `rollback`, `forward fix`, `feature disabled`, `traffic reduced`, `access revoked`, or `monitoring only`), name a human owner, and route to concrete next-record entries under `PRD Risks` and `PRD Open Questions`.

| Incident | Containment | Human owner | PRD risk routing | PRD open question routing | Evidence |
| --- | --- | --- | --- | --- | --- |
| none | n/a | n/a | n/a | n/a | n/a |

## Verdict

Verdict: <no_change / enhancement / incident> — <one-line reason>

## Open Follow-ups

| Follow-up | Route |
| --- | --- |
| none | none |
