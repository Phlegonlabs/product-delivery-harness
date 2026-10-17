"""Read-only local microbenchmarks; run from the repository root.

This is research code, not a verifier, authorization source, or production fix.
It writes one new JSON evidence file and refuses to overwrite prior evidence.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
from unittest.mock import patch

ROOT = Path.cwd().resolve()
sys.path.insert(0, str(ROOT / "skills/delivery-harness/scripts"))
import docs_weight
import harness_git
import harness_step


def measure(function, repetitions):
    samples = []
    values = []
    original = subprocess.run
    for _ in range(repetitions):
        calls = Counter()
        elapsed = defaultdict(float)

        def timed_run(argv, *args, **kwargs):
            # Keep command outputs and local configuration out of evidence.
            kind = next((name for name in ("config", "show", "cat-file", "ls-tree", "status", "rev-parse", "for-each-ref", "merge-base", "worktree") if name in argv), "other")
            started = time.perf_counter()
            try:
                return original(argv, *args, **kwargs)
            finally:
                calls[kind] += 1
                elapsed[kind] += time.perf_counter() - started

        started = time.perf_counter()
        with patch.object(subprocess, "run", timed_run):
            values.append(function())
        samples.append({"wall_ms": round((time.perf_counter() - started) * 1000, 3), "subprocess_calls": dict(calls), "subprocess_ms": {key: round(value * 1000, 3) for key, value in elapsed.items()}})
    return {"samples": samples, "median_ms": statistics.median(item["wall_ms"] for item in samples)}, values


def bulk_weights(sha):
    """Experimental equivalent word counts via one hardened batch read."""
    files = docs_weight.tracked_files(ROOT, sha)
    requests = "".join(f"{sha}:{path.as_posix()}\n" for path in files).encode()
    response = harness_git.run_git(ROOT, "cat-file", "--batch", input=requests, text=False, check=True).stdout
    offset = 0
    result = {}
    for path in files:
        end = response.index(b"\n", offset)
        _oid, kind, size_text = response[offset:end].split()
        if kind != b"blob":
            raise RuntimeError("Expected a blob")
        size = int(size_text)
        start = end + 1
        payload = response[start:start + size]
        if len(payload) != size or response[start + size:start + size + 1] != b"\n":
            raise RuntimeError("Malformed batch response")
        result[path.as_posix()] = len(payload.decode("utf-8").split())
        offset = start + size + 1
    if offset != len(response):
        raise RuntimeError("Unexpected trailing bytes")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=3)
    args = parser.parse_args()
    if args.out.exists() or args.repetitions < 1:
        parser.error("Use a new output path and a positive repetition count")
    sha = harness_git.run_git(ROOT, "rev-parse", "HEAD", check=True).stdout.strip()
    inventory = []
    for directory in sorted((ROOT / "skills").iterdir()):
        entry = directory / "SKILL.md"
        if entry.is_file():
            references = sorted((directory / "references").glob("*.md"))
            inventory.append({"skill": directory.name, "entry_words": len(entry.read_text(encoding="utf-8").split()), "reference_files": len(references), "reference_words": sum(len(path.read_text(encoding="utf-8").split()) for path in references)})
    sequential, expected = measure(lambda: docs_weight.weights(ROOT, sha), args.repetitions)
    batched, actual = measure(lambda: bulk_weights(sha), args.repetitions)
    if not all(value == expected[0] for value in expected + actual):
        raise RuntimeError("Word-count outputs differ")
    # Exercise only observe(): these are minimal synthetic context dictionaries,
    # not a valid PLAN/RUN and not a complete Harness transition benchmark.
    plan = {"revision": 1}
    run = {"plan": {"revision": 1, "digest_sha256": harness_step.plan_digest(plan)}, "integration": {"branch": "research-harness-speed", "batch_base_sha": sha}}
    observation, observed = measure(lambda: harness_step.observe(ROOT, plan, run), args.repetitions)
    if any(value["git"]["head_sha"] != sha for value in observed):
        raise RuntimeError("HEAD changed during observation")
    result = {"captured_at": datetime.now(timezone.utc).isoformat(), "head_sha": sha, "python": sys.version, "platform": platform.platform(), "repetitions": args.repetitions, "scope": "Warm-process local microbenchmarks, no end-to-end run, model calls, containers, or production changes. Existing per-command Git preflights retained in both blob-read variants.", "inventory": inventory, "baseline_file_count": len(expected[0]), "baseline_word_count": sum(expected[0].values()), "baseline_weights": sequential, "experimental_bulk_weights": batched, "outputs_equal": True, "observe_only": observation}
    with args.out.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(result, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(json.dumps({"head_sha": sha, "baseline_files": result["baseline_file_count"], "baseline_median_ms": sequential["median_ms"], "bulk_median_ms": batched["median_ms"], "observe_median_ms": observation["median_ms"], "outputs_equal": True}, indent=2))


if __name__ == "__main__":
    main()
