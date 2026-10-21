"""Native CSP provenance is narrow; every unproven console error stays blocking."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import check_ui_design_contract as ui_contract
import hifi_review_fixture as fixture
import review_evidence as evidence

DIAGNOSTIC_TEXT = "Unrecognized Content-Security-Policy directive 'navigate-to'."
OTHER_TEXT = "Refused to execute inline script because it violates CSP."
RAW_CAPTURE = "docs/evidence/native-events.json"


class NativeCspDiagnosticTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.child = self.root / "child.html"
        self.child.write_text("<h1>Child</h1>", encoding="utf-8", newline="")
        self.child_bytes = self.child.read_bytes()
        index_surface = {
            "id": "UI-001", "page": "index.html", "route": "/home", "states": ["ready"],
            "responsive": {"kind": "viewports", "targets": [390]},
            "navigation": [], "controls": [],
        }
        child_surface = dict(index_surface, id="UI-002", page="child.html", route="/detail")
        self.manifest = {
            "schema": "ui-hifi/2", "surfaces": [index_surface, child_surface],
            "pages": [{"path": "child.html", "sha256": self.sha(self.child)}],
            "interactions": [],
        }
        index_source = self.with_csp(fixture.add_shell(
            fixture._source_html(index_surface, component_types=("button",), version=3),
            self.manifest, component_types=("button",), version=3,
        ))
        child_source = self.with_csp(fixture.add_shell(
            fixture._source_html(child_surface, component_types=("button",), version=3),
            self.manifest, page="child.html", component_types=("button",), version=3,
        ))
        self.child.write_text(child_source, encoding="utf-8", newline="")
        self.child_bytes = self.child.read_bytes()
        self.manifest["pages"] = [{"path": "child.html", "sha256": self.sha(self.child)}]
        index_source = index_source.replace(
            "</head>",
            '<script id="ui-hifi-manifest" type="application/json">'
            + json.dumps(self.manifest) + "</script></head>",
            1,
        )
        subject = self.root / "index.html"
        subject.write_text(index_source, encoding="utf-8", newline="")
        self.subject = self.binding(subject)
        self.prd = self.root / "PRD.md"
        self.prd.write_text("# Frozen PRD", encoding="utf-8", newline="")
        self.capture = self.root / "capture.json"
        self.capture.write_text(json.dumps({"observed": "synthetic fixture"}), encoding="utf-8")
        self.capture_binding = self.binding(self.capture)

    def sha(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def binding(self, path: Path) -> dict[str, str]:
        return {"path": path.relative_to(self.root).as_posix(), "sha256": self.sha(path)}

    def write(self, path: Path, payload: object) -> dict[str, str]:
        path.write_text(json.dumps(payload), encoding="utf-8", newline="")
        return self.binding(path)

    def with_csp(self, html: str) -> str:
        meta = ('<meta http-equiv="Content-Security-Policy" content="'
                + ui_contract.check_wireframe_html.REQUIRED_HIFI_CSP.replace(
                    "navigate-to 'none'", "navigate-to 'self'"
                ) + '">')
        return html.replace("<head>", "<head>" + meta, 1)

    def native_event(self, *, url: str | None = None, entry_type: str = "Log.entryAdded",
                     source: str = "security", level: str = "error", text: str = DIAGNOSTIC_TEXT,
                     timestamp: float = 1792530128667.031) -> dict:
        return {
            "at": "2026-10-20T21:02:08.671104+00:00", "type": entry_type,
            "params": {"entry": {
                "source": source, "level": level, "text": text, "timestamp": timestamp,
                "url": url or self.root.joinpath("index.html").as_uri(), "lineNumber": 3,
            }},
        }

    def console_record(self, event: dict, *, url: str | None = None,
                       level: str = "error", message: str = DIAGNOSTIC_TEXT) -> dict:
        return {
            "level": level, "message": message,
            "url": url or self.root.joinpath("index.html").as_uri(),
            **event,
        }

    def runtime_info_event(self) -> dict:
        url = self.root.joinpath("index.html").as_uri()
        return {
            "at": "2026-10-20T21:02:08.672104+00:00",
            "type": "Runtime.consoleAPICalled",
            "params": {
                "type": "log",
                "args": [{"type": "string", "value": "ready"}],
            },
            "level": "info", "message": "ready", "url": url,
        }

    def downgraded_runtime_event(self, *, kind: str = "error") -> dict:
        url = self.root.joinpath("index.html").as_uri()
        params = ({"exceptionDetails": {"text": "Uncaught native failure."}}
                  if kind == "exception" else
                  {"type": kind, "args": [{"type": "string", "value": "failure"}]})
        return {
            "at": "2026-10-20T21:02:08.673104+00:00",
            "type": ("Runtime.exceptionThrown" if kind == "exception"
                     else "Runtime.consoleAPICalled"),
            "params": params,
            "level": "info", "message": "benign", "url": url,
        }

    def write_raw(self, events: list[dict]) -> dict[str, str]:
        (self.root / RAW_CAPTURE).parent.mkdir(parents=True, exist_ok=True)
        return self.write(self.root / RAW_CAPTURE, {
            "startedAt": "2026-10-20T21:02:08.000000+00:00",
            "finishedAt": "2026-10-20T21:02:09.000000+00:00",
            "browser": {"product": "synthetic fixture"}, "events": events,
        })

    def output(self, console: list[dict], raw_binding: dict[str, str] | None) -> dict:
        artifacts = [self.binding(self.prd), self.subject, self.binding(self.child)]
        if raw_binding is not None:
            artifacts.append(raw_binding)
        return {
            "schema": "ui-output/3", "check": "hifi-browser", "subject": self.subject,
            "matrix": {"cases": [{"surface": "UI-001", "state": "ready", "target": "390"}]},
            "results": [{"surface": "UI-001", "state": "ready", "target": "390", "result": "PASS"}],
            "execution": {
                "startedAt": "2026-01-01T00:00:00Z", "finishedAt": "2026-01-01T00:00:01Z",
                "tool": "playwright", "method": "sandboxed-offline-browser",
                "environment": {"browser": "synthetic test fixture"}, "artifacts": artifacts,
            },
            "sandbox": {"network": "disabled", "topNavigation": "allowlisted-local-pages",
                        "popups": "blocked", "forms": "blocked"},
            "console": console, "network": [], "navigation": [], "popups": [], "forms": [],
            "popupAttempts": 0, "formAttempts": 0, "interactions": [],
            "reviewer": fixture.observations(self.manifest, component_types=("button",), version=3),
        }

    def context(self, events: list[dict]):
        from native_csp_diagnostic import build_context
        from check_ui_design_contract import _hifi_bundle_documents

        subject_data = evidence.read_identity(self.root, self.subject)
        documents = _hifi_bundle_documents(
            evidence.safe_path(self.root, self.subject["path"]),
            subject_data.decode("utf-8"), self.manifest,
        )
        return build_context(
            self.root, self.subject, self.manifest,
            [self.binding(self.prd), self.subject, self.binding(self.child), self.write_raw(events)],
            documents,
        )

    def transcript(self, output: dict, context=None) -> list[str]:
        return ui_contract._offline_transcript_findings(
            dict(output, sandbox={"network": "disabled", "topNavigation": "blocked",
                                  "popups": "blocked", "forms": "blocked"}),
            context=context,
        )

    def test_exact_native_occurrence_is_retained_without_an_error_block(self) -> None:
        event = self.native_event()
        context = self.context([event])
        findings = self.transcript(
            self.output([self.console_record(event)], self.write_raw([event])), context,
        )
        self.assertEqual([], findings)

    def test_duplicate_native_occurrences_are_multiset_matched(self) -> None:
        event = self.native_event()
        context = self.context([event, dict(event)])
        records = [self.console_record(event), self.console_record(dict(event))]
        findings = self.transcript(self.output(records, self.write_raw([event, dict(event)])), context)
        self.assertEqual([], findings)

    def test_omitted_deduplicated_or_unmatched_raw_occurrence_fails(self) -> None:
        event = self.native_event()
        raw = self.write_raw([event])
        empty = self.transcript(self.output([], raw), self.context([event]))
        self.assertIn("HiFi offline transcript omits a native console observation", empty)
        duplicated = self.transcript(
            self.output([self.console_record(event)] * 2, raw), context=self.context([event]),
        )
        self.assertIn("native CSP diagnostic provenance is incomplete", " ".join(duplicated))
        forged = self.transcript(
            self.output([self.console_record(self.native_event(timestamp=2.0))], raw),
            context=self.context([event]),
        )
        self.assertIn("HiFi offline transcript contains a console error", forged)

    def test_wrong_provenance_message_or_channel_stays_blocking(self) -> None:
        native = self.native_event()
        raw = self.write_raw([native])
        mutations = (
            {"level": "warning"}, {"source": "rendering"}, {"text": DIAGNOSTIC_TEXT + " extra"},
            {"entry_type": "Runtime.consoleAPICalled"},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                event = self.native_event(**mutation)
                context = self.context([event])
                record = self.console_record(event)
                if "level" in mutation:
                    record["level"] = mutation["level"]
                findings = self.transcript(
                    self.output([record], raw), context=context,
                )
                if mutation == {"level": "warning"}:
                    self.assertEqual([], findings)
                else:
                    self.assertIn(
                        "HiFi offline transcript contains a console error",
                        " ".join(findings),
                    )

    def test_generic_runtime_error_and_genuine_csp_violation_stay_blocking(self) -> None:
        allowed = self.native_event()
        blocked = self.native_event(text=OTHER_TEXT)
        context = self.context([allowed, blocked])
        output = self.output([
            self.console_record(allowed),
            self.console_record(blocked, message=OTHER_TEXT),
        ], self.write_raw([allowed, blocked]))
        findings = self.transcript(output, context)
        self.assertIn("HiFi offline transcript contains a console error", findings)

    def test_native_info_and_warning_observations_reconcile_without_exemption(self) -> None:
        allowed = self.native_event()
        warning = self.native_event(level="warning", text="ready")
        info = self.runtime_info_event()
        context = self.context([allowed, warning, info])
        findings = self.transcript(self.output([
            self.console_record(allowed),
            self.console_record(warning, level="warning", message="ready"),
            self.console_record(info, message="ready"),
        ], self.write_raw([allowed, warning, info])), context)
        self.assertEqual([], findings)

    def test_matched_native_error_remains_blocking_beside_bound_info(self) -> None:
        allowed = self.native_event()
        genuine = self.native_event(text=OTHER_TEXT)
        info = self.runtime_info_event()
        context = self.context([allowed, genuine, info])
        findings = self.transcript(self.output([
            self.console_record(allowed),
            self.console_record(genuine, message=OTHER_TEXT),
            self.console_record(info, message="ready"),
        ], self.write_raw([allowed, genuine, info])), context)
        self.assertEqual(
            findings.count("HiFi offline transcript contains a console error"), 1
        )
        self.assertNotIn(
            "HiFi offline transcript native CSP diagnostic provenance is incomplete",
            findings,
        )

    def test_downgraded_native_runtime_errors_and_exceptions_stay_blocking(self) -> None:
        allowed = self.native_event()
        for kind in ("error", "assert", "exception"):
            with self.subTest(kind=kind):
                native = self.downgraded_runtime_event(kind=kind)
                context = self.context([allowed, native])
                findings = self.transcript(self.output([
                    self.console_record(allowed),
                    self.console_record(native, message="benign"),
                ], self.write_raw([allowed, native])), context)
                self.assertIn(
                    "HiFi offline transcript contains a console error", findings
                )
                self.assertIn(
                    "HiFi offline transcript native CSP diagnostic provenance is incomplete",
                    findings,
                )

    def test_url_query_or_foreign_page_is_not_matched(self) -> None:
        cases = (
            self.root.joinpath("index.html").as_uri() + "?drift=1",
            self.root.joinpath("child.html").as_uri().replace(
                "child.html", "%2e%2e%2Findex.html"
            ),
            self.root.joinpath("child.html").as_uri().replace(
                "child.html", "..%2Findex.html"
            ),
            self.root.joinpath("index.html").as_uri().replace(
                "index.html", "%69ndex.html"
            ),
            self.root.joinpath("foreign", "index.html").as_uri(),
        )
        for url in cases:
            with self.subTest(url=url):
                native = self.native_event(url=url)
                raw = self.write_raw([native])
                context = self.context([native])
                record = self.console_record(native, url=url)
                findings = self.transcript(
                    self.output([record], raw), context=context,
                )
                self.assertIn("HiFi offline transcript contains a console error", findings)

    def test_fragment_urls_and_manifest_child_pages_are_matched(self) -> None:
        for name in ("index.html", "child.html"):
            with self.subTest(page=name):
                url = self.root.joinpath(name).as_uri() + "#hifi-state=UI-001%2Fready"
                native = self.native_event(url=url)
                context = self.context([native])
                findings = self.transcript(
                    self.output(
                        [self.console_record(native, url=url)], self.write_raw([native])
                    ),
                    context,
                )
                self.assertEqual([], findings)

    def test_wrong_page_policy_rejects_the_context(self) -> None:
        from native_csp_diagnostic import build_context
        from check_ui_design_contract import _hifi_bundle_documents

        original = self.child.read_text(encoding="utf-8")
        self.child.write_text(original.replace("navigate-to 'self'", "navigate-to 'none'", 1),
                             encoding="utf-8", newline="")
        subject = self.root / "index.html"
        self.manifest["pages"] = [{"path": "child.html", "sha256": self.sha(self.child)}]
        subject_source = self.with_csp(fixture.add_shell(
            fixture._source_html(self.manifest["surfaces"][0], component_types=("button",), version=3),
            self.manifest, component_types=("button",), version=3,
        )).replace(
            "</head>",
            '<script id="ui-hifi-manifest" type="application/json">'
            + json.dumps(self.manifest) + "</script></head>",
            1,
        )
        subject.write_text(subject_source, encoding="utf-8", newline="")
        current_subject = self.binding(subject)
        subject_data = evidence.read_identity(self.root, current_subject)
        documents = _hifi_bundle_documents(
            evidence.safe_path(self.root, current_subject["path"]),
            subject_data.decode("utf-8"), self.manifest,
        )
        with self.assertRaises(ValueError):
            build_context(
                self.root, current_subject, self.manifest,
                [self.binding(self.prd), current_subject, self.binding(self.child), self.write_raw([self.native_event()])],
                documents,
            )

    def test_context_free_and_non_machine_output_remain_strict(self) -> None:
        event = self.native_event()
        output = self.output([self.console_record(event)], self.write_raw([event]))
        self.assertIn("HiFi offline transcript contains a console error",
                      self.transcript(output))

    def test_factory_pass_does_not_accept_a_strict_transcript(self) -> None:
        allowed = self.native_event()
        genuine = self.native_event(text=OTHER_TEXT)
        raw = self.write_raw([allowed, genuine])
        output = self.output([
            self.console_record(allowed),
            self.console_record(genuine, message=OTHER_TEXT),
        ], raw)
        output_binding = self.write(self.root / "docs/evidence/browser-output.json", output)
        receipt = evidence.build_receipt(self.root, output_binding["path"])
        self.assertEqual("PASS", receipt["result"])
        receipt_binding = self.write(self.root / "docs/evidence/browser.json", receipt)
        problems: list[str] = []
        ui_contract._resolve_evidence(
            f"PASS — evidence={receipt_binding['path']} @ sha256:{receipt_binding['sha256']}",
            repo_root=self.root, label="HiFi surface check", problems=problems,
            expected_artifact=self.subject["path"], expected_check="hifi-browser",
            expected_matrix=output["matrix"], require_machine=True,
        )
        self.assertIn("HiFi offline transcript contains a console error", " ".join(problems))

    def test_diagnostic_wave_treats_missing_provenance_as_structural(self) -> None:
        scores = {f"H{index}": 90 for index in range(1, 10)}
        case = {"surface": "UI-001", "state": "ready", "target": "390"}
        def wave(*, bind_raw: bool, event_url: str | None = None) -> list[str]:
            event = self.native_event(url=event_url)
            raw = self.write_raw([event])
            evidence_dir = self.root / "docs/evidence"
            evidence_dir.mkdir(parents=True, exist_ok=True)
            observations: dict[str, dict[str, str]] = {}
            for role, check in evidence.DIAGNOSTIC_CHECKS.items():
                if role == "browser":
                    output = self.output([self.console_record(event)], raw if bind_raw else None)
                else:
                    output = {
                        "schema": "ui-output/3", "check": check, "subject": self.subject,
                        "matrix": {"cases": [case]}, "results": [dict(case, result="PASS")],
                        "execution": {
                            "startedAt": "2026-01-01T00:00:00Z", "finishedAt": "2026-01-01T00:00:01Z",
                            "tool": "synthetic", "method": "browser-matrix",
                            "environment": {"runtime": "synthetic test fixture"},
                            "artifacts": [self.binding(self.prd), self.subject, self.binding(self.child)],
                        },
                        "assessment": {
                            "scores": scores, "blocks": [],
                            "observations": [dict(case, finding="Concrete synthetic rendering observation.",
                                                  evidence=[self.capture_binding])],
                        },
                    }
                output_binding = self.write(evidence_dir / f"{role}-output.json", output)
                receipt = evidence.build_receipt(self.root, output_binding["path"])
                observations[role] = self.write(evidence_dir / f"{role}.json", receipt)
            request = {
                "schema": evidence.DIAGNOSTIC_REQUEST_SCHEMA, "subject": self.subject,
                "frozenInputs": {"prd": self.binding(self.prd), "manifest": self.subject},
                "requiredCases": [case], "observations": observations,
            }
            request_binding = self.write(self.root / "diagnostic-request.json", request)
            return evidence.diagnostic_wave_findings(
                self.root, json.loads(request_binding and (self.root / "diagnostic-request.json").read_text("utf-8"))
            )

        self.assertEqual([], wave(bind_raw=True))
        self.assertIn("browser: HiFi offline transcript native CSP diagnostic provenance is incomplete",
                      wave(bind_raw=False))
        query_url = self.root.joinpath("index.html").as_uri() + "?drift=1"
        self.assertIn(
            "browser: HiFi offline transcript native CSP diagnostic provenance is incomplete",
            " ".join(wave(bind_raw=True, event_url=query_url)),
        )

if __name__ == "__main__":
    unittest.main()
