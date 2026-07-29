#!/usr/bin/env python3
"""Safely install the Cloudflare Worker deployment lifecycle template."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
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
    existing = [path for path in files if path.exists()]
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

    if existing and not args.overwrite:
        print("error: refusing to overwrite existing files:", file=sys.stderr)
        for path in existing:
            print(f"- {path.relative_to(repo)}", file=sys.stderr)
        print("Review them first, then use --overwrite only if replacement is intended.", file=sys.stderr)
        return 3

    for path, data in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        if path.name == "cloudflare-branch-worker.mjs":
            path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print("Installed Cloudflare Worker deployment lifecycle files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
