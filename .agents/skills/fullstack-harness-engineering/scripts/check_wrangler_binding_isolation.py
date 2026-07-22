#!/usr/bin/env python3
"""Check that a scaffolded wrangler.jsonc keeps development and production bindings isolated.

Per Cloudflare's Wrangler docs (https://developers.cloudflare.com/workers/wrangler/environments/),
bindings are non-inheritable: a named environment's effective binding set is exactly what is
declared under its own `env.<name>` section, never merged in from the top level. This script
resolves the effective `development` and `production` binding sets accordingly and flags:

- the same resource-identity value (D1 database_id, KV id, R2 bucket_name, queue name, or a
  Durable Object class_name+script_name pair) reused under both environments, and
- an identity-bearing binding declared only at the top level with no override in either named
  environment section, since that value will never actually be isolated between the two
  environments and is the common scaffolding mistake this check exists to catch.

`vars` and secrets are intentionally out of scope: an equal plain value there is often legitimate
(for example a shared application name) and is not a resource-identity collision.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def _strip_jsonc(text: str) -> str:
    """Remove // and /* */ comments and trailing commas, without touching string contents."""

    out: list[str] = []
    i = 0
    n = len(text)
    in_string = False
    while i < n:
        c = text[i]
        if in_string:
            out.append(c)
            if c == "\\" and i + 1 < n:
                out.append(text[i + 1])
                i += 2
                continue
            if c == '"':
                in_string = False
            i += 1
            continue
        if c == '"':
            in_string = True
            out.append(c)
            i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "/":
            i += 2
            while i < n and text[i] not in "\r\n":
                i += 1
            continue
        if c == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
            continue
        if c == ",":
            j = i + 1
            while j < n and text[j] in " \t\r\n":
                j += 1
            if j < n and text[j] in "}]":
                i += 1
                continue
        out.append(c)
        i += 1
    return "".join(out)


def load_wrangler_config(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        raw = handle.read()
    stripped = _strip_jsonc(raw)
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path} is not valid JSONC: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object at the root")
    return data


def _env_section(config: dict[str, Any], env_name: str) -> dict[str, Any]:
    env = config.get("env")
    if not isinstance(env, dict):
        return {}
    section = env.get(env_name)
    return section if isinstance(section, dict) else {}


def _get_nested(container: Any, path: tuple[str, ...]) -> list[Any]:
    current = container
    for key in path:
        if not isinstance(current, dict):
            return []
        current = current.get(key)
    return current if isinstance(current, list) else []


def _collect_by_name(
    items: list[Any], identity_field: str, name_field: str
) -> dict[str, str]:
    collected: dict[str, str] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        identity_value = item.get(identity_field)
        name_value = item.get(name_field)
        if not isinstance(identity_value, str) or not identity_value:
            continue
        if not isinstance(name_value, str) or not name_value:
            continue
        collected[name_value] = identity_value
    return collected


SIMPLE_BINDING_TYPES = (
    {"label": "d1_databases", "path": ("d1_databases",), "identity_field": "database_id", "name_field": "binding"},
    {"label": "kv_namespaces", "path": ("kv_namespaces",), "identity_field": "id", "name_field": "binding"},
    {"label": "r2_buckets", "path": ("r2_buckets",), "identity_field": "bucket_name", "name_field": "binding"},
    {"label": "queues.producers", "path": ("queues", "producers"), "identity_field": "queue", "name_field": "binding"},
)


def _check_simple_binding_type(
    config: dict[str, Any],
    *,
    label: str,
    path: tuple[str, ...],
    identity_field: str,
    name_field: str,
    errors: list[str],
) -> None:
    top_map = _collect_by_name(_get_nested(config, path), identity_field, name_field)
    dev_map = _collect_by_name(_get_nested(_env_section(config, "development"), path), identity_field, name_field)
    prod_map = _collect_by_name(_get_nested(_env_section(config, "production"), path), identity_field, name_field)

    for name in sorted(set(dev_map) & set(prod_map)):
        if dev_map[name] == prod_map[name]:
            errors.append(
                f"{label} binding '{name}' shares {identity_field} '{dev_map[name]}' "
                "between development and production — these must be isolated per-environment"
            )

    resolved_names = set(dev_map) | set(prod_map)
    for name in sorted(set(top_map) - resolved_names):
        errors.append(
            f"{label} binding '{name}' is declared only at the top level with {identity_field} "
            f"'{top_map[name]}' and has no development or production override — Wrangler bindings "
            "are non-inheritable, so it will not be isolated between environments"
        )


def _string_values_by_field(items: list[Any], field: str) -> set[str]:
    values: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        value = item.get(field)
        if isinstance(value, str) and value:
            values.add(value)
    return values


def _check_queue_consumers(config: dict[str, Any], errors: list[str]) -> None:
    path = ("queues", "consumers")
    top_queues = _string_values_by_field(_get_nested(config, path), "queue")
    dev_queues = _string_values_by_field(_get_nested(_env_section(config, "development"), path), "queue")
    prod_queues = _string_values_by_field(_get_nested(_env_section(config, "production"), path), "queue")

    for queue_name in sorted(dev_queues & prod_queues):
        errors.append(
            f"queues.consumers references queue '{queue_name}' in both development and production "
            "— consumers must be isolated per-environment"
        )

    for queue_name in sorted(top_queues - dev_queues - prod_queues):
        errors.append(
            f"queues.consumers queue '{queue_name}' is declared only at the top level and has no "
            "development or production override — Wrangler bindings are non-inheritable, so it will "
            "not be isolated between environments"
        )


def _durable_object_entries(items: list[Any]) -> dict[str, tuple[str, str | None]]:
    entries: dict[str, tuple[str, str | None]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        class_name = item.get("class_name")
        script_name = item.get("script_name")
        if not isinstance(name, str) or not name:
            continue
        if not isinstance(class_name, str) or not class_name:
            continue
        resolved_script = script_name if isinstance(script_name, str) and script_name else None
        entries[name] = (class_name, resolved_script)
    return entries


def _check_durable_objects(config: dict[str, Any], errors: list[str]) -> None:
    path = ("durable_objects", "bindings")
    top_map = _durable_object_entries(_get_nested(config, path))
    dev_map = _durable_object_entries(_get_nested(_env_section(config, "development"), path))
    prod_map = _durable_object_entries(_get_nested(_env_section(config, "production"), path))

    for name in sorted(set(dev_map) & set(prod_map)):
        dev_class, dev_script = dev_map[name]
        prod_class, prod_script = prod_map[name]
        if dev_script and prod_script and dev_class == prod_class and dev_script == prod_script:
            errors.append(
                f"durable_objects binding '{name}' shares class_name '{dev_class}' and script_name "
                f"'{dev_script}' between development and production — these must be isolated "
                "per-environment"
            )

    resolved_names = set(dev_map) | set(prod_map)
    for name in sorted(set(top_map) - resolved_names):
        class_name, script_name = top_map[name]
        if script_name:
            errors.append(
                f"durable_objects binding '{name}' is declared only at the top level with class_name "
                f"'{class_name}' and script_name '{script_name}' and has no development or production "
                "override — Wrangler bindings are non-inheritable, so it will not be isolated between "
                "environments"
            )


def check_binding_isolation(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for descriptor in SIMPLE_BINDING_TYPES:
        _check_simple_binding_type(config, errors=errors, **descriptor)
    _check_durable_objects(config, errors)
    _check_queue_consumers(config, errors)
    return sorted(set(errors))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wrangler-config", required=True, help="Path to a repository's wrangler.jsonc")
    args = parser.parse_args(argv)

    try:
        config = load_wrangler_config(args.wrangler_config)
    except (OSError, ValueError) as exc:
        print(str(exc))
        return 2

    errors = check_binding_isolation(config)
    for error in errors:
        print(error)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
