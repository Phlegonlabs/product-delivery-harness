#!/usr/bin/env python3
"""Read-only completeness check for one current UI diagnostic wave."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import review_evidence as evidence


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--request-sha256", required=True)
    args = parser.parse_args(argv)

    try:
        if args.request.stat().st_size > evidence.MAX_BYTES:
            raise ValueError("diagnostic request exceeds the bounded-input limit")
        payload = args.request.read_bytes()
        actual = hashlib.sha256(payload).hexdigest()
        if actual != args.request_sha256:
            raise ValueError("request changed after its independent read acknowledgment")
        request = json.loads(payload.decode("utf-8"))
        report = evidence.diagnostic_wave_report(args.repo_root.resolve(), request)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["complete"] else 1
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, json.JSONDecodeError) as exc:
        print(json.dumps({"schema": evidence.DIAGNOSTIC_REPORT_SCHEMA, "complete": False,
                          "repairEligible": False, "status": "blocked",
                          "findings": [str(exc)]}, ensure_ascii=False, indent=2))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
