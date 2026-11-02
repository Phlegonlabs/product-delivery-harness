#!/usr/bin/env python3
"""Find sentences that the skill documentation states in more than one file.

Scans every skills/<skill>/SKILL.md and every Markdown file under
skills/<skill>/references/ (the same selection as docs_weight.py; the
references/legacy/ folder is skipped). Fenced code, YAML front matter, HTML
comments, headings, and table header and separator rows are not prose and are
skipped. The rest is split into sentences and normalized: lowercase, collapsed
whitespace, backticks and emphasis removed, Markdown links reduced to their
text, trailing punctuation removed.

Two classes are reported:

* exact: one normalized sentence of at least --min-words words that appears in
  two or more files;
* near: sentences of at least 12 words in different files whose word 4-gram
  sets have Jaccard similarity of at least --threshold.

"Duplicated words" counts the saving if every group were reduced to one copy:
the words of each exact occurrence beyond the first, plus the words of each
near variant beyond the most common one. The report is read-only. It exits 0
unless --fail-over N is given and the total exceeds N.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, NamedTuple

DEFAULT_MIN_WORDS = 8
DEFAULT_NEAR_MIN_WORDS = 12
DEFAULT_THRESHOLD = 0.6
SHINGLE_SIZE = 4

FENCE = re.compile(r"^\s*(`{3,}|~{3,})")
HEADING = re.compile(r"^\s{0,3}#{1,6}(\s|$)")
RULE = re.compile(r"^\s{0,3}([-*_=])(\s*\1){2,}\s*$")
TABLE_ROW = re.compile(r"^\s*\|")
TABLE_SEPARATOR = re.compile(r"^\s*\|?(\s*:?-+:?\s*\|)*\s*:?-+:?\s*\|?\s*$")
LINK_DEFINITION = re.compile(r"^\s{0,3}\[[^\]]+\]:\s+\S+")
HTML_ONLY = re.compile(r"^\s*</?[A-Za-z][^>]*>\s*$")
LIST_ITEM = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+(?:\[[ xX]\]\s+)?")
CODE_SPAN = re.compile(r"(`+)(.+?)(?<!`)\1(?!`)", re.DOTALL)
SENTENCE_END = re.compile(r"[.!?][\"')\]*_]*\s+(?=[A-Z0-9\"'(\[*_<`\x00])")
ABBREVIATION = re.compile(r"(?:^|[\s(\[*_])(?:e\.g|i\.e|vs|cf)\.$", re.IGNORECASE)
IMAGE_OR_LINK = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
REFERENCE_LINK = re.compile(r"\[([^\]]+)\]\[[^\]]*\]")
AUTOLINK = re.compile(r"<(https?://[^>\s]+)>")
STRONG = re.compile(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1")
EMPHASIS_STAR = re.compile(r"(?<![\w*])\*(?=\S)([^*]+?)(?<=\S)\*(?![\w*])")
EMPHASIS_UNDERSCORE = re.compile(r"(?<![\w_])_(?=\S)([^_]+?)(?<=\S)_(?![\w_])")
PLACEHOLDER = re.compile(r"\x00(\d+)\x00")
WORD = re.compile(r"\w+")
TRAILING_PUNCTUATION = ".!?,;:…"


class Sentence(NamedTuple):
    line: int
    text: str  # normalized
    words: int


def _mask_code(text: str) -> tuple[str, list[str]]:
    """Replace inline code spans with placeholders so their punctuation survives."""

    spans: list[str] = []

    def hide(match: re.Match[str]) -> str:
        spans.append(match.group(2).strip())
        return f"\x00{len(spans) - 1}\x00" + "\n" * match.group(0).count("\n")

    return CODE_SPAN.sub(hide, text), spans


def _finish(masked: str, spans: list[str]) -> str:
    text = AUTOLINK.sub(r"\1", masked)
    text = IMAGE_OR_LINK.sub(r"\1", text)
    text = REFERENCE_LINK.sub(r"\1", text)
    text = STRONG.sub(r"\2", text)
    text = EMPHASIS_STAR.sub(r"\1", text)
    text = EMPHASIS_UNDERSCORE.sub(r"\1", text)
    text = PLACEHOLDER.sub(lambda match: spans[int(match.group(1))], text)
    text = " ".join(text.lower().split())
    return text.rstrip(TRAILING_PUNCTUATION + " ")


def normalize(sentence: str) -> str:
    """Lowercase, collapse whitespace, strip markup and trailing punctuation."""

    return _finish(*_mask_code(sentence))


def _split_sentences(masked: str) -> list[tuple[int, str]]:
    """Return (offset, segment) pairs for each sentence of a masked block."""

    segments: list[tuple[int, str]] = []
    start = 0
    for match in SENTENCE_END.finditer(masked):
        if ABBREVIATION.search(masked[: match.start() + 1]):
            continue
        segments.append((start, masked[start : match.end()]))
        start = match.end()
    segments.append((start, masked[start:]))
    return segments


def _blocks(text: str) -> list[tuple[int, list[str]]]:
    """Return (first line number, lines) for each prose block of one document."""

    lines = text.splitlines()
    blocks: list[tuple[int, list[str]]] = []
    current: tuple[int, list[str]] | None = None
    fence: str | None = None
    in_comment = False
    table_row = -1
    first = 0
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                first = index + 1
                break

    def flush() -> None:
        nonlocal current
        if current is not None:
            blocks.append(current)
            current = None

    for index in range(first, len(lines)):
        number = index + 1
        line = lines[index]
        match = FENCE.match(line)
        if match:
            marker = match.group(1)
            if fence is None:
                fence = marker
                flush()
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
            continue
        if fence is not None:
            continue
        if in_comment:
            in_comment = "-->" not in line
            continue
        line = re.sub(r"<!--.*?-->", "", line)
        if "<!--" in line:
            line = line.split("<!--", 1)[0]
            in_comment = True
        while line.lstrip().startswith(">"):
            line = line.lstrip()[1:]
        if not line.strip():
            flush()
            table_row = -1
            continue
        if TABLE_ROW.match(line):
            flush()
            table_row += 1
            if table_row == 0 or TABLE_SEPARATOR.match(line):
                continue
            cells = re.split(r"(?<!\\)\|", line.strip().strip("|"))
            for cell in cells:
                if cell.strip():
                    blocks.append((number, [cell.replace("\\|", "|").strip()]))
            continue
        table_row = -1
        if (
            HEADING.match(line)
            or RULE.match(line)
            or LINK_DEFINITION.match(line)
            or HTML_ONLY.match(line)
        ):
            flush()
            continue
        item = LIST_ITEM.match(line)
        if item:
            flush()
            current = (number, [line[item.end() :].strip()])
        elif current is None:
            current = (number, [line.strip()])
        else:
            current[1].append(line.strip())
    flush()
    return blocks


def parse_document(text: str) -> list[Sentence]:
    """Split one Markdown document into normalized prose sentences."""

    sentences: list[Sentence] = []
    for first_line, lines in _blocks(text):
        masked, spans = _mask_code("\n".join(lines))
        for offset, segment in _split_sentences(masked):
            normalized = _finish(segment, spans)
            if not WORD.search(normalized):
                continue
            lead = len(segment) - len(segment.lstrip())
            line = first_line + masked.count("\n", 0, offset + lead)
            sentences.append(Sentence(line, normalized, len(normalized.split())))
    return sentences


def document_paths(repo_root: Path) -> list[Path]:
    """SKILL.md plus nested references Markdown under skills/, minus references/legacy/."""

    skills = repo_root / "skills"
    if not skills.is_dir():
        return []
    found: list[Path] = []
    for skill in sorted(path for path in skills.iterdir() if path.is_dir()):
        if (skill / "SKILL.md").is_file():
            found.append(skill / "SKILL.md")
        references = skill / "references"
        if references.is_dir():
            for path in sorted(references.rglob("*.md")):
                if path.is_file() and path.relative_to(references).parts[0] != "legacy":
                    found.append(path)
    return found


def load_allowlist(path: Path) -> frozenset[str]:
    """Read normalized sentences, one per line; blank lines and # comments are ignored."""

    entries = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip() and not raw.lstrip().startswith("#"):
            entries.add(normalize(raw))
            entries.add(" ".join(raw.lower().split()).rstrip(TRAILING_PUNCTUATION + " "))
    return frozenset(entries)


def _shingles(sentence: str) -> frozenset[tuple[str, ...]]:
    words = WORD.findall(sentence)
    if len(words) < SHINGLE_SIZE:
        return frozenset()
    return frozenset(
        tuple(words[index : index + SHINGLE_SIZE])
        for index in range(len(words) - SHINGLE_SIZE + 1)
    )


def _similar_pairs(
    sets: list[frozenset[tuple[str, ...]]], threshold: float
) -> list[tuple[int, int, float]]:
    """Exact Jaccard pairs found through a prefix-filtered inverted index.

    Two sets with Jaccard >= t share at least ceil(t * size) elements, so
    indexing only the rarest (size - ceil(t * size) + 1) shingles of each set
    cannot miss a qualifying pair, and the posting lists stay short.
    """

    frequency = Counter(shingle for shingles in sets for shingle in shingles)
    index: dict[tuple[str, ...], list[int]] = defaultdict(list)
    pairs: list[tuple[int, int, float]] = []
    for current, shingles in enumerate(sets):
        if not shingles:
            continue
        ordered = sorted(shingles, key=lambda shingle: (frequency[shingle], shingle))
        prefix = len(ordered) - math.ceil(threshold * len(ordered) - 1e-9) + 1
        candidates: set[int] = set()
        for shingle in ordered[:prefix]:
            candidates.update(index[shingle])
            index[shingle].append(current)
        for other in sorted(candidates):
            shared = len(shingles & sets[other])
            similarity = shared / (len(shingles) + len(sets[other]) - shared)
            if similarity >= threshold - 1e-12:
                pairs.append((other, current, similarity))
    return pairs


def _near_groups(
    sentences: dict[str, list[dict[str, Any]]],
    threshold: float,
    near_min_words: int,
) -> list[dict[str, Any]]:
    texts = [text for text in sorted(sentences) if len(text.split()) >= near_min_words]
    sets = [_shingles(text) for text in texts]
    parent = list(range(len(texts)))
    weakest: dict[int, float] = {}

    def find(item: int) -> int:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    for first, second, similarity in _similar_pairs(sets, threshold):
        files_first = {entry["file"] for entry in sentences[texts[first]]}
        files_second = {entry["file"] for entry in sentences[texts[second]]}
        if len(files_first) == 1 and files_first == files_second:
            continue  # both only in one same file: not a cross-file repeat
        root_first, root_second = find(first), find(second)
        low = min(similarity, weakest.get(root_first, 1.0), weakest.get(root_second, 1.0))
        parent[root_second] = root_first
        weakest[root_first] = low

    members: dict[int, list[int]] = defaultdict(list)
    for item in range(len(texts)):
        members[find(item)].append(item)
    groups = []
    for root, items in members.items():
        if len(items) < 2:
            continue
        variants = sorted(
            (
                {
                    "sentence": texts[item],
                    "words": len(texts[item].split()),
                    "occurrences": sentences[texts[item]],
                }
                for item in items
            ),
            key=lambda variant: (-len(variant["occurrences"]), -variant["words"], variant["sentence"]),
        )
        groups.append(
            {
                "similarity": round(weakest[root], 3),
                "duplicated_words": sum(variant["words"] for variant in variants[1:]),
                "variants": variants,
            }
        )
    groups.sort(key=lambda group: (-group["duplicated_words"], group["variants"][0]["sentence"]))
    return groups


def _skill_of(path: str) -> str:
    return path.split("/", 2)[1]


def scan(
    repo_root: Path,
    *,
    min_words: int = DEFAULT_MIN_WORDS,
    threshold: float = DEFAULT_THRESHOLD,
    allowlist: frozenset[str] = frozenset(),
    near_min_words: int = DEFAULT_NEAR_MIN_WORDS,
) -> dict[str, Any]:
    occurrences: dict[str, list[dict[str, Any]]] = defaultdict(list)
    paths = document_paths(repo_root)
    sentence_count = word_count = 0
    for path in paths:
        relative = path.relative_to(repo_root).as_posix()
        for sentence in parse_document(path.read_text(encoding="utf-8")):
            sentence_count += 1
            word_count += sentence.words
            if sentence.text not in allowlist:
                occurrences[sentence.text].append({"file": relative, "line": sentence.line})

    exact = []
    for text, found in occurrences.items():
        words = len(text.split())
        if words >= min_words and len({entry["file"] for entry in found}) >= 2:
            exact.append(
                {
                    "sentence": text,
                    "words": words,
                    "occurrences": found,
                    "duplicated_words": words * (len(found) - 1),
                }
            )
    exact.sort(key=lambda group: (-group["duplicated_words"], group["sentence"]))
    near = _near_groups(occurrences, threshold, near_min_words) if threshold <= 1 else []

    involved: dict[tuple[str, int, str], int] = {}
    for group in exact:
        for entry in group["occurrences"]:
            involved[(entry["file"], entry["line"], group["sentence"])] = group["words"]
    for group in near:
        for variant in group["variants"]:
            for entry in variant["occurrences"]:
                involved[(entry["file"], entry["line"], variant["sentence"])] = variant["words"]
    per_file: dict[str, dict[str, int]] = {}
    per_skill: dict[str, dict[str, int]] = {}
    for path in paths:
        relative = path.relative_to(repo_root).as_posix()
        per_file[relative] = {"sentences": 0, "words_in_duplicates": 0}
        per_skill.setdefault(
            _skill_of(relative), {"files": 0, "sentences": 0, "words_in_duplicates": 0}
        )["files"] += 1
    for (file, _line, _text), words in involved.items():
        for bucket in (per_file[file], per_skill[_skill_of(file)]):
            bucket["sentences"] += 1
            bucket["words_in_duplicates"] += words

    exact_words = sum(group["duplicated_words"] for group in exact)
    near_words = sum(group["duplicated_words"] for group in near)
    return {
        "parameters": {
            "min_words": min_words,
            "near_min_words": near_min_words,
            "threshold": threshold,
            "allowlist_entries": len(allowlist),
        },
        "exact": exact,
        "near": near,
        "summary": {
            "files": len(paths),
            "sentences": sentence_count,
            "words": word_count,
            "exact_groups": len(exact),
            "near_groups": len(near),
            "exact_duplicated_words": exact_words,
            "near_duplicated_words": near_words,
            "duplicated_words": exact_words + near_words,
            "per_skill": dict(sorted(per_skill.items())),
            "per_file": dict(
                sorted(
                    per_file.items(),
                    key=lambda item: (-item[1]["words_in_duplicates"], item[0]),
                )
            ),
        },
    }


def _places(found: list[dict[str, Any]], indent: str) -> list[str]:
    return [f"{indent}{entry['file']}:{entry['line']}" for entry in found]


def render_groups(result: dict[str, Any]) -> list[str]:
    out = [f"EXACT DUPLICATES: {len(result['exact'])} groups"]
    for number, group in enumerate(result["exact"], 1):
        out.append(
            f"[E{number}] {group['words']} words x {len(group['occurrences'])}"
            f" = {group['duplicated_words']} duplicated"
        )
        out.append(f"    {group['sentence']}")
        out.extend(_places(group["occurrences"], "      "))
    out.append("")
    out.append(f"NEAR DUPLICATES: {len(result['near'])} groups")
    for number, group in enumerate(result["near"], 1):
        out.append(
            f"[N{number}] {len(group['variants'])} variants, similarity >= "
            f"{group['similarity']}, {group['duplicated_words']} duplicated"
        )
        for variant in group["variants"]:
            out.append(f"    ({variant['words']} words) {variant['sentence']}")
            out.extend(_places(variant["occurrences"], "      "))
    return out


def render_summary(summary: dict[str, Any]) -> list[str]:
    out = [
        f"files {summary['files']}, sentences {summary['sentences']}, words {summary['words']}",
        f"exact groups {summary['exact_groups']}: {summary['exact_duplicated_words']} duplicated words",
        f"near groups {summary['near_groups']}: {summary['near_duplicated_words']} duplicated words",
        f"DUPLICATED WORDS: {summary['duplicated_words']}",
        "",
        "words held in duplicated sentences, per skill:",
    ]
    for skill, bucket in summary["per_skill"].items():
        out.append(
            f"  {skill}: {bucket['words_in_duplicates']} words,"
            f" {bucket['sentences']} sentences, {bucket['files']} files"
        )
    out.append("")
    out.append("words held in duplicated sentences, per file:")
    for file, bucket in summary["per_file"].items():
        if bucket["sentences"]:
            out.append(f"  {file}: {bucket['words_in_duplicates']} words, {bucket['sentences']} sentences")
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="repository root (default: current directory)")
    parser.add_argument("--min-words", type=int, default=DEFAULT_MIN_WORDS, help="shortest exact-duplicate sentence (default: 8)")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD, help="near-duplicate Jaccard threshold on word 4-grams (default: 0.6)")
    parser.add_argument("--allowlist", type=Path, help="text file of normalized sentences to ignore, one per line")
    parser.add_argument("--summary", action="store_true", help="print only the counts per skill and per file")
    parser.add_argument("--json", action="store_true", help="print JSON instead of text")
    parser.add_argument("--fail-over", type=int, metavar="N", help="exit 1 when duplicated words exceed N")
    args = parser.parse_args(argv)
    try:
        allowlist = load_allowlist(args.allowlist) if args.allowlist else frozenset()
        result = scan(
            args.repo_root,
            min_words=args.min_words,
            threshold=args.threshold,
            allowlist=allowlist,
        )
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    summary = result["summary"]
    if args.json:
        payload = {"parameters": result["parameters"], "summary": summary}
        if not args.summary:
            payload = result
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        lines = [] if args.summary else render_groups(result) + [""]
        print("\n".join(lines + render_summary(summary)))
    if args.fail_over is not None and summary["duplicated_words"] > args.fail_over:
        return 1
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
