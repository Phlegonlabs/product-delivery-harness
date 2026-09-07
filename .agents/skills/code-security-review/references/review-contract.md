# Review Contract

Read this reference for a Delivery Harness security node or any result consumed by another agent.

## Harness Placement

The security review is an integration-stage runtime review. It covers every mission in the candidate and runs after serial integration fixes one integration_head_sha. It must complete before broad final regression and closeout.

The Harness parent owns selection, authorization, dispatch, the durable review receipt, repair routing, and result recording. The security reviewer receives a read-only checkout and returns evidence only. It does not edit PLAN or RUN or start nested agents. If the parent chooses a Codex Security scan as the executor, the parent starts that coordinator directly rather than asking a reviewer child to delegate.

A security integration review is never eligible for the byte-identical-tree skip. Its purpose is a fresh cross-boundary review of the unified candidate.

## Result

Return one object with these fields:

    {
      "review_type": "security",
      "decision": "pass | fix_required | blocked | contract_gap | retryable_failure",
      "reviewed_sha": "<full candidate SHA>",
      "base_sha": "<full base SHA or null>",
      "scope": ["<repository-relative path or subtree>"],
      "exclusions": ["<explicit exclusion and reason>"],
      "trust_boundaries": ["<boundary and protected asset>"],
      "tools": [
        {
          "name": "<tool or manual source review>",
          "status": "passed | findings | skipped | unavailable",
          "evidence": "<command/result or skip reason>"
        }
      ],
      "coverage": {
        "status": "complete | partial",
        "reviewed": ["<surface>"],
        "gaps": ["<gap and consequence>"]
      },
      "findings": [
        {
          "severity": "critical | high | medium | low",
          "confidence": "high | medium | low",
          "cwe": "<CWE id or null>",
          "location": "<path:line>",
          "summary": "<validated issue>",
          "source_to_sink": "<attacker input to impact>",
          "preconditions": "<required attacker position or state>",
          "impact": "<concrete consequence>",
          "counterevidence": "<control or uncertainty checked>",
          "remediation": "<smallest safe fix>",
          "remediation_test": "<observable regression test>"
        }
      ],
      "evidence": ["<exact-SHA and review evidence>"]
    }

Use pass only when reviewed_sha is a full SHA, the checkout is clean, required evidence is present, coverage gaps do not hide a blocking surface, no validated critical or high finding remains, and `exclusions` is an empty list. Under the current contract, a security PASS cannot carry an exclusion or silently narrow the declared scope. Medium and low findings remain visible and follow the project's declared blocking policy. If no policy exists, do not silently suppress them; report them and state the decision rationale.

Use fix_required for a validated code or configuration vulnerability when the active review node declares a bounded repair route. When that route was not planned, return blocked with security_repair_unplanned so the parent can refine PLAN before any write. Use blocked when required capability, authorization, source, or evidence is unavailable. Use contract_gap when safe behavior depends on a missing or contradictory product, architecture, or threat-model decision. Use retryable_failure only for a transient review failure that can be retried without changing scope or authority.

## Harness Evidence

The parent records the review through the existing reserve-review-dispatch and record-review-attempt transitions. Save the returned object as JSON outside the reviewed repository and pass it with `--security-result`. The transition rejects duplicate keys and validates the review type, decision, reserved and current SHA, dispatched base, exact PLAN scope, exclusions, trust boundaries, required tools, coverage, findings, and evidence before retaining the normalized object and its digest. A PASS must bind reviewed_sha to the current integration head and carry no exclusions. Security reservation and completion recheck the live integration checkout: the exact integration branch and HEAD, clean status (allowing only the exact tracked RUN exception), and ancestry from the current batch base. A mismatch blocks completion. Required security nodes cannot be skipped or superseded at closeout. Any repair changes the candidate, invalidates the prior PASS and downstream final-gate evidence, and requires a new security review.

When a managed route cannot provide a fresh eligible reviewer, return independent_reviewer_unavailable. When a project-required security tool is unavailable, return security_tool_unavailable:<tool>. When required network evidence was not authorized or available, return security_network_unavailable.
