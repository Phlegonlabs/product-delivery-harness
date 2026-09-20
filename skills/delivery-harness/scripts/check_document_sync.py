#!/usr/bin/env python3
"""Read-only document drift inventory; hashes are not semantic approval."""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from harness_contract import contract_digest


SCHEMA = "document-sync/1"
LIMIT = 2 * 1024 * 1024
DEFAULT_PATHS = (
    "AGENTS.md", "AGENTS.override.md", "CLAUDE.md", "docs/DOCUMENTS.md",
    "docs/product/PRD.md", "docs/product/architecture.md",
    "docs/product/stack-decisions.md", "docs/design/ui-design.md",
    "docs/DEPLOYMENT.md", "docs/ACTIVATION.md", "docs/goal/PLAN.md",
    "docs/goal/RUN.md",
)
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
RETIRED = re.compile(r"(?:skills[/\\]|`)(full-harness|prd-builder|product-design-builder)(?=[/\\`])")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def safe_path(root, relative, *, document=False):
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("path must be nonempty repository-relative POSIX text")
    parts = relative.split("/")
    if any(part in {"", ".", ".."} or ":" in part for part in parts):
        raise ValueError("unsafe path")
    lowered = [part.lower() for part in parts]
    if any(part.startswith(".env") or part in {".git", "archived", "outcomes", ".ssh"}
           or any(word in part for word in ("credential", "secret", "password", "token", "cookie"))
           for part in lowered):
        raise ValueError("secret, Git metadata or historical path is excluded")
    if document:
        instruction = parts[-1] in {"AGENTS.md", "AGENTS.override.md", "CLAUDE.md"}
        if not instruction and not parts[-1].endswith(".md"):
            raise ValueError("only instruction files and scoped Markdown docs may be inventoried")
    candidate = root
    for part in parts:
        candidate = candidate / part
        if candidate.is_symlink() or (hasattr(candidate, "is_junction") and candidate.is_junction()):
            raise ValueError("linked paths are excluded")
    if not candidate.resolve().is_relative_to(root):
        raise ValueError("path escapes repository")
    return candidate


def read_bounded(path):
    before = path.stat()
    if not path.is_file() or before.st_size > LIMIT:
        raise ValueError("input must be a bounded regular file")
    with path.open("rb") as stream:
        data = stream.read(LIMIT + 1)
    after = path.stat()
    if len(data) > LIMIT or (before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError("input changed during observation")
    return data


def impact_for(name, reason):
    """Conservative routing hints, never a substitute for semantic review."""
    filename = name.rsplit("/", 1)[-1]
    if filename in {"AGENTS.md", "AGENTS.override.md", "CLAUDE.md", "DOCUMENTS.md"}:
        artifacts, stages, checks = ["scoped live documents"], ["intake", "affected stages"], ["required reading", "references and skill bindings"]
    elif name == "docs/product/PRD.md":
        artifacts, stages, checks = ["architecture", "stack", "wireframes", "HiFi", "acceptance"], ["product", "design", "delivery"], ["product package", "affected UI gates", "requirement-linked tests"]
    elif name in {"docs/product/architecture.md", "docs/product/stack-decisions.md"}:
        artifacts, stages, checks = ["implementation", "deployment", "acceptance"], ["product", "delivery"], ["product package", "API and permission tests", "migration and recovery"]
    elif name.startswith("docs/design/"):
        artifacts, stages, checks = ["wireframes", "HiFi", "conditional design-system pair", "implementation"], ["design", "delivery"], ["UI contract", "product interactions", "visual and accessibility evidence"]
    elif filename in {"DEPLOYMENT.md", "ACTIVATION.md"}:
        artifacts, stages, checks = ["release evidence", "operational readiness"], ["deployment", "activation"], ["environment isolation", "build readback", "recovery and readiness"]
    elif name.startswith("docs/epics/"):
        artifacts, stages, checks = ["referenced PRD requirements", "affected live artifacts"], ["intake", "delivery"], ["Epic references and baseline", "accepted scope and outcomes"]
    else:
        artifacts, stages, checks = ["parent-selected affected sources"], ["parent semantic review"], ["source references and affected acceptance"]
    return {"source": name, "reason": reason, "affected_artifacts": artifacts,
            "affected_stages": stages, "required_checks": checks,
            "semantic_review_required": True}


def inspect(root, paths, loaded_digest, installed_digest, baseline=None, required=()):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("repository root must be a directory")
    if not (isinstance(installed_digest, str) and DIGEST.fullmatch(installed_digest)) or (
            loaded_digest is not None and not (isinstance(loaded_digest, str) and DIGEST.fullmatch(loaded_digest))):
        raise ValueError("loaded and installed contract digests must be lowercase SHA-256")
    if not isinstance(paths, (list, tuple)) or not paths or len(paths) > 128:
        raise ValueError("declare between 1 and 128 document paths")
    if not all(isinstance(item, str) for item in paths) or len(set(paths)) != len(paths):
        raise ValueError("document paths must be unique strings")
    if not set(required).issubset(paths):
        raise ValueError("required paths must be in the inventory")
    findings = []
    if loaded_digest is None:
        findings.append({"kind": "loaded_identity_unobserved"})
    elif loaded_digest != installed_digest:
        findings.append({"kind": "restart_required"})
    if baseline is not None:
        if not isinstance(baseline, dict) or baseline.get("schema") != SCHEMA:
            raise ValueError("invalid baseline schema")
        previous = baseline.get("documents")
        if not isinstance(previous, dict) or any(
            not isinstance(key, str) or (value is not None and
            (not isinstance(value, str) or not DIGEST.fullmatch(value)))
            for key, value in previous.items()
        ):
            raise ValueError("invalid baseline document hashes")
        if set(baseline) != {"schema", "installed_digest", "documents"}:
            raise ValueError("invalid baseline fields")
        if not isinstance(baseline.get("installed_digest"), str) or not DIGEST.fullmatch(baseline["installed_digest"]):
            raise ValueError("invalid baseline installed digest")
        if baseline["installed_digest"] != installed_digest:
            findings.append({"kind": "skill_contract_changed"})
        if set(previous) != set(paths):
            findings.append({"kind": "inventory_changed"})
    else:
        previous = {}
        findings.append({"kind": "baseline_review_required"})
    documents = {}
    impacts = []
    for name in paths:
        path = safe_path(root, name, document=True)
        if not path.exists():
            documents[name] = None
            if name in required or previous.get(name) is not None:
                findings.append({"kind": "missing_document", "path": name})
                impacts.append(impact_for(name, "missing_document"))
            continue
        data = read_bounded(path)
        text = data.decode("utf-8-sig")
        documents[name] = hashlib.sha256(data).hexdigest()
        if baseline is not None and previous.get(name) != documents[name]:
            findings.append({"kind": "document_changed", "path": name})
            impacts.append(impact_for(name, "document_changed"))
        elif baseline is None:
            impacts.append(impact_for(name, "first_observation"))
        for skill in sorted(set(RETIRED.findall(text))):
            findings.append({"kind": "legacy_pointer_review", "path": name, "skill": skill})
    snapshot = {"schema": SCHEMA, "installed_digest": installed_digest,
                "documents": documents}
    return {"status": "review_required" if findings else "unchanged",
            "findings": findings, "impacts": impacts, "snapshot": snapshot,
            "meaning": "Byte drift only; semantic review, capability, authorization and approval are separate."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--loaded-digest", help="observed session digest; omit when unobserved")
    parser.add_argument("--installed-digest", help="optional expected installed digest; checked against disk")
    parser.add_argument("--skills-root", help="observed installed sibling skill root; defaults to this bundle")
    parser.add_argument("--path", action="append", dest="paths")
    parser.add_argument("--required-path", action="append", default=[])
    parser.add_argument("--baseline", help="repository-relative prior snapshot JSON, not the whole report")
    args = parser.parse_args(argv)
    try:
        root = Path(args.repo_root).resolve(strict=True)
        installed_digest = contract_digest(args.skills_root)
        if args.installed_digest is not None and args.installed_digest != installed_digest:
            raise ValueError("installed skill bytes differ from expected digest")
        baseline = None
        if args.baseline:
            path = safe_path(root, args.baseline)
            if path.suffix != ".json":
                raise ValueError("baseline must be a JSON snapshot")
            baseline = json.loads(read_bounded(path).decode("utf-8-sig"), object_pairs_hook=unique_object)
        report = inspect(root, args.paths or DEFAULT_PATHS, args.loaded_digest,
                         installed_digest, baseline, args.required_path)
    except (ValueError, OSError, UnicodeError, RecursionError) as exc:
        # Never echo document content, JSON bodies, or credential values.
        print(json.dumps({"status": "invalid", "error": type(exc).__name__}))
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "unchanged" else 1


if __name__ == "__main__":
    sys.exit(main())
