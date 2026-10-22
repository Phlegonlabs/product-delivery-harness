# Archive publication

Publication of archive-only candidate A runs on the machine that runs the Harness. There is no separate host, signing key or machine policy.

1. `python "<delivery-harness-skill-root>/scripts/push_archived_candidate.py" prepare --repo-root <checkout> --archive <archive-dir> --remote <name> --request-out <absolute-path-outside-checkout>` verifies A and prints the argv. A must be the clean checked-out HEAD, a direct child of C, with a valid receipt and a C-to-A diff inside the archive allowlist. It writes one request outside the checkout with the push URL, branch ref, A and C. It never contacts the network and never pushes.
2. The parent runs the printed argv only after the owner's exact instruction naming the SHA and branch. The argv uses `git push --no-force` to the exact URL. Never add a force or lease flag; Git refuses a non-fast-forward.
3. `... verify-receipt --repo-root <checkout> --request <request>` reads the remote ref back from outside the repository. It passes only when the ref equals A. The parent records the SHA and ref in the Epic.

A private HTTPS remote uses the machine's own Git credential helper. Never put a credential in the URL, request or Epic. Publishing grants no protected-branch landing.
