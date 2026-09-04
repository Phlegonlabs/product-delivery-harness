# Deployment

The deployment record for this repository: the platform model, the setup only a human performs, and the live environment status. The governing semantics live in the Full-Stack Harness `deployment-contract.md`; this file is the project's filled-in instance. Keep it at `docs/DEPLOYMENT.md` and update it whenever the platform, environments, or verification method change.

## Record

- Platform: <cloudflare | vercel | aws | any lowercase id>
- Mode: git_connected (the platform builds on push) | ci_connected (a repository CI workflow deploys on push) | manual (a recorded deploy command the user runs)
- Production branch: the repository's resolved default branch (what lands there is the production candidate)
- Preview: tracks non-default branch pushes; a preview PASS never proves production
- Production URL: <url>
- Preview URL pattern: <pattern>
- Deployed-commit check: <platform API/CLI command or response header>
- Protected resources preview must never bind: <databases, buckets, secrets, domains>

## Human Setup Checklist

These steps are performed by a person with platform access; the Harness never performs, triggers, or reconfigures them. Check them off as completed.

### Git connection (git_connected mode)

- [ ] Connect the repository to the platform (Cloudflare Pages/Workers, Vercel project, or AWS Amplify app).
- [ ] Set the production branch to the repository's default branch.
- [ ] Enable automatic preview builds for non-default branches.

### CI connection (ci_connected mode)

- [ ] Create the project from the CLI (for example `wrangler pages project create <name> --production-branch <default-branch>`) and run the first deploy yourself.
- [ ] Add the repository workflow that deploys on push: the production branch to production, every other branch to a preview URL.
- [ ] Store the platform API token as a repository secret; never place it in the repository itself.
- [ ] Keep preview and production variables and secrets separate in the workflow, exactly as in a git-connected project.

### Environments

- [ ] Create separate preview and production environments with separate variables and secrets.
- [ ] Point preview at non-production databases, buckets, and auth providers; never bind a production resource to preview.
- [ ] Attach the production domain to the production environment only.

### Verification access

- [ ] Confirm the deployed-commit check command runs read-only with the available credentials.
- [ ] Record the check result for one known deployment below.

## Platform Notes

- cloudflare: prefer native Preview URLs; per-branch disposable Workers only when a feature such as Durable Objects requires them, with a reserved name prefix and a protected list of permanent Workers. Production is a separately gated environment, never a side effect of preview. `ci_connected` bootstraps the same model with `wrangler pages project create` plus a push-triggered CI workflow; a Wrangler-created Direct Upload project can never be converted to git-connected.
- vercel: preview per push, production on the default branch; environment scoping in project settings is the protected-production boundary.
- aws: Amplify branch mapping — default branch to production, non-default branches to automatic previews; separate backend environments and secrets per branch mapping.
- generic: record branch-build semantics when the platform supports them; otherwise record `manual` with the deploy command and the read-only check that follows.

## Environment Status

| Environment | URL | Expected head | Deployed SHA | Checked | Status |
| --- | --- | --- | --- | --- | --- |
| preview | | | | | |
| production | | | | | |

Verification is read-only: record what deployed, compare it to the expected head, and route any mismatch to the owner or a new mission — never redeploy from here.
