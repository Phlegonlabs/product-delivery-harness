#!/usr/bin/env python3
"""Invoke Claude Code as an external Harness Dynamic Workflow runtime."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PREFLIGHT = SKILL_ROOT / "assets" / "templates" / "CLAUDE_RUNTIME_PREFLIGHT.template.js"
DEFAULT_GRAPH_WORKFLOW = SKILL_ROOT / "assets" / "templates" / "CLAUDE_GRAPH_WORKFLOW.template.js"
PREFLIGHT_SCHEMA = {
    "type": "object",
    "required": [
        "provider",
        "driver",
        "protocol_version",
        "status",
        "probe_count",
        "probe_labels",
    ],
    "properties": {
        "provider": {"const": "claude_code"},
        "driver": {"const": "dynamic_workflow"},
        "protocol_version": {"const": 1},
        "status": {"const": "available"},
        "probe_count": {"const": 2},
        "probe_labels": {
            "type": "array",
            "prefixItems": [{"const": "probe-a"}, {"const": "probe-b"}],
            "minItems": 2,
            "maxItems": 2,
        },
    },
    "additionalProperties": False,
}
WAVE_SCHEMA = {
    "type": "object",
    "required": [
        "workflow_task_id",
        "workflow_run_id",
        "workflow_script_path",
        "workflow_error",
        "results",
    ],
    "properties": {
        "workflow_task_id": {"type": "string", "minLength": 1},
        "workflow_run_id": {"type": ["string", "null"]},
        "workflow_script_path": {"type": "string", "minLength": 1},
        "workflow_error": {"type": ["string", "null"]},
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["node_result"],
                "properties": {"node_result": {"type": "object"}},
                "additionalProperties": False,
            },
        }
    },
    "additionalProperties": False,
}
PERMISSION_MODES = {
    "acceptEdits",
    "auto",
    "bypassPermissions",
    "manual",
    "dontAsk",
    "plan",
}
TOOL_PROFILE_REQUIREMENTS = {
    "mission_write": {
        "Workflow",
        "EnterWorktree",
        "Read",
        "Glob",
        "Grep",
        "Edit",
        "Write",
        "Bash",
    },
    "code_review_readonly": {"Workflow", "Read", "Glob", "Grep"},
    "visual_review_readonly": {"Workflow", "Read", "Glob", "Grep"},
}
REVIEW_FORBIDDEN_TOOLS = {"EnterWorktree", "Edit", "Write", "NotebookEdit", "Bash"}


class BridgeError(RuntimeError):
    """Raised when the external runtime handshake or invocation fails."""


def _compact(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _resolve_claude(command: str) -> str:
    resolved = shutil.which(command)
    if resolved is None:
        raise BridgeError(f"Claude Code command not found: {command}")
    return resolved


def _claude_version(command: str, timeout: int) -> str:
    completed = subprocess.run(
        [command, "--version"],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        raise BridgeError("Claude Code version check failed")
    return completed.stdout.strip()


def _extract_structured(stdout: str) -> Any:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise BridgeError("Claude Code did not return JSON output") from exc
    if isinstance(payload, dict) and payload.get("structured_output") is not None:
        return payload["structured_output"]
    result = payload.get("result") if isinstance(payload, dict) else payload
    if isinstance(result, str):
        try:
            return json.loads(result)
        except json.JSONDecodeError as exc:
            raise BridgeError("Claude Code result was not structured JSON") from exc
    return result


def _build_command(
    *,
    command: str,
    prompt: str,
    schema: dict[str, Any],
    allowed_tools: list[str],
    permission_mode: str,
    max_budget_usd: float,
    model: str = "sonnet",
    reasoning_effort: str | None = None,
) -> list[str]:
    if permission_mode not in PERMISSION_MODES:
        raise BridgeError(f"Unsupported Claude permission mode: {permission_mode}")
    if "Workflow" not in allowed_tools:
        raise BridgeError("Claude runtime invocation must allow the Workflow tool")
    if max_budget_usd <= 0:
        raise BridgeError("max_budget_usd must be positive")
    if not isinstance(model, str) or not model.strip():
        raise BridgeError("model must be a non-empty Claude model name or alias")
    if reasoning_effort is not None and (
        not isinstance(reasoning_effort, str) or not reasoning_effort.strip()
    ):
        raise BridgeError("reasoning_effort must be null or a non-empty string")
    permission_args = (
        ["--dangerously-skip-permissions"]
        if permission_mode == "bypassPermissions"
        else ["--permission-mode", permission_mode]
    )
    effort_args = ["--effort", reasoning_effort] if reasoning_effort is not None else []
    return [
        command,
        "-p",
        "--model",
        model,
        *effort_args,
        "--output-format",
        "json",
        "--json-schema",
        _compact(schema),
        *permission_args,
        "--allowedTools",
        ",".join(allowed_tools),
        "--max-budget-usd",
        str(max_budget_usd),
        prompt,
    ]


def _invoke(command: list[str], *, cwd: Path, timeout: int) -> Any:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise BridgeError(f"Claude Code exited {completed.returncode}: {message[:1000]}")
    return _extract_structured(completed.stdout)


def preflight(
    *,
    claude: str,
    script: Path,
    cwd: Path,
    timeout: int,
    max_budget_usd: float,
    model: str = "haiku",
) -> dict[str, Any]:
    command = _resolve_claude(claude)
    if not script.is_file():
        raise BridgeError(f"Preflight workflow is missing: {script}")
    version = _claude_version(command, timeout)
    prompt = (
        "Use the Workflow tool exactly once. "
        f"Set scriptPath to {script.resolve()} and args to {{\"protocol_version\":1}}. "
        "Do not use any other tool. Return the workflow result as the final structured output."
    )
    result = _invoke(
        _build_command(
            command=command,
            prompt=prompt,
            schema=PREFLIGHT_SCHEMA,
            allowed_tools=["Workflow"],
            permission_mode="dontAsk",
            max_budget_usd=max_budget_usd,
            model=model,
        ),
        cwd=cwd,
        timeout=timeout,
    )
    expected = {
        "provider": "claude_code",
        "driver": "dynamic_workflow",
        "protocol_version": 1,
        "status": "available",
        "probe_count": 2,
        "probe_labels": ["probe-a", "probe-b"],
    }
    if result != expected:
        raise BridgeError(f"Unexpected Dynamic Workflow preflight result: {_compact(result)}")
    return {
        "status": "PASS",
        "runtime": {
            "provider": "claude_code",
            "driver": "dynamic_workflow",
            "command": command,
            "version": version,
            "completion_channel": "agent_result",
        },
        "evidence": ["Workflow agent returned the protocol-v1 structured preflight result"],
    }


def _validate_tool_profile(
    profile: str, tools: list[str], nodes: list[dict[str, Any]]
) -> None:
    required = TOOL_PROFILE_REQUIREMENTS.get(profile)
    if required is None:
        raise BridgeError(f"Unsupported Claude tool profile: {profile}")
    tool_set = set(tools)
    missing = sorted(required - tool_set)
    if missing:
        raise BridgeError(
            f"Tool profile {profile} is missing required tools: {', '.join(missing)}"
        )
    unexpected = sorted(tool_set - required)
    if unexpected:
        forbidden = sorted(REVIEW_FORBIDDEN_TOOLS & set(unexpected))
        if profile != "mission_write" and forbidden:
            raise BridgeError(
                f"Read-only tool profile {profile} contains write-capable tools: {', '.join(forbidden)}"
            )
        raise BridgeError(
            f"Tool profile {profile} contains unexpected tools: {', '.join(unexpected)}"
        )
    if profile == "mission_write":
        if any(node.get("node_kind") != "mission" for node in nodes):
            raise BridgeError("mission_write tool profile may contain only mission nodes")
        return
    forbidden = sorted(REVIEW_FORBIDDEN_TOOLS & tool_set)
    if forbidden:
        raise BridgeError(
            f"Read-only tool profile {profile} contains write-capable tools: {', '.join(forbidden)}"
        )
    if any(node.get("node_kind") != "review" for node in nodes):
        raise BridgeError(f"{profile} tool profile may contain only review nodes")
    review_types = {node.get("review_type") for node in nodes}
    if profile == "visual_review_readonly" and review_types != {"visual"}:
        raise BridgeError("visual_review_readonly requires only visual review nodes")
    if profile == "code_review_readonly" and not review_types.issubset(
        {"frontend_code", "backend_code"}
    ):
        raise BridgeError("code_review_readonly requires frontend_code or backend_code reviews")


def _load_wave_request(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BridgeError(f"Cannot load wave request: {path}") from exc
    required = {
        "run_id",
        "plan_id",
        "plan_revision",
        "plan_digest_sha256",
        "graph_revision",
        "batch_base_sha",
        "nodes",
        "tool_profile",
        "allowed_tools",
        "permission_mode",
        "model",
        "reasoning_effort",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise BridgeError("Wave request has missing or unknown top-level fields")
    if not isinstance(value["nodes"], list) or not value["nodes"]:
        raise BridgeError("Wave request requires a non-empty nodes array")
    node_ids: set[str] = set()
    mission_required = {
        "node_kind",
        "node_id",
        "attempt_id",
        "mission_id",
        "lease_id",
        "branch_ref",
        "worktree_path",
        "failure_outcome",
        "worker_prompt",
    }
    review_required = {
        "node_kind",
        "node_id",
        "attempt_id",
        "review_id",
        "review_type",
        "reviewed_sha",
        "review_path",
        "review_scope",
        "required_evidence",
        "failure_outcome",
        "worker_prompt",
    }
    for node in value["nodes"]:
        if not isinstance(node, dict):
            raise BridgeError("Every wave node must be an object")
        required = mission_required if node.get("node_kind") == "mission" else review_required
        if set(node) != required:
            raise BridgeError("Every wave node must use the exact mission or review handoff fields")
        string_fields = required - {"review_scope", "required_evidence"}
        if any(not isinstance(node[field], str) or not node[field] for field in string_fields):
            raise BridgeError("Every scalar wave node field must be a non-empty string")
        if node["node_kind"] not in {"mission", "review"}:
            raise BridgeError("Wave node_kind must be mission or review")
        if node["failure_outcome"] not in {"retryable_failure", "blocked"}:
            raise BridgeError("Every wave node requires retryable_failure or blocked failure_outcome")
        for field in ("review_scope", "required_evidence"):
            if field in node and (
                not isinstance(node[field], list)
                or not node[field]
                or any(not isinstance(item, str) or not item for item in node[field])
            ):
                raise BridgeError(f"{field} must be a non-empty list of strings")
        if node["node_id"] in node_ids:
            raise BridgeError("Wave node IDs must be unique")
        node_ids.add(node["node_id"])
    tools = value["allowed_tools"]
    if not isinstance(tools, list) or any(not isinstance(tool, str) or not tool for tool in tools):
        raise BridgeError("allowed_tools must be a list of non-empty strings")
    if "Workflow" not in tools:
        raise BridgeError("allowed_tools must include Workflow")
    _validate_tool_profile(value["tool_profile"], tools, value["nodes"])
    if value["permission_mode"] not in PERMISSION_MODES:
        raise BridgeError("Wave request has an unsupported permission_mode")
    if not isinstance(value["model"], str) or not value["model"].strip():
        raise BridgeError("Wave request model must be a non-empty Claude model name or alias")
    if value["reasoning_effort"] is not None and (
        not isinstance(value["reasoning_effort"], str) or not value["reasoning_effort"].strip()
    ):
        raise BridgeError("Wave request reasoning_effort must be null or a non-empty string")
    return value


def run_wave(
    *,
    claude: str,
    script: Path,
    request_path: Path,
    cwd: Path,
    timeout: int,
    max_budget_usd: float,
    model: str | None = None,
) -> dict[str, Any]:
    command = _resolve_claude(claude)
    if not script.is_file():
        raise BridgeError(f"Graph workflow is missing: {script}")
    request = _load_wave_request(request_path)
    requested_model = request["model"]
    if model is not None and model != requested_model:
        raise BridgeError("CLI model override must match the PLAN-selected wave model")
    version = _claude_version(command, timeout)
    workflow_args = {
        key: value
        for key, value in request.items()
        if key not in {"allowed_tools", "permission_mode", "model", "reasoning_effort"}
    }
    prompt = (
        "Use the Workflow tool exactly once. "
        f"Set scriptPath to {script.resolve()} and args to this exact JSON object: {_compact(workflow_args)}. "
        "Pass args as an actual object, not as a JSON-encoded string. "
        f"The accepted tool profile is {request['tool_profile']}; do not widen its tool allowlist. "
        "Do not change the arguments. Read the real taskId, optional runId, scriptPath, and optional error from the Workflow tool result; do not invent them. "
        "Return {\"workflow_task_id\": <taskId>, \"workflow_run_id\": <runId or null>, "
        "\"workflow_script_path\": <scriptPath>, \"workflow_error\": <error or null>, "
        "\"results\": <workflow result, or [] when error is non-null>} as the final structured output."
    )
    result = _invoke(
        _build_command(
            command=command,
            prompt=prompt,
            schema=WAVE_SCHEMA,
            allowed_tools=request["allowed_tools"],
            permission_mode=request["permission_mode"],
            max_budget_usd=max_budget_usd,
            model=requested_model,
            reasoning_effort=request["reasoning_effort"],
        ),
        cwd=cwd,
        timeout=timeout,
    )
    if not isinstance(result, dict):
        raise BridgeError("Claude graph wave did not return a structured wrapper")
    if result.get("workflow_error"):
        raise BridgeError(f"Claude Workflow launch failed: {result['workflow_error']}")
    expected_ids = {node["node_id"] for node in request["nodes"]}
    results = result.get("results", [])
    actual_ids = {
        item.get("node_result", {}).get("node_id")
        for item in results
        if isinstance(item, dict) and isinstance(item.get("node_result"), dict)
    }
    if actual_ids != expected_ids or len(results) != len(expected_ids):
        raise BridgeError("Claude graph wave did not return exactly one result per requested node")
    return {
        "status": "PASS",
        "runtime": {
            "provider": "claude_code",
            "driver": "dynamic_workflow",
            "command": command,
            "version": version,
            "completion_channel": "agent_result",
            "model": requested_model,
            "reasoning_effort": request["reasoning_effort"],
            "tool_profile": request["tool_profile"],
            "workflow_run_id": result["workflow_run_id"],
            "workflow_task_id": result["workflow_task_id"],
            "workflow_script_path": result["workflow_script_path"],
            "workflow_error": None,
        },
        "results": results,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claude", default="claude")
    parser.add_argument("--cwd", type=Path, default=Path.cwd())
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--max-budget-usd", type=float, default=0.25)
    parser.add_argument("--model", default=None)
    subparsers = parser.add_subparsers(dest="command", required=True)
    preflight_parser = subparsers.add_parser("preflight")
    preflight_parser.add_argument("--script", type=Path, default=DEFAULT_PREFLIGHT)
    wave_parser = subparsers.add_parser("run-wave")
    wave_parser.add_argument("--script", type=Path, default=DEFAULT_GRAPH_WORKFLOW)
    wave_parser.add_argument("--request", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "preflight":
            result = preflight(
                claude=args.claude,
                script=args.script,
                cwd=args.cwd,
                timeout=args.timeout,
                max_budget_usd=args.max_budget_usd,
                model=args.model or "haiku",
            )
        else:
            result = run_wave(
                claude=args.claude,
                script=args.script,
                request_path=args.request,
                cwd=args.cwd,
                timeout=args.timeout,
                max_budget_usd=args.max_budget_usd,
                model=args.model,
            )
    except (BridgeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "ERROR", "errors": [str(exc)]}, sort_keys=True, indent=2))
        return 2
    print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
