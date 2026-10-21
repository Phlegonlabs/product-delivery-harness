"""Exact provenance for the browser's one mandated HiFi CSP diagnostic."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from urllib.parse import urlsplit

import check_wireframe_html

NATIVE_EVENT_TYPES = {
    "Log.entryAdded", "Runtime.consoleAPICalled", "Runtime.exceptionThrown",
}
MANDATED_TEXT = "Unrecognized Content-Security-Policy directive 'navigate-to'."
ALIAS_KEYS = ("level", "message", "url")


def _identity(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _native_severity(native: dict) -> str:
    native_type = native.get("type")
    params = native.get("params")
    if not isinstance(params, dict):
        return ""
    if native_type == "Log.entryAdded":
        entry = params.get("entry")
        return entry.get("level", "") if isinstance(entry, dict) else ""
    if native_type == "Runtime.consoleAPICalled":
        value = params.get("type", "")
        if value in {"error", "assert"}:
            return "error"
        return "info" if value == "log" else str(value)
    if native_type == "Runtime.exceptionThrown":
        return "error"
    return ""


class NativeCspContext:
    """One validation call's verified pages and native console observations."""

    def __init__(
        self,
        *,
        root: Path,
        documents: dict[str, str],
        page_paths: dict[Path, str],
        native_events: Counter[str],
    ) -> None:
        self.root = root
        self.documents = documents
        self.page_paths = page_paths
        self.native_events = native_events
        self.lookup_count = 0

    def _unused_native_identity(self, event: object) -> str | None:
        """Return one unused raw identity when the complete event agrees."""

        if not isinstance(event, dict) or event.get("type") not in NATIVE_EVENT_TYPES:
            return None
        params = event.get("params")
        if not isinstance(params, dict) or event.get("at") is None:
            return None
        entry = params.get("entry") if event.get("type") == "Log.entryAdded" else None
        if event.get("type") == "Log.entryAdded" and not isinstance(entry, dict):
            return None
        observed_url = entry.get("url") if isinstance(entry, dict) else event.get("url")
        if self._event_page(observed_url) is None:
            return None
        for mask in range(1 << len(ALIAS_KEYS)):
            candidate = dict(event)
            for index, key in enumerate(ALIAS_KEYS):
                if mask & (1 << index):
                    candidate.pop(key, None)
            identity = _identity(candidate)
            self.lookup_count += 1
            if self.native_events.get(identity, 0) > 0:
                return identity
        return None

    def alias_mismatch(self, identity: str, event: object) -> bool:
        if not isinstance(event, dict):
            return True
        native = json.loads(identity)
        params = native.get("params")
        if not isinstance(params, dict):
            return True
        if native.get("type") == "Log.entryAdded":
            entry = params.get("entry")
            if not isinstance(entry, dict):
                return True
            return (
                event.get("level") != entry.get("level")
                or event.get("message") != entry.get("text")
                or event.get("url") != entry.get("url")
            )
        if event.get("level") != _native_severity(native):
            return True
        return any(
            key in event and event.get(key) != value
            for key, value in native.items()
        )

    def native_error(self, identity: str) -> bool:
        native = json.loads(identity)
        return _native_severity(native) in {
            "error", "assert", "exception", "uncaught",
        }

    def match_observation(self, event: object) -> str | None:
        """Return one unused raw identity for any normalized native observation."""

        return self._unused_native_identity(event)

    def match(self, event: object) -> str | None:
        """Return one unused native identity when every exact claim agrees."""

        if not isinstance(event, dict) or event.get("type") != "Log.entryAdded":
            return None
        params = event.get("params")
        entry = params.get("entry") if isinstance(params, dict) else None
        if not isinstance(entry, dict) or event.get("at") is None:
            return None
        if entry.get("source") != "security" or entry.get("level") != "error":
            return None
        if entry.get("text") != MANDATED_TEXT or event.get("message") != MANDATED_TEXT:
            return None
        if event.get("level") != "error" or event.get("url") != entry.get("url"):
            return None
        page = self._event_page(entry.get("url"))
        if page is None:
            return None
        return self._unused_native_identity(event)

    def consume(self, identity: str) -> None:
        self.native_events[identity] -= 1

    def unmatched_findings(self) -> list[str]:
        total = sum(count for count in self.native_events.values() if count > 0)
        return [
            "HiFi offline transcript omits a native console observation"
        ] if total else []

    def _event_page(self, url: object) -> str | None:
        if not isinstance(url, str):
            return None
        try:
            parsed = urlsplit(url)
            if parsed.scheme.lower() != "file" or parsed.query or not parsed.path:
                return None
            for path, name in self.page_paths.items():
                expected = urlsplit(path.as_uri())
                if parsed.netloc == expected.netloc and parsed.path == expected.path:
                    return name
        except ValueError:
            return None
        return None


def build_context(
    root: Path,
    subject: dict[str, object],
    manifest: dict[str, object],
    artifacts: list[object],
    documents: dict[str, str],
) -> NativeCspContext:
    """Build and verify the closed provenance context for one validation."""

    from review_evidence import read_identity, safe_path

    root = Path(root).resolve()
    pages = manifest.get("pages")
    if manifest.get("schema") != "ui-hifi/2" or not isinstance(pages, list):
        raise ValueError("native CSP diagnostic provenance requires ui-hifi/2")
    if not isinstance(subject, dict) or any(not isinstance(item, dict) for item in artifacts):
        raise ValueError("native CSP diagnostic provenance has invalid bindings")
    seen: set[str] = set()
    for binding in artifacts:
        path = str(binding.get("path", "")).casefold()
        if path in seen:
            raise ValueError("native CSP diagnostic provenance repeats an input")
        seen.add(path)

    subject_present = any(binding == subject for binding in artifacts)
    child_bindings = [
        {"path": (Path(str(subject["path"])).parent / str(row["path"])).as_posix(), "sha256": row["sha256"]}
        for row in pages if isinstance(row, dict)
    ]
    children_present = all(any(binding == child for binding in artifacts) for child in child_bindings)
    if not subject_present or not children_present:
        raise ValueError("native CSP diagnostic provenance lacks the HiFi entry or child identities")

    page_paths: dict[Path, str] = {}
    package_parent = Path(str(subject["path"])).parent
    expected_policy = check_wireframe_html.REQUIRED_HIFI_CSP.replace(
        "navigate-to 'none'", "navigate-to 'self'"
    )
    for name, html in documents.items():
        package_relative = (package_parent / name).as_posix()
        safe_path(root, package_relative)
        parser = check_wireframe_html.ResourceParser()
        parser.feed(html)
        parser.close()
        if parser.csp_document_errors or len(parser.content_security_policies) != 1:
            raise ValueError(f"HiFi {name} lacks one correctly placed canonical CSP")
        if parser.content_security_policies[0] != expected_policy:
            raise ValueError(f"HiFi {name} does not use the exact mandated local-page CSP")
        page_paths[safe_path(root, package_relative).resolve(strict=True)] = name

    native_events: Counter[str] = Counter()
    for binding in artifacts:
        relative = str(binding.get("path", ""))
        if relative.casefold().endswith((".html", ".md")):
            continue
        try:
            payload = json.loads(read_identity(root, binding).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeError):
            continue
        events = payload.get("events") if isinstance(payload, dict) else payload
        if not isinstance(events, list):
            continue
        for event in events:
            if not isinstance(event, dict) or event.get("type") not in NATIVE_EVENT_TYPES:
                continue
            params = event.get("params")
            if not isinstance(params, dict):
                raise ValueError("native console observation has malformed params")
            if event.get("type") == "Log.entryAdded" and not isinstance(params.get("entry"), dict):
                raise ValueError("native Log observation has malformed entry")
            native_events[_identity(event)] += 1
    return NativeCspContext(
        root=root, documents=documents, page_paths=page_paths, native_events=native_events,
    )


def context_failure(message: object) -> str:
    return "native CSP diagnostic context is incomplete: " + str(message)
