# Complete Package Review In Chat

Apply this contract at the two owner gates: Product Definition Approval and
Visual Approval. Present all current documents in one user-visible chat
response so the owner can review the whole package. Opening panels or linking
only `docs/DOCUMENTS.md` does not replace the individual document links.

## Inventory And Links

Use the current `docs/DOCUMENTS.md`, package manifests and actual output paths to
reconcile the inventory. Include every produced or retained current document
used by this round, including requested optional artifacts and review evidence.
Group the list by Product Definition, UI and project/operational documents.
Each item gives a verified absolute Markdown link, a short purpose and its actual
status: draft, approved, pending, blocked or retained. List each file separately;
do not hide sibling pages or evidence behind a directory link or “other files”.

- Product Definition includes `PRD.zh-TW.md` and `architecture.zh-TW.md` first,
  their English canonical sources, `stack-decisions.md`, produced research
  assessment and market research, and a requested `implementation-plan.md`.
- UI includes `ui-design.md`, this round's direction studies, the HiFi entry and
  every manifest-listed sibling page, review reports, captures and motion
  evidence, and the required design-system Markdown/JSON/HTML outputs.
  Include retained wireframes or design-system sources only when this round
  uses them; identify their historical status without renewing approval.
- Include applicable `DOCUMENTS.md`, Deployment, context files and
  the current Epic/task record. Separate superseded/archive paths from current
  review inputs. Exclude credentials, caches and unrelated historical packages.

Verify each link target before sending. Product Definition uses actual staging
paths while staged and canonical paths after publication. Visual Approval uses
final logical paths in the authorized publication checkout, then canonical
source paths after publication; never collect it on `.ui-staging` paths.
List a missing required file as a gap without inventing a link or a PASS. A
later-stage output, such as design-system compilation before Visual Approval,
is pending and does not block an earlier gate that does not require it.

## Review And Handoff

State the review focus, existing approval statuses and unresolved work. Request
the gate's existing explicit human decision and wait. After publication,
deferred publication or handoff, do not repeat the inventory: report only the
published, moved and archived paths with verified links and their approval
statuses. The Visual Approval inventory already lists the Product Definition
documents, so no combined handoff inventory follows it.
Unchanged approved decisions keep their approval;
presenting links never grants approval, publication, installation or
implementation authority.
