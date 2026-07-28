#!/usr/bin/env python3
"""Cloudflare/generic release-contract and deployment-state validation."""

from __future__ import annotations

from typing import Any

from harness_authorization import (
    authorization_covers,
    is_external_human_merge,
    is_legacy_completed_external_merge,
)
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
from harness_schema import (
    DEPLOYMENT_PROVIDERS,
    MIGRATION_CLASSIFICATIONS,
    RELEASE_DATA_MODES,
    RELEASE_SOURCES,
    RELEASE_STAGES,
    RELEASE_TRIGGERS,
    SHA256_RE,
)


def _validate_smoke_verifiers(errors: list[str], target_path: str, smoke: Any) -> None:
    if not isinstance(smoke, list) or not smoke:
        _add(errors, f"{target_path}.smoke_verifiers", "must be a non-empty list")
        return
    for index, verifier in enumerate(smoke):
        _validate_verifier(
            errors,
            f"{target_path}.smoke_verifiers[{index}]",
            verifier,
            cache_allowed=False,
        )


def _validate_release(
    errors: list[str], value: Any, *, schema_version: int | None = None
) -> None:
    path = "plan.release"
    if not _keys(errors, path, value, {"provider", "targets"}):
        return
    provider = value["provider"]
    if provider not in DEPLOYMENT_PROVIDERS:
        _add(errors, f"{path}.provider", f"must be one of {sorted(DEPLOYMENT_PROVIDERS)}")
        return
    if schema_version == 5:
        _validate_release_targets_v5(errors, path, value["targets"])
    elif provider == "cloudflare":
        _validate_cloudflare_release_targets(errors, path, value["targets"])
    else:
        _validate_generic_release_targets(errors, path, value["targets"])


def _validate_release_targets_v5(
    errors: list[str], path: str, targets_value: Any
) -> None:
    if not isinstance(targets_value, list) or not targets_value:
        _add(errors, f"{path}.targets", "must be a non-empty list")
        return

    target_keys = {
        "id",
        "stage",
        "source",
        "artifact_kind",
        "requires_signing",
        "channel",
        "data_mode",
        "trigger",
        "migration_classification",
        "commands",
        "prerequisites",
        "smoke_verifiers",
    }
    command_keys = {"build", "migrate", "publish"}
    seen_ids: set[str] = set()
    seen_stages: set[str] = set()
    for index, target in enumerate(targets_value):
        target_path = f"{path}.targets[{index}]"
        if not _keys(errors, target_path, target, target_keys):
            continue
        target_id = target["id"]
        if not _nonempty_string(target_id):
            _add(errors, f"{target_path}.id", "must be a non-empty stable target ID")
        elif target_id in seen_ids:
            _add(errors, f"{target_path}.id", "must be unique")
        else:
            seen_ids.add(target_id)
        stage = target["stage"]
        if stage not in RELEASE_STAGES:
            _add(errors, f"{target_path}.stage", "must be development or production")
        else:
            seen_stages.add(stage)
        if target["source"] is not None and target["source"] not in RELEASE_SOURCES:
            _add(errors, f"{target_path}.source", "must be null or a supported source")
        if target["artifact_kind"] is not None and not _nonempty_string(target["artifact_kind"]):
            _add(errors, f"{target_path}.artifact_kind", "must be null or a non-empty string")
        if target["requires_signing"] is not None and not isinstance(target["requires_signing"], bool):
            _add(errors, f"{target_path}.requires_signing", "must be null or boolean")
        if target["channel"] is not None and not _nonempty_string(target["channel"]):
            _add(errors, f"{target_path}.channel", "must be null or a non-empty exact channel")
        if target["data_mode"] not in RELEASE_DATA_MODES:
            _add(errors, f"{target_path}.data_mode", "has an unsupported value")
        if target["trigger"] is not None and target["trigger"] not in RELEASE_TRIGGERS:
            _add(errors, f"{target_path}.trigger", "must be null, manual, or merge")
        classification = target["migration_classification"]
        if classification not in MIGRATION_CLASSIFICATIONS:
            _add(
                errors,
                f"{target_path}.migration_classification",
                "must be null, not_applicable, additive, or destructive",
            )
        commands = target["commands"]
        if _keys(errors, f"{target_path}.commands", commands, command_keys):
            for command_name in command_keys:
                command = commands[command_name]
                if command is None:
                    if command_name == "migrate" and classification not in {
                        None,
                        "not_applicable",
                    }:
                        _add(
                            errors,
                            f"{target_path}.commands.migrate",
                            "is required for additive or destructive migration classification",
                        )
                    continue
                _validate_verifier(
                    errors,
                    f"{target_path}.commands.{command_name}",
                    command,
                    cache_allowed=False,
                )
            if target["trigger"] == "manual" and commands.get("publish") is None:
                _add(errors, f"{target_path}.commands.publish", "must not be null for manual trigger")
            if target["trigger"] == "merge" and commands.get("publish") is not None:
                _add(errors, f"{target_path}.commands.publish", "must be null for merge trigger")
        _strings(errors, f"{target_path}.prerequisites", target["prerequisites"], nonempty=True)
        _validate_smoke_verifiers(errors, target_path, target["smoke_verifiers"])
        if stage == "development":
            if target["source"] is not None and target["source"] not in {"pr_head", "integration_head"}:
                _add(errors, f"{target_path}.source", "development must use pr_head or integration_head")
            if target["data_mode"] != "isolated_non_production":
                _add(errors, f"{target_path}.data_mode", "development must use isolated_non_production")
        if stage == "production":
            if target["source"] is not None and target["source"] not in {
                "production_head",
                "merged_main",
            }:
                _add(
                    errors,
                    f"{target_path}.source",
                    "production must use production_head (or legacy merged_main)",
                )
            if target["data_mode"] != "production":
                _add(errors, f"{target_path}.data_mode", "production must use production")

    # The default branch model publishes one environment from `main`. A separate
    # preview or staging environment is optional, so only production is required.
    if "production" not in seen_stages:
        _add(errors, f"{path}.targets", "must include at least one production target")


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
        _validate_smoke_verifiers(errors, target_path, target["smoke_verifiers"])

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
        _validate_smoke_verifiers(errors, target_path, target["smoke_verifiers"])

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
    if development_source == "integration_head":
        integration_for_retention = run.get("integration")
        retention = (
            integration_for_retention.get("retention")
            if isinstance(integration_for_retention, dict)
            else None
        )
        if retention != "persistent":
            _add(
                errors,
                "run.integration.retention",
                "must be persistent when development release source is integration_head",
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


def _authorization_covers_release_head(
    run: dict[str, Any], action: str, mission_id: str, target_id: str, head_sha: Any
) -> bool:
    entry = run.get("authorizations", {}).get(action)
    if not isinstance(entry, dict) or entry.get("authorized_head_sha") != head_sha:
        return False
    return authorization_covers(
        run,
        action,
        mission_id,
        f"release:{target_id}",
        preserve_completed_run_expiry=True,
    )


def _validate_retained_evidence(
    errors: list[str], path: str, value: Any, extra_keys: set[str]
) -> bool:
    keys = {"subject", "retained_reference", "evidence_sha256"} | extra_keys
    if not _keys(errors, path, value, keys):
        return False
    if not _nonempty_string(value["subject"]):
        _add(errors, f"{path}.subject", "must identify the exact evidence subject")
    if not _nonempty_string(value["retained_reference"]):
        _add(errors, f"{path}.retained_reference", "must be a non-empty retained reference")
    digest = value["evidence_sha256"]
    if not isinstance(digest, str) or SHA256_RE.fullmatch(digest) is None:
        _add(errors, f"{path}.evidence_sha256", "must be a lowercase SHA-256 digest")
    return True


def _validate_targets(
    errors: list[str], value: Any, run: dict[str, Any], plan: dict[str, Any]
) -> None:
    path = "run.targets"
    release = plan.get("release")
    target_list = release.get("targets") if isinstance(release, dict) else None
    declared_targets = {
        target["id"]: target
        for target in (target_list or [])
        if isinstance(target, dict) and _nonempty_string(target.get("id"))
    }
    if not isinstance(value, dict):
        _add(errors, path, "must be an object keyed by PLAN release target ID")
        return
    if set(value) != set(declared_targets):
        _add(errors, path, "keys must exactly equal PLAN release target IDs")

    status_values = {"not_started", "pending", "PASS", "FAIL", "BLOCKED"}
    migration_values = status_values | {"not_required"}
    target_keys = {
        "status",
        "source_sha",
        "authorized_head_sha",
        "artifact",
        "channel",
        "promotion",
        "availability",
        "migration_status",
        "verification_status",
        "destructive_migration_confirmed_sha",
    }
    states: dict[str, dict[str, Any]] = {}
    for target_id, target in value.items():
        target_path = f"{path}.{target_id}"
        if not _keys(errors, target_path, target, target_keys):
            continue
        states[target_id] = target
        declared = declared_targets.get(target_id, {})
        if target["status"] not in status_values:
            _add(errors, f"{target_path}.status", "has an unsupported value")
        if target["migration_status"] not in migration_values:
            _add(errors, f"{target_path}.migration_status", "has an unsupported value")
        if target["verification_status"] not in status_values:
            _add(errors, f"{target_path}.verification_status", "has an unsupported value")
        _optional_sha(errors, f"{target_path}.source_sha", target["source_sha"])
        _optional_sha(errors, f"{target_path}.authorized_head_sha", target["authorized_head_sha"])
        _optional_sha(
            errors,
            f"{target_path}.destructive_migration_confirmed_sha",
            target["destructive_migration_confirmed_sha"],
        )
        if target["status"] == "not_started":
            for key in (
                "source_sha",
                "authorized_head_sha",
                "artifact",
                "channel",
                "promotion",
                "availability",
                "destructive_migration_confirmed_sha",
            ):
                if target[key] is not None:
                    _add(errors, target_path, "not_started target must not record release evidence")
                    break
            if target["migration_status"] != "not_started" or target["verification_status"] != "not_started":
                _add(errors, target_path, "not_started target requires not_started migration and verification")
        elif target["authorized_head_sha"] is None:
            _add(errors, f"{target_path}.authorized_head_sha", "is required after target execution starts")

        if target["artifact"] is not None and _validate_retained_evidence(
            errors,
            f"{target_path}.artifact",
            target["artifact"],
            {"build_id", "version", "signing_status"},
        ):
            for key in ("build_id", "version"):
                if not _nonempty_string(target["artifact"][key]):
                    _add(errors, f"{target_path}.artifact.{key}", "must be a non-empty string")
            if target["artifact"]["signing_status"] not in {"not_required", "PASS", "FAIL"}:
                _add(errors, f"{target_path}.artifact.signing_status", "has an unsupported value")
        if target["channel"] is not None and _validate_retained_evidence(
            errors, f"{target_path}.channel", target["channel"], {"name"}
        ):
            if target["channel"]["name"] != declared.get("channel"):
                _add(errors, f"{target_path}.channel.name", "must match PLAN release channel")
        for evidence_key in ("promotion", "availability"):
            evidence = target[evidence_key]
            if evidence is not None and _validate_retained_evidence(
                errors, f"{target_path}.{evidence_key}", evidence, {"status"}
            ) and evidence["status"] != "PASS":
                _add(errors, f"{target_path}.{evidence_key}.status", "must equal PASS")

        classification = declared.get("migration_classification")
        confirmed_sha = target["destructive_migration_confirmed_sha"]
        if target["status"] != "not_started" and classification is None:
            _add(
                errors,
                f"{target_path}.migration_status",
                "target execution cannot start with unresolved migration_classification",
            )
        if classification == "destructive":
            if confirmed_sha != target["authorized_head_sha"]:
                _add(
                    errors,
                    f"{target_path}.destructive_migration_confirmed_sha",
                    "must equal the current authorized target head",
                )
        elif confirmed_sha is not None:
            _add(
                errors,
                f"{target_path}.destructive_migration_confirmed_sha",
                "requires destructive PLAN migration classification",
            )

        source = declared.get("source")
        landing = run.get("landing") if isinstance(run.get("landing"), dict) else {}
        integration = run.get("integration") if isinstance(run.get("integration"), dict) else {}
        expected_source = {
            "pr_head": landing.get("pr_head_sha"),
            "integration_head": integration.get("integration_head_sha"),
            "production_head": landing.get("merged_sha"),
            "merged_main": landing.get("merged_sha"),
        }.get(source)
        trigger = declared.get("trigger")
        triggering_candidate_head = (
            landing.get("pr_head_sha")
            if is_full_sha(landing.get("pr_head_sha"))
            else integration.get("integration_head_sha")
        )
        expected_authorized_head = (
            triggering_candidate_head if trigger == "merge" else target["source_sha"]
        )
        if target["status"] != "not_started" and (
            target["authorized_head_sha"] != expected_authorized_head
        ):
            binding = "triggering PR/integration candidate" if trigger == "merge" else "manual source"
            _add(
                errors,
                f"{target_path}.authorized_head_sha",
                f"must bind the exact {binding} head",
            )

        if target["status"] == "PASS":
            if not is_full_sha(target["source_sha"]):
                _add(errors, target_path, "PASS requires an exact source SHA")
            for evidence_key in ("artifact", "channel", "promotion", "availability"):
                if not isinstance(target[evidence_key], dict):
                    _add(errors, target_path, f"PASS requires {evidence_key} evidence")
            if target["migration_status"] not in {"PASS", "not_required"}:
                _add(errors, target_path, "PASS requires migration PASS or not_required")
            if target["verification_status"] != "PASS":
                _add(errors, target_path, "PASS requires verification_status PASS")
            artifact = target["artifact"]
            if isinstance(artifact, dict):
                expected_signing = "PASS" if declared.get("requires_signing") else "not_required"
                if artifact.get("signing_status") != expected_signing:
                    _add(errors, f"{target_path}.artifact.signing_status", f"must equal {expected_signing}")
            merge_entry = run.get("authorizations", {}).get("merge_pr")
            observed_external_human_merge = (
                run.get("schema_version") == 10
                and trigger == "merge"
                and isinstance(merge_entry, dict)
                and merge_entry.get("authorized") is False
                and (
                    is_external_human_merge(run)
                    or is_legacy_completed_external_merge(run)
                )
            )
            actions = (
                ("deploy",)
                if trigger != "merge" or observed_external_human_merge
                else ("merge_pr", "deploy")
            )
            mission_states = run.get("mission_states")
            mission_ids = list(mission_states) if isinstance(mission_states, dict) else []
            for action in actions:
                if not mission_ids or any(
                    not _authorization_covers_release_head(
                        run,
                        action,
                        mission_id,
                        target_id,
                        expected_authorized_head,
                    )
                    for mission_id in mission_ids
                ):
                    _add(
                        errors,
                        target_path,
                        f"PASS requires exact {action} authorization for release:{target_id} at the authorized event head",
                    )

        if target["status"] == "PASS" and target["source_sha"] != expected_source:
            _add(errors, target_path, f"PASS must bind to the current {source} SHA")
        if source == "integration_head" and integration.get("retention") != "persistent":
            _add(errors, "run.integration.retention", "must be persistent for integration_head release source")

    for target_id, declared in declared_targets.items():
        if declared.get("stage") != "production":
            continue
        state = states.get(target_id)
        if state is None or state.get("status") != "PASS":
            continue
        development_ids = [
            item_id
            for item_id, item in declared_targets.items()
            if item.get("stage") == "development"
        ]
        if any(states.get(item_id, {}).get("status") != "PASS" for item_id in development_ids):
            _add(errors, f"{path}.{target_id}", "production PASS requires every development target PASS")

    # Declaring release targets in PLAN describes where the product deploys; it
    # does not oblige every run to deploy all of them. A run is complete when its
    # planned change is verified and pushed, so production stays not_started
    # until the human merges and a later authorized deploy runs. A run therefore
    # owes PASS for the targets it actually started, and nothing beyond them.
    def _status(target_id: str) -> Any:
        state = states.get(target_id)
        return state.get("status") if isinstance(state, dict) else None

    owed = {
        target_id
        for target_id in declared_targets
        if _status(target_id) not in {None, "not_started"}
    }
    if run.get("status") == "complete" and any(
        _status(target_id) != "PASS" for target_id in owed
    ):
        _add(errors, path, "complete run requires every started PLAN release target PASS")
