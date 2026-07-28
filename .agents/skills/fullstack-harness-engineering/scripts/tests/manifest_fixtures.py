"""Shared manifest fixtures for Harness command-line tests."""

from __future__ import annotations

import json


def manifest_markdown(
    heading: str, wrapper: str, value: dict[str, object]
) -> str:
    encoded = json.dumps({wrapper: value}, sort_keys=True, indent=2)
    return f"# Harness fixture\n\n{heading}\n\n```json\n{encoded}\n```\n"
