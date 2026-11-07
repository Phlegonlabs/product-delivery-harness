#!/usr/bin/env python3
"""Require frozen eval sources and executable gates without changing RUN schema."""

from __future__ import annotations

from pathlib import Path
import sys

import check_delivery_acceptance as acceptance
from delivery_acceptance_io import _read_bytes, _safe_file, _load_json, _sha256, _parse_required_prd_tests, AcceptanceError
from eval_verification import ep, validate_contract, QUALITY_ASSERTIONS, HANDOFF_ASSERTIONS
from harness_schema import run_required_harness_version, version_at_least
from harness_git import GitMetadataError, reject_object_substitution

INTRODUCTION_VERSION = (0, 60, 0)
ACCEPTANCE_GATE_VERSION = (0, 79, 0)
RESULTS_PATH = "docs/verification/delivery-results.json"


def _authority_bytes(root, source):
    """Prove one safe byte sequence before interpreting policy presence/absence."""
    path = _safe_file(root, str(source.get("location", "")))
    raw = _read_bytes(path, "PRD", root)
    if source.get("content_sha256") != _sha256(raw):
        ep.fail("PRD authority bytes do not match the frozen content_sha256")
    revision = source.get("source_revision")
    if revision is not None:
        if not isinstance(revision, str) or not acceptance.GIT_SHA_RE.fullmatch(revision):
            ep.fail("PRD authority source_revision must be a full Git SHA")
        reject_object_substitution(root)
        errors = acceptance._committed_file_errors(root, revision, path.relative_to(root).as_posix(), raw)
        if errors:
            ep.fail("PRD authority bytes do not match the frozen source_revision: " + "; ".join(errors))
    return raw


def _command(gate, script, expected):
    argv = gate.get("argv")
    execution = gate.get("execution")
    if (gate.get("cwd") != "." or gate.get("pass_signal") != "exit 0"
            or not isinstance(execution, dict) or execution.get("isolation") != "host"
            or not isinstance(argv, list) or len(argv) < 3 or any(not isinstance(x, str) for x in argv)
            or not Path(argv[0]).is_absolute()
            or Path(argv[0]).resolve() != Path(sys.executable).resolve()
            or not Path(argv[1]).is_absolute()
            or Path(argv[1]).resolve() != Path(__file__).with_name(script).resolve()):
        ep.fail("eval/acceptance gate must invoke the absolute installed checker with the observed absolute Python on the host from repository root")
    selection = gate.get("selection")
    if selection is not None and (not isinstance(selection, dict) or selection.get("mode") != "always"):
        ep.fail("eval/acceptance gates must always run")
    actual = {}
    index = 2
    while index < len(argv):
        name = argv[index]
        if name not in expected or name in actual:
            ep.fail("eval/acceptance checker has unknown or duplicate arguments")
        if name == "--candidate-from-head":
            actual[name] = True
            index += 1
        else:
            if index + 1 >= len(argv):
                ep.fail("eval/acceptance checker argument missing value")
            actual[name] = argv[index + 1]
            index += 2
    if actual != expected:
        ep.fail("eval/acceptance argv must exactly join frozen source paths/hashes and register")


def _topology(plan, gates, chain):
    graph = plan.get("graph")
    if not isinstance(graph, dict) or not isinstance(graph.get("nodes"), list) or not isinstance(graph.get("edges"), list):
        ep.fail("eval acceptance needs an executable verifier graph")
    nodes = graph["nodes"]
    bindings = {}
    for gate_id in gates:
        matches = [node for node in nodes if isinstance(node, dict) and node.get("ref") == gate_id]
        if (len(matches) != 1 or matches[0].get("kind") != "verifier"
                or matches[0].get("executor") != "local_command"):
            ep.fail("each eval/final gate needs one local-command verifier node")
        bindings[gate_id] = matches[0]["id"]
    adjacency = {}
    for edge in graph["edges"]:
        if (isinstance(edge, dict) and edge.get("kind") == "dependency"
                and edge.get("on_outcomes") == ["pass"] and edge.get("max_traversals") is None):
            adjacency.setdefault(edge.get("from"), set()).add(edge.get("to"))

    def reaches(source, target):
        pending, seen = [source], set()
        while pending:
            node = pending.pop()
            if node == target:
                return True
            if node not in seen:
                seen.add(node)
                pending.extend(adjacency.get(node, ()))
        return False

    for before, after in zip(chain, chain[1:]):
        if not reaches(bindings[before], bindings[after]):
            ep.fail("required dependency path: " + " -> ".join(chain))
    broad = set(gates) - set(chain)
    if not broad or any(not reaches(bindings[name], bindings[chain[0]]) for name in broad):
        ep.fail(f"every broad final check must precede {chain[0]}")


def _frozen_contract_source(plan, key, root, source_rows, resolve_source):
    rows, errors = source_rows(plan, key)
    if errors or len(rows) != 1:
        return None, None, errors or [f"eval-plan: requires one frozen {key} source"]
    source = rows[0]
    ep.safe_relative(source["location"])
    bounded = _read_bytes(root / source["location"], key, root)
    payload, errors = resolve_source(source, root, label=key, strict=True)
    if errors or payload != bounded:
        return None, None, errors or ["eval-plan: frozen contract changed during read"]
    return source, _load_json(payload, key), []


def validate_eval_plan(plan, repo_root, *, run=None, source_rows, resolve_source):
    if plan.get("schema_version") != 6:
        return []
    current = version_at_least(run_required_harness_version(run), INTRODUCTION_VERSION)
    root = Path(repo_root).resolve()
    try:
        candidates = [row for row in plan.get("sources", []) if isinstance(row, dict)
                      and (" ".join(str(row.get("kind", "")).replace("_", " ").replace("-", " ").casefold().split())
                           in {"prd", "product requirement", "product requirements"}
                           or row.get("location") == "docs/product/PRD.md"
                           or (row.get("status") in {"frozen", "delta_accepted", "delta accepted"}
                               and str(row.get("location", "")).rsplit("/", 1)[-1].casefold() == "prd.md"))]
        if not candidates:
            return ["eval-plan: current run needs one frozen PRD applicability declaration"] if current else []
        adopted = []
        for candidate in candidates:
            try:
                raw = _authority_bytes(root, candidate)
            except (OSError, AcceptanceError):
                ep.fail("PRD authority cannot be safely read; policy absence is unobserved")
            prd_text = raw.decode("utf-8")
            canonical = candidate.get("kind") == "prd" or candidate.get("location") == "docs/product/PRD.md"
            policy = ep.parse_eval_policy(prd_text, required=current and canonical)
            if policy is not None:
                adopted.append((raw, prd_text, policy))
        if not adopted:
            if current:
                ep.fail("current run needs a canonical PRD applicability declaration")
            return []
        if len(adopted) != 1:
            ep.fail("ambiguous PRD eval-policy authority")
        raw, prd_text, policy = adopted[0]
        policy_errors = ep.validate_eval_policy(prd_text, required=True, repo_root=root)
        if policy_errors:
            return policy_errors
        rows, errors = source_rows(plan, "prd")
        if errors or len(rows) != 1:
            return errors or ["eval-plan: one canonical frozen PRD source required"]
        prd_source = rows[0]
        frozen, errors = resolve_source(prd_source, root, label="PRD", strict=True)
        if errors or frozen != raw:
            return errors or ["eval-plan: adopted policy differs from the canonical frozen PRD authority"]
        if policy["applicability"] == "not_required":
            if not version_at_least(run_required_harness_version(run), ACCEPTANCE_GATE_VERSION):
                return []
            delivery_ref, delivery, errors = _frozen_contract_source(plan, "delivery-acceptance", root, source_rows, resolve_source)
            if errors:
                return errors
            if delivery.get("prd_sha256") != _sha256(raw):
                return ["eval-plan: delivery contract must bind frozen PRD hash"]
            gates = plan.get("final_gates")
            if not isinstance(gates, list) or any(not isinstance(gate, dict) for gate in gates):
                ep.fail("eval-plan: final gates missing")
            gate_map = {gate.get("id"): gate for gate in gates}
            if len(gate_map) != len(gates) or not {"delivery-acceptance", "final-closeout"} <= set(gate_map):
                ep.fail("eval-plan: required delivery/closeout final gates missing or duplicate")
            _command(gate_map["delivery-acceptance"], "check_delivery_acceptance.py", {
                "--repo-root": ".", "--prd": prd_source["location"], "--results": RESULTS_PATH,
                "--candidate-from-head": True, "--contract": delivery_ref["location"],
                "--contract-sha256": delivery_ref["content_sha256"]})
            _topology(plan, gate_map, chain=("delivery-acceptance", "final-closeout"))
            return []
        sources = {}
        resolved = {}
        for key in ("eval-contract", "delivery-acceptance"):
            source, payload, errors = _frozen_contract_source(plan, key, root, source_rows, resolve_source)
            if errors:
                return errors
            sources[key], resolved[key] = source, payload
        prd_hash = _sha256(raw)
        validate_contract(resolved["eval-contract"], policy, prd_hash)
        delivery = resolved["delivery-acceptance"]
        all_tests, required_tests, errors = _parse_required_prd_tests(raw)
        scenarios, findings = acceptance._contract(delivery, all_tests, required_tests)
        errors.extend(findings)
        if delivery.get("prd_sha256") != prd_hash:
            errors.append("eval-plan: delivery contract must bind frozen PRD hash")
        if errors:
            return errors
        for purpose, assertions in (("quality", QUALITY_ASSERTIONS), ("handoff", HANDOFF_ASSERTIONS)):
            declared = policy[purpose]
            scenario = scenarios.get((declared["test_id"], declared["scenario_id"]))
            if scenario is None or set(scenario["execution"]["assertions"]) != assertions:
                ep.fail("eval-plan: required quality/handoff scenario and exact assertions missing")
            if not acceptance._under_root(declared["report"], acceptance.evidence_root(RESULTS_PATH)):
                ep.fail("eval-plan: reports must be directly under the acceptance evidence root")
        gates = plan.get("final_gates")
        if not isinstance(gates, list) or any(not isinstance(gate, dict) for gate in gates):
            ep.fail("eval-plan: final gates missing")
        gate_map = {gate.get("id"): gate for gate in gates}
        if len(gate_map) != len(gates) or not {"eval-acceptance", "delivery-acceptance", "final-closeout"} <= set(gate_map):
            ep.fail("eval-plan: required eval/delivery/closeout final gates missing or duplicate")
        common = {"--repo-root": ".", "--prd": prd_source["location"], "--results": RESULTS_PATH,
                  "--candidate-from-head": True}
        delivery_ref = sources["delivery-acceptance"]
        eval_ref = sources["eval-contract"]
        _command(gate_map["eval-acceptance"], "check_eval_acceptance.py", {
            **common, "--prd-sha256": prd_source["content_sha256"],
            "--contract": eval_ref["location"], "--contract-sha256": eval_ref["content_sha256"],
            "--delivery-contract": delivery_ref["location"], "--delivery-contract-sha256": delivery_ref["content_sha256"]})
        _command(gate_map["delivery-acceptance"], "check_delivery_acceptance.py", {
            **common, "--contract": delivery_ref["location"], "--contract-sha256": delivery_ref["content_sha256"]})
        _topology(plan, gate_map, chain=("eval-acceptance", "delivery-acceptance", "final-closeout"))
        return []
    except (ep.PolicyError, AcceptanceError, GitMetadataError) as exc:
        return [f"eval-plan: {exc}"]
    except (OSError, UnicodeError, TypeError, KeyError, AttributeError, ValueError, RecursionError):
        return ["eval-plan: invalid or unreadable policy/source/gate"]
