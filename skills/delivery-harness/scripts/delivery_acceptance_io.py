"""Bounded artifact reads and canonical PRD obligation parsing."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import stat
from pathlib import Path
from typing import Any

MAX_ARTIFACT_BYTES = 16 * 1024 * 1024
TEST_ID_RE = re.compile(r"TEST-[A-Z0-9-]+")
SECRET_BASENAMES = {
    ".env",
    "credentials.json",
    "secrets.json",
    "service-account.json",
    "id_rsa",
}
SECRET_SUFFIXES = (".pem", ".key", ".p12", ".pfx", ".keystore")
SECRET_NAME_RE = re.compile(
    r"(?:^|[._-])(?:secret|secrets|password|credential|credentials|token|cookies?|storage[-_]state)"
    r"(?:[._-]|$)",
    re.IGNORECASE,
)
TABLE_HEADER = (
    "test id",
    "obligation",
    "test type",
    "required",
    "upstream trace ids",
    "expected signal",
)


class AcceptanceError(ValueError):
    """A bounded input could not be read or validated."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AcceptanceError("duplicate JSON key")
        result[key] = value
    return result


def _read_bytes(path: Path, label: str, root: Path) -> bytes:
    try:
        checked = _safe_file(root, str(path))
        info = checked.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_ARTIFACT_BYTES:
            raise AcceptanceError(f"{label} must be a bounded regular file")
        with checked.open("rb") as handle:
            data = handle.read(MAX_ARTIFACT_BYTES + 1)
        after = checked.stat()
        if len(data) > MAX_ARTIFACT_BYTES or (info.st_ino, info.st_size, info.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            raise AcceptanceError(f"{label} changed during observation or exceeds the size limit")
        return data
    except (OSError, ValueError) as exc:
        raise AcceptanceError(f"cannot safely read {label}") from exc


def _load_json(raw: bytes, label: str) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
        value = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except AcceptanceError:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise AcceptanceError(f"cannot parse {label} as UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise AcceptanceError(f"{label} must be a JSON object")
    return value


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _sibling_active_text(text: str) -> str:
    """Use the Product parser's active-Markdown view when it is installed."""

    parser = (
        Path(__file__).resolve().parents[2]
        / "product-definition-builder"
        / "scripts"
        / "markdown_contract.py"
    )
    try:
        spec = importlib.util.spec_from_file_location("delivery_markdown_contract", parser)
        if spec is None or spec.loader is None:
            raise OSError("parser loader is unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        active_text = module.active_text
        if not callable(active_text):
            raise TypeError("active_text is not callable")
        return active_text(text)
    except (OSError, TypeError, AttributeError) as exc:
        raise AcceptanceError(
            f"cannot load sibling Product Markdown parser {parser}: {exc}"
        ) from exc


def _table_cells(line: str) -> tuple[str, ...] | None:
    stripped = line.strip()
    if not stripped.startswith("|") or not stripped.endswith("|"):
        return None
    return tuple(cell.strip() for cell in stripped[1:-1].split("|"))


def _separator(cells: tuple[str, ...]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells)


def _parse_required_prd_tests(raw: bytes) -> tuple[set[str], set[str], list[str]]:
    try:
        text = raw.decode("utf-8")
    except UnicodeError as exc:
        raise AcceptanceError(f"PRD is not UTF-8: {exc}") from exc

    active = _sibling_active_text(text)
    headings = list(re.finditer(r"^## Test Obligations\s*$", active, re.MULTILINE))
    errors: list[str] = []
    if len(headings) != 1:
        return set(), set(), ["PRD requires exactly one Test Obligations section"]

    section = re.split(r"^## ", active[headings[0].end():], maxsplit=1, flags=re.MULTILINE)[0]
    lines = section.splitlines()
    headers = [
        index
        for index, line in enumerate(lines)
        if (cells := _table_cells(line)) is not None
        and tuple(cell.casefold() for cell in cells) == TABLE_HEADER
    ]
    if len(headers) != 1:
        return set(), set(), ["PRD Test Obligations requires exactly one canonical table"]

    start = headers[0] + 1
    separator = _table_cells(lines[start]) if start < len(lines) else None
    if separator is None or not _separator(separator) or len(separator) != len(TABLE_HEADER):
        return set(), set(), ["PRD Test Obligations separator row is malformed"]

    rows: list[tuple[str, ...]] = []
    index = start + 1
    while index < len(lines):
        cells = _table_cells(lines[index])
        if cells is None:
            if rows or lines[index].strip():
                break
            errors.append("PRD Test Obligations has no rows")
            break
        rows.append(cells)
        index += 1

    all_ids: set[str] = set()
    required: set[str] = set()
    for number, row in enumerate(rows, start=1):
        row_path = f"PRD Test Obligations row {number}"
        if len(row) != len(TABLE_HEADER):
            errors.append(f"{row_path} has {len(row)} cells, expected 6")
            continue
        if any(not cell for cell in row):
            errors.append(f"{row_path} has an empty cell")
            continue
        test_id = row[0].upper()
        if TEST_ID_RE.fullmatch(test_id) is None:
            errors.append(f"{row_path} has invalid TEST ID {row[0]!r}")
            continue
        if test_id in all_ids:
            errors.append(f"{row_path} duplicates {test_id}")
            continue
        all_ids.add(test_id)
        if row[3].casefold() not in {"yes", "no"}:
            errors.append(f"{test_id} Required must be Yes or No")
        elif row[3].casefold() == "yes":
            required.add(test_id)

    if not required:
        errors.append("PRD Test Obligations has no Required Yes test")
    return all_ids, required, errors


def _safe_file(root: Path, raw_path: str) -> Path:
    supplied = Path(raw_path)
    if ".." in supplied.parts:
        raise AcceptanceError("path traversal is forbidden")
    candidate = supplied if supplied.is_absolute() else root / supplied
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise AcceptanceError("path must stay inside the repository root") from exc
    current = root
    for component in relative.parts:
        name = component.casefold()
        if (name in SECRET_BASENAMES or name in {".git", ".ssh"} or name.startswith(".env.")
                or name.endswith(SECRET_SUFFIXES) or SECRET_NAME_RE.search(name)
                or ":" in component or name.rstrip(" .") != name):
            raise AcceptanceError("secret-like artifact name or unsafe path")
        current = current / component
        if current.is_symlink() or (hasattr(current, "is_junction") and current.is_junction()):
            raise AcceptanceError("path must not traverse or target a symlink or junction")
    if not current.resolve().is_relative_to(root):
        raise AcceptanceError("path must stay inside the repository root")
    return current
