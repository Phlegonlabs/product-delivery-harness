#!/usr/bin/env python3
"""Read-only document drift inventory; hashes are not semantic approval.

Epic hashes leave out the `## Handoff` section. Once docs/epics/ holds an Epic,
docs/DOCUMENTS.md needs a `Current Epic:` line that names an existing file.
"""

import argparse
import hashlib
import json
import os
import posixpath
import re
import sys
from pathlib import Path

from campaign_handoff import campaign_findings, campaign_links, is_campaign
from harness_contract import contract_digest
from research_claims import ASSESSMENT, MESSAGING, research_claim_findings


SCHEMA = "document-sync/1"
LIMIT = 2 * 1024 * 1024
# Machine-written coordination files may exceed LIMIT; they are stream-hashed up to
# this ceiling, and their text is not scanned.
COORDINATION_PATHS = frozenset({"docs/goal/PLAN.md", "docs/goal/RUN.md"})
COORDINATION_LIMIT = 256 * 1024 * 1024
DEFAULT_PATHS = (
    "AGENTS.md", "AGENTS.override.md", "CLAUDE.md", "docs/DOCUMENTS.md",
    "docs/product/PRD.md", "docs/product/architecture.md",
    "docs/product/stack-decisions.md", "docs/design/ui-design.md",
    "docs/DEPLOYMENT.md", "docs/goal/PLAN.md",
    "docs/goal/RUN.md",
)
OPTIONAL_HANDOFFS = ("docs/product/keyword-map.md", "docs/gtm/MESSAGING.md",
                     "docs/product/research-assessment.md", "docs/gtm/CAMPAIGN.md")
DISCOVERY_STUDY = re.compile(r"docs/research/discovery/\d{4}-\d{2}-\d{2}/DISCOVERY\.md\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
SESSION_MARKER = re.compile(r"[A-Za-z0-9._-]{1,128}:[0-9a-f]{64}\Z")
# Skills that install.sh retires; keep the two lists in step.
RETIRED_NAMES = (
    "full-harness", "prd-builder", "product-design-builder",
    "code-security-review", "product-activation", "seo-growth-review",
)
_RETIRED = "|".join(map(re.escape, RETIRED_NAMES))
RETIRED = re.compile(rf"(?:skills[/\\]|`)({_RETIRED})(?=[/\\`])")
RETIREMENT_CATALOG = re.compile(
    rf"\b(?:retire|retires|retired|retiring)\s+(?P<items>"
    rf"`(?:{_RETIRED})`"
    rf"(?:\s*,\s*`(?:{_RETIRED})`)*"
    rf"(?:\s*,?\s+and\s+`(?:{_RETIRED})`)?"
    r")",
    re.IGNORECASE,
)
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
MARKDOWN_LINK = re.compile(r"\[[^\]\r\n]*\](?:\([^\r\n)]*\)|\[[^\]\r\n]*\])")
CURRENT_EPIC = re.compile(r"^Current Epic: \[[^\]\r\n]+\]\(([^)\r\n]+)\)[ \t\r]*$", re.MULTILINE)


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
    if excluded_name(relative):
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


def hash_coordination_file(path):
    """Stream-hash a large machine-written coordination file; its text is not scanned."""
    before = path.stat()
    if not path.is_file() or before.st_size > COORDINATION_LIMIT:
        raise ValueError("input must be a bounded regular file")
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    after = path.stat()
    if (before.st_ino, before.st_size, before.st_mtime_ns) != (
            after.st_ino, after.st_size, after.st_mtime_ns):
        raise ValueError("input changed during observation")
    return digest.hexdigest(), before.st_size


def is_epic(name):
    return name.startswith("docs/epics/") and name.count("/") == 2


def without_handoff(data):
    """Drop an Epic's `## Handoff` section, rewritten at every checkpoint; it grants nothing."""
    kept = []
    fence = None
    skipping = False
    for raw in data.splitlines(keepends=True):
        line = raw.decode("utf-8")
        marker = FENCE.match(line)
        if fence is None and marker:
            fence = marker.group(1)
        elif fence is not None:
            if marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence):
                fence = None
        elif line.startswith("## "):
            skipping = line.rstrip() == "## Handoff"
        if not skipping:
            kept.append(raw)
    return b"".join(kept)


def excluded_name(relative):
    """True when a path part names secrets, Git metadata or historical records."""
    return any(part.startswith(".env") or part in {".git", "archived", "outcomes", ".ssh"}
               or any(word in part for word in ("credential", "secret", "password", "token", "cookie"))
               for part in relative.lower().split("/"))


def impact_for(name, reason):
    """Conservative routing hints, never a substitute for semantic review."""
    filename = name.rsplit("/", 1)[-1]
    if filename in {"AGENTS.md", "AGENTS.override.md", "CLAUDE.md", "DOCUMENTS.md"}:
        artifacts, stages, checks = ["scoped live documents"], ["intake", "affected stages"], ["required reading", "references and skill bindings"]
    elif name == "docs/product/PRD.md":
        artifacts, stages, checks = ["architecture", "stack", "HiFi", "legacy wireframes when pinned", "acceptance"], ["product", "design", "delivery"], ["product package", "affected UI gates", "requirement-linked tests"]
    elif name == "docs/product/keyword-map.md":
        artifacts = ["PRD discovery surfaces", "page metadata or store listing fields"]
        stages = ["growth", "product", "delivery"]
        checks = ["cluster IDs and mapped destinations", "page titles and descriptions or listing fields by locale"]
    elif name == "docs/gtm/MESSAGING.md":
        artifacts, stages, checks = ["public claims", "README and listing copy"], ["go-to-market", "readme-studio", "growth"], ["approved claims and per-surface one-liners"]
    elif name == "docs/product/research-assessment.md" or DISCOVERY_STUDY.fullmatch(name):
        artifacts, stages, checks = ["research findings", "approved public claims", "campaign drafts"], ["product", "go-to-market"], ["cited research and confidence after withdrawal"]
    elif is_campaign(name):
        artifacts, stages, checks = ["campaign drafts"], ["go-to-market"], ["current messaging revision and approved claims"]
    elif name in {"docs/product/architecture.md", "docs/product/stack-decisions.md"}:
        artifacts, stages, checks = ["implementation", "deployment", "acceptance"], ["product", "delivery"], ["product package", "API and permission tests", "migration and recovery"]
    elif name.startswith("docs/product/deltas/"):
        artifacts, stages, checks = ["bound Epic scope", "PRD baseline"], ["intake", "product", "delivery"], ["delta requirement IDs and TEST obligations", "Epic and PLAN delta binding"]
    elif name.startswith("docs/design/"):
        artifacts, stages, checks = ["HiFi", "legacy wireframes when pinned", "conditional design-system pair", "implementation"], ["design", "delivery"], ["UI contract", "product interactions", "visual and accessibility evidence"]
    elif filename == "DEPLOYMENT.md":
        artifacts, stages, checks = ["release evidence", "operational readiness"], ["deployment", "activation"], ["environment isolation", "build readback", "recovery and readiness"]
    elif name.startswith("docs/epics/"):
        artifacts, stages, checks = ["referenced PRD requirements", "affected live artifacts"], ["intake", "delivery"], ["Epic references and baseline", "accepted scope and outcomes"]
    else:
        artifacts, stages, checks = ["parent-selected affected sources"], ["parent semantic review"], ["source references and affected acceptance"]
    return {"source": name, "reason": reason, "affected_artifacts": artifacts,
            "affected_stages": stages, "required_checks": checks,
            "semantic_review_required": True}


def _retired_pointers(text):
    """Ignore only bare names in explicit retirement catalogs, not usable references."""
    pointers = set()
    fence = None
    for line in text.splitlines():
        marker = FENCE.match(line)
        in_fence = fence is not None
        if fence is None and marker:
            fence = marker.group(1)
            in_fence = True
        elif fence is not None and marker and marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence):
            fence = None
            in_fence = True

        quiet_spans = set()
        if not in_fence:
            linked_spans = {match.span() for match in MARKDOWN_LINK.finditer(line)}
            for catalog in RETIREMENT_CATALOG.finditer(line):
                item_span = catalog.span("items")
                if any(start <= item_span[0] and end >= item_span[1] for start, end in linked_spans):
                    continue
                for pointer in RETIRED.finditer(line):
                    if item_span[0] <= pointer.start() and pointer.end() <= item_span[1]:
                        quiet_spans.add(pointer.span())
        for pointer in RETIRED.finditer(line):
            if pointer.span() not in quiet_spans:
                pointers.add(pointer.group(1))
    return sorted(pointers)


def _bounded_children(root, name, label):
    folder = safe_path(root, name)
    if not folder.exists():
        return []
    if not folder.is_dir():
        raise ValueError(f"{label} inventory must be a directory")
    entries = []
    with os.scandir(folder) as iterator:
        for entry in iterator:
            if len(entries) >= 128:
                raise ValueError(f"scope the {label} directory explicitly")
            entries.append(Path(entry.path))
    return sorted(entries)


def _scoped_markdown_children(root, name, label, paths):
    """Append direct .md children of one scoped folder; never follow links."""
    for path in _bounded_children(root, name, label):
        if path.suffix == ".md":
            relative = path.relative_to(root).as_posix()
            if excluded_name(relative):
                continue
            safe_path(root, relative, document=True)
            paths.append(relative)
            if len(paths) > 128:
                raise ValueError(f"scope the {label} inventory explicitly")


def current_epic_findings(root, index_text):
    """Once docs/epics/ holds an Epic, the index's `Current Epic:` line must name an existing file."""
    folder = safe_path(root, "docs/epics")
    if not folder.is_dir():
        return []
    with os.scandir(folder) as entries:
        if not any(entry.name.endswith(".md") and entry.is_file(follow_symlinks=False)
                   and not excluded_name(entry.name) for entry in entries):
            return []
    targets = CURRENT_EPIC.findall(index_text)
    if not targets:
        return [{"kind": "current_epic_missing", "path": "docs/DOCUMENTS.md"}]
    findings = []
    for target in targets:
        try:
            exists = safe_path(root, posixpath.normpath("docs/" + target.split("#", 1)[0]),
                               document=True).is_file()
        except ValueError:
            exists = False
        if not exists:
            findings.append({"kind": "current_epic_missing", "path": "docs/DOCUMENTS.md",
                             "target": target})
    return findings


def _registered_campaigns(root):
    index = safe_path(root, "docs/DOCUMENTS.md", document=True)
    paths = set()
    if index.is_file():
        for target in campaign_links(read_bounded(index).decode("utf-8-sig")):
            # A web link is not a repository draft; a local absolute path cannot be checked.
            if re.match(r"^[A-Za-z][A-Za-z0-9+.-]+:", target):
                continue
            if re.match(r"^(?:[A-Za-z]:)?[\\/]", target):
                raise ValueError(f"campaign registration must be a repository-relative path: {target}")
            name = posixpath.normpath(posixpath.join("docs", target))
            safe_path(root, name, document=True)
            paths.add(name)
            if len(paths) > 128:
                raise ValueError("scope the campaign inventory explicitly")
    return paths


def default_inventory(root, baseline=None, *, registered=None):
    """Include live handoffs and retain previously inventoried paths to detect removal."""
    paths = list(DEFAULT_PATHS)
    for name in OPTIONAL_HANDOFFS:
        if safe_path(root, name, document=True).exists():
            paths.append(name)
    _scoped_markdown_children(root, "docs/epics", "Epic", paths)
    _scoped_markdown_children(root, "docs/product/deltas", "PRD delta", paths)
    _scoped_markdown_children(root, "docs/gtm/campaigns", "campaign", paths)
    for name in sorted(_registered_campaigns(root) if registered is None else registered):
        if name not in paths:
            paths.append(name)
    for folder in _bounded_children(root, "docs/research/discovery", "discovery"):
        name = f"docs/research/discovery/{folder.name}/DISCOVERY.md"
        if DISCOVERY_STUDY.fullmatch(name) and safe_path(root, name, document=True).is_file():
            paths.append(name)
    if isinstance(baseline, dict) and isinstance(baseline.get("documents"), dict):
        for name in baseline["documents"]:
            if not isinstance(name, str) or name in paths:
                continue
            retained = name in OPTIONAL_HANDOFFS or DISCOVERY_STUDY.fullmatch(name) or is_campaign(name) or is_epic(name) or (
                name.startswith("docs/product/deltas/") and name.count("/") == 3
            )
            if retained:
                safe_path(root, name, document=True)
                paths.append(name)
    return paths


def inspect(root, paths, loaded_digest, installed_digest, baseline=None, required=(),
            session_marker=None, *, full_inventory=False, registered=()):
    root = Path(root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("repository root must be a directory")
    if not (isinstance(installed_digest, str) and DIGEST.fullmatch(installed_digest)) or (
            loaded_digest is not None and not (isinstance(loaded_digest, str) and DIGEST.fullmatch(loaded_digest))):
        raise ValueError("loaded and installed contract digests must be lowercase SHA-256")
    if session_marker is not None and (loaded_digest is not None or not (
            isinstance(session_marker, str) and SESSION_MARKER.fullmatch(session_marker))):
        raise ValueError("session marker is <session-id>:<installed-digest> without a loaded digest")
    if not isinstance(paths, (list, tuple)) or not paths or len(paths) > 128:
        raise ValueError("declare between 1 and 128 document paths")
    if not all(isinstance(item, str) for item in paths) or len(set(paths)) != len(paths):
        raise ValueError("document paths must be unique strings")
    if not set(required).issubset(paths):
        raise ValueError("required paths must be in the inventory")
    findings = []
    # A marker recorded earlier this session against the same installed bytes
    # keeps the unknown identity visible without asking for another review.
    if loaded_digest is None and session_marker is not None and session_marker.endswith(":" + installed_digest):
        findings.append({"kind": "loaded_identity_unobserved", "session_marker": session_marker})
    elif loaded_digest is None:
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
    handoff_text = {}
    impacts = []
    for name in sorted(set(previous) - set(paths)):
        safe_path(root, name, document=True)
        findings.append({"kind": "removed_from_inventory", "path": name})
        impacts.append(impact_for(name, "removed_from_inventory"))
    for name in paths:
        path = safe_path(root, name, document=True)
        research_source = name in {ASSESSMENT, MESSAGING} or name.startswith("docs/research/discovery/")
        if not path.exists():
            documents[name] = None
            if research_source and name != MESSAGING:
                handoff_text[name] = ""
            if name in required or previous.get(name) is not None:
                findings.append({"kind": "missing_document", "path": name})
                impacts.append(impact_for(name, "missing_document"))
            continue
        if name in COORDINATION_PATHS and path.is_file() and path.stat().st_size > LIMIT:
            documents[name], size = hash_coordination_file(path)
            findings.append({"kind": "oversized_document", "path": name, "bytes": size})
            if baseline is not None and previous.get(name) != documents[name]:
                findings.append({"kind": "document_changed", "path": name})
                impacts.append(impact_for(name, "document_changed"))
            elif baseline is None:
                impacts.append(impact_for(name, "first_observation"))
            continue
        data = read_bounded(path)
        text = data.decode("utf-8-sig")
        if research_source or name in registered or is_campaign(name, text):
            handoff_text[name] = text
        documents[name] = hashlib.sha256(data).hexdigest()
        accepted = {documents[name]}
        if is_epic(name):
            # A baseline written before Handoff exclusion holds the whole-file hash.
            documents[name] = hashlib.sha256(without_handoff(data)).hexdigest()
            accepted.add(documents[name])
        if baseline is not None and previous.get(name) not in accepted:
            findings.append({"kind": "document_changed", "path": name})
            impacts.append(impact_for(name, "document_changed"))
        elif baseline is None:
            impacts.append(impact_for(name, "first_observation"))
        for skill in _retired_pointers(text):
            findings.append({"kind": "legacy_pointer_review", "path": name, "skill": skill})
        if name == "docs/DOCUMENTS.md":
            findings.extend(current_epic_findings(root, text))
    findings.extend(research_claim_findings(handoff_text, full_inventory=full_inventory))
    findings.extend(campaign_findings(handoff_text, registered))
    snapshot ={"schema": SCHEMA, "installed_digest": installed_digest,
                "documents": documents}
    review = [row for row in findings
              if "session_marker" not in row and row["kind"] != "oversized_document"]
    return {"status": "review_required" if review else "unchanged",
            "findings": findings, "impacts": impacts, "snapshot": snapshot,
            "meaning": "Checks byte drift and current handoff references. Capability, authorization and approval are separate."}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--loaded-digest", help="observed session digest; omit when unobserved")
    parser.add_argument("--session-marker", help="<session-id>:<installed-digest> recorded with this session's first loaded_identity_unobserved")
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
        registered = _registered_campaigns(root) if args.paths is None else set()
        paths = args.paths or default_inventory(root, baseline, registered=registered)
        report = inspect(root, paths, args.loaded_digest, installed_digest, baseline,
                         set(args.required_path) | registered, args.session_marker,
                         full_inventory=args.paths is None, registered=registered)
    except (ValueError, OSError, UnicodeError, RecursionError) as exc:
        # Never echo document content, JSON bodies, or credential values.
        print(json.dumps({"status": "invalid", "error": type(exc).__name__}))
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "unchanged" else 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.exit(main())
