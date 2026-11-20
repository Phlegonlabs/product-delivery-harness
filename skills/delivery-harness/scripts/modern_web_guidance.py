#!/usr/bin/env python3
"""Run Google's Modern Web Guidance CLI at the Harness pin, with telemetry off.

A project opts in with the optional `web_platform_guidance` row in its Skill
Bindings; --pin prints that row. Only `search`, `list` and `retrieve` run, so
the CLI never installs its skill, edits configuration or scans the code.

`retrieve` needs --baseline with the PRD's `Browser support` value. The CLI
runs in an empty temporary directory whose `.mwgrc` holds only that target, so
the guide names the fallbacks the target still needs, no project or user
`.mwgrc` applies, and nothing is written to the project: the CLI's own file
logging is switched off too. A guide too long for
the console is saved to a file whose path the CLI prints.

npx is looked up only in absolute PATH directories, never in the current
directory, and queries and guide IDs are limited to characters that Windows
`cmd` passes through unchanged when npx is a `.cmd` script.

The pin is the exact npm version: a published version cannot be replaced, and
npm checks the registry integrity when it downloads one. TARBALL_SHA256 is the
SHA-256 of `npm pack modern-web-guidance@<version>`; recompute it before
changing the pin.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SLOT = "web_platform_guidance"
STAGE = "optional: Modern Web Guidance for HiFi authoring and frontend implementation"
PACKAGE = "modern-web-guidance@1.0.1"
TARBALL_SHA256 = "713d3d344d6fad5c9267fb1ed8daff5dd72df4634e9ad6b2bd3b0ca17f8438a3"
COMMANDS = ("search", "list", "retrieve")
ARGUMENT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ,.:_/'+-]*")
BASELINE_RE = re.compile(
    r"Baseline (?:(?P<widely>Widely available)|(?P<newly>Newly available)|(?P<year>\d{4}))",
    re.IGNORECASE,
)


def baseline_target(value: str) -> str:
    """The `.mwgrc` baseline for a PRD `Browser support` value."""

    match = BASELINE_RE.fullmatch(value.strip())
    if match is None:
        raise ValueError(
            "--baseline takes the PRD's Browser support value: `Baseline Widely available`, "
            f"`Baseline Newly available` or `Baseline <year>`; got {value!r}"
        )
    return "widely" if match["widely"] else "newly" if match["newly"] else match["year"]


def find_npx() -> str | None:
    """npx from an absolute PATH directory; on Windows, shutil.which alone also searches the current one."""

    for directory in os.environ.get("PATH", "").split(os.pathsep):
        if directory and Path(directory).is_absolute():
            found = shutil.which(str(Path(directory) / "npx"))
            if found:
                return found
    return None


def binding_row() -> str:
    return f"| {SLOT} | {STAGE} | `{PACKAGE}` | `{TARBALL_SHA256}` |"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--pin", action="store_true", help="print the Skill Bindings row for this pin and exit")
    parser.add_argument("--baseline", help="the PRD's Browser support value; required for retrieve")
    parser.add_argument("command", nargs="?", choices=COMMANDS)
    parser.add_argument("arguments", nargs="*", help="the query, or comma-separated guide IDs for retrieve")
    args = parser.parse_args(argv)
    if args.pin:
        print(binding_row())
        return 0
    if args.command is None:
        parser.error("name a command: " + ", ".join(COMMANDS))
    config = {}
    if args.baseline is not None:
        try:
            config["baseline"] = baseline_target(args.baseline)
        except ValueError as error:
            parser.error(str(error))
    elif args.command == "retrieve":
        parser.error("retrieve needs --baseline with the PRD's Browser support value")
    for argument in args.arguments:
        if not ARGUMENT_RE.fullmatch(argument):
            parser.error(f"queries and guide IDs take letters, digits, spaces and ,.:_/'+- only; got {argument!r}")
    npx = find_npx()
    if npx is None:
        print("npx not found: Modern Web Guidance needs Node.js 22 or later", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="mwg-", ignore_cleanup_errors=True) as directory:
        Path(directory, ".mwgrc").write_text(json.dumps(config), encoding="utf-8")
        environment = dict(os.environ, DISABLE_TELEMETRY="1", ENABLE_FILE_LOGGING="false")
        command = [npx, "-y", PACKAGE, args.command, *args.arguments]
        return subprocess.run(command, cwd=directory, env=environment, check=False).returncode


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
