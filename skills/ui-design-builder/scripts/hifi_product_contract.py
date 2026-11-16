"""Direct PRD joins for the wireframe-free ui-hifi/2 preflight."""

import re
import json
from html.parser import HTMLParser
from typing import Any, Mapping

from check_wireframe_html import LOCALE_RE, validate_copy_item
from prd_ui_contract import parse_prd_ui_contract
from operation_coverage import hifi_coverage_findings, required_operations
from hifi_reviewer import ReviewerParser


UI_HIFI_COPY_RE = re.compile(
    r'<script\s+id=["\']ui-hifi-copy["\']\s+type=["\']application/json["\']\s*>'
    r"(?P<data>[\s\S]*?)</script>",
    re.IGNORECASE,
)
COPY_SOURCE_TAG_RE = re.compile(r"<script\b[^>]*\bid\s*=\s*[\"']ui-hifi-copy[\"']", re.IGNORECASE)


class _ProductCopyParser(HTMLParser):
    """Collect copy-bearing elements in product DOM, never reviewer chrome."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[tuple[str, str | None, dict[str, Any] | None]] = []
        self.records: list[dict[str, Any]] = []
        self.unbound: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        parent_surface = self.stack[-1][1] if self.stack else None
        parent_record = self.stack[-1][2] if self.stack else None
        inert = tag.lower() in {"template", "noscript", "script", "style"} or any(
            frame[0] in {"template", "noscript", "script", "style"} for frame in self.stack
        )
        declared_surface = values.get("data-ui-surface")
        surface = None if inert else (
            declared_surface.strip()
            if isinstance(declared_surface, str) and declared_surface.strip()
            else parent_surface
        )
        copy_id = values.get("data-copy-id")
        record = parent_record
        if (
            isinstance(copy_id, str)
            and copy_id.strip()
            and surface
        ):
            locale = values.get("data-copy-locale")
            copy_id = copy_id.strip()
            record = {
                "surface": surface,
                "id": copy_id,
                "locale": locale.strip() if isinstance(locale, str) else None,
                "text": [],
                "value": values.get("value"),
                "label": values.get("aria-label") or values.get("alt") or values.get("placeholder"),
                "tag": tag.lower(),
            }
            self.records.append(record)

        if surface and record is None and any(values.get(key) for key in ("aria-label", "alt", "placeholder")):
            self.unbound.append(surface)

        if tag not in {
            "area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr",
        }:
            self.stack.append((tag.lower(), surface, record))

    def handle_data(self, data: str) -> None:
        if self.stack:
            if any(frame[0] in {"template", "noscript", "script", "style"} for frame in self.stack):
                return
            record = self.stack[-1][2]
            if isinstance(record, dict) and isinstance(record.get("text"), list):
                record["text"].append(data)
            elif self.stack[-1][1] and data.strip():
                self.unbound.append(self.stack[-1][1])

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {
            "area", "base", "br", "col", "embed", "hr", "img", "input",
            "link", "meta", "param", "source", "track", "wbr",
        }:
            return
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break


def _normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()


def parse_hifi_copy(documents: Mapping[str, str]) -> tuple[dict[str, Any] | None, list[str]]:
    """Parse the index-only ui-hifi-copy/1 source contract."""

    if "index.html" not in documents:
        return None, ["ui-hifi-copy requires index.html"]
    matches = list(UI_HIFI_COPY_RE.finditer(documents["index.html"]))
    if len(matches) != 1 or len(COPY_SOURCE_TAG_RE.findall(documents["index.html"])) != 1:
        return None, ["HiFi requires exactly one index-only ui-hifi-copy source"]
    if any(COPY_SOURCE_TAG_RE.search(text) for name, text in documents.items() if name != "index.html"):
        return None, ["Only index.html may contain ui-hifi-copy"]
    try:
        value = json.loads(matches[0].group("data"))
    except ValueError as exc:
        return None, ["ui-hifi-copy is not valid JSON: " + str(exc)]
    if not isinstance(value, dict) or set(value) != {"schema", "locale", "surfaces"}:
        return None, ["ui-hifi-copy must contain exactly schema, locale, and surfaces"]
    if value.get("schema") != "ui-hifi-copy/1":
        return None, ["ui-hifi-copy schema must be ui-hifi-copy/1"]
    if not isinstance(value.get("locale"), str) or not LOCALE_RE.fullmatch(value["locale"]):
        return None, ["ui-hifi-copy locale must be a BCP 47-style language tag"]
    if not isinstance(value.get("surfaces"), list):
        return None, ["ui-hifi-copy surfaces must be an array"]
    return value, []


def _copy_dom_findings(
    documents: Mapping[str, str], copy_data: dict[str, Any]
) -> list[str]:
    records = []
    findings: list[str] = []
    for text in documents.values():
        parser = _ProductCopyParser()
        parser.feed(text)
        parser.close()
        records.extend(parser.records)
        if parser.unbound:
            findings.append("HiFi product text lacks data-copy-id in " + ", ".join(sorted(set(parser.unbound))))

    observed: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for record in records:
        key = (
            str(record.get("surface")),
            str(record.get("id")),
            str(record.get("locale")),
        )
        observed.setdefault(key, []).append(record)

    declared = set()
    for surface in copy_data.get("surfaces", []):
        if not isinstance(surface, dict):
            continue
        surface_id = surface.get("id")
        for item in surface.get("items", []):
            if not isinstance(item, dict):
                continue
            copy = item.get("copy")
            copy_id = item.get("id")
            if not isinstance(copy, dict) or not isinstance(copy_id, str):
                continue
            locales = [(copy.get("locale", copy_data["locale"]), _normalize_text(copy.get("text") or copy.get("example")))]
            pairs = copy.get("parallel", [])
            for paired in pairs if isinstance(pairs, list) else []:
                if isinstance(paired, dict):
                    locales.append((paired.get("locale"), _normalize_text(paired.get("text") or paired.get("example"))))

            for locale, expected in locales:
                if not isinstance(locale, str) or not locale:
                    continue
                declared.add((str(surface_id), copy_id, locale))
                candidates = observed.get((str(surface_id), copy_id, locale), [])
                if not candidates:
                    findings.append(
                        f"HiFi copy {surface_id}/{copy_id} lacks product DOM for locale {locale}"
                    )
                    continue
                # Visible text must match; value/label count only without it.
                matched = all(
                    _normalize_text("".join(record.get("text", []))) == expected
                    if _normalize_text("".join(record.get("text", [])))
                    else expected in {
                        _normalize_text(record.get("value")),
                        _normalize_text(record.get("label")),
                    }
                    for record in candidates
                )
                if not matched:
                    findings.append(
                        f"HiFi copy {surface_id}/{copy_id} product text differs from the source contract for locale {locale}"
                    )
    if set(observed) - declared:
        findings.append("HiFi product copy bindings contain undeclared IDs or locales")
    return findings


def hifi_copy_findings(
    prd_surfaces: Mapping[str, Mapping[str, Any]],
    manifest: Mapping[str, Any],
    documents: Mapping[str, str],
) -> list[str]:
    """Validate the source copy contract and its actual product DOM joins."""

    copy_data, findings = parse_hifi_copy(documents)
    if copy_data is None:
        return findings

    manifest_ids = {
        row.get("id") for row in manifest.get("surfaces", [])
        if isinstance(row, dict) and isinstance(row.get("id"), str)
    }
    copy_surfaces = copy_data.get("surfaces", [])
    if not isinstance(copy_surfaces, list):
        return findings + ["ui-hifi-copy surfaces must be an array"]
    copy_ids: list[str] = []
    for surface in copy_surfaces:
        if not isinstance(surface, dict) or set(surface) != {"id", "copyStatus", "items"}:
            findings.append("ui-hifi-copy surface must contain exactly id, copyStatus, and items")
            continue
        surface_id = surface.get("id")
        if not isinstance(surface_id, str) or not surface_id.strip() or surface_id in copy_ids:
            findings.append("ui-hifi-copy surface IDs must be unique non-empty strings")
            continue
        copy_ids.append(surface_id)
        status = surface.get("copyStatus")
        if status not in {"draft", "approved"}:
            findings.append(f"ui-hifi-copy {surface_id} copyStatus must be draft or approved")
        if not isinstance(surface.get("items"), list) or not surface["items"]:
            findings.append(f"ui-hifi-copy {surface_id} items must be a nonempty array")
            continue
        item_ids: list[str] = []
        for item in surface["items"]:
            if not isinstance(item, dict) or set(item) != {"id", "copy"}:
                findings.append(f"ui-hifi-copy {surface_id} item must contain exactly id and copy")
                continue
            item_id = item.get("id")
            if not isinstance(item_id, str) or not item_id.strip() or item_id in item_ids:
                findings.append(f"ui-hifi-copy {surface_id} item IDs must be unique non-empty strings")
                continue
            item_ids.append(item_id)
            copy_problems: list[str] = []
            validate_copy_item(item.get("copy"), f"ui-hifi-copy.{surface_id}.{item_id}.copy", copy_problems, require_approved=status == "approved")
            findings.extend(problem.replace("must be an object in wireframes/4", "must be a typed copy object") for problem in copy_problems)
        if status == "approved" and any(
            isinstance(item, dict)
            and isinstance(item.get("copy"), dict)
            and item["copy"].get("status") != "approved"
            for item in surface["items"]
        ):
            findings.append(f"ui-hifi-copy {surface_id} status approved requires every item to be approved")

    if set(copy_ids) != manifest_ids:
        findings.append(
            "ui-hifi-copy surfaces must exactly match the ui-hifi/2 manifest IDs"
        )
    for surface_id, prd in prd_surfaces.items():
        match = next((row for row in copy_surfaces if isinstance(row, dict) and row.get("id") == surface_id), None)
        prd_status = prd.get("copyStatus")
        if match is not None and match.get("copyStatus") != prd_status:
            findings.append(
                f"ui-hifi-copy {surface_id} copyStatus differs from PRD status {prd_status!r}"
            )

    if not findings:
        findings.extend(_copy_dom_findings(documents, copy_data))
    return findings


def hifi_prd_findings(
    prd_text: str,
    manifest: Mapping[str, Any],
    documents: Mapping[str, str],
) -> list[str]:
    """Return direct coverage findings without validating human approvals."""

    prd_surfaces, errors = parse_prd_ui_contract(
        prd_text,
        require_responsive=True,
        require_copy=True,
        web_floor=3,
    )
    findings = list(errors)
    if not isinstance(manifest, dict):
        return findings + ["HiFi manifest must be an object"]
    surfaces = manifest.get("surfaces")
    if not isinstance(surfaces, list):
        return findings + ["HiFi manifest surfaces must be an array"]

    by_id: dict[str, dict[str, Any]] = {}
    for row in surfaces:
        if not isinstance(row, dict) or not isinstance(row.get("id"), str):
            findings.append("HiFi manifest surface must have a string ID")
            continue
        if row["id"] in by_id:
            findings.append(f"HiFi manifest duplicates surface {row['id']}")
            continue
        by_id[row["id"]] = row

    if set(by_id) != set(prd_surfaces):
        missing = sorted(set(prd_surfaces) - set(by_id))
        extra = sorted(set(by_id) - set(prd_surfaces))
        findings.append(
            "HiFi surfaces do not exactly match PRD UI IDs"
            + (f"; missing={', '.join(missing)}" if missing else "")
            + (f"; extra={', '.join(extra)}" if extra else "")
        )

    for surface_id, expected in prd_surfaces.items():
        actual = by_id.get(surface_id)
        if actual is None:
            continue
        if actual.get("route") != (expected.get("routes") or [None])[0]:
            findings.append(f"HiFi {surface_id} route differs from PRD")
        if actual.get("states") != expected.get("states"):
            findings.append(f"HiFi {surface_id} states differ from PRD")
        actual_responsive = actual.get("responsive")
        expected_responsive = {
            "kind": expected.get("responsiveKind"),
            "targets": [int(value) if str(value).isdigit() else value for value in expected.get("responsiveTargets", [])],
        }
        if actual_responsive != expected_responsive:
            findings.append(f"HiFi {surface_id} responsive set differs from PRD")
        if expected.get("responsiveKind") == "viewports":
            actual_targets = actual_responsive.get("targets", []) if isinstance(actual_responsive, dict) else []
            normalized = [str(value) for value in actual_targets]
            if normalized != [str(value) for value in expected_responsive["targets"]]:
                findings.append(f"HiFi {surface_id} viewport targets must exactly match PRD")

    findings.extend(hifi_coverage_findings(prd_text, manifest))
    operations, operation_errors = required_operations(prd_text)
    if not operation_errors:
        terminal = set(prd_surfaces) - {row["surface"] for row in operations}
        for surface_id in terminal:
            actual = by_id.get(surface_id, {})
            if actual.get("navigation", []) or actual.get("controls", []):
                findings.append(f"HiFi {surface_id} has controls but PRD operations are none")
        for html in documents.values():
            parser = ReviewerParser()
            parser.feed(html)
            parser.close()
            for tag, attrs, parents in parser.nodes:
                surface_id = next((p["data-ui-surface"] for p in reversed(parents) if "data-ui-surface" in p), None)
                if (surface_id in terminal and id(attrs) not in parser.inert_nodes
                    and (tag in {"a", "button", "input", "select", "textarea"}
                         or attrs.get("role") in {"tab", "button", "link", "menuitem"})):
                    findings.append(f"HiFi {surface_id} renders a product control but PRD operations are none")
    findings.extend(hifi_copy_findings(prd_surfaces, manifest, documents))
    return findings
