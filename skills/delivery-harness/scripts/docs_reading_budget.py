#!/usr/bin/env python3
"""Measure how many words an agent must read before it can act at each stage.

Entry points are every skills/<skill>/SKILL.md and each "## " section of
skills/delivery-harness/references/stages/stage-cards.md (plus that file's
lead paragraph). From each entry the script follows links to Markdown files
under skills/ and counts words. References under references/legacy/, links
outside skills/ and external URLs are skipped.

Links are Markdown links to .md files and backticked paths such as
`references/x.md#anchor` that resolve to a real file (--markdown-links-only
keeps the first kind). A link with #anchor counts only that section, from its
heading to the next heading of the same or a higher level; a missing anchor
falls back to the whole file. Prose such as "read X through its Foo section"
is not parsed, so such a link counts the whole file. Words are counted as
docs_weight.py does (whitespace split, code blocks included), so the numbers
reconcile with it. --skip-section SLUG leaves a heading's section out.

Each link gets one class from the clause that holds it. A clause ends at . ! ?
; or a table cell border. Link text, link targets, code spans and quoted
section names are ignored while the clause is read. Rules, in order:

1. conditional: the clause has when, whenever, if, only, optional, unless,
   pinned or conditional, or starts with "For" ("For a web app, also read X"),
   or the link text or target contains "enhancement" or "legacy";
2. mandatory: the clause has read, follow, apply, use, run, complete, before,
   must, required or whole (the word RUN in capitals is a document name, not
   a verb), or a heading above the link names Required Reading, Required Skills
   And Inputs, Stage Routing or Mandatory Governance Routes;
3. anything else is conditional.

The rules are crude on purpose. A wrong class stays visible: --links prints
every link with its class and the words that decided it.

Per entry: own words, mandatory words at depth 1, mandatory words up to
--depth (default 2), conditional words at depth 1 not already read, and the ten
heaviest mandatory files ("whole" when some link reads the file without an
anchor, "part" when only named sections are read). Only mandatory links are followed past depth 1, and
only from the lines actually read. The report is read-only and exits 0 unless
--budget N is given and some entry's mandatory words exceed N.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, NamedTuple
from urllib.parse import unquote

STAGE_CARDS = "skills/delivery-harness/references/stages/stage-cards.md"
MANDATORY_HEADINGS = (
    "required reading",
    "required skills and inputs",
    "stage routing",
    "mandatory governance routes",
)
CONDITIONAL = re.compile(
    r"\b(when|whenever|if|only|optional(?:ly)?|unless|pinned|conditional)\b", re.IGNORECASE
)
LEADING_FOR = re.compile(r"\W*(?:also\s+)?(for)\b", re.IGNORECASE)  # "For a web app, also read X"
OBLIGATION = re.compile(  # first letter either case: "RUN" is a document name, not a verb
    r"\b(?:[Rr]eads?|[Ff]ollows?|[Aa]pply|[Aa]pplies|[Uu]ses?|[Rr]uns?|[Cc]omplete"
    r"|[Bb]efore|[Mm]ust|[Rr]equired|[Ww]hole)\b"
)
QUOTED = re.compile(r"\"[^\"\n]{1,80}\"|\u201c[^\u201d\n]{1,80}\u201d")
FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")
TABLE_ROW = re.compile(r"^\s*\|")
TABLE_SEPARATOR = re.compile(r"^[\s|:-]+$")
CODE_SPAN = re.compile(r"(`+)(.+?)(?<!`)\1(?!`)")
MD_LINK = re.compile(r"(?<!!)\[([^\]]*)\]\(<?([^)\s>]*)>?(?:\s+\"[^\"]*\")?\)")
PATH_REF = re.compile(r"^([^\s#`]+\.md)(?:#([^\s`]*))?$")
CLAUSE_END = re.compile(r"[.!?;](?=\s|$)|\|")
ABBREVIATION = re.compile(r"(?:^|[\s(\[*_])(?:e\.g|i\.e|vs|cf|etc)$", re.IGNORECASE)


class Link(NamedTuple):
    source: str
    line: int  # 0-based
    kind: str  # "link" or "path"
    text: str
    target: str | None  # repo-relative posix path, None when not found
    anchor: str
    status: str  # ok, missing, legacy
    cls: str  # mandatory or conditional
    why: str
    excerpt: str


class Doc:
    def __init__(self, path: str, text: str) -> None:
        self.path = path
        self.lines = text.splitlines()
        self.words = [len(line.split()) for line in self.lines]
        self.headings: list[tuple[int, int, str, str]] = []  # line, level, text, slug
        self.links: list[Link] = []
        self.by_line: dict[int, list[Link]] = {}

    def section(self, anchor: str) -> tuple[int, int] | None:
        for index, (start, level, _text, slug) in enumerate(self.headings):
            if slug == anchor:
                for line, deeper, _t, _s in self.headings[index + 1 :]:
                    if deeper <= level:
                        return start, line
                return start, len(self.lines)
        return None


def slugify(heading: str) -> str:
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading).replace("`", "")
    return re.sub(r"[^\w\- ]", "", text.lower()).replace(" ", "-")


def is_legacy(path: str) -> bool:
    parts = path.split("/")
    return len(parts) >= 5 and parts[2:4] == ["references", "legacy"]


def _blank(text: str, spans: list[tuple[int, int]]) -> str:
    for start, end in spans:
        text = text[:start] + re.sub(r"[^\n]", "_", text[start:end]) + text[end:]
    return text


def _blocks(doc: Doc) -> list[tuple[int, str, list[str]]]:
    """Prose blocks as (first line, text, ancestor headings); fences and headings skipped."""

    blocks: list[tuple[int, list[str], list[str]]] = []
    current: tuple[int, list[str], list[str]] | None = None
    fence: str | None = None
    chain: list[tuple[int, str]] = []
    start = 0
    if doc.lines and doc.lines[0].strip() == "---":
        start = next((i + 1 for i in range(1, len(doc.lines)) if doc.lines[i].strip() == "---"), 0)

    def flush() -> None:
        nonlocal current
        if current is not None:
            blocks.append(current)
            current = None

    for index in range(start, len(doc.lines)):
        line = doc.lines[index]
        marker = FENCE.match(line)
        if marker:
            flush()
            if fence is None:
                fence = marker.group(1)
            elif marker.group(1)[0] == fence[0] and len(marker.group(1)) >= len(fence):
                fence = None
            continue
        if fence is not None:
            continue
        heading = HEADING.match(line)
        if heading:
            flush()
            level, title = len(heading.group(1)), heading.group(2)
            doc.headings.append((index, level, title, ""))
            while chain and chain[-1][0] >= level:
                chain.pop()
            chain.append((level, title))
            continue
        titles = [title for _level, title in chain]
        if not line.strip():
            flush()
        elif TABLE_ROW.match(line):
            flush()
            if not TABLE_SEPARATOR.match(line):
                blocks.append((index, [line.strip()], titles))
        elif LIST_ITEM.match(line):
            flush()
            current = (index, [LIST_ITEM.sub("", line, count=1)], titles)
        elif current is None:
            current = (index, [line.strip()], titles)
        else:
            current[1].append(line.strip())
    flush()
    seen: dict[str, int] = {}
    slugged = []
    for line, level, title, _ in doc.headings:
        slug = slugify(title)
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        slugged.append((line, level, title, slug if not count else f"{slug}-{count}"))
    doc.headings = slugged
    return [(first, "\n".join(lines), titles) for first, lines, titles in blocks]


def _clause(masked: str, position: int) -> tuple[int, int]:
    start = 0
    for match in CLAUSE_END.finditer(masked):
        if ABBREVIATION.search(masked[: match.start()]):
            continue
        if match.end() <= position:
            start = match.end()
        else:
            return start, match.end()
    return start, len(masked)


def classify(clause: str, titles: list[str], text: str, target: str) -> tuple[str, str]:
    found = CONDITIONAL.search(clause) or LEADING_FOR.match(clause)
    if found:
        return "conditional", f"conditional word '{found.group(1).lower()}'"
    named = re.search(r"enhancement|legacy", f"{text} {target}", re.IGNORECASE)
    if named:
        return "conditional", f"link names '{named.group(0).lower()}'"
    found = OBLIGATION.search(clause)
    if found:
        return "mandatory", f"obligation word '{found.group(0).lower()}'"
    for title in titles:
        if any(name in title.lower() for name in MANDATORY_HEADINGS):
            return "mandatory", f"section '{title}'"
    return "conditional", "no marker"


def resolve(source: str, raw: str, root: Path, paths: bool) -> str | None:
    """Repo-relative path of an existing .md file, or None."""

    base = Path(unquote(raw))
    skill_dir = "/".join(source.split("/")[:2])
    options = [(root / source).parent / base]
    if paths:  # a backticked path may start at the skill root or the repo root
        options += [root / skill_dir / base, root / base]
    for option in options:
        absolute = option.resolve()
        if absolute.is_file():
            try:
                return absolute.relative_to(root.resolve()).as_posix()
            except ValueError:
                continue
    return None


def parse(doc: Doc, root: Path, paths: bool) -> None:
    for first, text, titles in _blocks(doc):
        spans = [m.span() for m in CODE_SPAN.finditer(text)]
        links = [
            m for m in MD_LINK.finditer(text) if not any(s <= m.start() < e for s, e in spans)
        ]
        quoted = [m.span() for m in QUOTED.finditer(text)]  # section names, not instructions
        masked = _blank(text, spans + quoted + [m.span() for m in links])
        found: list[tuple[int, str, str, str, str]] = []
        for m in links:
            target, _, anchor = m.group(2).partition("#")
            if re.match(r"[A-Za-z][A-Za-z0-9+.-]*:", target):
                continue
            if (target and not target.split("?")[0].endswith(".md")) or not (target or anchor):
                continue
            found.append((m.start(), "link", m.group(1), target.split("?")[0], anchor))
        for start, end in spans:
            if paths and not any(m.start() <= start < m.end() for m in links):
                ref = PATH_REF.match(text[start:end].strip("`"))
                if ref and "/" in ref.group(1):
                    found.append((start, "path", ref.group(1), ref.group(1), ref.group(2) or ""))
        for position, kind, label, target, anchor in sorted(found):
            if target:
                resolved = resolve(doc.path, target, root, kind == "path")
            else:
                resolved = doc.path  # "#anchor" points into this file
            status = "ok"
            if resolved is None:
                status = "missing"
            elif not resolved.startswith("skills/"):
                status = "outside"
            elif is_legacy(resolved):
                status = "legacy"
            if kind == "path" and status in ("missing", "outside"):
                continue
            begin, end = _clause(masked, position)
            cls, why = classify(masked[begin:end], titles, label, target)
            excerpt = " ".join(text[begin:end].split())
            line = first + text.count("\n", 0, position)
            link = Link(doc.path, line, kind, label, resolved, anchor, status, cls, why, excerpt)
            doc.links.append(link)
            doc.by_line.setdefault(line, []).append(link)


class Corpus:
    def __init__(self, root: Path, paths: bool = True, skip: tuple[str, ...] = ()) -> None:
        self.root, self.paths, self.skip = root, paths, skip
        self.docs: dict[str, Doc] = {}

    def doc(self, path: str) -> Doc:
        if path not in self.docs:
            doc = Doc(path, (self.root / path).read_text(encoding="utf-8"))
            parse(doc, self.root, self.paths)
            for slug in self.skip:  # drop whole sections from the reading
                for line in range(*(doc.section(slug) or (0, 0))):
                    doc.words[line] = 0
                    doc.by_line.pop(line, None)
            doc.links = [link for lines in doc.by_line.values() for link in lines]
            self.docs[path] = doc
        return self.docs[path]

    def entries(self) -> list[tuple[str, str, list[tuple[int, int]]]]:
        found = []
        for skill in sorted((self.root / "skills").glob("*/SKILL.md")):
            path = skill.relative_to(self.root).as_posix()
            found.append((skill.parent.name, path, [(0, len(self.doc(path).lines))]))
        if (self.root / STAGE_CARDS).is_file():
            doc = self.doc(STAGE_CARDS)
            cards = [h for h in doc.headings if h[1] == 2]
            lead = (0, cards[0][0] if cards else len(doc.lines))
            for line, _level, _title, slug in cards:
                found.append((f"stage-cards#{slug}", STAGE_CARDS, [lead, (line, doc.section(slug)[1])]))
        return found


def measure(corpus: Corpus, path: str, spans: list[tuple[int, int]], depth: int) -> dict[str, Any]:
    doc = corpus.doc(path)
    own_lines = {line for start, end in spans for line in range(start, end)}
    covered: dict[str, set[int]] = {path: set(own_lines)}
    own_words = sum(doc.words[i] for i in own_lines)
    frontier = [(path, own_lines)]
    reads: dict[str, dict[str, Any]] = {}
    per_depth = [0] * (depth + 1)
    conditional: list[Link] = [
        link for line in sorted(own_lines) for link in doc.by_line.get(line, [])
        if link.cls == "conditional" and link.status == "ok"
    ]
    for level in range(1, depth + 1):
        following: list[tuple[str, set[int]]] = []
        for source, lines in frontier:
            for line in sorted(lines):
                for link in corpus.doc(source).by_line.get(line, []):
                    if link.cls != "mandatory" or link.status != "ok":
                        continue
                    new = _lines(corpus, link, covered)
                    if new:
                        target = corpus.doc(link.target or "")
                        words = sum(target.words[i] for i in new)
                        per_depth[level] += words
                        info = reads.setdefault(
                            link.target or "", {"words_read": 0, "depth": level, "whole": False}
                        )
                        info["words_read"] += words
                        info["whole"] |= not link.anchor or target.section(link.anchor) is None
                        following.append((link.target or "", new))
        frontier = following
    sibling = 0
    seen: dict[str, set[int]] = {}
    for link in conditional:
        target = corpus.doc(link.target or "")
        span = _span(target, link.anchor)
        gap = set(range(*span)) - covered.get(target.path, set()) - seen.get(target.path, set())
        seen.setdefault(target.path, set()).update(gap)
        sibling += sum(target.words[i] for i in gap)
    heaviest = sorted(reads.items(), key=lambda item: (-item[1]["words_read"], item[0]))
    return {
        "file": path,
        "own_words": own_words,
        "mandatory_depth1_words": per_depth[1] if depth else 0,
        "mandatory_words": sum(per_depth),
        "conditional_depth1_words": sibling,
        "heaviest": [
            {
                "file": name,
                "words_read": info["words_read"],
                "file_words": sum(corpus.doc(name).words),
                "depth": info["depth"],
                "whole_file": info["whole"],
            }
            for name, info in heaviest[:10]
        ],
        "reads": {name: info["words_read"] for name, info in reads.items()},
        "covered": {name: sorted(lines) for name, lines in covered.items()},
    }


def _span(doc: Doc, anchor: str) -> tuple[int, int]:
    return (doc.section(anchor) if anchor else None) or (0, len(doc.lines))


def _lines(corpus: Corpus, link: Link, covered: dict[str, set[int]]) -> set[int]:
    doc = corpus.doc(link.target or "")
    new = set(range(*_span(doc, link.anchor))) - covered.setdefault(doc.path, set())
    covered[doc.path] |= new
    return new


def render(results: list[dict[str, Any]], depth: int) -> list[str]:
    out = [f"{'ENTRY':<46}{'own':>7}{'m@1':>8}{f'm@{depth}':>8}{'c@1':>8}{'must-read':>11}"]
    for item in results:
        out.append(
            f"{item['name']:<46}{item['own_words']:>7}{item['mandatory_depth1_words']:>8}"
            f"{item['mandatory_words']:>8}{item['conditional_depth1_words']:>8}"
            f"{item['own_words'] + item['mandatory_words']:>11}"
        )
    for item in results:
        out += ["", f"{item['name']}: heaviest mandatory files (words read / file words)"]
        out += [
            f"  {row['words_read']:>6} / {row['file_words']:<6} d{row['depth']} "
            f"{'whole' if row['whole_file'] else 'part '} {row['file']}"
            for row in item["heaviest"]
        ] or ["  none"]
    return out


def render_links(corpus: Corpus, selected: set[tuple[str, int]] | None) -> list[str]:
    out = []
    for path in sorted(corpus.docs):
        for link in corpus.docs[path].links:
            if selected is not None and (path, link.line) not in selected:
                continue
            target = (link.target or link.status) + (f"#{link.anchor}" if link.anchor else "")
            note = link.status if link.status != "ok" else link.cls
            out.append(f"{path}:{link.line + 1} [{note}] {link.kind} -> {target}")
            out.append(f"    {link.why}: {link.excerpt[:140]}")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="repository root (default: current directory)")
    parser.add_argument("--entry", action="append", help="entry name (or part of it); repeatable")
    parser.add_argument("--depth", type=int, default=2, help="link depth for mandatory words (default: 2)")
    parser.add_argument("--budget", type=int, metavar="N", help="exit 1 when an entry's mandatory words exceed N")
    parser.add_argument("--links", action="store_true", help="list each link with its class and deciding words")
    parser.add_argument("--markdown-links-only", action="store_true", help="ignore backticked paths")
    parser.add_argument("--skip-section", action="append", default=[], metavar="SLUG", help="leave a heading's section out of every file; repeatable")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    args = parser.parse_args(argv)
    if args.depth < 0:
        parser.error("--depth must be 0 or more")
    try:
        corpus = Corpus(args.repo_root, not args.markdown_links_only, tuple(args.skip_section))
        entries = corpus.entries()
        if args.entry:
            wanted = [name.lower() for name in args.entry]
            exact = [e for e in entries if e[0].lower() in wanted]
            entries = exact or [e for e in entries if any(w in e[0].lower() for w in wanted)]
            if not entries:
                print(f"error: no entry matches {args.entry}", file=sys.stderr)
                return 2
        results = [{"name": name, **measure(corpus, path, spans, args.depth)} for name, path, spans in entries]
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    over = [r for r in results if args.budget is not None and r["mandatory_words"] > args.budget]
    selected = None
    if args.entry:
        selected = {(p, line) for r in results for p, lines in r["covered"].items() for line in lines}
    listing = render_links(corpus, selected) if args.links else []
    for item in results:
        item.pop("covered")
    if args.json:
        payload: dict[str, Any] = {"parameters": {"depth": args.depth, "budget": args.budget}, "entries": results}
        if args.links:
            payload["links"] = listing
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("\n".join(listing if args.links else render(results, args.depth)))
    for item in over:
        print(f"over budget: {item['name']} {item['mandatory_words']} > {args.budget}")
    return 1 if over else 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
