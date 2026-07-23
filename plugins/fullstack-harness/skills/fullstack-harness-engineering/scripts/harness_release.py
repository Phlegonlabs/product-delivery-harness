#!/usr/bin/env python3
"""Cloudflare/generic release-contract and deployment-state validation."""

from __future__ import annotations

from typing import Any

from harness_authorization import authorization_covers
from harness_core import (
    _add,
    _keys,
    _nonempty_string,
    _optional_sha,
    _optional_string,
    _strings,
    _validate_verifier,
    is_full_sha,
    validate_scope_claim,
)
from harness_schema import DEPLOYMENT_PROVIDERS


def _validate_release(errors: list[str], value: Any) -> None:
    path = "plan.release"
    if not _keys(errors, path, value, {"provider", "targets"}):
        return
    provider = value["provider"]
    if provider not in DEPLOYMENT_PROVIDERS:
        _add(errors, f"{path}.provider", f"must be one of {sorted(DEPLOYMENT_PROVIDERS)}")
        return
    if provider == "cloudflare":
        _validate_cloudflare_release_targets(errors, path, value["targets"])
    else:
        _validate_generic_release_targets(errors, path, value["targets"])


def _validate_generic_release_targets(errors: list[str], path: str, targets_value: Any) -> None:
    if not isinstance(targets_value, list) or not targets_value:
        _add(errors, f"{path}.targets", "must be a non-empty list")
        return

    target_keys = {
        "id",
        "data_mode",
        "prerequisites",
        "migration_command",
        "deploy_command",
        "smoke_verifiers",
    }
    seen_ids: set[str] = set()
    seen_data_modes: set[str] = set()
    for index, target in enumerate(targets_value):
        target_path = f"{path}.targets[{index}]"
        if not _keys(errors, target_path, target, target_keys):
            continue
        target_id = target["id"]
        if not _nonempty_string(target_id):
            _add(errors, f"{target_path}.id", "must be a non-empty string")
        elif target_id in seen_ids:
            _add(errors, f"{target_path}.id", "must be unique")
        else:
            seen_ids.add(target_id)
        data_mode = target["data_mode"]
        if data_mode not in ("isolated_non_production", "production"):
            _add(
                errors,
                f"{target_path}.data_mode",
                "must be isolated_non_production or production",
            )
        else:
            seen_data_modes.add(data_mode)
        _strings(
            errors,
            f"{target_path}.prerequisites",
            target["prerequisites"],
            nonempty=True,
        )
        if target["migration_command"] is not None:
            _validate_verifier(
                errors,
                f"{target_path}.migration_command",
                target["migration_command"],
                cache_allowed=False,
            )
        _validate_verifier(
            errors,
            f"{target_path}.deploy_command",
            target["deploy_command"],
            cache_allowed=False,
        )
        smoke = target["smoke_verifiers"]
        if not isinstance(smoke, list) or not smoke:
            _add(errors, f"{target_path}.smoke_verifiers", "must be a non-empty list")
        else:
            for verifier_index, verifier in enumerate(smoke):
                _validate_verifier(
                    errors,
                    f"{target_path}.smoke_verifiers[{verifier_index}]",
                    verifier,
                    cache_allowed=False,
                )

    missing_data_modes = {"isolated_non_production", "production"} - seen_data_modes
    if missing_data_modes:
        _add(
            errors,
            f"{path}.targets",
            "must include at least one isolated_non_production and one production data_mode",
        )


def _validate_cloudflare_release_targets(errors: list[str], path: str, targets_value: Any) -> None:
    if not isinstance(targets_value, list) or len(targets_value) != 2:
        _add(errors, f"{path}.targets", "must contain development and production")
        return

    targets: dict[str, dict[str, Any]] = {}
    target_keys = {
        "id",
        "source",
        "worker_name",
        "wrangler_config_path",
        "wrangler_environment",
        "data_mode",
        "payment_mode",
        "auth_mode",
        "prerequisites",
        "migration_command",
        "deploy_command",
        "smoke_verifiers",
    }
    for index, target in enumerate(targets_value):
        target_path = f"{path}.targets[{index}]"
        if not _keys(errors, target_path, target, target_keys):
            continue
        target_id = target["id"]
        if not isinstance(target_id, str) or target_id not in (
            "development",
            "production",
        ):
            _add(errors, f"{target_path}.id", "must be development or production")
            continue
        if target_id in targets:
            _add(errors, f"{target_path}.id", "must be unique")
        targets[target_id] = target
        for key in ("worker_name", "wrangler_config_path", "wrangler_environment"):
            if not _nonempty_string(target[key]):
                _add(errors, f"{target_path}.{key}", "must be a non-empty string")
        config_path = target["wrangler_config_path"]
        config_problem = validate_scope_claim(config_path)
        if config_problem or (isinstance(config_path, str) and config_path.endswith("/**")):
            _add(
                errors,
                f"{target_path}.wrangler_config_path",
                config_problem or "must be an exact repository-relative path",
            )
        if target["wrangler_environment"] != target_id:
            _add(errors, f"{target_path}.wrangler_environment", "must match id")
        _strings(
            errors,
            f"{target_path}.prerequisites",
            target["prerequisites"],
            nonempty=True,
        )
        if target["migration_command"] is not None:
            _validate_verifier(
                errors,
                f"{target_path}.migration_command",
                target["migration_command"],
                cache_allowed=False,
            )
        _validate_verifier(
            errors,
            f"{target_path}.deploy_command",
            target["deploy_command"],
            cache_allowed=False,
        )
        smoke = target["smoke_verifiers"]
        if not isinstance(smoke, list) or not smoke:
            _add(errors, f"{target_path}.smoke_verifiers", "must be a non-empty list")
        else:
            for verifier_index, verifier in enumerate(smoke):
                _validate_verifier(
                    errors,
                    f"{target_path}.smoke_verifiers[{verifier_index}]",
                    verifier,
                    cache_allowed=False,
                )

    if set(targets) != {"development", "production"}:
        _add(errors, f"{path}.targets", "must contain development and production")
        return
    development = targets["development"]
    production = targets["production"]
    if development["source"] not in ("pr_head", "integration_head"):
        _add(
            errors,
            f"{path}.targets.development.source",
            "must equal pr_head or integration_head",
        )
    if production["source"] != "merged_main":
        _add(errors, f"{path}.targets.production.source", "must equal merged_main")
    if development["data_mode"] != "isolated_non_production":
        _add(
            errors,
            f"{path}.targets.development.data_mode",
            "must equal isolated_non_production",
        )
    if production["data_mode"] != "production":
        _add(errors, f"{path}.targets.production.data_mode", "must equal production")
    if development["payment_mode"] not in ("sandbox", "not_applicable"):
        _add(
            errors,
            f"{path}.targets.development.payment_mode",
            "must be sandbox or not_applicable",
        )
    if production["payment_mode"] not in ("live", "not_applicable"):
        _add(
            errors,
            f"{path}.targets.production.payment_mode",
            "must be live or not_applicable",
        )
    if development["auth_mode"] not in ("development", "not_applicable"):
        _add(
            errors,
            f"{path}.targets.development.auth_mode",
            "must be development or not_applicable",
        )
    if production["auth_mode"] not in ("production", "not_applicable"):
        _add(
            errors,
            f"{path}.targets.production.auth_mode",
            "must be production or not_applicable",
        )
    if development["worker_name"] == production["worker_name"]:
        _add(errors, f"{path}.targets", "development and production worker_name must differ")
    development_prerequisites = development["prerequisites"]
    if not isinstance(development_prerequisites, list) or (
        "current_head_ci" not in development_prerequisites
    ):
        _add(
            errors,
            f"{path}.targets.development.prerequisites",
            "must include current_head_ci",
        )
    production_prerequisites = production["prerequisites"]
    for prerequisite in ("development_pass", "merged_main"):
        if not isinstance(production_prerequisites, list) or (
            prerequisite not in production_prerequisites
        ):
            _add(
                errors,
                f"{path}.targets.production.prerequisites",
                f"must include {prerequisite}",
            )


def _validate_deployments(
    errors: list[str], value: Any, run: dict[str, Any], plan: dict[str, Any]
) -> None:
    path = "run.deployments"
    if not _keys(errors, path, value, {"provider", "development", "production"}):
        return
    provider = value["provider"]
    if provider not in DEPLOYMENT_PROVIDERS:
        _add(errors, f"{path}.provider", f"must be one of {sorted(DEPLOYMENT_PROVIDERS)}")

    release = plan.get("release")
    release_targets: dict[str, dict[str, Any]] = {}
    if plan.get("schema_version") not in {3, 4} or not isinstance(release, dict):
        _add(errors, path, "deployment state requires a PLAN release contract")
    elif release.get("provider") != value["provider"]:
        _add(errors, f"{path}.provider", "must match PLAN release provider")
    elif isinstance(release.get("targets"), list):
        release_targets = {
            target["id"]: target
            for target in release["targets"]
            if isinstance(target, dict)
            and target.get("id") in ("development", "production")
        }

    status_values = ("not_started", "pending", "PASS", "FAIL", "BLOCKED")
    migration_values = status_values + ("not_required",)
    target_keys = {
        "status",
        "source_sha",
        "worker_name",
        "url",
        "version_id",
        "migration_status",
        "verification_status",
        "rollback_version",
        "evidence",
    }
    targets: dict[str, dict[str, Any]] = {}
    for target_id in ("development", "production"):
        target = value[target_id]
        target_path = f"{path}.{target_id}"
        if not _keys(
            errors,
            target_path,
            target,
            target_keys,
            {
                "authorized_head_sha",
                "migration_classification",
                "destructive_migration_confirmed_sha",
            },
        ):
            continue
        targets[target_id] = target
        if target["status"] not in status_values:
            _add(errors, f"{target_path}.status", "has an unsupported value")
        if target["migration_status"] not in migration_values:
            _add(errors, f"{target_path}.migration_status", "has an unsupported value")
        if target["verification_status"] not in status_values:
            _add(errors, f"{target_path}.verification_status", "has an unsupported value")
        _optional_sha(errors, f"{target_path}.source_sha", target["source_sha"])
        _optional_sha(
            errors,
            f"{target_path}.authorized_head_sha",
            target.get("authorized_head_sha"),
        )
        if (
            target_id == "production"
            and target["status"] != "not_started"
            and target.get("authorized_head_sha") is None
        ):
            _add(
                errors,
                target_path,
                "production deployment past not_started requires authorized_head_sha",
            )
        migration_classification = target.get("migration_classification")
        if migration_classification not in (None, "additive", "destructive"):
            _add(
                errors,
                f"{target_path}.migration_classification",
                "must be null, additive, or destructive",
            )
        destructive_migration_confirmed_sha = target.get("destructive_migration_confirmed_sha")
        _optional_sha(
            errors,
            f"{target_path}.destructive_migration_confirmed_sha",
            destructive_migration_confirmed_sha,
        )
        if target_id == "production":
            if target["migration_status"] not in ("not_started", "not_required") and (
                migration_classification is None
            ):
                _add(
                    errors,
                    target_path,
                    "production migration past not_started/not_required requires migration_classification",
                )
            if (
                migration_classification == "destructive"
                and destructive_migration_confirmed_sha is None
            ):
                _add(
                    errors,
                    target_path,
                    "destructive migration_classification requires destructive_migration_confirmed_sha",
                )
            if (
                migration_classification != "destructive"
                and destructive_migration_confirmed_sha is not None
            ):
                _add(
                    errors,
                    target_path,
                    "destructive_migration_confirmed_sha requires destructive migration_classification",
                )
        for key in ("worker_name", "url", "version_id", "rollback_version"):
            _optional_string(errors, f"{target_path}.{key}", target[key])
        declared_target = release_targets.get(target_id)
        if (
            target["worker_name"] is not None
            and declared_target is not None
            and target["worker_name"] != declared_target.get("worker_name")
        ):
            _add(errors, f"{target_path}.worker_name", "must match PLAN release target")
        evidence = _strings(errors, f"{target_path}.evidence", target["evidence"])
        if target["status"] == "not_started":
            if any(
                target[key] is not None
                for key in (
                    "source_sha",
                    "worker_name",
                    "url",
                    "version_id",
                    "rollback_version",
                )
            ):
                _add(errors, target_path, "not_started deployment must not record release data")
            if target["migration_status"] != "not_started":
                _add(errors, target_path, "not_started deployment requires migration_status not_started")
            if target["verification_status"] != "not_started":
                _add(errors, target_path, "not_started deployment requires verification_status not_started")
            if evidence:
                _add(errors, target_path, "not_started deployment must not record evidence")
        if target["status"] == "PASS":
            if provider == "cloudflare":
                if any(
                    not _nonempty_string(target[key])
                    for key in ("worker_name", "url", "version_id")
                ) or not is_full_sha(target["source_sha"]):
                    _add(errors, target_path, "PASS requires source SHA, worker, URL, and version ID")
            elif provider in DEPLOYMENT_PROVIDERS and not is_full_sha(target["source_sha"]):
                _add(errors, target_path, "PASS requires a source SHA")
            if target["migration_status"] not in ("PASS", "not_required"):
                _add(errors, target_path, "PASS requires migration PASS or not_required")
            if target["verification_status"] != "PASS":
                _add(errors, target_path, "PASS requires verification_status PASS")
            if not evidence:
                _add(errors, target_path, "PASS requires retained evidence")
            mission_states = run.get("mission_states", {})
            mission_ids = list(mission_states) if isinstance(mission_states, dict) else []
            if not mission_ids or any(
                not authorization_covers(
                    run,
                    "deploy",
                    mission_id,
                    f"environment:{target_id}",
                    preserve_completed_run_expiry=True,
                )
                for mission_id in mission_ids
            ):
                _add(
                    errors,
                    target_path,
                    f"PASS requires deploy authorization for environment:{target_id}",
                )

    landing = run.get("landing")
    development = targets.get("development")
    production = targets.get("production")
    declared_development = release_targets.get("development")
    development_source = (
        declared_development.get("source") if isinstance(declared_development, dict) else None
    )
    if development is not None and development["status"] == "PASS":
        if development_source == "integration_head":
            integration = run.get("integration")
            integration_head_sha = (
                integration.get("integration_head_sha") if isinstance(integration, dict) else None
            )
            if development["source_sha"] != integration_head_sha:
                _add(
                    errors,
                    f"{path}.development",
                    "PASS must bind to the current integration branch head (run.integration.integration_head_sha)",
                )
        elif isinstance(landing, dict):
            if (
                landing.get("pr_state") not in ("draft", "open", "merged")
                or development["source_sha"] != landing.get("pr_head_sha")
                or landing.get("checks_status") != "PASS"
                or landing.get("checks_head_sha") != development["source_sha"]
            ):
                _add(
                    errors,
                    f"{path}.development",
                    "PASS must bind to the current PR head after current-head CI passes",
                )
    if isinstance(landing, dict) and production is not None and production["status"] == "PASS":
        if development is None or development.get("status") != "PASS":
            _add(errors, f"{path}.production", "PASS requires development PASS first")
        if (
            landing.get("pr_state") != "merged"
            or landing.get("merge_status") != "merged"
            or production["source_sha"] != landing.get("merged_sha")
        ):
            _add(
                errors,
                f"{path}.production",
                "PASS must bind to the merged main SHA",
            )
    if run.get("status") == "complete" and (
        development is None
        or production is None
        or development.get("status") != "PASS"
        or production.get("status") != "PASS"
    ):
        _add(errors, path, "complete run requires development and production PASS")
