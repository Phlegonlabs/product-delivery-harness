# Host Execution Trust

Current verifier declarations use explicit `execution.isolation: "host"` only.
Commands use the project's toolchain in the bound checkout with exact source/Git guards and execution-key evidence.
Record command identity, host, cwd, exact SHA, exit status and logs.
Host commands have current user permissions; a worktree and read-only declaration do not provide process confinement.
A verifier needing a separate checkout uses its own authorized worktree.
Historical container/runtime-image protocols run only from their [exact pinned bundle](legacy-pins.md#container-verifiers-before-066).

The supported test/runtime baseline is Python 3.10 or newer (CI runs 3.13).
Install and verify the repository test dependencies from the repository root:

```text
python -m pip install -r skills/delivery-harness/requirements-test.txt
python -c "import PIL, pyflakes; print(PIL.__version__)"
```

`Pillow` is required by visual evidence checks; `pyflakes` is required by the
canonical verification suite. Do not silently substitute an older Python or a
different image library in a candidate gate.
