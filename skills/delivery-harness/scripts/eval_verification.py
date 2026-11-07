#!/usr/bin/env python3
"""Deterministic eval calculation over approved policy and recorded trials."""

from __future__ import annotations

import datetime as dt
import importlib.util
from pathlib import Path
import re
import sys


def product_policy():
    """Load the installed sibling parser, never a caller-selected module."""
    folder = Path(__file__).resolve().parents[2] / "product-definition-builder" / "scripts"
    name = "pdh_eval_policy"
    if name in sys.modules:
        return sys.modules[name]
    sys.path.insert(0, str(folder))
    try:
        spec = importlib.util.spec_from_file_location(name, folder / "eval_policy.py")
        if spec is None or spec.loader is None:
            raise ImportError("installed sibling eval policy parser unavailable")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[name] = module
        return module
    except (ImportError, OSError, SyntaxError) as exc:
        raise ImportError("installed sibling eval policy parser unavailable") from exc
    finally:
        sys.path.remove(str(folder))


ep = product_policy()
# A rendered eval scenario's Then steps take these keys in this order.
QUALITY_KEYS = ("eval-inputs-match", "eval-complete", "eval-rate", "eval-slices", "eval-critical")
HANDOFF_KEYS = ("eval-handoff",)
QUALITY_ASSERTIONS = set(QUALITY_KEYS)
HANDOFF_ASSERTIONS = set(HANDOFF_KEYS)
GIT_SHA = re.compile(r"[0-9a-f]{40}\Z")


def timestamp(value):
    if not isinstance(value, str):
        ep.fail("timestamp must be RFC3339 text")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ep.PolicyError("invalid report timestamp") from exc
    if "T" not in value or parsed.tzinfo is None:
        ep.fail("timestamp needs date/time and timezone")
    try:
        return parsed.astimezone(dt.timezone.utc)
    except OverflowError as exc:
        raise ep.PolicyError("invalid report timestamp") from exc


def concrete_observation(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 8000:
        ep.fail(f"{label}: nonempty bounded redacted observation required")


def validate_contract(contract, policy, prd_sha256):
    ep.keys(contract, "schema prd_sha256 policy_sha256 quality handoff delivery", "eval contract")
    expected = {"schema": "eval-contract/1", "prd_sha256": prd_sha256,
                "policy_sha256": ep.policy_digest(policy),
                **{name: policy[name] for name in ("quality", "handoff", "delivery")}}
    if contract != expected:
        ep.fail("eval contract must derive exactly from authoritative PRD policy")


def usage(value, currency):
    ep.keys(value, "calls cost_microunits currency", "usage")
    ep.integer(value["calls"], "calls")
    ep.integer(value["cost_microunits"], "cost_microunits")
    if value["currency"] != currency:
        ep.fail("usage currency differs from policy")


def passes(passing, total, threshold):
    return total > 0 and passing * threshold["denominator"] >= total * threshold["numerator"]


def validate_report(report, policy, approved, *, purpose, candidate_sha, contract_sha256,
                    prd_sha256, execution, artifacts, now=None):
    """Raise on invalid/failing evidence. Never trust a report's PASS summary."""
    ep.keys(report, "schema purpose run_id candidate_sha contract_sha256 prd_sha256 policy_sha256 "
            "started_at finished_at execution artifacts provenance trials usage", "eval report")
    if (report["schema"] != "eval-report/1" or report["purpose"] != purpose
            or report["candidate_sha"] != candidate_sha or not GIT_SHA.fullmatch(candidate_sha)
            or report["contract_sha256"] != contract_sha256 or report["prd_sha256"] != prd_sha256
            or report["policy_sha256"] != ep.policy_digest(policy)):
        ep.fail("report identity differs from frozen inputs or candidate")
    ep.identifier(report["run_id"], "run_id")
    if report["execution"] != execution or report["artifacts"] != artifacts:
        ep.fail("report context or implementation/input bytes differ")
    start, finish = timestamp(report["started_at"]), timestamp(report["finished_at"])
    current = now or dt.datetime.now(dt.timezone.utc)
    if (not start <= finish <= current or (current - start).total_seconds() > policy["freshness"]["max_age_seconds"]
            or (finish - start).total_seconds() * 1000 > policy["limits"]["run_timeout_ms"]):
        ep.fail("report stale, future-dated or beyond run deadline")
    provenance = report["provenance"]
    ep.keys(provenance, "executor job_id checkout_sha git_status setup full dependency_readbacks", "provenance")
    for name in ("executor", "job_id"):
        ep.text(provenance[name], name)
    if provenance["checkout_sha"] != candidate_sha or provenance["git_status"] != "":
        ep.fail("run must originate from clean exact candidate checkout")
    for name in ("setup", "full"):
        receipt = provenance[name]
        ep.keys(receipt, "argv exit_code observation", "command receipt")
        if receipt["argv"] != policy["delivery"][name + "_argv"] or type(receipt["exit_code"]) is not int or receipt["exit_code"] != 0:
            ep.fail("setup/full receipt differs from delivered interface or failed")
        concrete_observation(receipt["observation"], "command observation")
    readbacks = provenance["dependency_readbacks"]
    dependencies = policy["freshness"]["dependencies"]
    if not isinstance(readbacks, dict) or set(readbacks) != set(dependencies):
        ep.fail("mutable dependency readbacks incomplete")
    for name, identity in dependencies.items():
        row = readbacks[name]
        ep.keys(row, "identity checked_at observation", "dependency readback")
        checked = timestamp(row["checked_at"])
        if row["identity"] != identity or not start <= checked <= finish:
            ep.fail("mutable dependency readback stale or identity changed")
        concrete_observation(row["observation"], "dependency observation")
    cases = {row["case_id"]: row for row in approved["dataset"]}
    dimensions = {row["id"]: row for row in approved["rubric"]["dimensions"]}
    assertions = approved["rubric"]["prohibited_assertions"]
    expected = {(case, index) for case in cases for index in range(1, policy["trials_per_case"] + 1)}
    trials = report["trials"]
    if not isinstance(trials, list) or len(trials) != len(expected):
        ep.fail("missing or extra planned trials")
    seen = set()
    trial_pass_counts = dict.fromkeys(cases, 0)
    calls, cost = 0, 0
    for row in trials:
        ep.keys(row, "case_id trial_index status scores assertion_results observed_subject observed_grader "
                "duration_ms usage redacted_output grading_observation tool_observations failure", "trial")
        ep.identifier(row["case_id"], "trial case")
        ep.integer(row["trial_index"], "trial index", 1, policy["trials_per_case"])
        key = (row["case_id"], row["trial_index"])
        if key not in expected or key in seen:
            ep.fail("extra or duplicate trial identity")
        seen.add(key)
        if row["status"] != "completed":
            ep.fail("skipped, timeout, error or unvalidated trial invalidates full run")
        if (row["observed_subject"] != approved["subject"]["identity"]
                or row["observed_grader"] != approved["grader"]["identity"]):
            ep.fail("observed subject or grader differs from approved identity")
        ep.integer(row["duration_ms"], "duration_ms", 0, policy["limits"]["trial_timeout_ms"])
        usage(row["usage"], policy["limits"]["currency"])
        calls += row["usage"]["calls"]
        cost += row["usage"]["cost_microunits"]
        for name in ("redacted_output", "grading_observation", "tool_observations"):
            concrete_observation(row[name], name)
        if not isinstance(row["failure"], str) or len(row["failure"]) > 8000:
            ep.fail("trial failure must be bounded text")
        scores = row["scores"]
        if not isinstance(scores, dict) or set(scores) != set(dimensions):
            ep.fail("trial scores must cover exact rubric dimensions")
        trial_pass = True
        for name, dimension in dimensions.items():
            ep.integer(scores[name], "score", dimension["minimum"], dimension["maximum"])
            trial_pass &= scores[name] >= dimension["passing_score"]
        outcomes = row["assertion_results"]
        if not isinstance(outcomes, dict) or set(outcomes) != set(assertions) or any(v not in {"pass", "fail"} for v in outcomes.values() if isinstance(v, str)):
            ep.fail("trial assertions must cover exact prohibited checks")
        if any(v != "pass" for v in outcomes.values()):
            ep.fail("prohibited outcome overrides aggregate threshold")
        if cases[key[0]]["critical"] and not trial_pass:
            ep.fail("critical trial failure overrides aggregate threshold")
        if not trial_pass and not row["failure"].strip():
            ep.fail("quality failure needs retained failure observation")
        trial_pass_counts[key[0]] += trial_pass
    if seen != expected:
        ep.fail("incomplete trial population")
    usage(report["usage"], policy["limits"]["currency"])
    if (report["usage"]["calls"] != calls or report["usage"]["cost_microunits"] != cost
            or calls > policy["limits"]["max_calls"] or cost > policy["limits"]["max_cost_microunits"]):
        ep.fail("usage does not recompute or exceeds approved budget")
    repeats = policy["trials_per_case"]
    counts = {case: (int(count == repeats), 1) if policy["metric"] == "case_all_trials" else (count, repeats)
              for case, count in trial_pass_counts.items()}
    passing = sum(count[0] for count in counts.values())
    total = sum(count[1] for count in counts.values())
    if not passes(passing, total, policy["minimum_rate"]):
        ep.fail("aggregate pass rate below approved threshold")
    slice_counts = {row["id"]: [0, 0, 0] for row in policy["slices"]}
    for name, case in cases.items():
        for slice_id in case["slices"]:
            count = slice_counts[slice_id]
            count[0] += 1
            count[1] += counts[name][0]
            count[2] += counts[name][1]
    slice_results = {}
    for row in policy["slices"]:
        members, slice_pass, slice_total = slice_counts[row["id"]]
        if members < row["minimum_cases"] or not passes(slice_pass, slice_total, row["minimum_rate"]):
            ep.fail("slice below approved coverage or pass threshold")
        slice_results[row["id"]] = {"passing": slice_pass, "total": slice_total}
    return {"passing": passing, "total": total, "slices": slice_results,
            "planned_trials": len(expected), "run_id": report["run_id"]}
