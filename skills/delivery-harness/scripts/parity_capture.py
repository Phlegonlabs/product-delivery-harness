#!/usr/bin/env python3
"""Capture design-reference vs implementation parity pairs for the UI gates.

Enumerates the route x breakpoint x state matrix from a validated PLAN's
``ui_surfaces`` (skipping ``<state>:n/a``), then drives the agent-browser
CLI to capture, for every combination, the approved design-reference HTML
render (``...-target.png``) and the implemented app page (``...-actual.png``)
at the same viewport, under ``docs/goal/evidence/``. It also runs a DOM
geometry probe on each app page (horizontal overflow plus visible-element
overlap findings) so ``layout_check`` attestations have a tool trace, and
writes a self-contained ``parity-board.html`` for the item-by-item
comparison judgment. Capture only — verdicts stay with the reviewer in
RUN's ``target_comparison`` records; this tool never edits RUN state.
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_core import ManifestError, load_plan  # noqa: E402
from harness_ui_evidence import _state_marker  # noqa: E402
from harness_git import windows_machine_roots, windows_parent_user_writable  # noqa: E402

DEFAULT_OUT = Path("docs/goal/evidence/parity")
VIEWPORT_HEIGHT = 1000
GEOMETRY_PROBE_LIMIT = 400
OVERLAP_REPORT_LIMIT = 10


def _capture_mode_errors(plan: dict[str, Any]) -> list[str]:
    """Reject only malformed capture modes; mixed plans remain reportable.

    ``parity_capture`` captures the hosted subset. Extension, native, and
    desktop groups are returned as manual/platform work in the manifest.
    """

    errors: list[str] = []
    for index, surface in enumerate(plan.get("ui_surfaces") or []):
        if not isinstance(surface, dict) or "capture_mode" not in surface:
            continue  # pre-0.38 plans retain the hosted-browser behavior
        mode = surface.get("capture_mode")
        if not isinstance(mode, str) or mode not in {
            "hosted-browser",
            "browser-extension",
            "native",
            "desktop",
        }:
            errors.append(
                f"PLAN ui_surfaces[{index}].capture_mode is invalid: {mode!r}"
            )
            continue
    return errors


def _unsupported_surface_groups(plan: dict[str, Any]) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for surface in plan.get("ui_surfaces") or []:
        if not isinstance(surface, dict):
            continue
        mode = surface.get("capture_mode", "hosted-browser")
        if mode == "hosted-browser":
            continue
        groups.append(
            {
                "surface_id": surface.get("id"),
                "route": surface.get("route"),
                "capture_mode": mode,
                "status": "manual_or_platform_tooling_required",
                "reason": "parity_capture only captures hosted-browser surfaces",
            }
        )
    return groups

GEOMETRY_PROBE_JS = """
(() => {
  const describe = (el) => {
    const tag = el.tagName.toLowerCase();
    const id = el.id ? "#" + el.id : "";
    const cls = el.classList && el.classList.length
      ? "." + Array.from(el.classList).slice(0, 3).join(".") : "";
    return tag + id + cls;
  };
  const doc = document.scrollingElement || document.documentElement;
  const overflowX = doc.scrollWidth - doc.clientWidth;
  const els = Array.from(document.querySelectorAll("body *"))
    .filter((el) => {
      const rect = el.getBoundingClientRect();
      const style = getComputedStyle(el);
      return rect.width > 0 && rect.height > 0
        && style.visibility !== "hidden" && style.display !== "none";
    })
    .slice(0, %LIMIT%);
  const overlaps = [];
  for (let i = 0; i < els.length && overlaps.length < %REPORT%; i++) {
    for (let j = i + 1; j < els.length && overlaps.length < %REPORT%; j++) {
      if (els[i].contains(els[j]) || els[j].contains(els[i])) continue;
      const a = els[i].getBoundingClientRect();
      const b = els[j].getBoundingClientRect();
      const ox = Math.min(a.right, b.right) - Math.max(a.left, b.left);
      const oy = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (ox > 1 && oy > 1) {
        overlaps.push({a: describe(els[i]), b: describe(els[j]),
                        px: Math.round(ox), py: Math.round(oy)});
      }
    }
  }
  return {overflowX: overflowX, scanned: els.length, overlaps: overlaps};
})()
""".replace("%LIMIT%", str(GEOMETRY_PROBE_LIMIT)).replace(
    "%REPORT%", str(OVERLAP_REPORT_LIMIT)
)


def _direct_node_launcher(wrapper: Path) -> list[str] | None:
    """Resolve a Windows npm/Volta shim to Node without invoking a shell."""

    wrapper = _trusted_launcher_path(wrapper, "agent-browser launcher")
    node = shutil.which("node.exe") or shutil.which("node")
    package_root = wrapper.parent
    javascript = package_root / "node_modules" / "agent-browser" / "bin" / "agent-browser.js"

    volta = wrapper.parent / "volta.exe"
    if not volta.is_file():
        resolved_volta = shutil.which("volta.exe") or shutil.which("volta")
        volta = Path(resolved_volta) if resolved_volta else volta
    if volta.is_file():
        try:
            volta = _trusted_launcher_path(volta, "Volta launcher")
        except RuntimeError:
            volta = Path()
        try:
            package_probe = subprocess.run(
                [str(volta.resolve()), "which", "agent-browser"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=False,
            )
            node_probe = subprocess.run(
                [str(volta.resolve()), "which", "node"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            package_probe = node_probe = None
        if (
            package_probe is not None
            and node_probe is not None
            and package_probe.returncode == 0
            and node_probe.returncode == 0
        ):
            package_launcher = Path(package_probe.stdout.strip())
            volta_node = Path(node_probe.stdout.strip())
            candidate = (
                package_launcher.parent
                / "node_modules"
                / "agent-browser"
                / "bin"
                / "agent-browser.js"
            )
            try:
                trusted_node = _trusted_launcher_path(volta_node, "Node runtime")
                trusted_candidate = _trusted_launcher_path(candidate, "agent-browser script")
            except RuntimeError:
                trusted_node = trusted_candidate = None
            if trusted_node is not None and trusted_candidate is not None:
                return [str(trusted_node), str(trusted_candidate)]

    if node:
        try:
            node_path = _trusted_launcher_path(Path(node), "Node runtime")
            script_path = _trusted_launcher_path(javascript, "agent-browser script")
        except RuntimeError:
            return None
        if node_path.is_file() and script_path.is_file():
            return [str(node_path), str(script_path)]
    return None


def _trusted_launcher_path(path: Path, label: str) -> Path:
    """Bind a browser launcher to a non-reparse, machine-managed install."""

    try:
        resolved = path.resolve(strict=True)
        resolved.stat()
    except OSError as exc:
        raise RuntimeError(f"{label} is unavailable: {path}") from exc
    # POSIX systems routinely expose the interpreter through a root-owned
    # symlink (/usr/bin/python3 -> python3.13); the resolved target stays
    # machine-managed, so only Windows rejects the link itself.
    if not resolved.is_file() or (os.name == "nt" and path.is_symlink()):
        raise RuntimeError(f"{label} must be a regular non-symlink file: {resolved}")
    for current in (resolved, *resolved.parents):
        try:
            if current.is_symlink() or getattr(current.stat(), "st_file_attributes", 0) & 0x0400:
                raise RuntimeError(f"{label} path contains a reparse point: {current}")
        except OSError as exc:
            raise RuntimeError(f"cannot inspect {label}: {exc}") from exc
    try:
        resolved.relative_to(Path.cwd().resolve())
    except ValueError:
        pass
    else:
        raise RuntimeError(f"{label} must not come from the current repository/worktree")
    if os.name == "nt":
        roots = list(windows_machine_roots())
        if not any(_path_within(resolved, root) for root in roots):
            raise RuntimeError(f"{label} must come from Program Files or Windows system directories")
        if windows_parent_user_writable(resolved):
            raise RuntimeError(f"{label} file is user-writable: {resolved}")
        if windows_parent_user_writable(resolved.parent):
            raise RuntimeError(f"{label} parent is user-writable: {resolved.parent}")
        if resolved.suffix.casefold() not in {".exe", ".com", ".js", ".py", ".cmd", ".bat"}:
            raise RuntimeError(f"{label} has an unsupported executable type")
    else:
        for component in (resolved, *resolved.parents):
            component_info = component.stat()
            if component_info.st_uid != 0 or component_info.st_mode & 0o022:
                raise RuntimeError(f"{label} path must be root-owned and not writable by group/other")
        if not any(_path_within(resolved, root) for root in (Path("/usr"), Path("/bin"), Path("/opt"))):
            raise RuntimeError(f"{label} must come from an OS-protected install path")
    return resolved


def _bind_posix_launcher(path: Path, *, executable: bool = True) -> tuple[str, int]:
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        try:
            fd = os.open(path, flags)
        except OSError as exc:
            # A symlinked launcher (for example a distro /usr/bin/python3)
            # raises ELOOP under O_NOFOLLOW; pin the resolved target instead
            # so the bound descriptor still names the machine-managed inode.
            if exc.errno != errno.ELOOP:
                raise
            fd = os.open(path.resolve(strict=True), flags)
        info = os.fstat(fd)
        if not os.path.isfile(path) or (executable and not (info.st_mode & 0o111)):
            os.close(fd)
            raise RuntimeError(f"launcher is not executable: {path}")
        for candidate in (f"/proc/self/fd/{fd}", f"/dev/fd/{fd}"):
            if Path(candidate).exists():
                return candidate, fd
        os.close(fd)
    except OSError as exc:
        raise RuntimeError(f"cannot bind launcher identity: {path}") from exc
    raise RuntimeError(f"descriptor-backed launcher path is unavailable: {path}")


def _path_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _resolve_cli() -> list[str] | None:
    resolved = shutil.which("agent-browser")
    if not resolved:
        return None
    try:
        path = _trusted_launcher_path(Path(resolved), "agent-browser launcher")
    except RuntimeError:
        return None
    if os.name == "nt":
        if path.suffix.casefold() in {".cmd", ".bat"}:
            # Shell wrappers are never executed.  Resolve to direct Node argv
            # only when both Node and the package script are machine-bound.
            try:
                return _direct_node_launcher(path)
            except RuntimeError:
                return None
        if path.suffix.casefold() == ".py":
            try:
                python_path = _trusted_launcher_path(Path(sys.executable), "Python runtime")
            except RuntimeError:
                return None
            return [str(python_path), str(path)]
        if path.suffix.casefold() not in {".exe", ".com"}:
            return _direct_node_launcher(path)
    return [str(path)]


def _run_browser(
    cli: list[str],
    argv: list[str],
    *,
    stdin: str | None = None,
    timeout: int = 90,
) -> subprocess.CompletedProcess[str]:
    if (
        not isinstance(cli, list)
        or not cli
        or any(not isinstance(item, str) or not item for item in cli)
        or any(item.casefold().endswith((".cmd", ".bat")) for item in cli)
    ):
        raise RuntimeError("agent-browser must use a direct native or Node argv")
    bound: list[str] = []
    descriptors: list[int] = []
    try:
        if os.name != "nt":
            for index, item in enumerate(cli):
                if index == 0 or item.endswith((".js", ".py")):
                    launch, descriptor = _bind_posix_launcher(
                        Path(item), executable=(index == 0)
                    )
                    bound.append(launch)
                    descriptors.append(descriptor)
                else:
                    bound.append(item)
        else:
            bound = list(cli)
        command = [*bound, *argv]
        options: dict[str, Any] = {
            "input": stdin,
            "capture_output": True,
            "text": True,
            "encoding": "utf-8",
            "errors": "replace",
            "timeout": timeout,
        }
        if descriptors:
            options["pass_fds"] = tuple(descriptors)
        return subprocess.run(command, **options)
    finally:
        for descriptor in descriptors:
            try:
                os.close(descriptor)
            except OSError:
                pass


def _token(value: str) -> str:
    token = re.sub(r"[^a-zA-Z0-9._-]+", "-", value.strip("/")).strip("-")
    return token or "root"


def _matrix(
    plan: dict[str, Any], only: str | None, *, hosted_only: bool = False
) -> list[dict[str, Any]]:
    combos = []
    for surface in plan.get("ui_surfaces") or []:
        if not isinstance(surface, dict):
            continue
        if hosted_only and surface.get("capture_mode", "hosted-browser") != "hosted-browser":
            continue
        route = surface.get("route")
        if only and route != only:
            continue
        for breakpoint in surface.get("breakpoints") or []:
            for state in surface.get("states") or []:
                if not isinstance(state, str) or not state.strip():
                    continue
                if _state_marker(state)[1]:
                    continue
                combos.append(
                    {
                        "surface_id": surface.get("id"),
                        "route": route,
                        "breakpoint": str(breakpoint),
                        "state": _state_marker(state)[0],
                    }
                )
    return combos


def _route_map_load(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ManifestError(f"route map {path} must be a JSON object")
    return data


def _navigate_reference(
    cli: list[str], reference_url: str, route: str, entry: dict[str, Any]
) -> tuple[bool, str]:
    """Open the reference file and select the route; return (ok, method)."""

    opened = _run_browser(cli, ["open", reference_url])
    if opened.returncode != 0:
        return False, f"open failed: {opened.stderr.strip()}"
    selector_entry = entry.get("reference") or {}
    selector = selector_entry.get("selector") if isinstance(
        selector_entry, dict
    ) else None
    if selector:
        clicked = _run_browser(
            cli,
            ["eval", f"document.querySelector({json.dumps(selector)})?.click()"],
        )
        if clicked.returncode != 0:
            return False, f"selector click failed: {clicked.stderr.strip()}"
        return True, f"route-map selector {selector}"
    # Best-effort probe for a plain link matching the route.
    probe = (
        f"(() => {{ const link = document.querySelector('a[href={json.dumps(route)}]')"
        f" || document.querySelector('a[href={json.dumps('#' + route)}]');"
        " if (link) { link.click(); return true; } return false; }})()"
    )
    probed = _run_browser(cli, ["eval", probe])
    if probed.returncode == 0 and probed.stdout.strip().endswith("true"):
        return True, f"probe a[href] for {route}"
    return False, f"no reference navigation found for {route}"


def _shoot(
    cli: list[str],
    *,
    viewport: tuple[str, int],
    screenshot: Path,
    full_page: bool,
    state_eval: str | None,
) -> list[str]:
    """Set viewport, apply an optional state trigger, and capture the shot."""

    errors: list[str] = []
    sized = _run_browser(
        cli, ["set", "viewport", viewport[0], str(viewport[1])]
    )
    if sized.returncode != 0:
        errors.append(f"set viewport failed: {sized.stderr.strip()}")
    if state_eval:
        triggered = _run_browser(cli, ["eval", "--stdin"], stdin=state_eval)
        if triggered.returncode != 0:
            errors.append(f"state eval failed: {triggered.stderr.strip()}")
    argv = ["screenshot", str(screenshot)]
    if full_page:
        argv.insert(1, "--full")
    shot = _run_browser(cli, argv)
    if shot.returncode != 0:
        errors.append(f"screenshot failed: {shot.stderr.strip()}")
    elif not screenshot.exists():
        errors.append("screenshot reported success but wrote no file")
    return errors


def _capture_app(
    cli: list[str],
    url: str,
    *,
    viewport: tuple[str, int],
    screenshot: Path,
    full_page: bool,
    state_eval: str | None,
) -> list[str]:
    opened = _run_browser(cli, ["open", url])
    if opened.returncode != 0:
        return [f"open {url} failed: {opened.stderr.strip()}"]
    waited = _run_browser(cli, ["wait", "--load", "networkidle"], timeout=120)
    wait_errors: list[str] = []
    if waited.returncode != 0:
        wait_errors.append(f"networkidle wait failed: {waited.stderr.strip()}")
    return wait_errors + _shoot(
        cli,
        viewport=viewport,
        screenshot=screenshot,
        full_page=full_page,
        state_eval=state_eval,
    )


def _geometry_probe(cli: list[str]) -> tuple[dict[str, Any] | None, str | None]:
    probed = _run_browser(
        cli, ["eval", "--stdin"], stdin=GEOMETRY_PROBE_JS, timeout=60
    )
    if probed.returncode != 0:
        reason = probed.stderr.strip() or f"browser eval exited {probed.returncode}"
        return None, reason
    text = probed.stdout.strip()
    # The CLI prints the eval result; accept the last JSON-looking line.
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                result = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(result, dict):
                return None, "geometry probe returned a non-object JSON value"
            overflow = result.get("overflowX")
            overlaps = result.get("overlaps")
            if not isinstance(overflow, (int, float)) or isinstance(overflow, bool):
                return None, "geometry probe returned an invalid overflowX value"
            if not isinstance(overlaps, list):
                return None, "geometry probe returned an invalid overlaps value"
            return result, None
    return None, "geometry probe returned no valid JSON object"


def _board(
    out_dir: Path,
    captured: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
) -> Path:
    rows = []
    for item in captured:
        label = (
            f"{item['surface_id']} · {item['route']} · "
            f"{item['breakpoint']}px · {item['state']}"
        )
        geometry = item.get("geometry") or {}
        geometry_error = item.get("geometry_error")
        findings = []
        if geometry.get("overflowX", 0) > 1:
            findings.append(f"horizontal overflow: {geometry['overflowX']}px")
        for overlap in geometry.get("overlaps") or []:
            findings.append(
                f"overlap {overlap.get('a')} × {overlap.get('b')} "
                f"({overlap.get('px')}×{overlap.get('py')}px)"
            )
        if geometry_error:
            findings.append(f"geometry probe unavailable: {geometry_error}")
        findings_html = (
            "<ul>"
            + "".join(f"<li>{html.escape(str(f))}</li>" for f in findings)
            + "</ul>"
        ) if findings else "<p>geometry probe: clean</p>"
        rows.append(
            "<section class='pair'>"
            f"<h3>{html.escape(label)}</h3>"
            f"<div class='imgs'><figure><img src='{item['target']}'>"
            "<figcaption>target (design reference)</figcaption></figure>"
            f"<figure><img src='{item['actual']}'>"
            "<figcaption>actual (implementation)</figcaption></figure></div>"
            f"<div class='findings'>{findings_html}</div>"
            "<div class='verdict'>verdict: pass / deviation — "
            "differences: ______________________</div>"
            "</section>"
        )
    for item in skipped:
        rows.append(
            "<section class='pair skipped'>"
            f"<h3>SKIPPED · {html.escape(str(item.get('route')))} · "
            f"{html.escape(str(item.get('breakpoint')))} · "
            f"{html.escape(str(item.get('state')))}</h3>"
            f"<p>{html.escape(str(item.get('reason')))}</p></section>"
        )
    board = out_dir / "parity-board.html"
    board.write_text(
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Parity board</title><style>"
        "body{font-family:sans-serif;margin:16px;background:#f5f5f5}"
        ".pair{background:#fff;border:1px solid #ccc;border-radius:8px;"
        "padding:12px;margin-bottom:16px}"
        ".pair.skipped{background:#fff8e1}"
        ".imgs{display:flex;gap:12px}.imgs figure{flex:1;margin:0}"
        ".imgs img{width:100%;border:1px solid #999}"
        "figcaption{font-size:12px;color:#555;margin-top:4px}"
        ".verdict{margin-top:8px;font-family:monospace}"
        "</style></head><body>"
        "<h1>Parity board — design reference vs implementation</h1>"
        "<p>Compare each pair item by item within ui-design.md's recorded "
        "tolerance; record the verdict in RUN's target_comparison.</p>"
        + "".join(rows)
        + "</body></html>",
        encoding="utf-8",
        newline="\n",
    )
    return board


def capture(args: argparse.Namespace) -> int:
    plan_path: Path = args.plan
    if not plan_path.is_file():
        print(f"error: PLAN not found: {plan_path}", file=sys.stderr)
        return 1
    reference: Path = args.reference
    if not reference.is_file():
        print(f"error: reference HTML not found: {reference}", file=sys.stderr)
        return 1
    try:
        plan = load_plan(plan_path)
        route_map = _route_map_load(args.route_map)
    except (ManifestError, json.JSONDecodeError, OSError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    mode_errors = _capture_mode_errors(plan)
    if mode_errors:
        for problem in mode_errors:
            print(f"error: {problem}", file=sys.stderr)
        return 1

    unsupported_groups = _unsupported_surface_groups(plan)
    all_combos = _matrix(plan, None)
    combos = _matrix(plan, args.only, hosted_only=True)
    if not combos:
        if unsupported_groups:
            print(
                "no hosted-browser parity combinations; manual/platform groups "
                "were reported and do not block this capture command"
            )
            for group in unsupported_groups:
                print(
                    f"manual/platform group {group['surface_id']}: "
                    f"{group['capture_mode']} ({group['reason']})"
                )
            return 0
        print("error: no route x breakpoint x state combinations found", file=sys.stderr)
        return 1

    cli = _resolve_cli()
    if cli is None:
        print(
            "error: agent-browser CLI not found on PATH; "
            "install with `npm i -g agent-browser && agent-browser install`",
            file=sys.stderr,
        )
        return 1
    version = _run_browser(cli, ["--version"], timeout=30)
    if version.returncode != 0:
        print(
            f"error: agent-browser not runnable: {version.stderr.strip()}",
            file=sys.stderr,
        )
        return 1

    if not args.base_url:
        print(
            "error: --base-url is required for hosted-browser parity capture; "
            "native, desktop, and browser-extension modes never use URL parity",
            file=sys.stderr,
        )
        return 1

    out_dir: Path = args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    session = args.session or f"parity-{uuid.uuid4().hex[:8]}"
    os.environ["AGENT_BROWSER_SESSION"] = session

    reference_url = reference.resolve().as_uri()
    base_url: str = str(args.base_url).rstrip("/")

    captured: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    errors: list[str] = []
    nav_methods: dict[str, str] = {}
    routes = sorted({combo["route"] for combo in combos})

    for route in routes:
        entry = route_map.get(route) or {}
        if not isinstance(entry, dict):
            entry = {}
        for combo in (c for c in combos if c["route"] == route):
            # Bind the filename to the exact tuple, not its lossy display tokens.
            identity = json.dumps(combo, sort_keys=True, ensure_ascii=False).encode("utf-8")
            label = (
                f"{_token(route)}-{_token(combo['state'])}-"
                f"{_token(combo['breakpoint'])}"
            )
            name = f"{label[:64]}-{hashlib.sha256(identity).hexdigest()}"
            target = out_dir / f"{name}-target.png"
            actual = out_dir / f"{name}-actual.png"
            breakpoint = combo["breakpoint"]
            viewport = (breakpoint, args.height or VIEWPORT_HEIGHT)
            state_entry = (entry.get("states") or {}).get(combo["state"]) or {}
            if not isinstance(state_entry, dict):
                state_entry = {}
            reference_eval = state_entry.get("reference_eval")
            app_eval = state_entry.get("app_eval")
            if not app_eval and combo["state"] != "ready":
                skipped.append(
                    {
                        **combo,
                        "reason": (
                            f"no app_eval trigger for state {combo['state']!r} "
                            "in the route map"
                        ),
                    }
                )
                continue

            # The reference must be re-opened and re-navigated per combo:
            # the app-side capture leaves the tab on the app page.
            ok, method = _navigate_reference(cli, reference_url, route, entry)
            nav_methods[route] = method
            if not ok:
                skipped.append({**combo, "reason": f"reference nav: {method}"})
                continue
            target_errors = _shoot(
                cli,
                viewport=viewport,
                screenshot=target,
                full_page=args.full_page,
                state_eval=reference_eval,
            )
            if target_errors:
                errors.extend(
                    f"{name} target: {problem}" for problem in target_errors
                )
                continue
            app_path = entry.get("app_path") or combo["route"]
            app_errors = _capture_app(
                cli,
                f"{base_url}{app_path}",
                viewport=viewport,
                screenshot=actual,
                full_page=args.full_page,
                state_eval=app_eval,
            )
            if app_errors:
                errors.extend(
                    f"{name} actual: {problem}" for problem in app_errors
                )
                continue
            geometry, geometry_error = _geometry_probe(cli)
            if geometry_error:
                errors.append(f"{name} actual: geometry probe failed: {geometry_error}")
            captured.append(
                {
                    **combo,
                    "target": target.as_posix(),
                    "actual": actual.as_posix(),
                    "geometry": geometry,
                    "geometry_error": geometry_error,
                }
            )
            print(f"captured {name}")

    _run_browser(cli, ["close"], timeout=30)
    if skipped:
        errors.extend(
            f"{item['route']} x {item['breakpoint']} x {item['state']}: "
            f"{item['reason']}" for item in skipped
        )
    if not captured:
        errors.append("no parity pairs were captured")
    # Any unsupported platform surface makes a mixed board diagnostic only;
    # a hosted subset can never turn the whole plan into a PASS.
    partial = bool(args.only or unsupported_groups)
    manifest = {
        "status": "FAIL" if errors else ("PARTIAL" if partial else "PASS"),
        "gating_eligible": not partial and not errors,
        "session": session,
        "reference": args.reference.as_posix(),
        "capture_mode": "hosted-browser",
        "base_url": base_url,
        "viewport_height": args.height or VIEWPORT_HEIGHT,
        "full_page": args.full_page,
        "reference_nav": nav_methods,
        "required_combinations": len(all_combos),
        "selected_combinations": len(combos),
        "only_routes": [args.only] if args.only else [],
        "captured": captured,
        "skipped": skipped,
        "unsupported_groups": unsupported_groups,
        "errors": errors,
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    board = _board(out_dir, captured, skipped)
    print(
        f"done: {len(captured)} of {len(combos)} selected pairs captured "
        f"({len(all_combos)} full-plan required), "
        f"{len(skipped)} skipped, "
        f"{len(errors)} errors; board: {board}"
    )
    for problem in errors:
        print(f"error: {problem}", file=sys.stderr)
    if errors:
        return 1
    if partial:
        print(
            "partial/platform diagnostic capture is not eligible for a parity gate",
            file=sys.stderr,
        )
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, required=True, help="PLAN.md path")
    parser.add_argument(
        "--reference", type=Path, required=True,
        help="approved design-reference HTML path",
    )
    parser.add_argument(
        "--base-url", help="implemented app origin for hosted-browser parity, e.g. http://localhost:3000"
    )
    parser.add_argument(
        "--route-map", type=Path, help="JSON mapping routes to reference selectors and state triggers"
    )
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUT,
        help=f"evidence output directory (default: {DEFAULT_OUT})",
    )
    parser.add_argument("--only", help="restrict capture to one route (repair recaptures)")
    parser.add_argument("--height", type=int, help=f"viewport height (default: {VIEWPORT_HEIGHT})")
    parser.add_argument(
        "--full-page", action="store_true",
        help="capture full scroll height instead of the viewport",
    )
    parser.add_argument("--session", help="agent-browser session name (default: generated)")
    args = parser.parse_args(argv)
    try:
        return capture(args)
    except subprocess.TimeoutExpired as exc:
        print(f"error: agent-browser timed out: {exc}", file=sys.stderr)
        return 1
    except (ManifestError, OSError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
