#!/usr/bin/env python3
"""Read-only drift inspection; never certifies completeness or design approval."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import sys

HARNESS = Path(__file__).resolve().parents[2] / "delivery-harness" / "scripts"
if str(HARNESS) not in sys.path:
    sys.path.insert(0, str(HARNESS))
from harness_contract import contract_digest

SHA = re.compile(r"^[0-9a-f]{64}$")
MAX_BYTES = 16 * 1024 * 1024


def checked_hash(value):
    if value is not None and (not isinstance(value, str) or not SHA.fullmatch(value)):
        raise ValueError("hash must be lowercase SHA-256 or null")
    return value


def safe_file(root, name):
    if not isinstance(name, str) or "\\" in name or ":" in name:
        raise ValueError("expected a repository-relative product/design path")
    parts = PurePosixPath(name).parts
    if (len(parts) < 3 or parts[:2] not in (("docs", "product"), ("docs", "design"))
            or any(part in ("..", ".") or part.startswith(".") for part in parts)
            or PurePosixPath(name).suffix not in (".md", ".html", ".json")):
        raise ValueError("only non-secret docs/product and docs/design artifacts are allowed")
    candidate = root
    for part in parts:
        candidate = candidate / part
        if candidate.exists() or candidate.is_symlink():
            info = candidate.lstat()
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                raise ValueError("linked artifact paths are not supported")
    return candidate


def file_hash(path):
    if not path.exists():
        return None
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError("artifact is not a bounded regular file")
    with path.open("rb") as stream:
        data = stream.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("artifact exceeds read limit")
    return hashlib.sha256(data).hexdigest()


def inspect(root, baseline, installed_digest, loaded_digest=None):
    """Compare supplied observation bindings, propagating dependency drift."""
    root = Path(root).resolve()
    if not isinstance(baseline, dict) or baseline.get("schema") != "design-observation/1":
        raise ValueError("expected design-observation/1")
    old_skill = checked_hash(baseline.get("skillDigest"))
    checked_hash(installed_digest)
    checked_hash(loaded_digest)
    implementation = baseline.get("implementation")
    if implementation not in ("not_started", "started", "unknown"):
        raise ValueError("implementation must be not_started, started or unknown")
    evidence = baseline.get("implementationEvidence")
    if not isinstance(evidence, str) or not evidence.strip():
        raise ValueError("implementationEvidence is required; no RUN is not evidence")
    entries = baseline.get("artifacts")
    if not isinstance(entries, list) or not 1 <= len(entries) <= 1000:
        raise ValueError("artifacts must contain 1-1000 observation entries")
    findings = []
    if installed_digest is None or loaded_digest is None:
        findings.append("skill_identity_unknown")
    elif loaded_digest != installed_digest:
        findings.append("restart_required")
    if old_skill is None:
        findings.append("artifact_skill_provenance_unknown")
    elif old_skill != installed_digest:
        findings.append("skill_changed_semantic_review_required")
    if implementation == "unknown":
        findings.append("implementation_status_unknown")
    rows = {}
    observed = {}

    def observe(binding):
        if not isinstance(binding, dict) or "sha256" not in binding:
            raise ValueError("each binding needs path and sha256")
        name = binding.get("path")
        path = safe_file(root, name)
        expected = checked_hash(binding["sha256"])
        if name not in observed:
            observed[name] = file_hash(path)
        actual = observed[name]
        reason = "missing" if actual is None else "provenance_unknown" if expected is None else "changed" if expected != actual else None
        return name, actual, reason

    for entry in entries:
        name, actual, reason = observe(entry)
        if name in rows:
            raise ValueError("duplicate artifact path")
        inputs = entry.get("inputs")
        if not isinstance(inputs, list) or not 1 <= len(inputs) <= 1000:
            raise ValueError("each artifact needs 1-1000 source bindings")
        reasons = [f"artifact_{reason}"] if reason else []
        dependencies = []
        for item in inputs:
            source, _, drift = observe(item)
            if source == name or source in dependencies:
                raise ValueError("self or duplicate dependency")
            dependencies.append(source)
            if drift:
                reasons.append(f"input_{drift}: {source}")
        rows[name] = {"path": name, "sha256": actual, "inputs": dependencies, "reasons": reasons}
    # Reject cycles instead of certifying a mutually dependent observation.
    visiting, visited = set(), set()

    def visit(name):
        if name in visiting:
            raise ValueError("artifact dependency cycle")
        if name in visited or name not in rows:
            return
        visiting.add(name)
        for dependency in rows[name]["inputs"]:
            visit(dependency)
            if dependency in rows and rows[dependency]["reasons"]:
                rows[name]["reasons"].append(f"upstream_review_required: {dependency}")
        visiting.remove(name)
        visited.add(name)

    for name in rows:
        visit(name)
    for row in rows.values():
        row["status"] = "review_required" if row["reasons"] or findings else "bytes_unchanged"
    return {"status": "review_required" if findings or any(r["reasons"] for r in rows.values()) else "bytes_unchanged",
            "implementation": implementation, "implementationEvidence": evidence,
            "skills": {"recorded": old_skill, "installed": installed_digest, "loaded": loaded_digest},
            "findings": findings, "artifacts": list(rows.values()),
            "meaning": "Inventoried byte drift only; verify full package coverage, rule impact and human approvals separately."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--skills-root", required=True)
    parser.add_argument("--loaded-digest")
    args = parser.parse_args()
    try:
        baseline_path = Path(args.baseline)
        if baseline_path.is_symlink() or baseline_path.stat().st_size > MAX_BYTES:
            raise ValueError("baseline must be bounded and not a symlink")
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        report = inspect(args.repo_root, baseline, contract_digest(args.skills_root), args.loaded_digest)
    except (OSError, ValueError, RecursionError) as exc:
        print(json.dumps({"status": "invalid", "error": str(exc)}))
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "bytes_unchanged" else 1


if __name__ == "__main__":
    raise SystemExit(main())
