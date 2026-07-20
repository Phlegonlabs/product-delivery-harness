#!/usr/bin/env python3
"""Invoke Claude Code as an external Harness Dynamic Workflow runtime."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from harness_manifest import (
    ManifestError,
    authorization_covers,
    execution_covers,
    load_plan,
    load_run,
    plan_digest,
    validate_plan,
    validate_run,
)
from select_ready_nodes import _required_actions, _runtime_binding, _tool_profile


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
        "workflow_run_id": {"type": "string", "minLength": 1},
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
    "code_review_readonly": {"Workflow", "EnterWorktree", "Read", "Glob", "Grep"},
    "visual_review_readonly": {"Workflow", "EnterWorktree", "Read", "Glob", "Grep"},
}
REVIEW_FORBIDDEN_TOOLS = {"Edit", "Write", "NotebookEdit", "Bash"}


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


def _json_object(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    text = value if isinstance(value, str) else None
    if isinstance(value, list):
        text_parts = [
            item.get("text")
            for item in value
            if isinstance(item, dict) and isinstance(item.get("text"), str)
        ]
        if text_parts:
            text = "".join(text_parts)
    if text is None:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _extract_workflow_stream(
    stdout: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise BridgeError("Claude Code stream contained invalid JSON") from exc
        if not isinstance(event, dict):
            raise BridgeError("Claude Code stream event must be an object")
        events.append(event)

    tool_calls: list[tuple[int, dict[str, Any]]] = []
    for event_index, event in enumerate(events):
        if event.get("type") != "assistant":
            continue
        message = event.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "tool_use":
                continue
            tool_calls.append((event_index, item))
    if len(tool_calls) != 1 or tool_calls[0][1].get("name") != "Workflow":
        raise BridgeError(
            "Claude Code must emit exactly one Workflow tool call and no other tool calls"
        )

    tool_call_index, workflow_call = tool_calls[0]
    tool_use_id = workflow_call.get("id")
    tool_input = workflow_call.get("input")
    if not isinstance(tool_use_id, str) or not isinstance(tool_input, dict):
        raise BridgeError("Claude Workflow tool call metadata is malformed")

    workflow_results: list[tuple[int, dict[str, Any]]] = []
    for event_index, event in enumerate(events):
        if event.get("type") != "user":
            continue
        message = event.get("message")
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        matching_blocks = [
            item
            for item in content
            if isinstance(item, dict)
            and item.get("type") == "tool_result"
            and item.get("tool_use_id") == tool_use_id
        ]
        if not matching_blocks:
            continue
        if event_index <= tool_call_index:
            raise BridgeError("Claude Workflow tool result occurred before its tool call")
        if len(matching_blocks) != 1:
            raise BridgeError("Claude Code emitted duplicate Workflow tool result blocks")
        raw_result = _json_object(event.get("tool_use_result"))
        if raw_result is None:
            raw_result = _json_object(matching_blocks[0].get("content"))
        if raw_result is None:
            raise BridgeError("Claude Workflow runtime metadata is unavailable")
        workflow_results.append((event_index, raw_result))
    if len(workflow_results) != 1:
        raise BridgeError("Claude Code must emit one matching Workflow tool result")

    result_index, runtime_result = workflow_results[0]
    final_events = [
        (event_index, event)
        for event_index, event in enumerate(events)
        if event.get("type") == "result"
    ]
    if len(final_events) != 1:
        raise BridgeError("Claude Code must emit one final result event")
    final_index, final_event = final_events[0]
    if final_index <= result_index:
        raise BridgeError("Claude Code final result occurred before the Workflow tool result")
    wrapper = _json_object(final_event.get("structured_output"))
    if wrapper is None:
        wrapper = _json_object(final_event.get("result"))
    if wrapper is None:
        raise BridgeError("Claude Code result was not structured JSON")
    return wrapper, runtime_result, tool_input


def _validate_workflow_evidence(
    wrapper: dict[str, Any],
    runtime_result: dict[str, Any],
    tool_input: dict[str, Any],
    *,
    workflow_script_path: Path,
    workflow_args: dict[str, Any],
) -> None:
    if tool_input.get("args") != workflow_args:
        raise BridgeError("Claude Workflow tool call changed the wave arguments")
    input_script = tool_input.get("scriptPath")
    if not isinstance(input_script, str) or Path(input_script).resolve() != workflow_script_path:
        raise BridgeError("Claude Workflow tool call used a different scriptPath")

    if runtime_result.get("status") != "async_launched":
        raise BridgeError("Claude Workflow did not launch a local workflow")
    if runtime_result.get("taskType") != "local_workflow":
        raise BridgeError("Claude Workflow did not launch a local workflow")
    runtime_error = runtime_result.get("error")
    if runtime_error is not None:
        raise BridgeError(f"Claude Workflow launch failed: {runtime_error}")

    task_id = runtime_result.get("taskId")
    run_id = runtime_result.get("runId")
    script_path = runtime_result.get("scriptPath")
    if not isinstance(task_id, str) or not task_id.strip():
        raise BridgeError("Claude Workflow runtime did not return a taskId")
    if not isinstance(run_id, str) or not run_id.strip():
        raise BridgeError("Claude Workflow runtime did not return a runId")
    if not isinstance(script_path, str) or Path(script_path).resolve() != workflow_script_path:
        raise BridgeError("Claude Workflow runtime used a different scriptPath")
    if wrapper.get("workflow_task_id") != task_id:
        raise BridgeError("Claude Workflow task ID does not match runtime evidence")
    if wrapper.get("workflow_run_id") != run_id:
        raise BridgeError("Claude Workflow run ID does not match runtime evidence")
    if wrapper.get("workflow_error") != runtime_error:
        raise BridgeError("Claude Workflow error does not match runtime evidence")
    wrapper_script = wrapper.get("workflow_script_path")
    if not isinstance(wrapper_script, str) or Path(wrapper_script).resolve() != workflow_script_path:
        raise BridgeError("Claude Workflow script path does not match runtime evidence")


def _build_command(
    *,
    command: str,
    prompt: str,
    schema: dict[str, Any] | None,
    allowed_tools: list[str],
    permission_mode: str,
    max_budget_usd: float,
    model: str = "sonnet",
    reasoning_effort: str | None = None,
    output_format: str = "json",
    verbose: bool = False,
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
    if output_format not in {"json", "stream-json"}:
        raise BridgeError(f"Unsupported Claude output format: {output_format}")
    effort_args = ["--effort", reasoning_effort] if reasoning_effort is not None else []
    schema_args = ["--json-schema", _compact(schema)] if schema is not None else []
    verbose_args = ["--verbose"] if verbose else []
    return [
        command,
        "-p",
        "--model",
        model,
        *effort_args,
        "--output-format",
        output_format,
        *verbose_args,
        *schema_args,
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
    output_format = command[command.index("--output-format") + 1]
    if output_format == "stream-json":
        return _extract_workflow_stream(completed.stdout)
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


def _git_output(cwd: Path, *args: str, timeout: int = 30) -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(cwd), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BridgeError(f"Cannot inspect Git checkout at {cwd}") from exc
    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip()
        raise BridgeError(f"Git checkout validation failed at {cwd}: {message[:500]}")
    return completed.stdout.strip()


def _validate_checkout(
    path: Path,
    *,
    expected_sha: str,
    repository_path: Path,
    expected_branch: str | None = None,
) -> None:
    if not path.is_absolute():
        raise BridgeError(f"Checkout path must be absolute: {path}")
    checkout_root = Path(_git_output(path, "rev-parse", "--show-toplevel")).resolve()
    if checkout_root != path.resolve():
        raise BridgeError(f"Checkout path is not the Git worktree root: {path}")
    checkout_common = Path(
        _git_output(path, "rev-parse", "--path-format=absolute", "--git-common-dir")
    ).resolve()
    repository_common = Path(
        _git_output(
            repository_path,
            "rev-parse",
            "--path-format=absolute",
            "--git-common-dir",
        )
    ).resolve()
    if checkout_common != repository_common:
        raise BridgeError(f"Checkout does not belong to the RUN repository: {path}")
    if _git_output(path, "rev-parse", "HEAD") != expected_sha:
        raise BridgeError(f"Checkout HEAD does not match the allocated SHA: {path}")
    if expected_branch is not None:
        if not expected_branch.startswith("refs/heads/"):
            raise BridgeError("Mission branch_ref must be a full refs/heads/ ref")
        if _git_output(path, "symbolic-ref", "--quiet", "HEAD") != expected_branch:
            raise BridgeError(f"Checkout branch does not match the allocated branch: {path}")


def _require_authorizations(
    run: dict[str, Any],
    node: dict[str, Any],
    binding: dict[str, Any],
    mission_ids: list[str],
    *,
    worker_id: str,
    worktree_path: str | None = None,
    branch_ref: str | None = None,
) -> None:
    targets = {
        "invoke_external_runtime": "runtime:claude_code",
        "spawn_subagents": f"worker:{worker_id}",
        "create_local_worktrees": (
            f"worktree:{worktree_path}" if worktree_path is not None else None
        ),
        "create_local_branches": f"branch:{branch_ref}" if branch_ref is not None else None,
        "create_local_commits": f"branch:{branch_ref}" if branch_ref is not None else None,
    }
    for mission_id in mission_ids:
        if not execution_covers(run, mission_id):
            raise BridgeError(f"Execution authorization does not cover mission {mission_id}")
        for action in _required_actions(node, binding, run["runtime_capabilities"]):
            target = targets.get(action)
            if target is None or not authorization_covers(run, action, mission_id, target):
                raise BridgeError(
                    f"Action authorization {action} does not cover mission {mission_id} target {target}"
                )


def _validate_current_wave_binding(
    request: dict[str, Any],
    plan: dict[str, Any],
    run: dict[str, Any],
) -> None:
    plan_errors = validate_plan(plan)
    if plan_errors:
        raise BridgeError("PLAN validation failed:\n" + "\n".join(plan_errors))
    run_errors = validate_run(plan, run)
    if run_errors:
        raise BridgeError("RUN validation failed:\n" + "\n".join(run_errors))
    if plan.get("schema_version") != 4 or run.get("schema_version") not in {8, 9}:
        raise BridgeError("run-wave requires PLAN v4 and RUN v8 or v9")
    if run.get("status") != "running" or run.get("plan_readiness") != "ready":
        raise BridgeError("RUN must be running with a ready PLAN")

    digest = plan_digest(plan)
    identity = {
        "run_id": run.get("run_id"),
        "plan_id": plan.get("plan_id"),
        "plan_revision": plan.get("revision"),
        "plan_digest_sha256": digest,
        "graph_revision": run.get("graph_state", {}).get("graph_revision"),
        "batch_base_sha": run.get("integration", {}).get("batch_base_sha"),
    }
    for field, expected in identity.items():
        if request.get(field) != expected:
            raise BridgeError(f"Wave request {field} does not match current PLAN/RUN state")

    runtime = run["runtime_capabilities"]
    external = [
        item
        for item in runtime.get("runtime_adapter", {}).get("external_runtimes", [])
        if isinstance(item, dict)
        and item.get("provider") == "claude_code"
        and item.get("driver") == "dynamic_workflow"
        and item.get("status") == "available"
        and item.get("completion_channel") == "agent_result"
        and item.get("evidence")
    ]
    if len(external) != 1:
        raise BridgeError("Current RUN does not record one available Claude Dynamic Workflow runtime")
    if run.get("observed", {}).get("runtime", {}).get("completion_channel_available") is not True:
        raise BridgeError("Current RUN completion channel is unavailable")
    permission = runtime.get("permission_boundary")
    if not isinstance(permission, dict) or permission.get("status") != "ready":
        raise BridgeError("Current RUN permission boundary is not ready")
    if (
        request["permission_mode"] == "bypassPermissions"
        and permission.get("selected_mode") != "full_access"
    ):
        raise BridgeError("bypassPermissions requires a ready full_access permission boundary")

    repository_path_value = run.get("observed", {}).get("git", {}).get(
        "parent_worktree_path"
    )
    if not isinstance(repository_path_value, str) or not repository_path_value:
        raise BridgeError("Current RUN is missing the parent repository path")
    repository_path = Path(repository_path_value)
    graph_nodes = {node["id"]: node for node in plan["graph"]["nodes"]}
    node_states = run["graph_state"]["node_states"]

    running_attempts = {
        (node_id, attempt_id)
        for workflow in run.get("workflow_runs", [])
        if isinstance(workflow, dict) and workflow.get("status") == "running"
        for node_id, attempt_id in workflow.get("attempt_ids", {}).items()
    }

    for request_node in request["nodes"]:
        node_id = request_node["node_id"]
        node = graph_nodes.get(node_id)
        if node is None or node.get("executor") != "runtime_worker":
            raise BridgeError(f"Wave node {node_id} is not a PLAN runtime worker")
        state = node_states[node_id]
        attempt_id = request_node["attempt_id"]
        if (
            state.get("phase") != "running"
            or state.get("last_attempt_id") != attempt_id
            or not state.get("bound_worker_id")
        ):
            raise BridgeError(f"Wave node {node_id} does not match the active graph attempt")
        if (node_id, attempt_id) in running_attempts:
            raise BridgeError(f"Wave node {node_id} already has a running Workflow record")

        binding = _runtime_binding(node, runtime)
        if not isinstance(binding, dict) or (
            binding.get("provider"),
            binding.get("driver"),
            binding.get("source"),
        ) != ("claude_code", "external_dynamic_workflow", "external_bridge"):
            raise BridgeError(f"Wave node {node_id} is not currently bound to external Claude")
        if (
            binding.get("model") != request["model"]
            or binding.get("reasoning_effort") != request["reasoning_effort"]
            or _tool_profile(node) != request["tool_profile"]
        ):
            raise BridgeError(f"Wave node {node_id} runtime policy does not match the request")

        bound_worker_id = state["bound_worker_id"]
        if request_node["node_kind"] == "mission":
            if node.get("kind") != "mission" or node.get("ref") != request_node["mission_id"]:
                raise BridgeError(f"Wave mission node {node_id} does not match the PLAN mission")
            mission_id = request_node["mission_id"]
            mission_state = run["mission_states"][mission_id]
            workers = [
                worker
                for worker in run["workers"]
                if worker.get("worker_id") == bound_worker_id
                and worker.get("mission_id") == mission_id
            ]
            if len(workers) != 1:
                raise BridgeError(f"Wave mission node {node_id} has no unique allocated worker")
            worker = workers[0]
            expected_mission = {
                "lease_id": request_node["lease_id"],
                "lease_plan_revision": plan["revision"],
                "lease_plan_digest_sha256": digest,
                "worker_id": bound_worker_id,
                "base_sha": request["batch_base_sha"],
            }
            if any(mission_state.get(key) != value for key, value in expected_mission.items()):
                raise BridgeError(f"Wave mission node {node_id} does not match its current lease")
            if mission_state.get("phase") not in {"leased", "worker_running"}:
                raise BridgeError(f"Wave mission node {node_id} is not launchable")
            expected_worker = {
                "lease_id": request_node["lease_id"],
                "plan_revision": plan["revision"],
                "plan_digest_sha256": digest,
                "batch_base_sha": request["batch_base_sha"],
                "worker_runtime": "subagent",
                "workspace_mode": "parent_managed_worktree",
                "completion_channel": "agent_result",
                "worktree_path": request_node["worktree_path"],
                "branch_ref": request_node["branch_ref"],
            }
            if any(worker.get(key) != value for key, value in expected_worker.items()):
                raise BridgeError(f"Wave mission node {node_id} worker binding is stale")
            if worker.get("phase") not in {"leased", "worker_running"}:
                raise BridgeError(f"Wave mission node {node_id} worker is not launchable")
            if worker.get("runtime_binding") != binding:
                raise BridgeError(f"Wave mission node {node_id} runtime binding is stale")
            _require_authorizations(
                run,
                node,
                binding,
                [mission_id],
                worker_id=bound_worker_id,
                worktree_path=request_node["worktree_path"],
                branch_ref=request_node["branch_ref"],
            )
            _validate_checkout(
                Path(request_node["worktree_path"]),
                expected_sha=request["batch_base_sha"],
                repository_path=repository_path,
                expected_branch=request_node["branch_ref"],
            )
            continue

        if node.get("kind") != "verifier" or node.get("review") is None:
            raise BridgeError(f"Wave review node {node_id} does not match a PLAN review")
        review = node["review"]
        expected_review = {
            "review_id": node["ref"],
            "review_type": review["type"],
            "review_scope": review["scope"],
            "required_evidence": review["required_evidence"],
        }
        if any(request_node.get(key) != value for key, value in expected_review.items()):
            raise BridgeError(f"Wave review node {node_id} does not match the PLAN review contract")
        review_workers = [
            worker
            for worker in run["review_workers"]
            if worker.get("worker_id") == bound_worker_id
            and worker.get("node_id") == node_id
            and worker.get("attempt_id") == attempt_id
        ]
        if len(review_workers) != 1:
            raise BridgeError(f"Wave review node {node_id} has no unique allocated review worker")
        worker = review_workers[0]
        expected_worker = {
            "plan_revision": plan["revision"],
            "plan_digest_sha256": digest,
            "graph_revision": request["graph_revision"],
            "reviewed_sha": request_node["reviewed_sha"],
            "review_path": request_node["review_path"],
            "worker_runtime": "subagent",
            "completion_channel": "agent_result",
        }
        if any(worker.get(key) != value for key, value in expected_worker.items()):
            raise BridgeError(f"Wave review node {node_id} worker binding is stale")
        if worker.get("phase") not in {"leased", "worker_running"}:
            raise BridgeError(f"Wave review node {node_id} worker is not launchable")
        if worker.get("runtime_binding") != binding:
            raise BridgeError(f"Wave review node {node_id} runtime binding is stale")
        mission_ids = review["mission_ids"]
        _require_authorizations(
            run,
            node,
            binding,
            mission_ids,
            worker_id=bound_worker_id,
        )
        _validate_checkout(
            Path(request_node["review_path"]),
            expected_sha=request_node["reviewed_sha"],
            repository_path=repository_path,
        )


def run_wave(
    *,
    claude: str,
    script: Path,
    plan_path: Path,
    run_path: Path,
    request_path: Path,
    cwd: Path,
    timeout: int,
    max_budget_usd: float,
    model: str | None = None,
) -> dict[str, Any]:
    request = _load_wave_request(request_path)
    requested_model = request["model"]
    if model is not None and model != requested_model:
        raise BridgeError("CLI model override must match the PLAN-selected wave model")
    plan = load_plan(plan_path)
    run = load_run(run_path)
    _validate_current_wave_binding(request, plan, run)
    command = _resolve_claude(claude)
    if not script.is_file():
        raise BridgeError(f"Graph workflow is missing: {script}")
    workflow_script_path = script.resolve()
    workflow_script_sha256 = hashlib.sha256(workflow_script_path.read_bytes()).hexdigest()
    version = _claude_version(command, timeout)
    workflow_args = {
        key: value
        for key, value in request.items()
        if key not in {"allowed_tools", "permission_mode", "model", "reasoning_effort"}
    }
    prompt = (
        "Use the Workflow tool exactly once. Do not use any other tool. "
        f"Set scriptPath to {workflow_script_path} and args to this exact JSON object: {_compact(workflow_args)}. "
        "Pass args as an actual object, not as a JSON-encoded string. "
        f"The accepted tool profile is {request['tool_profile']}; do not widen its tool allowlist. "
        "Do not change the arguments. Read the real taskId, runId, scriptPath, and optional error from the Workflow tool result; do not invent them. "
        "A successful Workflow call must provide a real non-empty runId. "
        "Return {\"workflow_task_id\": <taskId>, \"workflow_run_id\": <runId>, "
        "\"workflow_script_path\": <scriptPath>, \"workflow_error\": <error or null>, "
        "\"results\": <workflow result, or [] when error is non-null>} as the final structured output."
    )
    result, workflow_runtime, tool_input = _invoke(
        _build_command(
            command=command,
            prompt=prompt,
            schema=None,
            allowed_tools=request["allowed_tools"],
            permission_mode=request["permission_mode"],
            max_budget_usd=max_budget_usd,
            model=requested_model,
            reasoning_effort=request["reasoning_effort"],
            output_format="stream-json",
            verbose=True,
        ),
        cwd=cwd,
        timeout=timeout,
    )
    if not isinstance(result, dict):
        raise BridgeError("Claude graph wave did not return a structured wrapper")
    if set(result) != set(WAVE_SCHEMA["required"]):
        raise BridgeError("Claude graph wave returned missing or unknown wrapper fields")
    _validate_workflow_evidence(
        result,
        workflow_runtime,
        tool_input,
        workflow_script_path=workflow_script_path,
        workflow_args=workflow_args,
    )
    workflow_run_id = result.get("workflow_run_id")
    if not isinstance(workflow_run_id, str) or not workflow_run_id.strip():
        raise BridgeError("Claude Workflow did not return a real non-empty workflow_run_id")
    if result.get("workflow_error"):
        raise BridgeError(f"Claude Workflow launch failed: {result['workflow_error']}")
    returned_script_path = result.get("workflow_script_path")
    if not isinstance(returned_script_path, str) or not returned_script_path.strip():
        raise BridgeError("Claude Workflow did not return a workflow_script_path")
    if Path(returned_script_path).resolve() != workflow_script_path:
        raise BridgeError("Claude Workflow used a different workflow_script_path")
    if hashlib.sha256(workflow_script_path.read_bytes()).hexdigest() != workflow_script_sha256:
        raise BridgeError("Graph workflow changed during Claude execution")
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
            "workflow_script_path": str(workflow_script_path),
            "workflow_script_sha256": workflow_script_sha256,
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
    wave_parser.add_argument("--plan", required=True, type=Path)
    wave_parser.add_argument("--run", required=True, type=Path)
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
                plan_path=args.plan,
                run_path=args.run,
                request_path=args.request,
                cwd=args.cwd,
                timeout=args.timeout,
                max_budget_usd=args.max_budget_usd,
                model=args.model,
            )
    except (BridgeError, ManifestError, OSError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "ERROR", "errors": [str(exc)]}, sort_keys=True, indent=2))
        return 2
    print(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
