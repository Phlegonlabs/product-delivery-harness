"""Derived states: Approved target scope, evidence matrix and the HiFi joins.

Fixtures are synthetic validator inputs, never product approvals or browser runs.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import hifi_reviewer  # noqa: E402
from hifi_product_contract import hifi_prd_findings  # noqa: E402
from hifi_review_fixture import _source_html, add_shell  # noqa: E402
from test_hifi_product_contract import documents, fixture  # noqa: E402
from test_structure_publication import checker  # noqa: E402

STATES = ["ready", "confirm-discard", "confirm-discard-loading"]
DERIVED = {"confirm-discard-loading": "confirm-discard"}


def scope_source(*, derived=DERIVED, states=STATES, responsive=None):
    surface = {"id": "UI-001", "route": "/editor", "states": states}
    if derived is not None:
        surface["derivedStates"] = derived
    if responsive is not None:
        surface["responsive"] = responsive
    return ("docs/design/ui-references/run-1/index.html @ sha256:" + "a" * 64
            + "; scope=surfaces=" + json.dumps([surface], separators=(",", ":"))
            + '|routes=["/editor"]|states=' + json.dumps(sorted(states), separators=(",", ":"))
            + '|responsive={"kind":"viewports","targets":[390,768,1200]}'
            + '|tolerance="exact"|allowedDeviations=[]|captureMode=hosted-browser')


def parsed_scope(**kwargs):
    problems = []
    scope = checker._target_scope(scope_source(**kwargs), "Approved target", problems)
    return scope, problems


def cases(scope):
    return [(case["state"], case["target"]) for case in checker._evidence_matrix(scope)["cases"]]


class TargetScopeTests(unittest.TestCase):
    def test_scope_accepts_the_field(self):
        scope, problems = parsed_scope()
        self.assertEqual([], problems)
        self.assertEqual(DERIVED, scope["surfaces"][0]["derivedStates"])

    def test_scope_rejects_unknown_na_and_cyclic_maps(self):
        for label, kwargs, expected in (
            ("unknown parent", {"derived": {"confirm-discard-loading": "missing"}}, "unknown or n/a parent"),
            ("n/a parent", {"derived": {"confirm-discard-loading": "error"}, "states": [*STATES, "error:n/a"]},
             "unknown or n/a parent"),
            ("unlisted child", {"derived": {"other": "ready"}}, "must be a non-n/a state"),
            ("self cycle", {"derived": {"ready": "ready"}}, "form a cycle"),
            ("two-state cycle", {"derived": {"confirm-discard": "confirm-discard-loading",
                                             "confirm-discard-loading": "confirm-discard"}}, "form a cycle"),
            ("not an object", {"derived": ["confirm-discard-loading"]}, "non-empty object"),
            ("empty object", {"derived": {}}, "non-empty object"),
        ):
            with self.subTest(label):
                _, problems = parsed_scope(**kwargs)
                self.assertTrue(any("derivedStates" in item and expected in item for item in problems), problems)


class EvidenceMatrixTests(unittest.TestCase):
    def test_surface_without_the_field_keeps_the_full_cross_product(self):
        scope, _ = parsed_scope(derived=None)
        self.assertEqual([(state, target) for state in STATES for target in ("390", "768", "1200")], cases(scope))

    def test_derived_state_is_captured_once_at_the_smallest_target(self):
        scope, _ = parsed_scope()
        self.assertEqual(
            [(state, target) for state in STATES[:2] for target in ("390", "768", "1200")]
            + [("confirm-discard-loading", "390")],
            cases(scope),
        )

    def test_smallest_target_is_the_surface_own_first_target(self):
        scope, _ = parsed_scope(responsive={"kind": "viewports", "targets": [320, 800, 1280]})
        self.assertEqual([("confirm-discard-loading", "320")], [row for row in cases(scope) if row[0] == "confirm-discard-loading"])
        scope, _ = parsed_scope(responsive={"kind": "sizeClasses", "targets": ["phone-small", "phone-large"]})
        self.assertEqual([("confirm-discard-loading", "phone-small")], [row for row in cases(scope) if row[0] == "confirm-discard-loading"])

    def test_chain_members_are_each_captured_once(self):
        scope, _ = parsed_scope(derived={"confirm-discard": "ready", **DERIVED})
        self.assertEqual(
            [("ready", "390"), ("ready", "768"), ("ready", "1200"),
             ("confirm-discard", "390"), ("confirm-discard-loading", "390")],
            cases(scope),
        )


class ScopeJoinTests(unittest.TestCase):
    def join(self, prd_text, scope):
        with tempfile.TemporaryDirectory() as temp:
            prd = Path(temp) / "PRD.md"
            prd.write_text(prd_text, encoding="utf-8")
            problems = []
            checker._validate_target_scope_join(scope, prd_path=prd, wireframes_path=None, stack_text="",
                                                architecture_text="", problems=problems)
        return [item for item in problems if "derivedStates" in item]

    def prd(self, *, derived):
        anchor = f"- `derivedStates`: {json.dumps(derived)}\n" if derived else ""
        return ("<!-- ui-surface-contract:start -->\n### UI-001 — Editor\n- `route`: /editor\n"
                f"- `states`: {', '.join(STATES)}\n{anchor}- `responsive`: viewports: 390, 768, 1200\n"
                "- `copy`: approved\n<!-- ui-surface-contract:end -->\n")

    def test_target_must_declare_exactly_the_prd_derived_states(self):
        declared, _ = parsed_scope()
        undeclared, _ = parsed_scope(derived=None)
        other, _ = parsed_scope(derived={"confirm-discard": "ready"})
        self.assertEqual([], self.join(self.prd(derived=DERIVED), declared))
        self.assertEqual([], self.join(self.prd(derived=None), undeclared))
        for label, text, scope in (("target drops the field", self.prd(derived=DERIVED), undeclared),
                                   ("target adds the field", self.prd(derived=None), declared),
                                   ("different map", self.prd(derived=DERIVED), other)):
            with self.subTest(label):
                self.assertEqual(1, len(self.join(text, scope)), label)


class HiFiJoinTests(unittest.TestCase):
    def derived_fixture(self, derived):
        product, manifest, inventory, markup = fixture()
        anchor = f"\n- `derivedStates`: {json.dumps(derived)}" if derived is not None else ""
        product = product.replace("`states`: ready", "`states`: ready, confirm, confirm-loading" + anchor, 1)
        manifest["surfaces"][0]["states"] = ["ready", "confirm", "confirm-loading"]
        return product, manifest, documents(inventory, markup)

    def test_derived_state_is_an_ordinary_manifest_state(self):
        product, manifest, docs = self.derived_fixture({"confirm-loading": "confirm"})
        self.assertEqual([], hifi_prd_findings(product, manifest, docs))
        missing = copy.deepcopy(manifest)
        missing["surfaces"][0]["states"] = ["ready", "confirm"]
        self.assertTrue(any("states differ from PRD" in item for item in hifi_prd_findings(product, missing, docs)))

    def test_unknown_parent_and_cycle_fail_the_preflight(self):
        for derived in ({"confirm-loading": "missing"}, {"confirm": "confirm-loading", "confirm-loading": "confirm"}):
            with self.subTest(derived):
                product, manifest, docs = self.derived_fixture(derived)
                self.assertTrue(any("derivedStates" in item for item in hifi_prd_findings(product, manifest, docs)))

    def test_derived_state_still_needs_its_state_control(self):
        manifest = {"schema": "ui-hifi/2", "surfaces": [{
            "id": "UI-001", "page": "index.html", "route": "/", "states": ["ready", "confirm", "confirm-loading"],
            "responsive": {"targets": [390, 768]},
        }]}
        html = add_shell(_source_html(manifest["surfaces"][0], version=3), manifest, version=3)
        self.assertEqual([], hifi_reviewer.reviewer_contract({"index.html": html}, manifest)[0])
        control = ('<button type="button" data-hifi-state-control="confirm-loading" '
                   'data-hifi-state-surface="UI-001" aria-pressed="false">confirm-loading</button>')
        self.assertEqual(1, html.count(control))
        errors = hifi_reviewer.reviewer_contract({"index.html": html.replace(control, "")}, manifest)[0]
        self.assertTrue(any("state controls must match manifest surface states" in item for item in errors), errors)


if __name__ == "__main__":
    unittest.main()
