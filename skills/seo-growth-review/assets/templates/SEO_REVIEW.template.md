# SEO Growth Review

Use this template only when the owner asks to save a lifecycle public-release review. Save it once at `docs/seo/reviews/YYYY-MM-DD-<slug>.md`; do not overwrite an earlier issue. An inline standalone audit does not create this file.

## Record

- Schema: seo-review/1
- Mode: <baseline / growth_review / traffic_drop>
- Review type: lifecycle_public_release
- Review owner: <human owner>
- Production release target: <architecture release-target-id>
- Release SHA: <full lowercase Git SHA>
- Artifact / build identity: <exact artifact or build identity>
- Deployment identity: <release-name;exact-channel;artifact/build-identity>
- Deployment checked: <RFC3339>
- Production domain: <lowercase production host>
- Data cutoff: <RFC3339>
- Activation record: docs/ACTIVATION.md
- Activation sha256: <lowercase SHA-256 of current docs/ACTIVATION.md>
- Review date: <YYYY-MM-DD>

## Verified Sources

| MS ID | Scope | Release binding | Source role | Data cutoff | Evidence |
| --- | --- | --- | --- | --- | --- |
| MS-001 | <exact Activation source target scope> | <target>@<sha>#<artifact> | <role derived from Activation retrieval> | <latest PASS Activation evidence RFC3339> | <Activation EVID-* IDs and non-secret verification evidence> |

## Measurement Integrity

| Check | Result | Evidence |
| --- | --- | --- |
| Production scope | PASS | <canonical host and route scope match> |
| Release identity | PASS | <target, SHA, artifact, and deployment match> |
| Date coverage | PASS | <complete periods and cutoff evidence> |

## Technical Findings

| Priority | Finding | Scope | Evidence | Impact | Route |
| --- | --- | --- | --- | --- | --- |
| <blocker / high / medium / low> | <observed defect> | <route or template> | <observed / estimated / hypothesis> | <effect> | <product_activation / product_definition / delivery / connector / observe_later / owner> |

## Growth Opportunities

| Priority | Query or topic | Intent / type | Evidence | Current page | Action / route | Follow-up metric |
| --- | --- | --- | --- | --- | --- | --- |
| <high / medium / low> | <query or topic> | <existing_page / ctr / content_gap / decay / intent_mismatch / cannibalization / internal_link / trust_value> | <observed / estimated / hypothesis> | <URL or none> | <action / product_activation / product_definition / delivery / connector / observe_later / owner> | <metric and window> |

## What To Do First

1. <Smallest ordered action; technical blockers precede growth experiments.>

## Limits And Next Window

<What is not observable, the exact data that would settle it, and the next complete comparison window.>
