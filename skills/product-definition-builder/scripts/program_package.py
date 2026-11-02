#!/usr/bin/env python3
"""Validate a `program` Product Definition package: the Module Map, the shared
program contracts, and every module package under docs/product/modules/."""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import partial
from pathlib import Path

# Module-attribute access only: check_product_package imports this module too,
# so nothing here may read it at import time.
import check_product_package as cpp
from contract_utils import canonical_product_bytes, safe_read_text, sha256_text
from markdown_contract import active_text
from release_targets import KEBAB_RE

PROGRAM_SCOPES = ("PRG", "E2E", "MIG")
RESERVED_SCOPES = frozenset("PRD ARCH UI UX TEST DS RA MR MS TRUST AI BR PRG E2E MIG".split())
SCOPE_RE = re.compile(r"[A-Z][A-Z0-9]{1,4}")
# Registry families; UX IDs are scope-checked but never referenced across modules.
FAMILIES = ("PRD", "UI", "ARCH", "TEST", "BR")
MAP_HEADER = ("module", "scope", "name", "owns", "depends on", "order", "status")
SHARED_HEADER = ("entity", "owner module", "readers", "identity key", "change rule")
GLOSSARY_HEADER = ("term", "definition", "owning module", "avoid")
ROLES_HEADER = ("role", "description", "scope")
SOD_HEADER = ("duty a", "duty b", "rule", "test id")
CAPACITY_HEADER = ("driver", "value", "basis", "nfr ids")
REGISTER_HEADER = (
    "external system", "direction and cadence", "idempotency key",
    "reconciliation report", "error queue owner", "modules", "test ids",
)
PROCESS_HEADER = ("process", "modules in order", "test ids")

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


def _table(
    text: str, scope: str, problems: list[str], require_filled: bool,
    heading: str, header: tuple[str, ...],
) -> list[tuple[str, ...]] | None:
    """Full-width rows of the canonical table under `heading`; None if the heading is absent."""

    section = (cpp._subsection if heading.startswith("###") else cpp._section)(text, heading)
    if section is None:
        return None
    if cpp._explicit_absence_reason(section) is not None:
        return []
    label = heading.lstrip("# ")
    rows = cpp._find_table(section, header)
    if rows is None:
        cpp._add(problems, scope, f"{label} must use the canonical table")
        return []
    cpp._validate_table_rows(
        rows, len(header), label=label, require_filled=require_filled,
        problems=problems, path=scope,
    )
    return [row for row in rows if len(row) == len(header)]


def _split(cell: str) -> list[str]:
    """Items of a comma-, semicolon- or slash-separated cell; `none` is no item."""

    items = (item.strip() for item in re.split(r"[,;/]", cell))
    return [item for item in items if item and item.casefold() != "none"]


def _mapped(program: Program) -> dict[str, ModuleRef]:
    return {ref.module_id: ref for ref in program.modules if ref.mapped}


def _test_rows(prd: str) -> dict[str, tuple[str, ...]]:
    section = cpp._section(prd, "## Test Obligations") or ""
    width = len(cpp.TEST_OBLIGATIONS_HEADER)
    rows = cpp._find_table(section, cpp.TEST_OBLIGATIONS_HEADER) or []
    return {row[0].upper(): row for row in rows if len(row) == width}


def _required(tests: dict[str, tuple[str, ...]], identifier: str) -> bool:
    return identifier in tests and tests[identifier][3].casefold() == "yes"


def _check_map(program: Program, require_filled: bool, problems: list[str]) -> None:
    add = partial(cpp._add, problems, "program")
    if _table(program.prd, "program", problems, require_filled, "## Module Map", MAP_HEADER) is None:
        add("missing required heading '## Module Map'")
    by_id = _mapped(program)
    mapped = list(by_id.values())
    for label, values in (
        ("module id", [m.module_id for m in program.modules if m.mapped]),
        ("scope", [m.scope for m in mapped]),
        ("Order", [m.order for m in mapped if m.order is not None]),
    ):
        for value in sorted({v for v in values if values.count(v) > 1}):
            add(f"Module Map repeats {label} {value!r}")
    for m in mapped:
        if not KEBAB_RE.match(m.module_id):
            add(f"Module Map module id {m.module_id!r} must be lowercase kebab-case")
        if m.scope in RESERVED_SCOPES:
            add(f"Module Map scope {m.scope!r} of {m.module_id!r} is reserved")
        elif not SCOPE_RE.fullmatch(m.scope):
            add(
                f"Module Map scope {m.scope!r} of {m.module_id!r} must be "
                "2-5 uppercase characters starting with a letter"
            )
        if m.order is None:
            add(f"Module Map Order of {m.module_id!r} must be an integer")
        for dep in m.depends_on:
            if dep not in by_id:
                add(f"Module Map: {m.module_id!r} depends on unknown module {dep!r}")
            elif None not in (m.order, by_id[dep].order) and by_id[dep].order >= m.order:
                add(f"Module Map Order puts {m.module_id!r} before its dependency {dep!r}")
    done: set[str] = set()

    def visit(node: str, trail: tuple[str, ...]) -> None:
        if node in trail:
            add("Module Map Depends on cycle: " + " -> ".join((*trail[trail.index(node):], node)))
        elif node not in done and node in by_id:
            for dep in by_id[node].depends_on:
                visit(dep, (*trail, node))
            done.add(node)

    for module_id in by_id:
        visit(module_id, ())


def _check_data(program: Program, require_filled: bool, problems: list[str]) -> None:
    add = partial(cpp._add, problems, "program")
    rows = partial(_table, program.prd, "program", problems, require_filled)
    by_id = _mapped(program)
    for entity, owner, readers, *_ in rows("## Shared Data", SHARED_HEADER) or []:
        if owner not in by_id:
            add(f"Shared Data {entity!r} owner {owner!r} is not in the Module Map")
        for reader in _split(readers):
            if reader not in by_id:
                add(f"Shared Data {entity!r} reader {reader!r} is not in the Module Map")
            elif reader != owner and owner not in by_id[reader].depends_on:
                add(f"Shared Data {entity!r} reader {reader!r} must depend on owner {owner!r}")
    terms: set[str] = set()
    for term, _definition, owner, _avoid in rows("## Glossary", GLOSSARY_HEADER) or []:
        if term.casefold() in terms:
            add(f"Glossary repeats term {term!r}")
        terms.add(term.casefold())
        if owner not in by_id:
            add(f"Glossary term {term!r} owning module {owner!r} is not in the Module Map")
    roles: set[str] = set()
    for role, *_ in rows("### Roles", ROLES_HEADER) or []:
        if role.casefold() in roles:
            add(f"Roles repeats role {role!r}")
        roles.add(role.casefold())
    known_tests = {i for fams in program.registry.values() for i in fams.get("TEST", ())}
    for duty_a, duty_b, _rule, test in rows("### Segregation of Duties", SOD_HEADER) or []:
        named = cpp._ids(test, "TEST")
        if not named:
            add(f"Segregation of Duties pair {duty_a} / {duty_b} names no TEST ID")
        for identifier in sorted(named - known_tests):
            add(f"Segregation of Duties pair {duty_a} / {duty_b} names unknown {identifier}")
    section = cpp._section(program.prd, "## Non-Functional Requirements") or ""
    nfr_rows = [
        row for row in cpp._find_table(section, cpp.NFR_HEADER) or []
        if len(row) == len(cpp.NFR_HEADER)
    ]
    nfr_ids = {row[0].upper() for row in nfr_rows}
    covered: set[str] = set()
    for driver, _value, _basis, nfrs in rows("## Capacity Assumptions", CAPACITY_HEADER) or []:
        named = cpp._ids(nfrs, "PRD")
        if not named:
            add(f"Capacity driver {driver!r} names no NFR ID")
        for identifier in sorted(named - nfr_ids):
            add(f"Capacity driver {driver!r} names unknown NFR {identifier}")
        covered |= named
    for row in nfr_rows:
        if re.search(r"performance|scalab", row[1], re.I) and row[0].upper() not in covered:
            add(f"{row[0]} ({row[1]}) is not named by any Capacity Assumptions row")


def _check_flows(program: Program, require_filled: bool, problems: list[str]) -> None:
    add = partial(cpp._add, problems, "program")
    rows = partial(_table, program.prd, "program", problems, require_filled)
    by_id = _mapped(program)
    tests = _test_rows(program.prd)
    systems = {
        row[0].casefold()
        for row in cpp._find_table(
            cpp._section(program.architecture, "## Integrations") or "",
            cpp.ARCHITECTURE_TABLE_HEADERS["## Integrations"],
        ) or []
    }
    for row in rows("## Integrations Register", REGISTER_HEADER) or []:
        system, names = row[0], _split(row[5])
        if system.casefold() not in systems:
            add(f"Integrations Register system {system!r} is not in the architecture Integrations table")
        if not names:
            add(f"Integrations Register system {system!r} names no module")
        for name in names:
            if name not in by_id:
                add(f"Integrations Register system {system!r} module {name!r} is not in the Module Map")
    for process, names, test_ids in rows("## Business Processes", PROCESS_HEADER) or []:
        listed = _split(names)
        for name in listed:
            if name not in by_id:
                add(f"Business Process {process!r} module {name!r} is not in the Module Map")
        orders = [by_id[n].order for n in listed if n in by_id and by_id[n].order is not None]
        if orders != sorted(set(orders)):
            add(f"Business Process {process!r} must list its modules in Module Map order")
        if not any(t.startswith("TEST-E2E-") and _required(tests, t) for t in cpp._ids(test_ids, "TEST")):
            add(f"Business Process {process!r} needs a Required Yes TEST-E2E-* test in the program Test Obligations")
    if "gl" in by_id and not any(
        identifier.startswith("TEST-E2E-") and _required(tests, identifier)
        and re.search(r"period[ -]close", row[1], re.I)
        for identifier, row in tests.items()
    ):
        add("a gl module requires a Required Yes TEST-E2E-* period-close test")
    section = cpp._section(program.architecture, "## Migration and Cutover")
    if section is None:
        add("architecture is missing required heading '## Migration and Cutover'")
        return
    reason = cpp._explicit_absence_reason(section)
    if reason is not None:
        if not cpp._meaningful(reason, minimum=12):
            add("Migration and Cutover not_required needs a concrete reason")
        return
    for number in range(1, 5):
        identifier = f"TEST-MIG-00{number}"
        if not _required(tests, identifier):
            add(f"Migration and Cutover requires {identifier} as a Required Yes obligation")


def _check_program_ids(program: Program, problems: list[str]) -> None:
    for identifier in sorted(_defined_ids(program.prd) | _defined_ids(program.architecture)):
        if _scope_of(identifier) not in PROGRAM_SCOPES:
            cpp._add(problems, "program", f"{identifier} must use a program scope (PRG, E2E or MIG)")


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
    _check_map(program, require_filled, problems)
    _check_data(program, require_filled, problems)
    _check_flows(program, require_filled, problems)
    _check_program_ids(program, problems)
    return problems
