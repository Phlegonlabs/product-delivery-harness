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

Each pair is also diffed (Pillow, when importable) and classified
``identical`` or ``changed``; the board lists changed pairs first and folds
the identical ones. The classification is reviewer input, not a verdict.
``--carry-from`` records a pair as ``carried`` (and skips its reference
capture) when nothing that shapes it changed since an identical one.
"""

from __future__ import annotations

import argparse
from collections import Counter
from contextlib import contextmanager
from dataclasses import dataclass, field
import errno
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Iterator

SCRIPTS_DIR = Path(__file__).resolve().parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_core import ManifestError, load_plan  # noqa: E402
from harness_design_coverage import surface_capture_rows  # noqa: E402
from harness_git import windows_machine_roots, windows_parent_user_writable  # noqa: E402

DEFAULT_OUT = Path("docs/goal/evidence/parity")
_clock = time.perf_counter  # tests replace this to get fixed durations
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
        # macOS lists /dev/fd/N but refuses to execute it; only reads work there.
        candidates = [f"/proc/self/fd/{fd}"]
        if not (executable and sys.platform == "darwin"):
            candidates.append(f"/dev/fd/{fd}")
        for candidate in candidates:
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
        rows, _projection_errors = surface_capture_rows(surface)
        for row in rows:
            if "design_coverage" not in surface:
                combos.append({key: row[key] for key in ("surface_id", "route", "breakpoint", "state")})
            else:
                reduced = row["kind"] == "design-condition" and row["state"] == "reduced-motion"
                combos.append({**row, "media_preference": "reduced" if reduced else "normal"})
    return combos


def _capture_projection_errors(plan: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for surface in plan.get("ui_surfaces") or []:
        if not isinstance(surface, dict):
            continue
        _rows, projection_errors = surface_capture_rows(surface)
        errors.extend(projection_errors)
    return errors


def _condition_entry(entry: dict[str, Any], combo: dict[str, Any]) -> dict[str, Any]:
    if combo.get("kind") != "design-condition":
        return {}
    conditions = entry.get("conditions")
    value = conditions.get(combo["state"]) if isinstance(conditions, dict) else None
    return value if isinstance(value, dict) else {}


def _read_media_preferences(cli: list[str]) -> tuple[tuple[str, bool] | None, str | None]:
    checked = _run_browser(cli, ["eval", "({scheme: matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light', reduced: matchMedia('(prefers-reduced-motion: reduce)').matches})"], timeout=30)
    try:
        value = json.loads(checked.stdout)
        if checked.returncode or not isinstance(value, dict):
            raise ValueError("browser preference query failed")
        if value.get("scheme") not in {"light", "dark"} or type(value.get("reduced")) is not bool:
            raise ValueError("browser preference response is malformed")
        return (value["scheme"], value["reduced"]), None
    except (ValueError, TypeError):
        return None, "browser preference query did not return a scheme and motion boolean"


def _set_motion_preference(cli: list[str], scheme: str, reduced: bool) -> list[str]:
    command = ["set", "media", scheme] + (["reduced-motion"] if reduced else [])
    applied = _run_browser(cli, command, timeout=30)
    if applied.returncode:
        return [f"browser media command failed: {applied.stderr.strip()}"]
    observed, problem = _read_media_preferences(cli)
    if problem or observed != (scheme, reduced):
        return [problem or "browser did not apply the requested motion preference"]
    return []


@contextmanager
def _motion_scope(
    cli: list[str], combo: dict[str, Any], original: tuple[str, bool] | None,
    errors: list[str], label: str,
) -> Iterator[bool]:
    if "kind" not in combo:
        yield True
        return
    if original is None:
        errors.append(f"{label}: original browser preferences were not observed")
        yield False
        return
    try:
        problems = _set_motion_preference(cli, original[0], combo.get("media_preference") == "reduced")
        errors.extend(f"{label}: {problem}" for problem in problems)
        yield not problems
    finally:
        errors.extend(f"{label} restore: {problem}" for problem in _set_motion_preference(cli, *original))


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


def _prepare(
    cli: list[str],
    *,
    viewport: tuple[str, int],
    state_eval: str | None,
    condition_eval: str | None = None,
) -> list[str]:
    """Set the viewport and apply the optional state and condition triggers."""

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
    if condition_eval:
        triggered = _run_browser(cli, ["eval", "--stdin"], stdin=condition_eval)
        if triggered.returncode != 0:
            errors.append(f"condition eval failed: {triggered.stderr.strip()}")
    return errors


def _screenshot(cli: list[str], screenshot: Path, full_page: bool) -> list[str]:
    argv = ["screenshot", str(screenshot)]
    if full_page:
        argv.insert(1, "--full")
    shot = _run_browser(cli, argv)
    if shot.returncode != 0:
        return [f"screenshot failed: {shot.stderr.strip()}"]
    if not screenshot.exists():
        return ["screenshot reported success but wrote no file"]
    return []


def _shoot(
    cli: list[str],
    *,
    viewport: tuple[str, int],
    screenshot: Path,
    full_page: bool,
    state_eval: str | None,
    condition_eval: str | None = None,
) -> list[str]:
    """Set viewport, apply an optional state trigger, and capture the shot."""

    return _prepare(
        cli, viewport=viewport, state_eval=state_eval, condition_eval=condition_eval
    ) + _screenshot(cli, screenshot, full_page)


def _open_app(cli: list[str], url: str) -> tuple[bool, list[str]]:
    """Load the app page; return (opened, problems). A slow idle wait is not fatal."""

    opened = _run_browser(cli, ["open", url])
    if opened.returncode != 0:
        return False, [f"open {url} failed: {opened.stderr.strip()}"]
    waited = _run_browser(cli, ["wait", "--load", "networkidle"], timeout=120)
    if waited.returncode != 0:
        return True, [f"networkidle wait failed: {waited.stderr.strip()}"]
    return True, []


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


def _load_pillow() -> tuple[Any, Any] | None:
    """Pillow is optional: without it pairs are reviewed by eye, never failed."""

    try:
        from PIL import Image, ImageChops
    except ImportError:
        return None
    return Image, ImageChops


def _fingerprint(geometry: dict[str, Any] | None) -> str | None:
    """Lowercase SHA-256 over the canonical geometry probe JSON of the app page."""

    if geometry is None:
        return None
    canonical = json.dumps(geometry, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _pixel_diff(target: Path, actual: Path) -> tuple[dict[str, Any] | None, str | None]:
    """Compare the pair; return (diff, None) or (None, why it could not run).

    Sizes are normalised onto the larger canvas. Area that only one image
    covers counts as differing, so a height mismatch shows up in the ratio.
    """

    pillow = _load_pillow()
    if pillow is None:
        return None, "Pillow is not installed"
    image_module, chops = pillow
    try:
        with image_module.open(target) as target_file, image_module.open(actual) as actual_file:
            left, right = target_file.convert("RGBA"), actual_file.convert("RGBA")
    except (OSError, ValueError, image_module.DecompressionBombError) as exc:
        return None, f"cannot decode the pair: {exc}"
    width, height = max(left.width, right.width), max(left.height, right.height)
    canvases = []
    for image in (left, right):
        canvas = image_module.new("RGBA", (width, height), (0, 0, 0, 0))
        canvas.paste(image, (0, 0))
        canvases.append(canvas)
    red, green, blue, alpha = chops.difference(*canvases).split()
    changed = chops.lighter(chops.lighter(red, green), chops.lighter(blue, alpha))
    total = width * height
    differing = total - changed.histogram()[0]
    return {
        "ratio": differing / total,
        "differing_pixels": differing,
        "total_pixels": total,
        "sizes_matched": left.size == right.size,
        "target_size": list(left.size),
        "actual_size": list(right.size),
    }, None


def _ratio(text: str) -> float:
    value = float(text)
    if not 0.0 <= value <= 1.0:
        raise argparse.ArgumentTypeError(f"{text} is not a fraction between 0.0 and 1.0")
    return value


def _classify(pixel_diff: dict[str, Any] | None, tolerance: float) -> str:
    """`identical` only for a same-size pair at or under the tolerance; else review it."""

    if (
        pixel_diff is not None
        and pixel_diff["sizes_matched"]
        and pixel_diff["ratio"] <= tolerance
    ):
        return "identical"
    return "changed"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_has_hash(path: Any, digest: Any) -> bool:
    if not isinstance(path, str) or not isinstance(digest, str) or not Path(path).is_file():
        return False
    try:
        return _file_sha256(Path(path)) == digest
    except OSError:
        return False


def _load_carry_source(path: Path) -> dict[str, dict[str, Any]]:
    """Index a previous manifest's captured rows by tuple hash.

    Rows from a manifest written before this field existed have no key and
    can never be carried.
    """

    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("captured") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        raise ManifestError(f"carry-from manifest {path} has no captured list")
    return {
        row["tuple_sha256"]: row
        for row in rows
        if isinstance(row, dict) and isinstance(row.get("tuple_sha256"), str)
    }


def _can_carry(previous: dict[str, Any], job: dict[str, Any], tolerance: float) -> bool:
    """True when nothing that shapes this pair changed since an identical one.

    The geometry fingerprint alone cannot see a colour or text change, so the
    fresh app screenshot must also hash the same as the previous one, and the
    reference side (HTML file, route-map triggers, viewport) must be unchanged.
    The previous files must still match their recorded hashes.
    """

    try:
        return (
            previous.get("classification") in ("identical", "carried")
            and _classify(previous.get("pixel_diff"), tolerance) == "identical"
            and job["geometry_fingerprint"] is not None
            and previous.get("geometry_fingerprint") == job["geometry_fingerprint"]
            and previous.get("actual_sha256") == job["actual_sha256"]
            and previous.get("target_inputs_sha256") == job["target_inputs_sha256"]
            and _file_has_hash(previous.get("target"), previous.get("target_sha256"))
            and _file_has_hash(previous.get("actual"), previous.get("actual_sha256"))
        )
    except (KeyError, TypeError):
        return False


@dataclass
class _Run:
    """State shared by the capture phases of one invocation."""

    cli: list[str]
    reference_url: str
    reference_sha256: str
    full_page: bool
    tolerance: float = 0.0
    previous: dict[str, dict[str, Any]] = field(default_factory=dict)
    carry_from: str | None = None
    errors: list[str] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)
    nav_methods: dict[str, str] = field(default_factory=dict)


@contextmanager
def _timed(job: dict[str, Any]) -> Iterator[None]:
    """Add the time spent in the block, including any page load, to the tuple."""

    began = _clock()
    try:
        yield
    finally:
        job["seconds"] += _clock() - began


def _app_dirty(job: dict[str, Any]) -> bool:
    return bool(job["app_eval"] or job["condition_app_eval"])


def _reference_dirty(job: dict[str, Any]) -> bool:
    return bool(job["reference_eval"] or job["condition_reference_eval"])


def _plan_job(
    run: _Run,
    combo: dict[str, Any],
    index: int,
    entry: dict[str, Any],
    out_dir: Path,
    height: int,
    base_url: str,
) -> dict[str, Any] | None:
    """Resolve one matrix tuple into a capture job, or record why it is skipped."""

    # Bind the filename to the exact tuple, not its lossy display tokens.
    identity = json.dumps(combo, sort_keys=True, ensure_ascii=False).encode("utf-8")
    label = (
        f"{_token(combo['route'])}-{_token(combo['state'])}-"
        f"{_token(combo['breakpoint'])}"
    )
    tuple_sha256 = hashlib.sha256(identity).hexdigest()
    name = f"{label[:64]}-{tuple_sha256}"
    is_condition = combo.get("kind") == "design-condition"
    base_state = combo["base_state"] if is_condition else combo["state"]
    states_map = entry.get("states") or {}
    base_entry = states_map.get(base_state) or {}
    if not isinstance(base_entry, dict):
        base_entry = {}
    condition_entry = _condition_entry(entry, combo)
    app_eval = base_entry.get("app_eval")
    condition_reference_eval = (
        condition_entry.get("reference_eval") if is_condition else None
    )
    condition_app_eval = condition_entry.get("app_eval") if is_condition else None
    if not app_eval and base_state != "ready":
        run.skipped.append(
            {
                **combo,
                "reason": (
                    f"no app_eval trigger for {'base state' if is_condition else 'state'} {base_state!r} "
                    "in the route map"
                ),
            }
        )
        return None
    if is_condition and combo["state"] == "long-content":
        if not all(isinstance(value, str) and value.strip() for value in (condition_reference_eval, condition_app_eval)):
            run.skipped.append(
                {
                    **combo,
                    "reason": (
                        "long-content requires both reference_eval and "
                        "app_eval in the route-map conditions"
                    ),
                }
            )
            return None
    app_path = entry.get("app_path") or combo["route"]
    reference_eval = base_entry.get("reference_eval")
    # Everything that shapes the target image; a change forces a recapture.
    target_inputs = json.dumps(
        {
            "reference_sha256": run.reference_sha256,
            "route": combo["route"],
            "reference": entry.get("reference"),
            "reference_eval": reference_eval,
            "condition_reference_eval": condition_reference_eval,
            "viewport": [combo["breakpoint"], height],
            "full_page": run.full_page,
            "media_preference": combo.get("media_preference"),
        },
        sort_keys=True, ensure_ascii=False,
    )
    return {
        "combo": combo,
        "index": index,
        "route": combo["route"],
        "entry": entry,
        "name": name,
        "tuple_sha256": tuple_sha256,
        "target_inputs_sha256": hashlib.sha256(target_inputs.encode("utf-8")).hexdigest(),
        "target": out_dir / f"{name}-target.png",
        "actual": out_dir / f"{name}-actual.png",
        "viewport": (combo["breakpoint"], height),
        "url": f"{base_url}{app_path}",
        "reference_eval": reference_eval,
        "app_eval": app_eval,
        "condition_reference_eval": condition_reference_eval,
        "condition_app_eval": condition_app_eval,
        "app_ok": False,
        "done": False,
        "carried": None,
        "seconds": 0.0,
    }


def _app_step(run: _Run, job: dict[str, Any], loaded: bool) -> bool:
    """Capture one app page; return whether the loaded page is still untouched."""

    name = job["name"]
    problems: list[str] = []
    if not loaded:
        opened, problems = _open_app(run.cli, job["url"])
        if not opened:
            run.errors.extend(f"{name} actual: {problem}" for problem in problems)
            return False
    problems += _prepare(
        run.cli,
        viewport=job["viewport"],
        state_eval=job["app_eval"],
        condition_eval=job["condition_app_eval"],
    )
    problems += _screenshot(run.cli, job["actual"], run.full_page)
    untouched = not _app_dirty(job)
    if problems:
        run.errors.extend(f"{name} actual: {problem}" for problem in problems)
        return untouched
    geometry, geometry_error = _geometry_probe(run.cli)
    if geometry_error:
        run.errors.append(f"{name} actual: geometry probe failed: {geometry_error}")
    job.update(app_ok=True, geometry=geometry, geometry_error=geometry_error)
    job["geometry_fingerprint"] = _fingerprint(geometry)
    job["actual_sha256"] = _file_sha256(job["actual"])
    previous = run.previous.get(job["tuple_sha256"])
    if previous is not None and _can_carry(previous, job, run.tolerance):
        job.update(carried=previous, done=True)
        print(f"carried {name}")
    return untouched


def _app_phase(run: _Run, jobs: list[dict[str, Any]]) -> None:
    """Capture every app page of one route, loading the page once while it stays clean.

    A state or condition trigger changes the page, so those tuples load a fresh
    page each; trigger-free tuples run first and share one load.
    """

    loaded = False
    for job in sorted(jobs, key=lambda item: (_app_dirty(item), item["index"])):
        with _timed(job):
            loaded = _app_step(run, job, loaded)


def _reference_step(
    run: _Run, job: dict[str, Any], route: str, loaded: bool
) -> tuple[bool, bool]:
    """Capture one reference render; return (page still untouched, route unreachable)."""

    if not loaded:
        ok, method = _navigate_reference(run.cli, run.reference_url, route, job["entry"])
        run.nav_methods[route] = method
        if not ok:
            run.skipped.append({**job["combo"], "reason": f"reference nav: {method}"})
            return False, True
    problems = _shoot(
        run.cli,
        viewport=job["viewport"],
        screenshot=job["target"],
        full_page=run.full_page,
        state_eval=job["reference_eval"],
        condition_eval=job["condition_reference_eval"],
    )
    untouched = not _reference_dirty(job)
    if problems:
        run.errors.extend(f"{job['name']} target: {problem}" for problem in problems)
        return untouched, False
    job["done"] = True
    job["target_sha256"] = _file_sha256(job["target"])
    job["pixel_diff"], job["pixel_diff_reason"] = _pixel_diff(job["target"], job["actual"])
    job["classification"] = _classify(job["pixel_diff"], run.tolerance)
    print(f"captured {job['name']}")
    return untouched, False


def _row(job: dict[str, Any], carry_from: str | None) -> dict[str, Any]:
    """The manifest row of a captured pair, or of one carried from a previous run."""

    carried = job["carried"]
    row = {
        **job["combo"],
        "tuple_sha256": job["tuple_sha256"],
        "target": job["target"].as_posix(),
        "actual": job["actual"].as_posix(),
        "target_sha256": job.get("target_sha256"),
        "actual_sha256": job["actual_sha256"],
        "target_inputs_sha256": job["target_inputs_sha256"],
        "geometry": job["geometry"],
        "geometry_error": job["geometry_error"],
        "geometry_fingerprint": job["geometry_fingerprint"],
        "pixel_diff": job.get("pixel_diff"),
        "pixel_diff_reason": job.get("pixel_diff_reason"),
        "classification": job.get("classification"),
        "duration_ms": round(job["seconds"] * 1000),
    }
    if carried:
        row.update(
            {key: carried[key] for key in (
                "target", "actual", "target_sha256", "actual_sha256",
                "pixel_diff", "pixel_diff_reason",
            )},
            classification="carried",
            carried_from={"manifest": carry_from, "classification": carried["classification"]},
        )
    return row


def _reference_phase(run: _Run, route: str, jobs: list[dict[str, Any]]) -> None:
    """Capture the reference renders of one route, navigating once while it stays clean."""

    loaded = False
    unreachable = False
    pending = [job for job in jobs if job["app_ok"] and not job["carried"]]
    for job in sorted(pending, key=lambda item: (_reference_dirty(item), item["index"])):
        if unreachable:
            run.skipped.append(
                {**job["combo"], "reason": f"reference nav: {run.nav_methods[route]}"}
            )
            continue
        with _timed(job):
            loaded, unreachable = _reference_step(run, job, route, loaded)


def _board_src(path: str, board_dir: Path) -> str:
    """Image URL relative to the board, so it opens from any directory."""

    try:
        return Path(os.path.relpath(path, board_dir)).as_posix()
    except ValueError:  # another drive on Windows
        return Path(path).resolve().as_uri()


def _diff_note(item: dict[str, Any]) -> str:
    """One line on how far the pair is from identical."""

    diff = item.get("pixel_diff")
    if diff is None:
        return f"pixel diff unavailable: {item.get('pixel_diff_reason')}"
    note = f"{diff['ratio'] * 100:.4f}% of pixels differ ({diff['differing_pixels']} of {diff['total_pixels']})"
    if not diff["sizes_matched"]:
        t, a = diff["target_size"], diff["actual_size"]
        note += f" · size mismatch: target {t[0]}×{t[1]}, actual {a[0]}×{a[1]}"
    return note


def _pair_card(item: dict[str, Any], out_dir: Path) -> str:
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
    return (
        "<section class='pair'>"
        f"<h3>{html.escape(label)}</h3>"
        f"<p class='diff'>{html.escape(item['classification'])} · {html.escape(_diff_note(item))}</p>"
        f"<div class='imgs'><figure><img src=\"{html.escape(_board_src(item['target'], out_dir))}\">"
        "<figcaption>target (design reference)</figcaption></figure>"
        f"<figure><img src=\"{html.escape(_board_src(item['actual'], out_dir))}\">"
        "<figcaption>actual (implementation)</figcaption></figure></div>"
        f"<div class='findings'>{findings_html}</div>"
        "<div class='verdict'>verdict: pass / deviation — "
        "differences: ______________________</div>"
        "</section>"
    )


def _board(
    out_dir: Path,
    captured: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
) -> Path:
    def unreviewed_first(item: dict[str, Any]) -> float:
        diff = item.get("pixel_diff")
        return -2.0 if diff is None else -diff["ratio"]

    changed = sorted(
        (item for item in captured if item["classification"] == "changed"),
        key=unreviewed_first,
    )
    sections = [_pair_card(item, out_dir) for item in changed]
    for kind in ("identical", "carried"):
        folded = [item for item in captured if item["classification"] == kind]
        if folded:
            sections.append(
                f"<details><summary>{len(folded)} {kind} "
                f"{'pair' if len(folded) == 1 else 'pairs'}</summary>"
                + "".join(_pair_card(item, out_dir) for item in folded)
                + "</details>"
            )
    for item in skipped:
        sections.append(
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
        ".diff{font-family:monospace;margin:4px 0 8px}"
        ".verdict{margin-top:8px;font-family:monospace}"
        "details{margin-bottom:16px}"
        "summary{cursor:pointer;font-weight:bold;margin-bottom:12px}"
        "</style></head><body>"
        "<h1>Parity board — design reference vs implementation</h1>"
        "<p>Compare each pair item by item within ui-design.md's recorded "
        "tolerance; record the verdict in RUN's target_comparison.</p>"
        + "".join(sections)
        + "</body></html>",
        encoding="utf-8",
        newline="\n",
    )
    return board


def capture(args: argparse.Namespace) -> int:
    started = _clock()
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

    carry_from: Path | None = getattr(args, "carry_from", None)
    recapture_carried: bool = getattr(args, "recapture_carried", False)
    previous: dict[str, dict[str, Any]] = {}
    if carry_from is not None and not recapture_carried:
        try:
            previous = _load_carry_source(carry_from)
        except (ManifestError, json.JSONDecodeError, OSError, UnicodeError) as exc:
            print(f"error: --carry-from {carry_from}: {exc}", file=sys.stderr)
            return 1

    projection_errors = _capture_projection_errors(plan)
    if projection_errors:
        for problem in projection_errors:
            print(f"error: {problem}", file=sys.stderr)
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

    run = _Run(
        cli=cli,
        reference_url=reference.resolve().as_uri(),
        reference_sha256=_file_sha256(reference),
        full_page=args.full_page,
        tolerance=getattr(args, "tolerance", 0.0),
        previous=previous,
        carry_from=carry_from.as_posix() if carry_from else None,
    )
    base_url: str = str(args.base_url).rstrip("/")
    routes = sorted({combo["route"] for combo in combos})
    original_media = None
    if any("kind" in combo for combo in combos):
        opened = _run_browser(cli, ["open", "about:blank"])
        original_media, media_problem = _read_media_preferences(cli)
        if opened.returncode or media_problem:
            run.errors.append(media_problem or "could not open the private browser context")

    jobs: list[dict[str, Any]] = []
    for route in routes:
        entry = route_map.get(route) or {}
        if not isinstance(entry, dict):
            entry = {}
        for combo in (c for c in combos if c["route"] == route):
            job = _plan_job(
                run, combo, len(jobs), entry, out_dir,
                args.height or VIEWPORT_HEIGHT, base_url,
            )
            if job:
                jobs.append(job)

    # One media-preference change covers every tuple that shares it.
    scopes: dict[Any, list[dict[str, Any]]] = {}
    for job in jobs:
        scopes.setdefault(job["combo"].get("media_preference"), []).append(job)
    for media, scope_jobs in scopes.items():
        with _motion_scope(
            cli, scope_jobs[0]["combo"], original_media, run.errors, f"{media} media"
        ) as prepared:
            if not prepared:
                continue
            for route in routes:
                route_jobs = [job for job in scope_jobs if job["route"] == route]
                if route_jobs:
                    _app_phase(run, route_jobs)
                    _reference_phase(run, route, route_jobs)

    _run_browser(cli, ["close"], timeout=30)
    captured = [_row(job, run.carry_from) for job in jobs if job["done"]]
    skipped, errors, nav_methods = run.skipped, run.errors, run.nav_methods
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
        "duration_ms": round((_clock() - started) * 1000),
        "tolerance": run.tolerance,
        "carry_from": run.carry_from,
        "recapture_carried": recapture_carried,
        "classification_counts": dict(Counter(row["classification"] for row in captured)),
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
        f"{len(errors)} errors in {manifest['duration_ms'] / 1000:.1f}s; board: {board}"
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
    parser.add_argument(
        "--tolerance", type=_ratio, default=0.0,
        help="largest fraction of differing pixels (0.0-1.0) still classed identical "
        "(default: 0.0, exact)",
    )
    parser.add_argument(
        "--carry-from", type=Path, metavar="MANIFEST",
        help="previous manifest.json; a pair whose app page and reference inputs are "
        "unchanged since an identical one is recorded as carried and not recaptured",
    )
    parser.add_argument(
        "--recapture-carried", action="store_true",
        help="with --carry-from, capture every pair again instead of carrying",
    )
    args = parser.parse_args(argv)
    if args.recapture_carried and args.carry_from is None:
        parser.error("--recapture-carried needs --carry-from")
    try:
        return capture(args)
    except subprocess.TimeoutExpired as exc:
        print(f"error: agent-browser timed out: {exc}", file=sys.stderr)
        return 1
    except (ManifestError, OSError, UnicodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="backslashreplace")
    raise SystemExit(main())
