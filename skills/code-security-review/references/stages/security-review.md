# Security Review Stage

## Path Interpretation

Outside a real Markdown link, `references/...`, `scripts/...`, and sibling skill paths such as `../delivery-harness/...` are logical installed-skill paths from `<code-security-review-skill-root>`. `docs/...` remains repository-relative.

## Required Inputs

Resolve before review:

- repository root and effective repository instructions;
- exact full candidate SHA and, when reviewing a change, its base SHA;
- review scope and explicit exclusions;
- applicable SECURITY.md, threat model, architecture, data boundaries, and deployment assumptions;
- required project security commands or evidence;
- whether an independent reviewer, network access, or a particular scanner was explicitly required and authorized.

Use a clean checkout at the candidate SHA. A dirty or uncommitted target may receive advisory analysis, but it cannot receive a security PASS.

## Workflow

1. Verify the repository, candidate SHA, clean checkout, scope, and applicable instructions.
2. Map entry points, trust boundaries, privileged operations, sensitive data, external calls, persistence, and deployment configuration.

    When an exact-scope review can benefit from a security baseline, consult `../delivery-harness/references/reference-selection.md` and only the relevant material in `../delivery-harness/references/option-library/security.md`. Use it to frame the declared scope; it is not a second PASS standard, compliance claim, or replacement for source-to-sink review.
3. Trace attacker-controlled input to sensitive sinks. Check authentication and authorization, tenant isolation, injection, XSS and CSRF, SSRF, path and command execution, secret exposure, cryptography, unsafe deserialization, dependency and supply-chain configuration, concurrency, replay, and fail-open behavior where applicable.
4. Run only already-installed, explicitly read-only local security commands that apply to the declared scope. Record each command, result, and any omitted coverage. A PASS needs at least one review tool or manual source review recorded as `passed` or `findings`; an all-skipped or unavailable tool set cannot PASS.
5. Validate each candidate finding from source to sink. Record preconditions, reachable impact, counterevidence, severity, confidence, and a concrete remediation test.
6. Return the exact-SHA result defined in [Review Contract](../review-contract.md). A PASS is complete for the declared scope and cannot carry exclusions or silently narrow coverage. Do not change code or suppress a finding merely to reach PASS.

## Handoff

Return all validated findings in one pass. For a managed review, return the exact JSON object from [Review Contract](../review-contract.md), with contract_adoption_check beside it when that contract applies; the parent does not reconstruct missing fields. A fix_required result routes back to Delivery Harness as a bounded repair on a separately authorized write path; contract_gap routes to the product or architecture owner. The Review Contract's targeted re-check covers the repaired SHA.
