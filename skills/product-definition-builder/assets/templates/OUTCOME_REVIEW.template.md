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
- Prior outcome sha256: <required only when --prior-outcome appends immutable history>

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

Include this section for a multi-target review. Repeat each PRD metric and required `TEST-*` signal only for the targets listed for that signal in Activation Outcome Coverage; each row names the exact target and matching `MS-*` source.

Use only the targets listed for that signal in Activation Outcome Coverage. Match any numeric PRD window duration exactly and start/end strictly after that target's Deployment checked date.

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

For a multi-target review, use `Incident | Release target | Containment | Human owner | PRD risk routing | PRD open question routing | Evidence`. Every incident row must use a verified source bound to that target, and an incident row is required exactly for each target whose Target Review verdict is `incident`; the aggregate verdict must follow the target verdicts.

Replace the active single-target table below with this shape for a multi-target review:

```markdown
| Incident | Release target | Containment | Human owner | PRD risk routing | PRD open question routing | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| <none or incident> | <production target> | <typed containment or n/a> | <human or n/a> | <PRD Risks routing or n/a> | <PRD Open Questions routing or n/a> | <MS-* or n/a> |
```

| Incident | Containment | Human owner | PRD risk routing | PRD open question routing | Evidence |
| --- | --- | --- | --- | --- | --- |
| none | n/a | n/a | n/a | n/a | n/a |

## Verdict

Verdict: <no_change / enhancement / incident> — <one-line reason>

## Open Follow-ups

| Follow-up | Route |
| --- | --- |
| none | none |

Use no substantive follow-up for `no_change`; route `enhancement` to an
enhancement request and `incident` to a risk or open question.
