#!/usr/bin/env python3
"""Safely install the Cloudflare Worker deployment lifecycle template."""

from __future__ import annotations

import argparse
import errno
import json
import os
import re
import secrets
import shlex
import stat
import sys
from pathlib import Path


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = SKILL_ROOT / "assets" / "template"
WORKER_NAME_PATTERN = re.compile(r"^[a-z][a-z0-9-]*$")
DESTINATIONS = (
    (Path(".cloudflare/branch-workers.json"), Path(".cloudflare/branch-workers.json")),
    (
        Path(".github/workflows/cloudflare-branch-workers.yml"),
        Path(".github/workflows/cloudflare-branch-workers.yml"),
    ),
    (
        Path(".github/workflows/cloudflare-production.yml"),
        Path(".github/workflows/cloudflare-production.yml"),
    ),
    (Path("scripts/cloudflare-branch-worker.mjs"), Path("scripts/cloudflare-branch-worker.mjs")),
    (
        Path("scripts/cloudflare-branch-worker.test.mjs"),
        Path("scripts/cloudflare-branch-worker.test.mjs"),
    ),
)


def is_link(path: Path) -> bool:
    """Return whether a path can redirect traversal outside the repository."""

    is_junction = getattr(path, "is_junction", None)
    return path.is_symlink() or (is_junction is not None and is_junction())


def destination_path_problem(path: Path, repo: Path) -> str | None:
    """Return a safety error when a destination can escape the repository.

    Existing symlinks and Windows junctions are rejected even when they resolve
    back inside the repository.  Rejecting them avoids silently replacing a
    path whose meaning can change between the preview and the write.
    """

    try:
        relative_path = path.relative_to(repo)
    except ValueError:
        return f"destination is outside the repository: {path}"

    candidate = repo
    for part in relative_path.parts:
        candidate /= part
        if is_link(candidate):
            kind = "target" if candidate == path else "ancestor"
            return f"symlinked destination {kind}: {candidate}"

    try:
        path.resolve(strict=False).relative_to(repo.resolve(strict=True))
    except (OSError, RuntimeError, ValueError):
        return f"resolved destination is outside the repository: {path}"
    return None


def validate_destinations(files: dict[Path, bytes], repo: Path) -> None:
    """Fail before any write if one planned destination is unsafe."""

    problems = [
        problem
        for path in files
        if (problem := destination_path_problem(path, repo)) is not None
    ]
    if problems:
        raise ValueError("; ".join(problems))


class SecureInstallerError(ValueError):
    """A destination cannot be written with the installer's safety contract."""


class ExistingFilesError(SecureInstallerError):
    """The caller did not authorize replacing an existing destination."""

    def __init__(self, paths: list[Path]):
        self.paths = paths
        super().__init__("existing lifecycle files require --overwrite")


class UnsupportedSecureWriteError(SecureInstallerError):
    """The host does not provide the required no-follow dirfd primitives."""


def secure_write_supported() -> bool:
    """Return whether this host supports the installer's safe write primitive."""

    if os.name != "posix":
        return False
    required_flags = ("O_CLOEXEC", "O_DIRECTORY", "O_NOFOLLOW")
    if any(not hasattr(os, flag) for flag in required_flags):
        return False
    required_dirfd = (os.open, os.mkdir, os.stat, os.unlink, os.rename, os.link)
    supports_dir_fd = getattr(os, "supports_dir_fd", set())
    supports_follow_symlinks = getattr(os, "supports_follow_symlinks", set())
    return (
        all(function in supports_dir_fd for function in required_dirfd)
        and os.stat in supports_follow_symlinks
        and os.link in supports_follow_symlinks
    )


def require_secure_write_support() -> None:
    if not secure_write_supported():
        raise UnsupportedSecureWriteError(
            "safe apply requires POSIX openat-style dirfd and O_NOFOLLOW support"
        )


def _is_symlink_stat(result: os.stat_result) -> bool:
    return stat.S_ISLNK(result.st_mode)


class SecureRepository:
    """Write planned files through no-follow directory descriptors.

    POSIX directory descriptors remain the authority after the initial path
    validation.  Every directory traversal uses O_NOFOLLOW, and every create,
    rename, and cleanup operation is relative to an already-open descriptor.
    """

    def __init__(self, repo: Path):
        require_secure_write_support()
        self.repo_input = Path(repo).absolute()
        self.repo = self.repo_input.resolve()
        self.repo_fd: int | None = None

    @staticmethod
    def _open_absolute_directory(path: Path) -> int:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        current_fd = os.open(os.path.sep, flags)
        try:
            for component in path.parts[1:]:
                try:
                    next_fd = os.open(component, flags, dir_fd=current_fd)
                except OSError as error:
                    if error.errno in {errno.ELOOP, errno.ENOTDIR}:
                        raise SecureInstallerError(
                            f"symlinked repository ancestor: {path}"
                        ) from error
                    raise
                os.close(current_fd)
                current_fd = next_fd
            return current_fd
        except Exception:
            os.close(current_fd)
            raise

    def __enter__(self) -> "SecureRepository":
        try:
            self.repo_fd = self._open_absolute_directory(self.repo)
        except OSError as error:
            raise SecureInstallerError(
                f"refusing unsafe repository root: {self.repo}: {error}"
            ) from error
        return self

    def __exit__(self, _type, _value, _traceback) -> None:
        if self.repo_fd is not None:
            os.close(self.repo_fd)
            self.repo_fd = None

    def _open_parent(self, destination: Path) -> tuple[int, str]:
        if self.repo_fd is None:
            raise SecureInstallerError("secure repository is not open")
        try:
            relative = Path(destination).absolute().relative_to(self.repo_input)
        except ValueError as error:
            raise SecureInstallerError(
                f"destination is outside the repository: {destination}"
            ) from error
        parts = relative.parts
        if not parts or any(part in {"", ".", ".."} for part in parts):
            raise SecureInstallerError(f"invalid destination path: {destination}")

        current_fd = os.dup(self.repo_fd)
        try:
            for component in parts[:-1]:
                flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
                try:
                    next_fd = os.open(component, flags, dir_fd=current_fd)
                except FileNotFoundError:
                    try:
                        os.mkdir(component, 0o777, dir_fd=current_fd)
                    except FileExistsError:
                        pass
                    try:
                        next_fd = os.open(component, flags, dir_fd=current_fd)
                    except OSError as error:
                        if error.errno in {errno.ELOOP, errno.ENOTDIR}:
                            raise SecureInstallerError(
                                f"symlinked destination ancestor: {destination}"
                            ) from error
                        raise
                except OSError as error:
                    if error.errno in {errno.ELOOP, errno.ENOTDIR}:
                        raise SecureInstallerError(
                            f"symlinked destination ancestor: {destination}"
                        ) from error
                    raise
                os.close(current_fd)
                current_fd = next_fd
            return current_fd, parts[-1]
        except Exception:
            os.close(current_fd)
            raise

    @staticmethod
    def _target_mode(parent_fd: int, name: str) -> int:
        try:
            result = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            current_umask = os.umask(0)
            os.umask(current_umask)
            return 0o666 & ~current_umask
        if _is_symlink_stat(result):
            raise SecureInstallerError(f"symlinked destination target: {name}")
        if not stat.S_ISREG(result.st_mode):
            raise SecureInstallerError(f"destination is not a regular file: {name}")
        return stat.S_IMODE(result.st_mode)

    @staticmethod
    def _create_temporary(parent_fd: int, destination_name: str) -> tuple[str, int]:
        flags = (
            os.O_WRONLY
            | os.O_CREAT
            | os.O_EXCL
            | os.O_NOFOLLOW
            | os.O_CLOEXEC
        )
        for _ in range(100):
            temporary_name = f".{destination_name}.tmp-{secrets.token_hex(16)}"
            try:
                temporary_fd = os.open(
                    temporary_name,
                    flags,
                    0o600,
                    dir_fd=parent_fd,
                )
                return temporary_name, temporary_fd
            except FileExistsError:
                continue
        raise SecureInstallerError(
            f"could not allocate a private temporary file for {destination_name}"
        )

    @staticmethod
    def _write_all(file_fd: int, data: bytes) -> None:
        view = memoryview(data)
        while view:
            written = os.write(file_fd, view)
            if written <= 0:
                raise OSError("short write while installing lifecycle file")
            view = view[written:]

    def write(self, destination: Path, data: bytes, overwrite: bool = True) -> None:
        parent_fd, destination_name = self._open_parent(destination)
        temporary_name: str | None = None
        temporary_fd: int | None = None
        try:
            mode = self._target_mode(parent_fd, destination_name)
            temporary_name, temporary_fd = self._create_temporary(
                parent_fd, destination_name
            )
            os.fchmod(temporary_fd, mode)
            self._write_all(temporary_fd, data)
            os.fsync(temporary_fd)
            if destination_name == "cloudflare-branch-worker.mjs":
                os.fchmod(temporary_fd, mode | 0o111)
                os.fsync(temporary_fd)

            # lstat through the parent descriptor rejects a final link without
            # ever following it.  A create-only publish uses link(2), which is
            # atomic and refuses an existing destination instead of replacing it.
            try:
                result = os.stat(
                    destination_name,
                    dir_fd=parent_fd,
                    follow_symlinks=False,
                )
            except FileNotFoundError:
                result = None
            if result is not None and _is_symlink_stat(result):
                raise SecureInstallerError(
                    f"symlinked destination target: {destination_name}"
                )
            if overwrite:
                # The rename is dirfd-relative, so an ancestor swap cannot
                # redirect the write outside this already-open parent handle.
                os.rename(
                    temporary_name,
                    destination_name,
                    src_dir_fd=parent_fd,
                    dst_dir_fd=parent_fd,
                )
                temporary_name = None
            else:
                try:
                    os.link(
                        temporary_name,
                        destination_name,
                        src_dir_fd=parent_fd,
                        dst_dir_fd=parent_fd,
                        follow_symlinks=False,
                    )
                except FileExistsError as error:
                    raise ExistingFilesError([destination]) from error
                os.unlink(temporary_name, dir_fd=parent_fd)
                temporary_name = None
            os.fsync(parent_fd)
        finally:
            if temporary_fd is not None:
                os.close(temporary_fd)
            if temporary_name is not None:
                try:
                    os.unlink(temporary_name, dir_fd=parent_fd)
                except FileNotFoundError:
                    pass
            os.close(parent_fd)


def before_apply_write() -> None:
    """Test seam between lexical validation and descriptor-backed writes."""


def existing_destinations(files: dict[Path, bytes]) -> list[Path]:
    return [path for path in files if path.exists() or is_link(path)]


def apply_files(files: dict[Path, bytes], repo: Path, overwrite: bool) -> None:
    """Apply files using only secure descriptor-relative filesystem calls."""

    validate_destinations(files, repo)
    existing = existing_destinations(files)
    if existing and not overwrite:
        raise ExistingFilesError(existing)
    require_secure_write_support()
    before_apply_write()
    try:
        with SecureRepository(repo) as secure_repository:
            for path, data in files.items():
                secure_repository.write(path, data, overwrite)
    except OSError as error:
        raise SecureInstallerError(f"secure install failed: {error}") from error


def command(value: str, label: str) -> list[str]:
    parts = shlex.split(value)
    if not parts:
        raise argparse.ArgumentTypeError(f"{label} must not be empty")
    return parts


def infer_toolchain(repo: Path) -> dict[str, str]:
    if (repo / "bun.lock").exists() or (repo / "bun.lockb").exists():
        return {
            "install": "bun install --frozen-lockfile",
            "verify": "bun run verify",
            "build": "bun run build",
            "wrangler": "bunx wrangler",
        }
    if (repo / "pnpm-lock.yaml").exists():
        return {
            "install": "pnpm install --frozen-lockfile",
            "verify": "pnpm run verify",
            "build": "pnpm run build",
            "wrangler": "pnpm exec wrangler",
        }
    return {
        "install": "npm ci",
        "verify": "npm test",
        "build": "npm run build",
        "wrangler": "npx wrangler",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preview or install automatic per-branch Cloudflare Worker lifecycle files."
    )
    parser.add_argument("--repo", default=".", help="Target repository root.")
    parser.add_argument("--worker-prefix", required=True)
    parser.add_argument("--workers-dev-subdomain", required=True)
    parser.add_argument(
        "--protected-branch",
        action="append",
        dest="protected_branches",
        default=None,
        help="Protected branch; repeat as needed. Defaults to main.",
    )
    parser.add_argument(
        "--protected-worker",
        action="append",
        dest="protected_workers",
        required=True,
        help="Permanent Worker name; repeat as needed.",
    )
    parser.add_argument("--install-command")
    parser.add_argument("--verify-command")
    parser.add_argument("--build-command")
    parser.add_argument("--wrangler-command")
    parser.add_argument("--wrangler-cwd", default=".")
    parser.add_argument("--wrangler-environment", default="development")
    parser.add_argument("--wrangler-config")
    parser.add_argument(
        "--production-worker",
        help="Permanent production Worker name. Also list it with --protected-worker.",
    )
    parser.add_argument("--production-environment", default="production")
    parser.add_argument(
        "--github-production-environment",
        default="production",
        help="GitHub Environment used to gate manual production deployment.",
    )
    parser.add_argument(
        "--force-delete",
        action="store_true",
        help="Enable destructive forced Worker deletion. Keep disabled for shared state.",
    )
    parser.add_argument("--apply", action="store_true", help="Write files. Default is dry-run.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing lifecycle files. Requires --apply.",
    )
    args = parser.parse_args()
    if args.overwrite and not args.apply:
        parser.error("--overwrite requires --apply")
    if args.production_worker and args.production_worker not in args.protected_workers:
        parser.error("--production-worker must also be listed with --protected-worker")
    if args.production_worker and not WORKER_NAME_PATTERN.fullmatch(args.production_worker):
        parser.error("--production-worker must be a valid lowercase Cloudflare Worker name")
    if args.production_worker and args.production_environment == args.wrangler_environment:
        parser.error("--production-environment must differ from --wrangler-environment")
    return args


def render_config(args: argparse.Namespace, repo: Path) -> str:
    defaults = infer_toolchain(repo)
    config = json.loads((TEMPLATE_ROOT / ".cloudflare/branch-workers.json").read_text())
    config["workerPrefix"] = args.worker_prefix
    config["workersDevSubdomain"] = args.workers_dev_subdomain
    config["protectedBranches"] = args.protected_branches or ["main"]
    config["protectedWorkers"] = args.protected_workers
    config["install"]["command"] = command(
        args.install_command or defaults["install"], "install command"
    )
    config["verify"]["command"] = command(
        args.verify_command or defaults["verify"], "verify command"
    )
    config["build"]["command"] = command(
        args.build_command or defaults["build"], "build command"
    )
    config["wrangler"]["command"] = command(
        args.wrangler_command or defaults["wrangler"], "Wrangler command"
    )
    config["wrangler"]["cwd"] = args.wrangler_cwd
    config["wrangler"]["environment"] = args.wrangler_environment
    config["wrangler"]["config"] = args.wrangler_config
    config["production"] = (
        {
            "workerName": args.production_worker,
            "environment": args.production_environment,
            "config": args.wrangler_config,
        }
        if args.production_worker
        else None
    )
    config["delete"]["force"] = args.force_delete
    return json.dumps(config, indent=2) + "\n"


def render_workflow(args: argparse.Namespace) -> str:
    workflow = (TEMPLATE_ROOT / ".github/workflows/cloudflare-branch-workers.yml").read_text()
    protected = args.protected_branches or ["main"]
    replacement = "    branches-ignore:\n" + "".join(f"      - {branch}\n" for branch in protected)
    marker = "    branches-ignore:\n      - main\n"
    if workflow.count(marker) != 1:
        raise RuntimeError("Workflow template branches-ignore marker is missing or ambiguous")
    return workflow.replace(marker, replacement, 1)


def render_production_workflow(args: argparse.Namespace) -> str:
    workflow = (TEMPLATE_ROOT / ".github/workflows/cloudflare-production.yml").read_text()
    marker = '    environment: "production"\n'
    replacement = f"    environment: {json.dumps(args.github_production_environment)}\n"
    if workflow.count(marker) != 1:
        raise RuntimeError("Production workflow environment marker is missing or ambiguous")
    return workflow.replace(marker, replacement, 1)


def planned_files(args: argparse.Namespace, repo: Path) -> dict[Path, bytes]:
    rendered: dict[Path, bytes] = {}
    for source_rel, destination_rel in DESTINATIONS:
        if (
            destination_rel == Path(".github/workflows/cloudflare-production.yml")
            and not args.production_worker
        ):
            continue
        if destination_rel == Path(".cloudflare/branch-workers.json"):
            data = render_config(args, repo).encode()
        elif destination_rel == Path(".github/workflows/cloudflare-branch-workers.yml"):
            data = render_workflow(args).encode()
        elif destination_rel == Path(".github/workflows/cloudflare-production.yml"):
            data = render_production_workflow(args).encode()
        else:
            data = (TEMPLATE_ROOT / source_rel).read_bytes()
        rendered[repo / destination_rel] = data
    return rendered


def main() -> int:
    args = parse_args()
    repo = Path(args.repo).expanduser().resolve()
    if not (repo / ".git").exists():
        print(f"error: target is not a Git repository root: {repo}", file=sys.stderr)
        return 2
    if not TEMPLATE_ROOT.exists():
        print(f"error: bundled template is missing: {TEMPLATE_ROOT}", file=sys.stderr)
        return 2

    files = planned_files(args, repo)
    existing = existing_destinations(files)
    print("Mode:", "apply" if args.apply else "dry-run")
    print("Repository:", repo)
    for path in files:
        state = "replace" if path.exists() else "create"
        print(f"- {state}: {path.relative_to(repo)}")

    if not args.apply:
        if existing:
            print("Existing files would require --apply --overwrite after review.")
        else:
            print("No files written. Add --apply to install.")
        return 0

    try:
        apply_files(files, repo, args.overwrite)
    except ExistingFilesError as error:
        print("error: refusing to overwrite existing files:", file=sys.stderr)
        for path in error.paths or existing:
            print(f"- {path.relative_to(repo)}", file=sys.stderr)
        print(
            "Review them first, then use --overwrite only if replacement is intended.",
            file=sys.stderr,
        )
        return 3
    except ValueError as error:
        print(f"error: refusing unsafe destination: {error}", file=sys.stderr)
        return 4

    print("Installed Cloudflare Worker deployment lifecycle files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
