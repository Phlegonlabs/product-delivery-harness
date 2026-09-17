# Host execution and optional container trust

New PLANs default to explicit `execution.isolation: "host"`. Host verifiers run declared commands with the project's installed toolchain in the bound checkout; they do not need Docker, Podman, an image, or an administrator-managed container policy. Record command identity, host, cwd, exact SHA, exit status, and logs. Commands run with the current user's permissions; a worktree and source guards are not process isolation.

Existing `container` declarations stay container-only. Never retry them on the host after a missing runtime or failed preflight. Switching a declared mode requires a PLAN revision and fresh evidence.

Optional container verifiers use an administrator-installed Docker or Podman executable.
The Harness never trusts the first `docker`/`podman` name found in a repository,
worktree, current directory, or user-writable `PATH` entry.

## Optional container setup

On Windows, install the native `docker.exe` or `podman.exe` under `Program Files`
or the Windows system directory. Do not point a PLAN at `.cmd`, `.bat`, `.ps1`,
or an executable in a checkout, `%TEMP%`, `%APPDATA%`, or a user-owned tools
directory. The preflight checks the canonical path, native `.exe` suffix, ACL-safe
machine location, and non-reparse components. The runtime, Git, and browser
launcher checks inspect the file's owner and DACL separately from its parent;
a protected directory does not make a file with a user-write ACE trusted.
A Windows administrator should
verify the path with `Get-Item` and `Get-Acl`; all parent directories must deny
ordinary users write access.

On POSIX, install the native executable in `/usr/bin`, `/bin`, `/usr/local/bin`,
or another administrator-managed `/opt` path. Every component must be a regular
directory owned by root and not writable by group or other users; the executable
must be root-owned and executable. A symlink, junction, or user-writable shadow
path fails before the version probe.

The observed path, SHA-256, owner/mode proof, and non-reparse result are retained
in `runtime_probe.trust` in RUN evidence. Execution rechecks the proof and holds a
descriptor (POSIX) or no-delete native handle (Windows) across the probe and
container invocation. A fake native executable with a matching name or hash is
therefore not trusted.

## Verification

Run the read-only preflight from the repository root:

```text
python "<delivery-harness-skill-root>/scripts/validate_harness_plan.py" --plan <PLAN.md> --probe-sandboxes
```

The command is diagnostic only. A managed run must still record the fresh
observation with `harness_transition.py record-observation`. Only declared
container verifiers require container probes and machine trust evidence; a
host-only PLAN records its PLAN/host binding without those probes.

The supported test/runtime baseline is Python 3.10 or newer (CI runs 3.13).
Install and verify the repository test dependencies from the repository root:

```text
python -m pip install -r skills/delivery-harness/requirements-test.txt
python -c "import PIL, pyflakes; print(PIL.__version__)"
```

`Pillow` is required by visual evidence checks; `pyflakes` is required by the
canonical verification suite. Do not silently substitute an older Python or a
different image library in a candidate gate.
