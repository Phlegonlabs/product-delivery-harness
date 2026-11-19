"""Check explicit campaign-to-messaging bindings, independently of byte baselines."""

import re


MESSAGING = "docs/gtm/MESSAGING.md"
CAMPAIGN = "docs/gtm/CAMPAIGN.md"
CLAIM_ID = re.compile(r"\b(?:C-?\d+|CLAIM-[A-Za-z0-9]+)\b")
REVISION = r"[A-Za-z0-9]+(?:[._/-][A-Za-z0-9]+)*"
FIELD = re.compile(r"^\s*(?:[-*]\s+)?(?:\*\*)?([^:\n]+?)(?:\*\*)?:\s*(.*)$")
HISTORY = {"change log", "changelog", "history", "revision history", "archived drafts", "historical drafts"}


def _live_lines(text, *, include_fenced=False):
    """Keep active sections; fenced copy can use IDs but cannot declare metadata."""
    section = ""
    historical_level = None
    fence = None
    for line in text.splitlines():
        marker = re.match(r"^\s*(`{3,}|~{3,})", line)
        if marker:
            if fence is None:
                fence = marker[1]
            elif marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                fence = None
            continue
        if fence is not None:
            if include_fenced and historical_level is None:
                yield section, line
            continue
        heading = re.match(r"^(#{1,6})\s+(.+?)\s*#*\s*$", line)
        if heading:
            level, title = len(heading[1]), heading[2].lower()
            if historical_level is not None and level <= historical_level:
                historical_level = None
            if title in HISTORY:
                historical_level = level
            section = title
        if historical_level is None:
            yield section, line


def _value(value):
    return value.strip().strip("`*").strip()


def _revision(value):
    value = _value(value)
    return value if re.fullmatch(REVISION, value) else None


def is_campaign(name, text=""):
    return (name == CAMPAIGN or
            (name.startswith("docs/gtm/campaigns/") and name.count("/") == 3 and name.endswith(".md")) or
            re.match(r"\A\s*# Campaign Review Package\s*(?:[:—-]|\r?$)", text, re.I | re.M) is not None)


def campaign_links(index_text):
    for _, line in _live_lines(index_text):
        yield from re.findall(r"\[(?:Campaign|Campaign Review Package)\]\(([^()\s#]+\.md)(?:#[^()\s]+)?\)", line, re.I)


def campaign_findings(texts, registered=()):
    """Read only inventoried text. A missing dependency remains an explicit gap."""
    findings = []
    campaigns = [name for name, text in texts.items() if name in registered or is_campaign(name, text)]
    for name in campaigns:
        def finding(kind, **details):
            findings.append({"kind": kind, "path": name, "source": MESSAGING, **details})

        campaign = list(_live_lines(texts[name]))
        references = []
        unverified = False
        for _, line in campaign:
            field = FIELD.match(line)
            if field and field[1].lower() in {"messaging revision", "messaging record revision"}:
                revision = _revision(field[2])
                if revision:
                    references.append(revision)
                else:
                    unverified = True
            # Existing packages cite the source inline, including Markdown links.
            if "MESSAGING.md" in line:
                targets = list(re.finditer(r"(?:[A-Za-z0-9._:/-]+/)?MESSAGING\.md", line))
                for index, target in enumerate(targets):
                    if target[0] not in {MESSAGING, "MESSAGING.md", "./MESSAGING.md"}:
                        unverified = True
                        continue
                    end = targets[index + 1].start() if index + 1 < len(targets) else len(line)
                    suffix = line[target.end():end]
                    citation = re.match(
                        rf"[)`*\]]*\s*[,;:]?\s+(?:revision\s*:?\s*|@\s*)"
                        rf"[`*]*({REVISION})(?=[`*\s;,.]|$)", suffix, re.IGNORECASE)
                    if citation:
                        references.append(citation[1])
                    elif not (field and field[1].lower() in {"source", "messaging source", "messaging record"}
                              and re.fullmatch(r"[)`*\]\s.,;]*", suffix)):
                        unverified = True

        if not references or unverified:
            finding("campaign_handoff_unverified", reason="missing_or_unreadable_messaging_revision")
        if MESSAGING not in texts:
            finding("campaign_handoff_unverified", reason="messaging_source_not_in_inventory_or_missing")
            continue

        source = list(_live_lines(texts[MESSAGING]))
        revisions = []
        approved, forbidden = set(), set()
        approval = []
        for section, line in source:
            field = FIELD.match(line)
            if field and field[1].lower() == "revision":
                revisions.append(_revision(field[2]))
            if field and field[1].lower() == "owner approval source and approved revision":
                approval.append(_value(field[2]))
            if section == "approved public claims" and line.lstrip().startswith("|"):
                # Only the claim columns declare IDs; evidence references do not.
                cells = line.strip().strip("|").split("|")
                approved.update(CLAIM_ID.findall(cells[0]))
            if section in {"claims not allowed", "withdrawn claims"}:
                forbidden.update(CLAIM_ID.findall(line))
        current = revisions[0] if len(revisions) == 1 else None
        if current is None:
            finding("campaign_handoff_unverified", reason="missing_or_unreadable_source_revision")
        else:
            for revision in sorted(set(references)):
                if revision != current:
                    finding("campaign_messaging_stale", referenced_revision=revision,
                            current_revision=current)

        used = set(CLAIM_ID.findall("\n".join(
            line for _, line in _live_lines(texts[name], include_fenced=True))))
        for claim in sorted(used):
            if claim in forbidden or claim not in approved:
                finding("campaign_claim_not_approved", claim_id=claim,
                        reason="withdrawn" if claim in forbidden else "not_in_approved_public_claims")
        if used & approved and current is not None:
            bound_approval = len(approval) == 1 and re.search(
                rf"(?<![A-Za-z0-9._/-]){re.escape(current)}(?![A-Za-z0-9._/-])", approval[0])
            if not bound_approval:
                finding("campaign_handoff_unverified", reason="claim_approval_revision_unverified")
    return findings
