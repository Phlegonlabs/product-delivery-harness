#!/usr/bin/env python3
"""Validate a `program` Product Definition package: the Module Map, the shared
program contracts, and every module package under docs/product/modules/."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Module-attribute access only: check_product_package imports this module too,
# so nothing here may read it at import time.
import check_product_package as cpp
from contract_utils import canonical_product_bytes, safe_read_text, sha256_text
from markdown_contract import active_text

PROGRAM_SCOPES = ("PRG", "E2E", "MIG")
# Registry families; UX IDs are scope-checked but never referenced across modules.
FAMILIES = ("PRD", "UI", "ARCH", "TEST", "BR")
MAP_HEADER = ("module", "scope", "name", "owns", "depends on", "order", "status")

_ID_RE = re.compile(r"(?:PRD|UX|UI|ARCH|TEST|BR)-[A-Z0-9]+(?:-[A-Z0-9]+)*", re.I)
_UI_HEADING_RE = re.compile(r"^###\s+(UI-[A-Z0-9]+(?:-[A-Z0-9]+)*)\b", re.I)


@dataclass(frozen=True)
class ModuleRef:
    module_id: str
    scope: str
    depends_on: tuple[str, ...]  # module ids, as written in the Module Map
    order: int | None
    status: str
    directory: Path | None  # modules/<id>; None when the directory is absent
    mapped: bool  # False for a directory that has no Module Map row


@dataclass(frozen=True)
class Program:
    root: Path
    prd: str
    architecture: str
    stack: str
    modules: tuple[ModuleRef, ...]
    texts: dict[str, tuple[str, str]]  # module id -> (PRD, architecture), readable modules only
    registry: dict[str, dict[str, frozenset[str]]]  # scope -> family -> defined IDs
    digest: str  # program_prd_digest of the program PRD
    problems: tuple[str, ...]  # files that could not be read


@dataclass(frozen=True)
class ProgramContext:
    """What `validate_texts` needs to check one module inside its program."""

    module_id: str
    scope: str
    program_prd: str
    program_architecture: str
    registry: dict[str, dict[str, frozenset[str]]]
    depends_on: frozenset[str]  # scope tokens of the modules this one depends on
    program_digest: str

    def other_ids(self, family: str) -> frozenset[str]:
        """IDs of one family defined by the program and every other module."""

        return frozenset(
            identifier
            for scope, families in self.registry.items()
            if scope != self.scope
            for identifier in families.get(family, ())
        )


def program_prd_digest(prd_text: str) -> str:
    """`sha256:<hex>` of the canonical program PRD (approval block excluded)."""

    return "sha256:" + sha256_text(canonical_product_bytes(prd_text, "", ""))


def _scope_of(identifier: str) -> str:
    parts = identifier.split("-")
    return parts[1] if len(parts) > 2 else ""


def _defined_ids(text: str) -> set[str]:
    """IDs a document defines: a table's first cell or a `### UI-...` heading."""

    found: set[str] = set()
    for line in active_text(text).splitlines():
        heading = _UI_HEADING_RE.match(line)
        cells = cpp._table_cells(line)
        first = heading.group(1) if heading else (cells[0] if cells else "")
        if _ID_RE.fullmatch(first):
            found.add(first.upper())
    return found


def _discover(product_root: Path, prd_text: str) -> list[ModuleRef]:
    section = cpp._section(prd_text, "## Module Map") or ""
    rows = cpp._find_table(section, MAP_HEADER) or []
    modules_dir = product_root / "modules"
    directories = (
        {path.name: path for path in modules_dir.iterdir() if path.is_dir()}
        if modules_dir.is_dir()
        else {}
    )
    refs: list[ModuleRef] = []
    for row in rows:
        if len(row) != len(MAP_HEADER):
            continue
        module_id, scope, _name, _owns, depends, order, status = row
        deps = () if depends.casefold() == "none" else tuple(
            item.strip() for item in depends.split(",") if item.strip()
        )
        refs.append(ModuleRef(
            module_id, scope, deps, int(order) if order.isdigit() else None,
            status.casefold(), directories.get(module_id), True,
        ))
    mapped = {ref.module_id for ref in refs}
    refs.extend(
        ModuleRef(name, "", (), None, "", path, False)
        for name, path in sorted(directories.items())
        if name not in mapped
    )
    return refs


def discover_modules(product_root: Path) -> list[ModuleRef]:
    """Module Map rows joined to the directories under `modules/`."""

    prd_text, _ = safe_read_text(product_root / "PRD.md")
    return _discover(product_root, prd_text or "")


def _register(
    registry: dict[str, dict[str, set[str]]], scopes: tuple[str, ...], ids: set[str]
) -> None:
    for identifier in ids:
        family = identifier.split("-")[0]
        if _scope_of(identifier) in scopes and family in FAMILIES:
            registry.setdefault(_scope_of(identifier), {}).setdefault(family, set()).add(identifier)


def load_program(product_root: Path) -> Program:
    """Read the program files, discover the modules and build the ID registry."""

    problems: list[str] = []

    def read(path: Path, label: str) -> str | None:
        text, error = safe_read_text(path)
        if error is not None:
            problems.append(f"{label}: {error}")
        return text

    prd = read(product_root / "PRD.md", "program") or ""
    architecture = read(product_root / "architecture.md", "program") or ""
    stack = read(product_root / "stack-decisions.md", "program") or ""
    modules = tuple(_discover(product_root, prd))
    texts: dict[str, tuple[str, str]] = {}
    raw: dict[str, dict[str, set[str]]] = {}
    _register(raw, PROGRAM_SCOPES, _defined_ids(prd) | _defined_ids(architecture))
    for ref in modules:
        if not (ref.mapped and ref.directory):
            continue
        module_prd = read(ref.directory / "PRD.md", ref.scope)
        module_architecture = read(ref.directory / "architecture.md", ref.scope)
        if module_prd is None or module_architecture is None:
            continue
        texts[ref.module_id] = (module_prd, module_architecture)
        _register(raw, (ref.scope,), _defined_ids(module_prd) | _defined_ids(module_architecture))
    registry = {
        scope: {family: frozenset(ids) for family, ids in families.items()}
        for scope, families in raw.items()
    }
    return Program(
        product_root, prd, architecture, stack, modules, texts, registry,
        program_prd_digest(prd), tuple(problems),
    )


def module_context(program: Program, module_id: str) -> ProgramContext:
    """The program view `validate_texts` receives for one module (no I/O)."""

    ref = next((m for m in program.modules if m.module_id == module_id and m.mapped), None)
    if ref is None:
        raise ValueError(f"unknown module {module_id!r}")
    scopes = {m.module_id: m.scope for m in program.modules}
    return ProgramContext(
        module_id, ref.scope, program.prd, program.architecture, program.registry,
        frozenset(scopes[dep] for dep in ref.depends_on if dep in scopes),
        program.digest,
    )


def _check_discovery(program: Program, problems: list[str]) -> None:
    for ref in program.modules:
        if not ref.mapped:
            cpp._add(problems, "program", f"modules/{ref.module_id} has no Module Map row")
        elif ref.directory is None and ref.status != "planned":
            cpp._add(
                problems, "program",
                f"Module Map row {ref.module_id!r} has status {ref.status!r} "
                f"but no modules/{ref.module_id} directory",
            )


def validate_program(
    product_root: Path,
    *,
    module: str | None = None,
    require_filled: bool = False,
    require_approved: bool = False,
    notes: list[str] | None = None,
) -> list[str]:
    """Return `<scope>: <message>` failures for a program package.

    Program files always run, because they supply the registry. `module`
    limits the per-module pass to one module id. Warnings that must not fail
    the run, such as `stale_program_revision`, are appended to `notes`.
    """

    program = load_program(product_root)
    problems = list(program.problems)
    _check_discovery(program, problems)
    return problems
