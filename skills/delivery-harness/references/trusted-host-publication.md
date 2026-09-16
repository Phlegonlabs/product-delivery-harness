# Trusted-host archive publication

The local Harness prepares an immutable archive request and emits a URL-only,
no-force `git push` handoff. It never invokes that argv. Publication evidence is
created on a separately administered host with the shell-specific commands
below.

The helper is intentionally fail-closed. It requires the administrator's
machine policy and OpenSSH verifier, reloads and hashes the request and attempt,
revalidates the exact URL and remote pre-state, sanitizes Git configuration, and
executes only the request-bound no-force URL argv. It signs the canonical
evidence payload with the supplied machine key, writes a detached signature, and
then reads the exact branch ref back before writing the evidence file. Set
`HARNESS_TRUSTED_HOST=1` on that host; without it the command exits before any
Git side effect. Agents and the local executor must not set the variable or run
the helper as a workaround.

The allowed-signers policy is exactly one OpenSSH line:

```text
principal ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... comment
```

Use the public key that matches the machine signing key; never put a private key
in the registry, policy file, repository, request, attempt, receipt, or evidence.

Generate or import the signing key on the trusted host, outside the checkout.
On Windows keep the private key under `C:\ProgramData\ProductDeliveryHarness`
with an administrator-only ACL; on POSIX keep it under
`/etc/product-delivery-harness/` or another root-owned directory with mode
`0600`. Derive the public key and policy line from that key, then verify both
before preparing a request:

```bash
ssh-keygen -t ed25519 -N '' -f /etc/product-delivery-harness/machine-key
ssh-keygen -y -f /etc/product-delivery-harness/machine-key > /etc/product-delivery-harness/machine-key.pub
chmod 600 /etc/product-delivery-harness/machine-key
```

The policy hash and principal must match the derived public key and the
trusted-host verifier must report the same machine path/hash. Rotate by
installing a new key and allowed-signers line, verifying the new pair, and
waiting for all receipts bound to the old policy to close before removing the
old private/public key files. Never delete a key while a request or attempt
still references it.

Run this in an elevated PowerShell session on Windows, replacing the example
line with the administrator-approved principal and public key:

```powershell
$SignerLine = 'principal ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... comment'
New-Item -Path 'HKLM:\SOFTWARE\ProductDeliveryHarness' -Force | Out-Null
New-ItemProperty -Path 'HKLM:\SOFTWARE\ProductDeliveryHarness' -Name 'ArchivePushAllowedSigners' -PropertyType String -Value $SignerLine -Force | Out-Null
Get-ItemPropertyValue -Path 'HKLM:\SOFTWARE\ProductDeliveryHarness' -Name 'ArchivePushAllowedSigners'
```

Run this as an administrator on POSIX:

```bash
SIGNER_LINE='principal ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAA... comment'
sudo install -d -o root -g root -m 0755 /etc/product-delivery-harness
printf '%s\n' "$SIGNER_LINE" | sudo tee /etc/product-delivery-harness/archive-push.allowed_signers >/dev/null
sudo chown root:root /etc/product-delivery-harness/archive-push.allowed_signers
sudo chmod 0644 /etc/product-delivery-harness/archive-push.allowed_signers
sudo cat /etc/product-delivery-harness/archive-push.allowed_signers
```

Read back the canonical policy ID, principal, policy hash, verifier path, and
verifier hash before preparing a publication request:

```text
python "<delivery-harness-skill-root>/scripts/trusted_host_publication.py" verify-policy --repo-root <absolute-repository-root>
```

Rotation is an administrator operation: write the replacement line, run
`verify-policy`, create new requests only after the new ID/hash is observed, and
remove the old key only after every in-flight receipt bound to it is closed.
To disable publication after reconciliation, use elevated PowerShell
`Remove-ItemProperty -Path 'HKLM:\SOFTWARE\ProductDeliveryHarness' -Name
'ArchivePushAllowedSigners'` or POSIX
`sudo rm -- /etc/product-delivery-harness/archive-push.allowed_signers`.
These commands intentionally disable new preparation/recovery and are never
agent actions.

## Execute and recover one publication

The trusted host must be checked out at clean candidate A. Use one shell's
syntax end to end. POSIX:

```bash
export HARNESS_TRUSTED_HOST=1
python "<delivery-harness-skill-root>/scripts/trusted_host_publication.py" execute \
  --request /absolute/external/request.json \
  --attempt /absolute/external/attempt.json \
  --evidence-out /absolute/external/execution-evidence.json \
  --signing-key /administrator/private/machine-key \
  --trusted-host-issuer host-id
unset HARNESS_TRUSTED_HOST
```

PowerShell:

```powershell
$env:HARNESS_TRUSTED_HOST='1'
python "<delivery-harness-skill-root>/scripts/trusted_host_publication.py" execute --request C:\external\request.json --attempt C:\external\attempt.json --evidence-out C:\external\execution-evidence.json --signing-key C:\ProgramData\ProductDeliveryHarness\machine-key --trusted-host-issuer host-id
Remove-Item Env:HARNESS_TRUSTED_HOST
```

The helper recomputes request and attempt digests, revalidates archive authority,
branch, clean candidate A, exact URL and remote pre-state, uses sanitized Git,
binds the OS-managed verifier, performs only the request-bound no-force push,
reads back A, signs canonical evidence, and creates the evidence path once. Move
that evidence to the recovery host only through the already-bound external path,
then run the documented `push_archived_candidate.py recover` command. Never edit
request, attempt, signature, or evidence bytes by hand.

Evidence records must conform to `trusted-host-publication.schema.json` and are
verified by `push_archived_candidate.py recover` before a receipt can close.

## Private HTTPS credentials

An administrator may install a non-secret JSON policy in the Windows 64-bit HKLM `SOFTWARE\ProductDeliveryHarness` value `ArchivePushCredentials` (REG_SZ), or `/etc/product-delivery-harness/archive-push.credentials.json` on POSIX. The POSIX file and all parents must be root-owned, non-link, and not group/world writable. This is a separate administrator action, never an agent-created credential workaround.

The closed object has `endpoints` (exact canonical HTTPS repository URLs, without credentials, query, or fragment), `helper` (absolute path to an administrator-installed native credential helper), and `sha256` (its lowercase raw-file digest). The executable must pass the same OS-protected install, file/parent ownership or ACL, and non-reparse checks as Git. Use the helper's own approved login/storage setup; never place a token or password in this policy.

Prepare, trusted-host push, and readback/recovery use isolated Git configuration with only that approved helper and `credential.useHttpPath=true`; terminal and GCM interactive prompts, HTTP redirects, and Git/GCM credential tracing are disabled. Repository/user helpers, askpass overrides, and config injection remain excluded. A matching policy adds `credential_binding` to the v3 request, binding the policy bytes, helper path/hash, and exact endpoint; its signed request digest also binds the attempt and execution evidence. Old requests without this field remain valid only when no helper policy applies. Installing, rotating, or removing a matching policy invalidates pending requests; reconcile them before rotation. No publication action is authorized by installing a policy. Helper/Git error output is not copied into evidence because it can contain credential material.
