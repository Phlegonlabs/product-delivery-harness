"""Derive design work scope from an existing task record and Git; never approve work."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

from review_evidence import safe_path

MODES = {"initial_design", "enhancement", "maintenance", "full_redesign"}


def git(root, *arguments):
    result = subprocess.run(["git", "-C", str(root), *arguments], capture_output=True,
                            text=True, encoding="utf-8", timeout=30)
    if result.returncode:
        raise ValueError(result.stderr.strip())
    return result.stdout.strip()


def read_scope(text):
    active = []
    fence = None
    for line in text.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence is None:
            active.append(line)
    text = "\n".join(active)
    matches = re.findall(r"^Design workflow:\s*(\S+)\s*$", text, re.M)
    if len(matches) != 1 or matches[0] not in MODES:
        raise ValueError("task record needs one Design workflow: initial_design|enhancement|maintenance|full_redesign")
    section = re.search(r"^### UI Change Scope\s*\n([\s\S]*?)(?=^#{1,3} |\Z)", text, re.M)
    rows = []
    if section:
        for line in section.group(1).splitlines():
            if not line.strip().startswith("|"):
                continue
            cells = [cell.strip().strip(chr(96)) for cell in line.strip().strip("|").split("|")]
            if cells[0] == "Disposition" or set(cells[0]) <= {"-", ":", " "}:
                continue
            if len(cells) != 3 or cells[0] not in {"added", "changed", "preserved", "shared"} or not cells[2]:
                raise ValueError("UI Change Scope needs Disposition | Path | Reason / consumers")
            rows.append(dict(zip(("disposition", "path", "reason"), cells)))
    if matches[0] == "enhancement" and not rows:
        raise ValueError("enhancement needs added/changed/preserved scope before authoring")
    if len({row["path"].casefold() for row in rows}) != len(rows):
        raise ValueError("duplicate UI scope paths")
    return matches[0], rows


def report(root, task_record, baseline=None):
    root = Path(root).resolve()
    record = safe_path(root, task_record)
    if not task_record.startswith(("docs/",)) or record.suffix != ".md":
        raise ValueError("use the existing Markdown task or Epic under docs/")
    payload = record.read_bytes()
    if len(payload) > 1024 * 1024:
        raise ValueError("task record is too large")
    text = payload.decode("utf-8")
    mode, rows = read_scope(text)
    head = git(root, "rev-parse", "HEAD")
    base = git(root, "rev-parse", "--verify", (baseline or head) + "^{commit}")
    if not re.fullmatch(r"[0-9a-f]{40,64}", base):
        raise ValueError("baseline must resolve to a commit")
    problems = []
    observed = []
    for row in rows:
        path = safe_path(root, row["path"])
        current = path.read_bytes() if path.is_file() else None
        previous = subprocess.run(["git", "-C", str(root), "show", base + ":" + row["path"]],
                                  capture_output=True, timeout=30)
        prior = previous.stdout if previous.returncode == 0 else None
        changed = current != prior
        if row["disposition"] == "preserved" and changed:
            problems.append("preserved page changed: " + row["path"])
        if row["disposition"] == "added" and prior is not None:
            problems.append("added page already exists in baseline: " + row["path"])
        observed.append(dict(row, changed=changed,
                             sha256=hashlib.sha256(current).hexdigest() if current is not None else None))
    dirty = git(root, "status", "--porcelain=v1", "--untracked-files=all").splitlines()
    active_tasks = [name for name in ("docs/PLAN.md", "docs/RUN.json", "PLAN.md", "RUN.json")
                    if (root / name).is_file()]
    pending = [item.strip() for item in re.findall(r"^- \[ \] (.+)$", text, re.M)]
    return {
        "schema": "design-work-summary/1", "head": head, "baseline": base,
        "taskRecord": {"path": task_record, "sha256": hashlib.sha256(payload).hexdigest()},
        "workflow": mode, "designRequired": mode != "maintenance",
        "scope": observed, "findings": problems, "dirty": dirty, "activeTaskFiles": active_tasks,
        "remaining": pending, "next": pending[0] if pending else "Reconcile recorded results with current verification.",
        "meaning": "Derived scope only. No approval, evidence reuse, or permission is granted.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--task-record", required=True)
    parser.add_argument("--baseline")
    options = parser.parse_args()
    try:
        result = report(options.repo_root, options.task_record, options.baseline)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}))
        return 2
    print(json.dumps(result, indent=2))
    return 1 if result["findings"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
