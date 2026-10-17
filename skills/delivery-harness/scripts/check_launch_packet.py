#!/usr/bin/env python3
"""Check the UTF-8 size of a launch message against an explicit budget."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


class LaunchPacketError(ValueError):
    """Base error for an invalid or oversized launch message."""


class InvalidMessageBudgetError(LaunchPacketError):
    """The budget is not a strict positive integer or the payload is not text."""


class MessageBudgetOverflowError(LaunchPacketError):
    """The final UTF-8 message exceeds the explicit byte budget."""


def check_message(message: str, max_message_bytes: int) -> int:
    """Return the final UTF-8 byte count after enforcing the exact budget.

    This function is stateless. It reads no files and starts no processes.
    """

    if isinstance(max_message_bytes, bool) or not isinstance(
        max_message_bytes, int
    ):
        raise InvalidMessageBudgetError(
            "--max-message-bytes must be a strict positive integer"
        )
    if max_message_bytes < 1:
        raise InvalidMessageBudgetError(
            "--max-message-bytes must be a strict positive integer"
        )
    if not isinstance(message, str):
        raise InvalidMessageBudgetError("message must be text")
    encoded = message.encode("utf-8")
    message_bytes = len(encoded)
    if message_bytes > max_message_bytes:
        raise MessageBudgetOverflowError(
            f"message is {message_bytes} UTF-8 bytes; "
            f"--max-message-bytes is {max_message_bytes}"
        )
    return message_bytes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--message-file", type=Path, required=True)
    parser.add_argument("--max-message-bytes", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        check_message("", args.max_message_bytes)
        with args.message_file.open("rb") as stream:
            encoded = stream.read(args.max_message_bytes + 1)
        if len(encoded) > args.max_message_bytes:
            raise MessageBudgetOverflowError(
                f"message exceeds {args.max_message_bytes} UTF-8 bytes"
            )
        message = encoded.decode("utf-8")
        message_bytes = check_message(message, args.max_message_bytes)
    except LaunchPacketError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    except (OSError, UnicodeError) as exc:
        print(f"cannot read a UTF-8 message file: {exc}", file=sys.stderr)
        return 2
    print(
        json.dumps(
            {
                "message_bytes": message_bytes,
                "max_message_bytes": args.max_message_bytes,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
