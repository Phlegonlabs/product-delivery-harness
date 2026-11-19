"""Compare approved RA-backed claims using only jointly inventoried Markdown.

The caller owns safe, bounded reads and missing-file findings. Both canonical
paths must be supplied; omitted paths are out of scope, not missing evidence.
Linked studies are checked only when their text is supplied too. No snapshot,
filesystem, approval inference, or general claim verification happens here.
"""

import posixpath
import re
from urllib.parse import unquote, urlsplit


MESSAGING = "docs/gtm/MESSAGING.md"
ASSESSMENT = "docs/product/research-assessment.md"
RA_ID = re.compile(r"\bRA-[A-Za-z0-9]+\b", re.IGNORECASE)
SOURCE_ID = re.compile(r"\bS-\d+\b")
PARTICIPANT = re.compile(r"\bP\d+\b")
WITHDRAWN = re.compile(r"\b(?:withdrawn|retracted|retired)\b", re.IGNORECASE)


def _plain(value):
    return value.replace("`", "").replace("**", "").strip()


def _rows(text, section):
    """Read direct tables in one named heading, excluding fences and subsections."""
    active = False
    fence = None
    header = None
    separated = False
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        marker = re.match(r"(`{3,}|~{3,})", stripped)
        if marker:
            token = marker.group(1)
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence:
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)(?:\s+#+)?$", stripped)
        if heading:
            active = len(heading.group(1)) == 2 and _plain(heading.group(2)).casefold() == section.casefold()
            header = None
            separated = False
            continue
        if not active or not stripped.startswith("|"):
            header = None
            separated = False
            continue
        cells = [_plain(cell.replace(r"\|", "|")) for cell in
                 re.split(r"(?<!\\)\|", stripped.strip("|"))]
        if header is None:
            header = [cell.casefold() for cell in cells]
        elif all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            separated = True
        elif separated and len(cells) == len(header):
            yield dict(zip(header, cells)), line_number


def _indexed(text, section, key):
    indexed = {}
    for row, _ in _rows(text, section):
        identity = row.get(key, "").upper()
        indexed.setdefault(identity, []).append(row)
    return indexed


def _support_problem(row):
    confidence = row.get("confidence", "")
    if WITHDRAWN.search(confidence + " " + row.get("sources", "")) or re.match(
            r"^(?:withdrawn|retracted|retired)\b", row.get("finding", ""), re.IGNORECASE):
        return "withdrawn"
    category = confidence.split(";", 1)[0].strip().casefold()
    if category == "unvalidated":
        return "unvalidated"
    if category not in {"sourced", "reported"}:
        return "unknown_confidence"
    if not row.get("sources", "").strip():
        return "missing_sources"
    return None


def _study_path(value, documents):
    link = re.fullmatch(r"\[[^\]]*\]\(([^)]+)\)", value)
    target = urlsplit(link.group(1) if link else value)
    if target.scheme or target.netloc:
        return None
    path = unquote(target.path)
    # Source templates use repository-relative paths; also accept Markdown's
    # assessment-relative links, but never discover a path outside the inventory.
    for candidate in (path, posixpath.normpath(posixpath.join("docs/product", path))):
        if candidate.startswith("docs/research/discovery/") and candidate in documents:
            return candidate
    return None


def _study_problem(text, research_id):
    candidates = _indexed(text, "RA-* Candidates", "ra id").get(research_id, [])
    if len(candidates) != 1:
        return "missing_candidate" if not candidates else "ambiguous_candidate"
    candidate = candidates[0]
    problem = _support_problem(candidate)
    if problem:
        return problem
    if candidate["confidence"].split(";", 1)[0].strip().casefold() != "sourced":
        return "unknown_confidence"
    # Only evidence cited by this candidate can weaken its support. Other study
    # hypotheses and disconfirming results are independent findings.
    codes = set(PARTICIPANT.findall(candidate.get("sources", "")))
    observed = set()
    evidence = list(_rows(text, "Evidence Table"))
    for row, _ in evidence:
        code = row.get("participant code", "")
        if code not in codes:
            continue
        if WITHDRAWN.search(row.get("observation or quote (redacted)", "")):
            return "withdrawn_observation"
        strength = next((value for key, value in row.items() if key.startswith("strength")), "")
        if strength.casefold() == "observed":
            observed.add(code)
    if evidence and codes and len(observed) < 3:
        return "insufficient_observations"
    return None


def research_claim_findings(documents):
    """Return current content conflicts as ``{kind, path, line, claim, ...}``.

    Accept research-first's sourced/reported categories; UNVALIDATED, withdrawal,
    unknown confidence, and unresolved explicit RA/source IDs cannot support an
    approved claim. This is not a comparison of claim wording or approval dates.
    """
    if MESSAGING not in documents or ASSESSMENT not in documents:
        return []
    assessment = documents[ASSESSMENT]
    research = _indexed(assessment, "Findings", "ra id")
    sources = _indexed(assessment, "Sources", "source id")
    findings = []
    for claim, line in _rows(documents[MESSAGING], "Approved Public Claims"):
        if not claim.get("claim"):
            continue
        references = sorted({value.upper() for value in RA_ID.findall(
            claim["claim"] + " " + claim.get("evidence", ""))})
        for research_id in references:
            rows = research.get(research_id, [])
            problem = ("missing_finding" if not rows else "ambiguous_finding") if len(rows) != 1 else None
            evidence_path = ASSESSMENT
            if not problem:
                problem = _support_problem(rows[0])
            if not problem:
                for source_id in sorted(set(SOURCE_ID.findall(rows[0]["sources"]))):
                    source_rows = sources.get(source_id, [])
                    if len(source_rows) != 1:
                        problem = "unknown_source" if not source_rows else "ambiguous_source"
                        break
                    source = source_rows[0]
                    if WITHDRAWN.search(" ".join(source.values())):
                        problem = "withdrawn_source"
                        break
                    study = _study_path(source.get("url", ""), documents)
                    if study:
                        problem = _study_problem(documents[study], research_id)
                        if problem:
                            evidence_path = study
                            break
            if problem:
                findings.append({"kind": "approved_claim_research_conflict", "path": MESSAGING,
                                 "line": line, "claim": claim["claim"], "research_id": research_id,
                                 "evidence_path": evidence_path, "reason": problem})
    return findings
