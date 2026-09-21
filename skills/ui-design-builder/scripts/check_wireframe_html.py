#!/usr/bin/env python3
"""Validate a self-contained UI Design Builder wireframe projection."""

from __future__ import annotations

import argparse
from datetime import date
import hashlib
import json
import math
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

PRODUCT_BUILDER_SCRIPTS = (
    Path(__file__).resolve().parents[2] / "product-definition-builder" / "scripts"
)
if str(PRODUCT_BUILDER_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(PRODUCT_BUILDER_SCRIPTS))

from prd_ui_contract import validate_prd_wireframe_data


DATA_BLOCK_RE = re.compile(
    r'<script\s+id=["\']wireframe-data["\']\s+type=["\']application/json["\']\s*>'
    r"(?P<data>[\s\S]*?)</script>",
    re.IGNORECASE,
)
CSS_URL_RE = re.compile(
    r"""url\s*\(\s*(?:
        "(?P<double>[^"]+)"
        |'(?P<single>[^']+)'
        |(?P<bare>[^\s)]+)
    )\s*\)""",
    re.IGNORECASE | re.VERBOSE,
)
CSS_IMAGE_SET_RE = re.compile(r"(?:-webkit-)?image-set\s*\(", re.IGNORECASE)
REMOTE_CSS_STRING_RE = re.compile(
    r"""(?:
        "(?P<double>(?:https?:)?//[^"]+)"
        |'(?P<single>(?:https?:)?//[^']+)'
        |(?P<bare>(?<![A-Za-z0-9_'\"])(?:https?:)?//[^\s,)'\"]+)
    )""",
    re.IGNORECASE | re.VERBOSE,
)
CSS_STRING_RE = re.compile(r'"(?P<double>[^"]+)"|\'(?P<single>[^\']+)\'')
REMOTE_SCRIPT_URL_RE = re.compile(r"(?:https?:)?//", re.IGNORECASE)
NETWORK_SCRIPT_RE = re.compile(
    r"\b(?:fetch|XMLHttpRequest|WebSocket|EventSource|sendBeacon|"
    r"importScripts|Worker|SharedWorker)\b|\bimport\b",
    re.IGNORECASE,
)
RUNTIME_QA_RE = re.compile(
    r"function\s+runLayoutQa\s*\(|(?:const|let|var)\s+runLayoutQa\s*=",
    re.IGNORECASE,
)
DYNAMIC_ATTRIBUTE_RE = re.compile(
    r"setAttribute\(\s*['\"]([a-z0-9_.:-]+)['\"]",
    re.IGNORECASE,
)
SAFE_DATA_IMAGE_TYPES = {
    "image/apng",
    "image/avif",
    "image/bmp",
    "image/gif",
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}
RESOURCE_ATTRIBUTES = {
    "href",
    "src",
    "srcset",
    "poster",
    "data",
    "xlink:href",
    "action",
    "formaction",
    "ping",
    "cite",
    "background",
    "manifest",
}
SAFE_DATA_FONT_TYPES = {
    "font/otf",
    "font/ttf",
    "font/woff",
    "font/woff2",
    "application/font-sfnt",
    "application/vnd.ms-fontobject",
    "application/x-font-ttf",
    "application/x-font-woff",
}
SAFE_DATA_AUDIO_TYPES = {
    "audio/aac",
    "audio/flac",
    "audio/mpeg",
    "audio/ogg",
    "audio/wav",
    "audio/webm",
}
SAFE_DATA_VIDEO_TYPES = {
    "video/mp4",
    "video/mpeg",
    "video/ogg",
    "video/webm",
}
SAFE_DATA_IMAGE_TAGS = {"img", "input", "object", "picture", "source"}
PLACEHOLDER_RE = re.compile(r"<[^<>]+>")
LOCALE_RE = re.compile(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")
VALID_APPROVAL_STATUSES = {"draft", "approved", "revision_requested", "blocked"}
VALID_PRIORITIES = {"primary", "secondary", "quiet"}
VALID_FLOW_PRESENTATIONS = {"page", "overlay", "feedback"}
VALID_MEDIA_TREATMENTS = {"none", "image", "motion", "image + motion"}
LEGACY_MEDIA_TREATMENTS = {"motion-led", "imagery-led", "motion + imagery"}
VALID_COPY_ITEM_STATUSES = {"draft", "approved"}
VALID_COPY_KINDS = {"static", "dynamic"}
COPY_CONTRACT_FIELDS = ("source", "order", "format", "count", "length", "fallback")
COMPOSITION_KEYS = {"canvas", "regions"}
COMPOSITION_CANVAS_KEYS = {"padding", "gap"}
COMPOSITION_REGION_KEYS = {
    "padding",
    "gap",
    "maxWidth",
    "actionsPlacement",
    "itemColumns",
    "mediaAspectRatio",
}
VALID_ACTION_PLACEMENTS = {"before", "after", "inline"}
LOCAL_SEARCH_KEYS = {
    "formRegion",
    "resultsRegion",
    "queryLabel",
    "languageLabel",
    "languageOptions",
    "submitAction",
    "clearAction",
    "states",
    "items",
}
LOCAL_SEARCH_STATE_KEYS = {"initial", "results", "empty"}
LOCAL_SEARCH_OPTION_KEYS = {"value", "copy"}
LOCAL_SEARCH_ITEM_KEYS = {"language", "copy", "searchText"}
LOCAL_SEARCH_MAX_OPTIONS = 8
LOCAL_SEARCH_MAX_ITEMS = 10000
LOCAL_SEARCH_MAX_VALUE_LENGTH = 48
LOCAL_SEARCH_MAX_SEARCH_TEXT_LENGTH = 4096
NON_HUMAN_OWNERS = {
    "ai",
    "agent",
    "assistant",
    "automation",
    "codex",
    "model",
    "system",
}
WIREFRAME_SCHEMA = "wireframes/4"
INTERACTIVE_WIREFRAME_SCHEMAS = {"wireframes/3", WIREFRAME_SCHEMA}
LEGACY_WIREFRAME_SCHEMAS = {"wireframes/2", "wireframes/3"}

# Connected HiFi references are rendered as a local, offline review target.
# Keep this policy closed and deterministic: a publication either carries this
# exact directive set or it is rejected.  The browser receipt separately proves
# that the sandbox observed no request, navigation, popup, form submission, or
# console error; this static policy is not a claim that regex can prove arbitrary
# JavaScript safety.
HIFI_CSP_DIRECTIVES = (
    ("default-src", ("'none'",)),
    ("base-uri", ("'none'",)),
    ("connect-src", ("'none'",)),
    ("form-action", ("'none'",)),
    ("frame-src", ("'none'",)),
    ("object-src", ("'none'",)),
    ("navigate-to", ("'none'",)),
    ("img-src", ("data:",)),
    ("media-src", ("data:",)),
    ("font-src", ("data:",)),
    ("style-src", ("'unsafe-inline'",)),
    ("script-src", ("'unsafe-inline'",)),
)
REQUIRED_HIFI_CSP = "; ".join(
    f"{directive} {' '.join(tokens)}" for directive, tokens in HIFI_CSP_DIRECTIVES
)
HIFI_CSP_DIRECTIVE_MAP = dict(HIFI_CSP_DIRECTIVES)


def validate_hifi_csp_policy(value: str) -> list[str]:
    """Return deterministic findings for the closed HiFi CSP policy."""

    if not isinstance(value, str) or not value.strip():
        return ["HiFi CSP policy is missing"]
    directives: dict[str, tuple[str, ...]] = {}
    for raw_directive in value.split(";"):
        parts = raw_directive.strip().split()
        if not parts:
            return ["HiFi CSP policy contains an empty directive"]
        name = parts[0].casefold()
        if name not in HIFI_CSP_DIRECTIVE_MAP:
            return [f"HiFi CSP policy contains unknown directive {name!r}"]
        if name in directives:
            return [f"HiFi CSP policy duplicates directive {name!r}"]
        directives[name] = tuple(parts[1:])
    expected = dict(HIFI_CSP_DIRECTIVES)
    if value.strip() != REQUIRED_HIFI_CSP:
        return [
            "HiFi CSP policy must exactly equal the required offline policy: "
            + REQUIRED_HIFI_CSP
        ]
    if tuple(directives) != tuple(expected):
        return ["HiFi CSP policy directives must use the canonical closed order"]
    for name, tokens in expected.items():
        if directives.get(name) != tokens:
            return [f"HiFi CSP policy directive {name!r} is weakened or malformed"]
    return []


def _normalize_url(value: str) -> str:
    """Remove characters browsers ignore while recognizing a URL scheme."""

    return re.sub(r"[\x00-\x20\x7f]+", "", value)


def _url_scheme(value: str) -> str:
    match = re.match(r"([A-Za-z][A-Za-z0-9+.-]*):", _normalize_url(value))
    return match.group(1).lower() if match else ""


def _is_network_url(value: str) -> bool:
    normalized = _normalize_url(value)
    return normalized.startswith("//") or _url_scheme(normalized) in {
        "http",
        "https",
    }


def _is_local_navigation(value: str) -> bool:
    normalized = _normalize_url(value)
    return not normalized or normalized.startswith("#")


def _data_media_type(value: str) -> str | None:
    normalized = _normalize_url(value)
    if not normalized.lower().startswith("data:"):
        return None
    payload = normalized[5:]
    comma = payload.find(",")
    if comma < 0:
        return None
    return payload[:comma].split(";", 1)[0].strip().lower() or "text/plain"


def _is_safe_data_url(
    value: str,
    *,
    allow_images: bool = True,
    allow_fonts: bool = False,
    allow_audio: bool = False,
    allow_video: bool = False,
) -> bool:
    media_type = _data_media_type(value)
    if media_type is None:
        return False
    if allow_images and media_type in SAFE_DATA_IMAGE_TYPES:
        return True
    if allow_fonts and media_type in SAFE_DATA_FONT_TYPES:
        return True
    if allow_audio and media_type in SAFE_DATA_AUDIO_TYPES:
        return True
    if allow_video and media_type in SAFE_DATA_VIDEO_TYPES:
        return True
    return False


def _is_safe_embedded_css_resource(
    value: str,
    *,
    allow_fonts: bool = False,
) -> bool:
    normalized = _normalize_url(value)
    return normalized.startswith("#") or _is_safe_data_url(
        normalized,
        allow_fonts=allow_fonts,
    )


def _srcset_urls(value: str) -> list[str]:
    """Return candidate URLs without splitting the required comma in data URLs."""

    urls: list[str] = []
    position = 0
    length = len(value)
    while position < length:
        while position < length and (value[position].isspace() or value[position] == ","):
            position += 1
        if position >= length:
            break
        start = position
        if value[position : position + 5].casefold() == "data:":
            while position < length and not value[position].isspace():
                position += 1
        else:
            while position < length and not value[position].isspace() and value[position] != ",":
                position += 1
        urls.append(value[start:position])
        while position < length and value[position] != ",":
            position += 1
    return urls


def _strip_javascript_comments(code: str) -> str:
    """Blank JS comments so commented network code cannot be treated as live."""

    output: list[str] = []
    index = 0
    quote: str | None = None
    escaped = False
    while index < len(code):
        character = code[index]
        if quote is not None:
            output.append(character)
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
            index += 1
            continue
        if character in {"'", '"', "`"}:
            quote = character
            output.append(character)
            index += 1
            continue
        if code.startswith("//", index):
            end = code.find("\n", index + 2)
            if end < 0:
                break
            output.append("\n")
            index = end + 1
            continue
        if code.startswith("/*", index):
            end = code.find("*/", index + 2)
            if end < 0:
                break
            output.append(" ")
            index = end + 2
            continue
        if code.startswith("<!--", index):
            end = code.find("\n", index + 4)
            if end < 0:
                break
            output.append("\n")
            index = end + 1
            continue
        output.append(character)
        index += 1
    return "".join(output)


def _strip_css_comments(css: str) -> str:
    """Remove CSS comments without treating comment markers inside strings as syntax."""

    output: list[str] = []
    index = 0
    quote: str | None = None
    escaped = False
    while index < len(css):
        char = css[index]
        if quote is not None:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue
        if char in {"'", '"'}:
            quote = char
            output.append(char)
            index += 1
            continue
        if css.startswith("/*", index):
            end = css.find("*/", index + 2)
            index = len(css) if end < 0 else end + 2
            output.append(" ")
            continue
        output.append(char)
        index += 1
    return "".join(output)


def _decode_css_escapes(css: str) -> str:
    """Decode CSS escapes before checking resource-bearing CSS tokens.

    CSS permits escaped code points in identifiers and strings, including the
    protocol prefix inside ``url()`` and the names of ``image-set`` and
    ``@import``.  Decode the standard one-to-six hexadecimal form (including
    its optional whitespace terminator) and the single-character form.  The
    caller strips comments first, so decoding cannot turn comment contents into
    active CSS, and JSON-recorded URLs never enter this CSS-only path.
    """

    output: list[str] = []
    index = 0
    hexadecimal = set("0123456789abcdefABCDEF")
    whitespace = {" ", "\t", "\r", "\n", "\f"}
    while index < len(css):
        character = css[index]
        if character != "\\":
            output.append(character)
            index += 1
            continue

        index += 1
        if index >= len(css):
            output.append("\ufffd")
            break

        character = css[index]
        if character in "\r\n\f":
            # A backslash-newline is a CSS line continuation.
            if character == "\r" and index + 1 < len(css) and css[index + 1] == "\n":
                index += 1
            index += 1
            continue

        if character in hexadecimal:
            start = index
            while index < len(css) and index - start < 6 and css[index] in hexadecimal:
                index += 1
            code_point = int(css[start:index], 16)
            if index < len(css) and css[index] in whitespace:
                if css[index] == "\r" and index + 1 < len(css) and css[index + 1] == "\n":
                    index += 1
                index += 1
            if code_point == 0 or code_point > 0x10FFFF or 0xD800 <= code_point <= 0xDFFF:
                output.append("\ufffd")
            else:
                output.append(chr(code_point))
            continue

        # A non-hex escaped character represents that character literally.
        output.append(character)
        index += 1

    return "".join(output)


class ResourceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.data_block_count = 0
        self.data_blocks: list[str] = []
        self.duplicate_attributes: list[str] = []
        self.external_resources: list[str] = []
        self.external_css_resources: list[str] = []
        self.active_security_surfaces: list[str] = []
        self.active_attribute_names: set[str] = set()
        self.active_ids: set[str] = set()
        self.active_classes: set[str] = set()
        self.active_text: list[str] = []
        self.executable_scripts: list[str] = []
        self.css_imports = False
        self._data_block: list[str] | None = None
        self._style_depth = 0
        self._css_chunks: list[str] = []
        self._inert_depth = 0
        self._in_script = False
        self._script_is_executable = False
        self.link_tags = 0
        self.content_security_policies: list[str] = []
        self.csp_document_errors: list[str] = []
        self.head_depth = 0
        self.body_depth = 0
        self.body_started = False
        self._document_order = 0
        self._first_csp_blocking_order: int | None = None

    @staticmethod
    def _csp_blocking_element(
        tag_name: str, values: dict[str, str | None]
    ) -> bool:
        if tag_name in {
            "script",
            "style",
            "link",
            "img",
            "audio",
            "video",
            "source",
            "track",
            "iframe",
            "object",
            "embed",
            "form",
        }:
            return True
        return any(
            name.casefold() in RESOURCE_ATTRIBUTES or name.casefold() == "style"
            for name in values
        )

    @staticmethod
    def _is_executable_script(script_type: str | None) -> bool:
        if script_type is None:
            return True
        media_type = script_type.strip().partition(";")[0].strip().lower()
        return media_type in {
            "",
            "application/ecmascript",
            "application/javascript",
            "application/x-ecmascript",
            "application/x-javascript",
            "module",
            "text/ecmascript",
            "text/javascript",
            "text/jscript",
            "text/x-ecmascript",
            "text/x-javascript",
        }

    def _record_url(self, tag: str, name: str, value: str) -> None:
        if not value:
            return
        lowered = _normalize_url(value).lower()
        if lowered.startswith("javascript:"):
            self.active_security_surfaces.append(f"{tag}[{name}=javascript:]")
            return

        if lowered.startswith("data:"):
            data_allowed = tag in SAFE_DATA_IMAGE_TAGS and name in RESOURCE_ATTRIBUTES
            if tag == "audio" and name in RESOURCE_ATTRIBUTES:
                data_allowed = _is_safe_data_url(
                    value, allow_images=False, allow_audio=True
                )
            elif tag == "video" and name in RESOURCE_ATTRIBUTES:
                data_allowed = _is_safe_data_url(
                    value, allow_images=False, allow_video=True
                )
            elif tag == "source" and name in RESOURCE_ATTRIBUTES:
                data_allowed = _is_safe_data_url(
                    value,
                    allow_images=True,
                    allow_audio=True,
                    allow_video=True,
                )
            elif data_allowed:
                data_allowed = _is_safe_data_url(value)
            if not data_allowed:
                self.active_security_surfaces.append(f"{tag}[{name}=data:]")
            return

        if name in {"action", "formaction"}:
            if not _is_local_navigation(value):
                self.active_security_surfaces.append(
                    f"{tag}[{name}={value.strip()!r}]"
                )
            return

        if tag == "a" and name == "href":
            if not _is_local_navigation(value):
                self.active_security_surfaces.append(
                    f"{tag}[{name}={value.strip()!r}]"
                )
            return

        if name == "href" and _normalize_url(value).startswith("#"):
            return

        if name in RESOURCE_ATTRIBUTES and value.strip():
            self.external_resources.append(f"{tag}[{name}={value!r}]")
            return

        if _is_network_url(value):
            if tag == "script" and name == "src":
                self.active_security_surfaces.append(f"{tag}[{name}={value!r}]")
            else:
                self.external_resources.append(f"{tag}[{name}={value!r}]")
        elif _url_scheme(value) and name in {
            "src",
            "href",
            "xlink:href",
            "poster",
            "data",
        }:
            self.external_resources.append(f"{tag}[{name}={value!r}]")

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag_name = tag.lower()
        self._document_order += 1
        order = self._document_order
        if self._inert_depth:
            if tag_name == "template":
                self._inert_depth += 1
            return
        if tag_name == "template":
            if any(name.lower() == "shadowrootmode" for name, _ in attrs):
                self.active_security_surfaces.append("template[shadowrootmode]")
            self._inert_depth += 1
            return

        seen_attributes: set[str] = set()
        for name, _ in attrs:
            lowered_name = name.lower()
            if lowered_name in seen_attributes:
                self.duplicate_attributes.append(f"{tag_name}[{lowered_name}]")
            seen_attributes.add(lowered_name)
        values = dict(attrs)
        if tag_name == "head":
            self.head_depth += 1
        elif tag_name == "body":
            self.body_depth += 1
            self.body_started = True
        is_csp_meta = (
            tag_name == "meta"
            and values.get("http-equiv", "").strip().casefold()
            == "content-security-policy"
        )
        if is_csp_meta:
            if self.head_depth != 1:
                self.csp_document_errors.append("CSP meta must be inside <head>")
            if self.body_started:
                self.csp_document_errors.append("CSP meta must appear before <body>")
            if self._first_csp_blocking_order is not None:
                self.csp_document_errors.append(
                    "CSP meta must appear before every script, style, link, or resource-bearing element"
                )
        elif self._first_csp_blocking_order is None and self._csp_blocking_element(
            tag_name, values
        ):
            self._first_csp_blocking_order = order
        self.active_attribute_names.update(name.lower() for name in values)
        for name in values:
            if re.fullmatch(r"on[a-z0-9_-]+", name, re.IGNORECASE):
                self.active_security_surfaces.append(
                    f"{tag_name}[{name.lower()}] inline event handler"
                )
        identifier = values.get("id")
        if identifier:
            self.active_ids.add(identifier)
        classes = values.get("class")
        if classes:
            self.active_classes.update(classes.split())

        if tag_name == "link":
            self.link_tags += 1
        if is_csp_meta:
            self.content_security_policies.append(values.get("content", "") or "")
        if tag_name == "script":
            script_id = values.get("id")
            script_type = values.get("type")
            self._in_script = True
            self._script_is_executable = self._is_executable_script(script_type)
            if (
                isinstance(script_id, str)
                and script_id.strip().lower() == "wireframe-data"
                and isinstance(script_type, str)
                and script_type.strip().lower() == "application/json"
            ):
                self.data_block_count += 1
                self._data_block = []
        elif tag_name == "style":
            self._style_depth += 1

        if (
            tag_name == "base"
            and isinstance(values.get("href"), str)
        ):
            self.active_security_surfaces.append("base[href]")
        if (
            tag_name == "meta"
            and values.get("http-equiv", "").strip().lower() == "refresh"
        ):
            self.active_security_surfaces.append("meta[http-equiv=refresh]")
        if tag_name == "iframe" and values.get("srcdoc"):
            self.active_security_surfaces.append("iframe[srcdoc]")

        inline_style = values.get("style")
        if inline_style:
            self._css_chunks.append(inline_style)

        for name in (
            "src",
            "href",
            "xlink:href",
            "poster",
            "action",
            "formaction",
            "cite",
            "background",
            "manifest",
        ):
            value = values.get(name)
            if isinstance(value, str):
                self._record_url(tag_name, name.lower(), value)

        ping = values.get("ping")
        if isinstance(ping, str):
            for target in re.split(r"\s+", ping.strip()):
                if target:
                    self._record_url(tag_name, "ping", target)

        if tag_name == "object":
            value = values.get("data")
            if isinstance(value, str):
                self._record_url(tag_name, "data", value)

        srcset = values.get("srcset")
        if srcset:
            for resource in _srcset_urls(srcset):
                self._record_url(tag_name, "srcset", resource)

    def handle_data(self, data: str) -> None:
        if self._data_block is not None:
            self._data_block.append(data)
            return
        if self._inert_depth:
            return
        if self._style_depth:
            self._css_chunks.append(data)
            return
        if self._in_script:
            if self._script_is_executable:
                self.executable_scripts.append(data)
            return
        self.active_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag_name = tag.lower()
        if self._inert_depth:
            if tag_name == "template":
                self._inert_depth -= 1
            return
        if tag_name == "head" and self.head_depth:
            self.head_depth -= 1
        elif tag_name == "body" and self.body_depth:
            self.body_depth -= 1
        if tag_name == "script":
            if self._data_block is not None:
                self.data_blocks.append("".join(self._data_block))
                self._data_block = None
            self._in_script = False
            self._script_is_executable = False
        elif tag_name == "style" and self._style_depth:
            self._style_depth -= 1

    def close(self) -> None:
        super().close()
        css = _decode_css_escapes(_strip_css_comments("\n".join(self._css_chunks)))
        self.css_imports = re.search(r"@import\b", css, re.IGNORECASE) is not None
        for match in CSS_URL_RE.finditer(css):
            resource = next(
                value for value in match.groups() if value is not None
            )
            # A data font is allowed only from an @font-face rule.  Images
            # remain valid embedded CSS resources; audio/video data belongs in
            # media elements where the CSP media-src directive applies.
            context = css[max(0, match.start() - 256) : match.start()]
            allow_fonts = re.search(r"@font-face\b", context, re.IGNORECASE) is not None
            if not _is_safe_embedded_css_resource(resource, allow_fonts=allow_fonts):
                self.external_css_resources.append(f"CSS url({resource!r})")
        for match in CSS_IMAGE_SET_RE.finditer(css):
            start = match.end()
            depth = 1
            quote: str | None = None
            escaped = False
            index = start
            while index < len(css) and depth:
                character = css[index]
                if quote is not None:
                    if escaped:
                        escaped = False
                    elif character == "\\":
                        escaped = True
                    elif character == quote:
                        quote = None
                elif character in {"'", '"'}:
                    quote = character
                elif character == "(":
                    depth += 1
                elif character == ")":
                    depth -= 1
                index += 1
            contents = css[start : index - 1 if depth == 0 else index]
            for resource_match in REMOTE_CSS_STRING_RE.finditer(contents):
                resource = next(
                    value
                    for value in resource_match.groups()
                    if value is not None
                )
                self.external_css_resources.append(
                    f"CSS image-set({resource!r})"
                )
            for resource_match in CSS_STRING_RE.finditer(contents):
                prefix = contents[max(0, resource_match.start() - 8) : resource_match.start()]
                if re.search(r"type\s*\(\s*$", prefix, re.IGNORECASE):
                    continue
                resource = next(
                    value
                    for value in resource_match.groups()
                    if value is not None
                )
                if not _is_safe_embedded_css_resource(resource):
                    self.external_css_resources.append(
                        f"CSS image-set({resource!r})"
                    )
        executable_code = _strip_javascript_comments(
            "\n".join(self.executable_scripts)
        )
        if REMOTE_SCRIPT_URL_RE.search(executable_code):
            self.active_security_surfaces.append("script external URL")
        for match in NETWORK_SCRIPT_RE.finditer(executable_code):
            self.active_security_surfaces.append(
                f"script network API {match.group(0).strip()!r}"
            )


def _shell_without_product_data(html_text: str) -> str | None:
    normalized = html_text.replace("\r\n", "\n")
    matches = list(DATA_BLOCK_RE.finditer(normalized))
    if len(matches) != 1:
        return None
    match = matches[0]
    start, end = match.span("data")
    return normalized[:start] + "\n__PRODUCT_WIREFRAME_DATA__\n" + normalized[end:]


def canonical_shell_sha256(html_text: str) -> str | None:
    shell = _shell_without_product_data(html_text)
    if shell is None:
        return None
    return hashlib.sha256(shell.encode("utf-8")).hexdigest()


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _human_owner(value: Any) -> bool:
    if not _nonempty(value):
        return False
    normalized = value.strip().casefold().strip(".:-")
    return normalized not in NON_HUMAN_OWNERS


def _iso_date(value: Any) -> bool:
    if not _nonempty(value):
        return False
    try:
        date.fromisoformat(value.strip())
    except ValueError:
        return False
    return True


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(_nonempty(item) for item in value)


def _display_element(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if not isinstance(value, dict) or not _nonempty(value.get("label")):
        return False
    contract = value.get("contract")
    if contract is None:
        return True
    return (
        isinstance(contract, dict)
        and bool(contract)
        and all(_nonempty(key) and _nonempty(item) for key, item in contract.items())
    )


def _validate_copy_item(
    value: Any,
    path: str,
    problems: list[str],
    *,
    require_approved: bool,
) -> None:
    if not isinstance(value, dict):
        _add(problems, path, "must be an object in wireframes/4")
        return

    for key in ("locale",):
        if key in value and (not isinstance(value[key], str) or not LOCALE_RE.fullmatch(value[key])):
            _add(problems, f"{path}.{key}", "must be a BCP 47-style language tag")
    if "direction" in value and value["direction"] not in ("ltr", "rtl", "auto"):
        _add(problems, f"{path}.direction", "must be ltr, rtl or auto")
    if "parallel" in value:
        if str(value.get("role", "")).strip().lower() in ("field value", "select option"):
            _add(problems, f"{path}.parallel", "native input values and select options cannot display stacked language pairs")
        parallel = value["parallel"]
        if not isinstance(parallel, list) or not 1 <= len(parallel) <= 3:
            _add(problems, f"{path}.parallel", "must contain 1-3 paired language copies")
        else:
            locales = [value.get("locale")]
            if not isinstance(value.get("locale"), str) or not LOCALE_RE.fullmatch(value["locale"]):
                _add(problems, f"{path}.locale", "paired copy needs an explicit primary locale")
            for index, paired in enumerate(parallel):
                paired_path = f"{path}.parallel[{index}]"
                if not isinstance(paired, dict) or "parallel" in paired:
                    _add(problems, paired_path, "must be a copy object without nested parallel copies")
                    continue
                locale = paired.get("locale")
                if not isinstance(locale, str) or not LOCALE_RE.fullmatch(locale):
                    _add(problems, paired_path, "paired copy needs a valid locale")
                elif locale.casefold() in [v.casefold() for v in locales if isinstance(v, str)]:
                    _add(problems, paired_path, "paired locales must be distinct")
                locales.append(locale)
                if paired.get("role") != value.get("role") or paired.get("kind") != value.get("kind"):
                    _add(problems, paired_path, "paired copy must preserve role and kind")
                _validate_copy_item(paired, paired_path, problems, require_approved=require_approved)
    kind = value.get("kind")
    if not isinstance(kind, str) or kind not in VALID_COPY_KINDS:
        _add(problems, f"{path}.kind", f"must be one of {sorted(VALID_COPY_KINDS)}")
    for key in ("role", "source"):
        if not _nonempty(value.get(key)):
            _add(problems, f"{path}.{key}", "must be a non-empty string")

    status = value.get("status")
    if not isinstance(status, str) or status not in VALID_COPY_ITEM_STATUSES:
        _add(
            problems,
            f"{path}.status",
            f"must be one of {sorted(VALID_COPY_ITEM_STATUSES)}",
        )
    elif require_approved and status != "approved":
        _add(problems, f"{path}.status", "must be 'approved' when copy is frozen")

    if kind == "static":
        if not _nonempty(value.get("text")):
            _add(problems, f"{path}.text", "must be exact non-empty product copy")
    elif kind == "dynamic":
        if not _nonempty(value.get("example")):
            _add(
                problems,
                f"{path}.example",
                "must be a non-empty representative value",
            )
        contract = value.get("contract")
        if not isinstance(contract, dict):
            _add(problems, f"{path}.contract", "must be an object")
        else:
            for key in COPY_CONTRACT_FIELDS:
                if not _nonempty(contract.get(key)):
                    _add(
                        problems,
                        f"{path}.contract.{key}",
                        "must be a non-empty string",
                    )


def _validate_action(
    value: Any,
    path: str,
    problems: list[str],
    *,
    require_approved: bool,
) -> str | None:
    if not isinstance(value, dict):
        _add(problems, path, "must be an object in wireframes/4")
        return None
    for key in ("label", "source"):
        if not _nonempty(value.get(key)):
            _add(problems, f"{path}.{key}", "must be a non-empty string")
    status = value.get("status")
    if not isinstance(status, str) or status not in VALID_COPY_ITEM_STATUSES:
        _add(
            problems,
            f"{path}.status",
            f"must be one of {sorted(VALID_COPY_ITEM_STATUSES)}",
        )
    elif require_approved and status != "approved":
        _add(problems, f"{path}.status", "must be 'approved' when copy is frozen")
    if "variant" in value and value["variant"] not in ("secondary", "tertiary", "destructive"):
        _add(problems, f"{path}.variant", "must be secondary, tertiary or destructive; primaryAction owns primary emphasis")
    if "size" in value and value["size"] not in ("regular", "large"):
        _add(problems, f"{path}.size", "must be regular or large")
    if "fullWidth" in value and not isinstance(value["fullWidth"], bool):
        _add(problems, f"{path}.fullWidth", "must be boolean")
    label = value.get("label")
    return label if _nonempty(label) else None


def _validate_copy_freeze(data: dict[str, Any], problems: list[str]) -> bool:
    value = data.get("copyFreeze")
    path = "wireframe-data.copyFreeze"
    if not isinstance(value, dict):
        _add(problems, path, "must be an object in wireframes/4")
        return False
    status = value.get("status")
    if not isinstance(status, str) or status not in VALID_APPROVAL_STATUSES:
        _add(
            problems,
            f"{path}.status",
            f"must be one of {sorted(VALID_APPROVAL_STATUSES)}",
        )
    for key in ("owner", "locale", "approvedOn"):
        if not _nonempty(value.get(key)):
            _add(problems, f"{path}.{key}", "must be a non-empty string")
    owner = value.get("owner")
    if _nonempty(owner) and not _human_owner(owner):
        _add(problems, f"{path}.owner", "must name a human owner")
    locale = value.get("locale")
    if (
        _nonempty(locale)
        and PLACEHOLDER_RE.search(locale) is None
        and LOCALE_RE.fullmatch(locale.strip()) is None
    ):
        _add(problems, f"{path}.locale", "must be a BCP 47-style language tag")
    approved_on = value.get("approvedOn")
    if status == "approved" and not _iso_date(approved_on):
        _add(
            problems,
            f"{path}.approvedOn",
            "must be an ISO YYYY-MM-DD date when copy is approved",
        )
    return status == "approved"


def _add(problems: list[str], path: str, message: str) -> None:
    problems.append(f"{path}: {message}")


def _validate_media_intent(
    value: Any,
    path: str,
    problems: list[str],
    *,
    schema: str,
) -> None:
    if not isinstance(value, dict):
        _add(problems, path, "must be an object when present")
        return
    treatment = value.get("treatment")
    valid_treatments = (
        VALID_MEDIA_TREATMENTS
        if schema == WIREFRAME_SCHEMA
        else LEGACY_MEDIA_TREATMENTS
    )
    if not isinstance(treatment, str) or treatment not in valid_treatments:
        _add(
            problems,
            f"{path}.treatment",
            f"must be one of {sorted(valid_treatments)}",
        )
    required = ["draftPrompt", "source"]
    if schema == WIREFRAME_SCHEMA:
        required.extend(
            (
                "purpose",
                "trigger",
                "reducedMotionFallback",
                "generationRoute",
            )
        )
    for key in required:
        if not _nonempty(value.get(key)):
            _add(problems, f"{path}.{key}", "must be a non-empty string")
    if "motionSpec" in value:
        motion = value["motionSpec"]
        fields = {"scope", "behavior", "space", "compact", "playback", "cost"}
        if treatment not in ("motion", "image + motion"):
            _add(problems, f"{path}.motionSpec", "requires a motion treatment")
        if not isinstance(motion, dict) or set(motion) != fields:
            _add(problems, f"{path}.motionSpec", "must contain scope, behavior, space, compact, playback and cost")
        else:
            for key in fields:
                if not _nonempty(motion[key]):
                    _add(problems, f"{path}.motionSpec.{key}", "must be a non-empty description")
    if value.get("generationStatus") != "deferred":
        _add(problems, f"{path}.generationStatus", "must be 'deferred'")


def _responsive_key(value: Any) -> str:
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _bounded_number(value: Any, *, minimum: float, maximum: float) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and minimum <= value <= maximum
        and math.isfinite(value)
    )


def _validate_composition(
    value: Any,
    path: str,
    region_ids: set[str],
    problems: list[str],
) -> None:
    """Validate the optional geometry metadata consumed by the template.

    Composition stays deliberately small: it describes measurable spacing and
    action/media placement for the review canvas, but never adds product
    behavior or arbitrary CSS.  The renderer and this contract intentionally
    share these exact keys and bounds.
    """

    if not isinstance(value, dict) or set(value) != COMPOSITION_KEYS:
        _add(problems, path, "must contain exactly canvas and regions")
        return

    canvas = value.get("canvas")
    if not isinstance(canvas, dict) or set(canvas) != COMPOSITION_CANVAS_KEYS:
        _add(problems, f"{path}.canvas", "must contain exactly padding and gap")
    elif (
        not _bounded_number(canvas.get("padding"), minimum=0, maximum=128)
        or not _bounded_number(canvas.get("gap"), minimum=0, maximum=128)
    ):
        if not _bounded_number(canvas.get("padding"), minimum=0, maximum=128):
            _add(problems, f"{path}.canvas.padding", "must be a number from 0 to 128")
        if not _bounded_number(canvas.get("gap"), minimum=0, maximum=128):
            _add(problems, f"{path}.canvas.gap", "must be a number from 0 to 128")

    regions = value.get("regions")
    if not isinstance(regions, dict):
        _add(problems, f"{path}.regions", "must be an object keyed by region ID")
        return
    unknown_regions = sorted(set(regions) - region_ids)
    if unknown_regions:
        _add(
            problems,
            f"{path}.regions",
            "references unknown region IDs: " + ", ".join(unknown_regions),
        )
    for region_id, region in regions.items():
        region_path = f"{path}.regions.{region_id}"
        if not isinstance(region, dict):
            _add(problems, region_path, "must be an object")
            continue
        unknown_keys = sorted(set(region) - COMPOSITION_REGION_KEYS)
        if unknown_keys:
            _add(
                problems,
                region_path,
                "contains unknown keys: " + ", ".join(unknown_keys),
            )
        for key in ("padding", "gap"):
            if key in region and not _bounded_number(
                region[key], minimum=0, maximum=128
            ):
                _add(
                    problems,
                    f"{region_path}.{key}",
                    "must be a number from 0 to 128",
                )
        if "maxWidth" in region and not _bounded_number(
            region["maxWidth"], minimum=1, maximum=2400
        ):
            _add(
                problems,
                f"{region_path}.maxWidth",
                "must be a number from 1 to 2400",
            )
        if "actionsPlacement" in region and (
            not isinstance(region["actionsPlacement"], str)
            or region["actionsPlacement"] not in VALID_ACTION_PLACEMENTS
        ):
            _add(
                problems,
                f"{region_path}.actionsPlacement",
                "must be before, after, or inline",
            )
        if "itemColumns" in region and (
            not isinstance(region["itemColumns"], int)
            or isinstance(region["itemColumns"], bool)
            or not 1 <= region["itemColumns"] <= 12
        ):
            _add(
                problems,
                f"{region_path}.itemColumns",
                "must be an integer from 1 to 12",
            )
        if "mediaAspectRatio" in region and not _bounded_number(
            region["mediaAspectRatio"], minimum=0.25, maximum=4
        ):
            _add(
                problems,
                f"{region_path}.mediaAspectRatio",
                "must be a number from 0.25 to 4",
            )


def _validate_local_search(
    value: Any,
    path: str,
    regions: list[dict[str, Any]],
    state_ids: set[str],
    state_records: list[dict[str, Any]],
    problems: list[str],
    *,
    require_approved: bool,
) -> None:
    """Validate the bounded, local-only search projection.

    The search model intentionally describes only the two reviewer regions,
    their copy, three existing screen states, and a finite local item set. It
    does not accept selectors, callbacks, URLs, or arbitrary renderer data.
    """

    if not isinstance(value, dict):
        _add(problems, path, "must be an object")
        return
    unknown = sorted(set(value) - LOCAL_SEARCH_KEYS)
    if unknown:
        _add(problems, path, "contains unknown keys: " + ", ".join(unknown))
    missing = sorted(LOCAL_SEARCH_KEYS - set(value))
    if missing:
        _add(problems, path, "must include: " + ", ".join(missing))

    region_by_id = {
        region.get("id"): region
        for region in regions
        if isinstance(region, dict) and _nonempty(region.get("id"))
    }
    form_region = value.get("formRegion")
    results_region = value.get("resultsRegion")
    if not _nonempty(form_region) or form_region not in region_by_id:
        _add(problems, f"{path}.formRegion", "must reference an existing region ID")
    if not _nonempty(results_region) or results_region not in region_by_id:
        _add(problems, f"{path}.resultsRegion", "must reference an existing region ID")
    if _nonempty(form_region) and form_region == results_region:
        _add(problems, f"{path}.resultsRegion", "must differ from formRegion")
    if (
        _nonempty(results_region)
        and results_region in region_by_id
        and region_by_id[results_region].get("presentation", "content") != "list"
    ):
        _add(problems, f"{path}.resultsRegion", "must reference a list presentation region")

    for key in ("queryLabel", "languageLabel"):
        label = value.get(key)
        _validate_copy_item(
            label,
            f"{path}.{key}",
            problems,
            require_approved=require_approved,
        )
        if isinstance(label, dict) and label.get("kind") != "static":
            _add(problems, f"{path}.{key}.kind", "must be static copy")

    options = value.get("languageOptions")
    option_values: list[str] = []
    if not isinstance(options, list) or not 1 <= len(options) <= LOCAL_SEARCH_MAX_OPTIONS:
        _add(
            problems,
            f"{path}.languageOptions",
            f"must be a list with 1 to {LOCAL_SEARCH_MAX_OPTIONS} options",
        )
    else:
        for index, option in enumerate(options):
            option_path = f"{path}.languageOptions[{index}]"
            if not isinstance(option, dict):
                _add(problems, option_path, "must be an object")
                continue
            option_unknown = sorted(set(option) - LOCAL_SEARCH_OPTION_KEYS)
            if option_unknown:
                _add(
                    problems,
                    option_path,
                    "contains unknown keys: " + ", ".join(option_unknown),
                )
            option_missing = sorted(LOCAL_SEARCH_OPTION_KEYS - set(option))
            if option_missing:
                _add(
                    problems,
                    option_path,
                    "must include: " + ", ".join(option_missing),
                )
            option_value = option.get("value")
            if not _nonempty(option_value) or len(option_value) > LOCAL_SEARCH_MAX_VALUE_LENGTH:
                _add(
                    problems,
                    f"{option_path}.value",
                    f"must be a non-empty string of at most {LOCAL_SEARCH_MAX_VALUE_LENGTH} characters",
                )
            elif option_value in option_values:
                _add(problems, f"{option_path}.value", f"duplicates {option_value!r}")
            else:
                option_values.append(option_value)
            option_copy = option.get("copy")
            _validate_copy_item(
                option_copy,
                f"{option_path}.copy",
                problems,
                require_approved=require_approved,
            )
            if isinstance(option_copy, dict) and option_copy.get("kind") != "static":
                _add(problems, f"{option_path}.copy.kind", "must be static copy")

    for key in ("submitAction", "clearAction"):
        action = value.get(key)
        if not _nonempty(action) or len(action) > 120:
            _add(
                problems,
                f"{path}.{key}",
                "must be a non-empty action label of at most 120 characters",
            )
    submit_action = value.get("submitAction")
    clear_action = value.get("clearAction")
    if _nonempty(submit_action) and submit_action == clear_action:
        _add(problems, f"{path}.clearAction", "must differ from submitAction")
    form_actions = []
    if _nonempty(form_region) and form_region in region_by_id:
        raw_actions = region_by_id[form_region].get("actions")
        if isinstance(raw_actions, list):
            form_actions = [
                action.get("label") if isinstance(action, dict) else action
                for action in raw_actions
            ]
    for key, action in (("submitAction", submit_action), ("clearAction", clear_action)):
        if _nonempty(action) and form_actions.count(action) != 1:
            _add(
                problems,
                f"{path}.{key}",
                "must match exactly one action label in formRegion",
            )

    states = value.get("states")
    state_values: list[str] = []
    if not isinstance(states, dict) or set(states) != LOCAL_SEARCH_STATE_KEYS:
        _add(
            problems,
            f"{path}.states",
            "must contain exactly initial, results, and empty",
        )
    else:
        for key in ("initial", "results", "empty"):
            state_id = states.get(key)
            if not _nonempty(state_id):
                _add(problems, f"{path}.states.{key}", "must be a non-empty state ID")
            elif state_id not in state_ids:
                _add(
                    problems,
                    f"{path}.states.{key}",
                    f"references unknown state ID {state_id}",
                )
            elif state_id in state_values:
                _add(problems, f"{path}.states.{key}", f"duplicates {state_id}")
            else:
                state_values.append(state_id)

    items = value.get("items")
    if not isinstance(items, list) or len(items) > LOCAL_SEARCH_MAX_ITEMS:
        _add(
            problems,
            f"{path}.items",
            f"must be a list with at most {LOCAL_SEARCH_MAX_ITEMS} items",
        )
    else:
        for index, item in enumerate(items):
            item_path = f"{path}.items[{index}]"
            if not isinstance(item, dict):
                _add(problems, item_path, "must be an object")
                continue
            item_unknown = sorted(set(item) - LOCAL_SEARCH_ITEM_KEYS)
            if item_unknown:
                _add(
                    problems,
                    item_path,
                    "contains unknown keys: " + ", ".join(item_unknown),
                )
            item_missing = sorted(LOCAL_SEARCH_ITEM_KEYS - set(item))
            if item_missing:
                _add(problems, item_path, "must include: " + ", ".join(item_missing))
            language = item.get("language")
            if not _nonempty(language) or language not in option_values[1:]:
                _add(
                    problems,
                    f"{item_path}.language",
                    "must match a declared non-sentinel language option value",
                )
            search_text = item.get("searchText")
            if not _nonempty(search_text) or len(search_text) > LOCAL_SEARCH_MAX_SEARCH_TEXT_LENGTH:
                _add(
                    problems,
                    f"{item_path}.searchText",
                    f"must be non-empty text of at most {LOCAL_SEARCH_MAX_SEARCH_TEXT_LENGTH} characters",
                )
            item_copy = item.get("copy")
            _validate_copy_item(
                item_copy,
                f"{item_path}.copy",
                problems,
                require_approved=require_approved,
            )
            if isinstance(item_copy, dict) and item_copy.get("kind") != "dynamic":
                _add(problems, f"{item_path}.copy.kind", "must be dynamic copy")

    if isinstance(states, dict) and _nonempty(results_region) and results_region in region_by_id:
        # ``states`` points at existing screen treatments. Requiring copy at
        # both result branches prevents the renderer from inventing a count or
        # empty message when a local query has no matches.
        state_by_id = {
            screen_state.get("id"): screen_state
            for screen_state in state_records
            if isinstance(screen_state, dict) and _nonempty(screen_state.get("id"))
        }
        for key in ("results", "empty"):
            state_id = states.get(key)
            state_record = state_by_id.get(state_id) if _nonempty(state_id) else None
            treatment = (
                state_record.get("treatments", {}).get(results_region)
                if isinstance(state_record, dict)
                and isinstance(state_record.get("treatments"), dict)
                else None
            )
            treatment_copy = treatment.get("copy") if isinstance(treatment, dict) else None
            if not isinstance(treatment_copy, list) or not treatment_copy:
                _add(
                    problems,
                    f"{path}.states.{key}",
                    "must reference a screen state with declared treatment copy for resultsRegion",
                )


def _validate_responsive_data(
    data: dict[str, Any], problems: list[str]
) -> list[str]:
    responsive_by_surface = data.get("responsiveBySurface")
    if isinstance(responsive_by_surface, dict) and responsive_by_surface:
        if "viewports" in data or "sizeClasses" in data:
            _add(
                problems,
                "wireframe-data.responsiveBySurface",
                "per-surface responsive data must not be combined with global viewports or sizeClasses",
            )
            # Keep validating the per-surface entries so callers receive all
            # structural findings in one deterministic result.
        else:
            targets_by_surface: dict[str, list[str]] = {}
            for surface_id, spec in responsive_by_surface.items():
                if not isinstance(surface_id, str) or not isinstance(spec, dict) or set(spec) != {"kind", "targets", "canvasWidths"}:
                    _add(problems, f"wireframe-data.responsiveBySurface.{surface_id}", "must contain kind, targets, and canvasWidths")
                    continue
                kind = spec.get("kind")
                targets = spec.get("targets")
                if kind == "viewports":
                    valid = isinstance(targets, list) and len(targets) >= (3 if data.get("schema") in INTERACTIVE_WIREFRAME_SCHEMAS else 2) and all(isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value > 0 for value in targets) and len(set(targets)) == len(targets) and all(left < right for left, right in zip(targets, targets[1:]))
                elif kind == "sizeClasses":
                    valid = isinstance(targets, list) and len(targets) >= 2 and all(_nonempty(value) for value in targets) and len(set(targets)) == len(targets)
                else:
                    valid = False
                if not valid:
                    _add(problems, f"wireframe-data.responsiveBySurface.{surface_id}", "has an invalid responsive set")
                    continue
                target_keys = [_responsive_key(value) for value in targets]
                canvas_widths = spec.get("canvasWidths")
                if not isinstance(canvas_widths, dict) or set(canvas_widths) != set(target_keys):
                    _add(
                        problems,
                        f"wireframe-data.responsiveBySurface.{surface_id}.canvasWidths",
                        "must contain exactly one width for every target",
                    )
                    continue
                invalid_width = any(
                    not isinstance(width, (int, float))
                    or isinstance(width, bool)
                    or not math.isfinite(width)
                    or width <= 0
                    or (kind == "viewports" and float(width) != float(target))
                    for target, width in canvas_widths.items()
                )
                if invalid_width:
                    _add(
                        problems,
                        f"wireframe-data.responsiveBySurface.{surface_id}.canvasWidths",
                        "must use positive widths and match numeric viewport targets",
                    )
                    continue
                targets_by_surface[surface_id] = target_keys
            data["_validatedResponsiveBySurface"] = targets_by_surface
            return []
    has_viewports = "viewports" in data
    has_size_classes = "sizeClasses" in data
    viewports = data.get("viewports")
    size_classes = data.get("sizeClasses")
    # Interactive schemas carry the three-viewport web floor; wireframes/2
    # files stay readable with their historical two-target sets.
    web_floor = 3 if data.get("schema") in INTERACTIVE_WIREFRAME_SCHEMAS else 2
    floor_words = {2: "two", 3: "three"}
    valid_viewports = (
        isinstance(viewports, list)
        and len(viewports) >= web_floor
        and all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value > 0
            for value in viewports
        )
        and len(set(viewports)) == len(viewports)
        and all(left < right for left, right in zip(viewports, viewports[1:]))
    )
    valid_size_classes = (
        isinstance(size_classes, list)
        and len(size_classes) >= 2
        and all(_nonempty(value) for value in size_classes)
        and len(set(size_classes)) == len(size_classes)
    )
    if (
        has_viewports == has_size_classes
        or (has_viewports and not valid_viewports)
        or (has_size_classes and not valid_size_classes)
    ):
        _add(
            problems,
            "wireframe-data",
            "must declare exactly one responsive set: at least "
            f"{floor_words.get(web_floor, str(web_floor))} "
            "ascending numeric viewports for web, or at least two unique "
            "string sizeClasses for native or desktop",
        )
        return []

    targets = viewports if has_viewports else size_classes
    target_keys = [_responsive_key(value) for value in targets]
    canvas_widths = data.get("canvasWidths")
    if not isinstance(canvas_widths, dict):
        _add(
            problems,
            "wireframe-data.canvasWidths",
            "must map every responsive target to a positive review-canvas width",
        )
    else:
        actual_keys = set(canvas_widths)
        expected_keys = set(target_keys)
        if actual_keys != expected_keys:
            _add(
                problems,
                "wireframe-data.canvasWidths",
                "must contain exactly the responsive target keys: "
                + ", ".join(target_keys),
            )
        for target, width in canvas_widths.items():
            if (
                not isinstance(width, (int, float))
                or isinstance(width, bool)
                or not math.isfinite(width)
                or width <= 0
            ):
                _add(
                    problems,
                    f"wireframe-data.canvasWidths.{target}",
                    "must be a positive numeric width",
                )
            elif (
                has_viewports
                and target in expected_keys
                and float(width) != float(target)
            ):
                _add(
                    problems,
                    f"wireframe-data.canvasWidths.{target}",
                    "must equal its web viewport target",
                )
    return target_keys


def _validate_data(data: Any, *, require_filled: bool) -> list[str]:
    problems: list[str] = []
    if not isinstance(data, dict):
        return ["wireframe-data: must be a JSON object"]

    schema = data.get("schema")
    supported_schemas = LEGACY_WIREFRAME_SCHEMAS | {WIREFRAME_SCHEMA}
    if schema not in supported_schemas:
        _add(
            problems,
            "wireframe-data.schema",
            f"must be one of {sorted(supported_schemas)}",
        )
    interactive_contract = schema in INTERACTIVE_WIREFRAME_SCHEMAS
    copy_contract = schema == WIREFRAME_SCHEMA

    for key in ("product", "approvalStatus", "source"):
        if not _nonempty(data.get(key)):
            _add(problems, f"wireframe-data.{key}", "must be a non-empty string")

    status = data.get("approvalStatus")
    if _nonempty(status) and status not in VALID_APPROVAL_STATUSES:
        _add(
            problems,
            "wireframe-data.approvalStatus",
            f"must be one of {sorted(VALID_APPROVAL_STATUSES)}",
        )
    if data.get("source") != "PRD.md#UI-Surface-Contract":
        _add(
            problems,
            "wireframe-data.source",
            "must be 'PRD.md#UI-Surface-Contract'",
        )

    copy_is_frozen = _validate_copy_freeze(data, problems) if copy_contract else False

    responsive_targets = _validate_responsive_data(data, problems)
    responsive_by_surface = data.get("_validatedResponsiveBySurface", {})

    screens = data.get("screens")
    if not isinstance(screens, list) or not screens:
        _add(problems, "wireframe-data.screens", "must be a non-empty list")
        return problems

    seen_screens: set[str] = set()
    seen_routes: dict[str, str] = {}
    actions_by_screen: dict[str, list[str]] = {}
    action_regions_by_screen: dict[str, dict[str, set[str]]] = {}
    for screen_index, screen in enumerate(screens):
        path = f"wireframe-data.screens[{screen_index}]"
        if not isinstance(screen, dict):
            _add(problems, path, "must be an object")
            continue
        screen_id = screen.get("id")
        if not _nonempty(screen_id) or not screen_id.startswith("UI-"):
            _add(problems, f"{path}.id", "must be a non-empty UI-* ID")
        elif screen_id in seen_screens:
            _add(problems, f"{path}.id", f"duplicates {screen_id}")
        else:
            seen_screens.add(screen_id)

        for key in ("name", "route", "goal"):
            if not _nonempty(screen.get(key)):
                _add(problems, f"{path}.{key}", "must be a non-empty string")
        route = screen.get("route")
        if isinstance(route, str) and route.strip().casefold() not in {"n/a", "na"}:
            previous_route = seen_routes.get(route)
            if previous_route is not None:
                _add(problems, f"{path}.route", f"duplicates non-n/a route {route!r} used by {previous_route}")
            else:
                seen_routes[route] = str(screen_id)
        if copy_contract:
            copy_status = screen.get("copyStatus")
            if (
                not isinstance(copy_status, str)
                or copy_status not in VALID_APPROVAL_STATUSES
            ):
                _add(
                    problems,
                    f"{path}.copyStatus",
                    f"must be one of {sorted(VALID_APPROVAL_STATUSES)}",
                )
            elif copy_is_frozen and copy_status != "approved":
                _add(
                    problems,
                    f"{path}.copyStatus",
                    "must be 'approved' when copy is frozen",
                )
        if "traces" in screen and not _string_list(screen["traces"]):
            _add(problems, f"{path}.traces", "must be a string list when present")
        if interactive_contract and "mediaIntent" in screen:
            if isinstance(screen["mediaIntent"], dict) and "motionSpec" in screen["mediaIntent"]:
                _add(problems, f"{path}.mediaIntent.motionSpec", "place motionSpec on each affected region for visible boundaries")
            _validate_media_intent(
                screen["mediaIntent"],
                f"{path}.mediaIntent",
                problems,
                schema=schema,
            )

        regions = screen.get("regions")
        if not isinstance(regions, list) or not regions:
            _add(problems, f"{path}.regions", "must be a non-empty list")
            continue

        region_ids: list[str] = []
        for region_index, region in enumerate(regions):
            region_path = f"{path}.regions[{region_index}]"
            if not isinstance(region, dict):
                _add(problems, region_path, "must be an object")
                continue
            region_id = region.get("id")
            if not _nonempty(region_id):
                _add(problems, f"{region_path}.id", "must be a non-empty string")
            elif region_id in region_ids:
                _add(problems, f"{region_path}.id", f"duplicates {region_id}")
            else:
                region_ids.append(region_id)
            for key in ("section", "purpose"):
                if not _nonempty(region.get(key)):
                    _add(problems, f"{region_path}.{key}", "must be a non-empty string")
            if region.get("priority") not in VALID_PRIORITIES:
                _add(
                    problems,
                    f"{region_path}.priority",
                    f"must be one of {sorted(VALID_PRIORITIES)}",
                )
            span = region.get("span")
            if not isinstance(span, int) or isinstance(span, bool) or not 1 <= span <= 12:
                _add(problems, f"{region_path}.span", "must be an integer from 1 to 12")
            elements = region.get("elements")
            presentation = region.get("presentation", "content")
            if presentation not in ("content", "navigation", "editorial", "list", "form", "table"):
                _add(problems, f"{region_path}.presentation", "must be content, navigation, editorial, list, form, or table")
            if isinstance(elements, list):
                roles = [item.get("role") if isinstance(item, dict) else None for item in elements]
                if presentation == "table":
                    headers = roles.count("table header")
                    cells = roles.count("table cell")
                    if not headers or not cells or cells % headers:
                        _add(problems, region_path, "table requires headers and complete rows of table cells")
                    start = next((index for index, role in enumerate(roles) if role in ("table header", "table cell")), len(roles))
                    if roles[start:] != ["table header"] * headers + ["table cell"] * cells:
                        _add(problems, region_path, "table copy must be introduction, headers, then row-major cells")
                if presentation == "list" and "list item" not in roles:
                    _add(problems, region_path, "list requires list item copy")
                elif presentation == "list":
                    start = roles.index("list item")
                    if any(role != "list item" for role in roles[start:]):
                        _add(problems, region_path, "list introduction must precede all list items")
                if presentation == "form":
                    if "field label" not in roles:
                        _add(problems, region_path, "form requires field label copy")
                    for index, role in enumerate(roles):
                        if role == "field value" and (index == 0 or roles[index - 1] != "field label"):
                            _add(problems, region_path, "field value must immediately follow its field label")
            if not isinstance(elements, list) or not elements:
                _add(problems, f"{region_path}.elements", "must be a non-empty list")
            elif copy_contract:
                for element_index, item in enumerate(elements):
                    _validate_copy_item(
                        item,
                        f"{region_path}.elements[{element_index}]",
                        problems,
                        require_approved=copy_is_frozen,
                    )
            elif not all(_display_element(item) for item in elements):
                _add(
                    problems,
                    f"{region_path}.elements",
                    "must be a non-empty list of strings or {label, contract} objects",
                )
            actions = region.get("actions")
            if "primaryAction" in region and (
                not _nonempty(region["primaryAction"])
                or not isinstance(actions, list)
                or sum(
                    (action.get("label") if isinstance(action, dict) else action) == region["primaryAction"]
                    for action in actions
                ) != 1
            ):
                _add(problems, f"{region_path}.primaryAction", "must match exactly one existing action label")
            action_labels: list[str] = []
            if not isinstance(actions, list):
                _add(problems, f"{region_path}.actions", "must be a list")
            elif copy_contract:
                for action_index, item in enumerate(actions):
                    label = _validate_action(
                        item,
                        f"{region_path}.actions[{action_index}]",
                        problems,
                        require_approved=copy_is_frozen,
                    )
                    if label is not None:
                        action_labels.append(label)
            elif not all(_nonempty(item) for item in actions):
                _add(problems, f"{region_path}.actions", "must be a string list")
            else:
                action_labels = actions
            if _nonempty(screen_id):
                actions_by_screen.setdefault(screen_id, []).extend(action_labels)
                by_label = action_regions_by_screen.setdefault(screen_id, {})
                for label in action_labels:
                    regions_for_label = by_label.setdefault(label, set())
                    if region_id in regions_for_label:
                        _add(
                            problems,
                            f"{region_path}.actions",
                            f"must not repeat action label {label!r} within a region",
                        )
                    regions_for_label.add(region_id)
            if "traces" in region and not _string_list(region["traces"]):
                _add(problems, f"{region_path}.traces", "must be a string list when present")
            if "disclosure" in region:
                disclosure = region["disclosure"]
                if not copy_contract or region.get("presentation") != "navigation":
                    _add(problems, f"{region_path}.disclosure", "requires schema-4 navigation presentation")
                if not isinstance(disclosure, dict) or set(disclosure) != {"targets", "label"}:
                    _add(problems, f"{region_path}.disclosure", "must contain targets and label")
                else:
                    targets = disclosure["targets"]
                    declared = screen.get("responsiveLayouts", {})
                    if (not _string_list(targets) or not targets or len(set(targets)) != len(targets)
                            or not isinstance(declared, dict) or any(t not in declared for t in targets)):
                        _add(problems, f"{region_path}.disclosure.targets", "must name distinct declared responsive targets")
                    _validate_copy_item(disclosure["label"], f"{region_path}.disclosure.label", problems,
                                        require_approved=copy_is_frozen)
                    if isinstance(disclosure["label"], dict) and disclosure["label"].get("kind") != "static":
                        _add(problems, f"{region_path}.disclosure.label", "must be static navigation copy")
            if interactive_contract and "mediaIntent" in region:
                _validate_media_intent(
                    region["mediaIntent"],
                    f"{region_path}.mediaIntent",
                    problems,
                    schema=schema,
                )

        never_drop = screen.get("neverDrop")
        if not _string_list(never_drop) or not never_drop:
            _add(problems, f"{path}.neverDrop", "must be a non-empty string list")
            never_drop_ids: set[str] = set()
        else:
            never_drop_ids = set(never_drop)
            if len(never_drop) != len(never_drop_ids):
                _add(problems, f"{path}.neverDrop", "must not contain duplicates")
            unknown_never_drop = sorted(never_drop_ids - set(region_ids))
            if unknown_never_drop:
                _add(
                    problems,
                    f"{path}.neverDrop",
                    "references unknown region IDs: " + ", ".join(unknown_never_drop),
                )
            primary_regions = {
                region.get("id")
                for region in regions
                if isinstance(region, dict)
                and region.get("priority") == "primary"
                and _nonempty(region.get("id"))
            }
            missing_primary = sorted(primary_regions - never_drop_ids)
            if missing_primary:
                _add(
                    problems,
                    f"{path}.neverDrop",
                    "must include every primary region: " + ", ".join(missing_primary),
                )

        screen_targets = responsive_by_surface.get(screen_id, responsive_targets) if isinstance(responsive_by_surface, dict) else responsive_targets
        responsive_layouts = screen.get("responsiveLayouts")
        if not isinstance(responsive_layouts, dict):
            _add(
                problems,
                f"{path}.responsiveLayouts",
                "must be an object keyed by every responsive target",
            )
            responsive_layouts = {}
        elif set(responsive_layouts) != set(screen_targets):
            _add(
                problems,
                f"{path}.responsiveLayouts",
                "must contain exactly the responsive targets: "
                + ", ".join(screen_targets),
            )
        for target in screen_targets:
            layout = responsive_layouts.get(target)
            layout_path = f"{path}.responsiveLayouts.{target}"
            if not isinstance(layout, dict):
                _add(problems, layout_path, "must be an object")
                continue
            if schema == WIREFRAME_SCHEMA and "composition" in layout:
                _validate_composition(
                    layout["composition"],
                    f"{layout_path}.composition",
                    set(region_ids),
                    problems,
                )
            order = layout.get("order")
            if not _string_list(order):
                _add(problems, f"{layout_path}.order", "must be a non-empty string list")
            elif len(order) != len(set(order)) or set(order) != set(region_ids):
                _add(
                    problems,
                    f"{layout_path}.order",
                    "must contain every region ID exactly once",
                )
            hidden = layout.get("hidden")
            if not isinstance(hidden, list) or not all(_nonempty(item) for item in hidden):
                _add(problems, f"{layout_path}.hidden", "must be a string list")
                hidden_ids: set[str] = set()
            else:
                hidden_ids = set(hidden)
                if len(hidden) != len(hidden_ids):
                    _add(problems, f"{layout_path}.hidden", "must not contain duplicates")
                unknown_hidden = sorted(hidden_ids - set(region_ids))
                if unknown_hidden:
                    _add(
                        problems,
                        f"{layout_path}.hidden",
                        "references unknown region IDs: " + ", ".join(unknown_hidden),
                    )
                hidden_never_drop = sorted(hidden_ids & never_drop_ids)
                if hidden_never_drop:
                    _add(
                        problems,
                        f"{layout_path}.hidden",
                        "must not hide never-drop regions: "
                        + ", ".join(hidden_never_drop),
                    )
            columns = layout.get("columns")
            if (
                not isinstance(columns, int)
                or isinstance(columns, bool)
                or not 1 <= columns <= 12
            ):
                _add(problems, f"{layout_path}.columns", "must be an integer from 1 to 12")
                columns = 12
            spans = layout.get("spans")
            if not isinstance(spans, dict) or set(spans) != set(region_ids):
                _add(
                    problems,
                    f"{layout_path}.spans",
                    "must map every region ID exactly once",
                )
            else:
                for region_id, span in spans.items():
                    if (
                        not isinstance(span, int)
                        or isinstance(span, bool)
                        or not 1 <= span <= columns
                    ):
                        _add(
                            problems,
                            f"{layout_path}.spans.{region_id}",
                            f"must be an integer from 1 to {columns}",
                        )
            for key in ("reflow", "interaction"):
                if not _nonempty(layout.get(key)):
                    _add(problems, f"{layout_path}.{key}", "must be a non-empty string")

        states = screen.get("states")
        if not isinstance(states, list) or not states:
            _add(problems, f"{path}.states", "must be a non-empty list")
            continue
        if (
            copy_contract
            and isinstance(states[0], dict)
            and states[0].get("id") != "ready"
        ):
            _add(
                problems,
                f"{path}.states[0].id",
                "must be 'ready' as the schema-4 baseline state",
            )
        seen_states: set[str] = set()
        for state_index, screen_state in enumerate(states):
            state_path = f"{path}.states[{state_index}]"
            if not isinstance(screen_state, dict):
                _add(problems, state_path, "must be an object")
                continue
            state_id = screen_state.get("id")
            if not _nonempty(state_id):
                _add(problems, f"{state_path}.id", "must be a non-empty string")
            elif state_id in seen_states:
                _add(problems, f"{state_path}.id", f"duplicates {state_id}")
            else:
                seen_states.add(state_id)
            if not _nonempty(screen_state.get("label")):
                _add(problems, f"{state_path}.label", "must be a non-empty string")
            treatments = screen_state.get("treatments")
            if not isinstance(treatments, dict):
                _add(problems, f"{state_path}.treatments", "must be an object")
            else:
                unknown = sorted(set(treatments) - set(region_ids))
                if unknown:
                    _add(
                        problems,
                        f"{state_path}.treatments",
                        "references unknown region IDs: " + ", ".join(unknown),
                    )
                state_copy_count = 0
                for region_id, treatment in treatments.items():
                    treatment_path = f"{state_path}.treatments.{region_id}"
                    if not copy_contract:
                        if not _nonempty(treatment):
                            _add(problems, treatment_path, "must be a non-empty string")
                        continue
                    if not isinstance(treatment, dict):
                        _add(
                            problems,
                            treatment_path,
                            "must be an object in wireframes/4",
                        )
                        continue
                    if not _nonempty(treatment.get("layout")):
                        _add(
                            problems,
                            f"{treatment_path}.layout",
                            "must be a non-empty reviewer-only layout description",
                        )
                    treatment_copy = treatment.get("copy")
                    if not isinstance(treatment_copy, list):
                        _add(
                            problems,
                            f"{treatment_path}.copy",
                            "must be a list",
                        )
                        continue
                    state_copy_count += len(treatment_copy)
                    for copy_index, item in enumerate(treatment_copy):
                        _validate_copy_item(
                            item,
                            f"{treatment_path}.copy[{copy_index}]",
                            problems,
                            require_approved=copy_is_frozen,
                        )
                if copy_contract and state_index > 0 and state_copy_count == 0:
                    _add(
                        problems,
                        f"{state_path}.treatments",
                        "must include product or assistive copy for every alternate state",
                    )

        if "localSearch" in screen and not copy_contract:
            _add(problems, f"{path}.localSearch", "requires wireframes/4")
        if copy_contract and "localSearch" in screen:
            _validate_local_search(
                screen["localSearch"],
                f"{path}.localSearch",
                [region for region in regions if isinstance(region, dict)],
                seen_states,
                [state for state in states if isinstance(state, dict)],
                problems,
                require_approved=copy_is_frozen,
            )

    flows = data.get("flows")
    flow_keys: list[tuple[str, str]] = []
    if flows is not None:
        if not isinstance(flows, list):
            _add(problems, "wireframe-data.flows", "must be a list when present")
        else:
            for flow_index, flow in enumerate(flows):
                flow_path = f"wireframe-data.flows[{flow_index}]"
                if not isinstance(flow, dict):
                    _add(problems, flow_path, "must be an object")
                    continue
                for key in ("from", "trigger", "to"):
                    if not _nonempty(flow.get(key)):
                        _add(problems, f"{flow_path}.{key}", "must be a non-empty string")
                origin = flow.get("from")
                trigger = flow.get("trigger")
                target = flow.get("to")
                if _nonempty(origin) and origin not in seen_screens:
                    _add(
                        problems,
                        f"{flow_path}.from",
                        f"references unknown screen ID {origin}",
                    )
                presentation = flow.get("presentation")
                if interactive_contract and presentation not in VALID_FLOW_PRESENTATIONS:
                    _add(
                        problems,
                        f"{flow_path}.presentation",
                        f"must be one of {sorted(VALID_FLOW_PRESENTATIONS)}",
                    )
                if (
                    interactive_contract
                    and presentation in {"page", "overlay"}
                    and _nonempty(target)
                    and target not in seen_screens
                ):
                    _add(
                        problems,
                        f"{flow_path}.to",
                        f"{presentation} must target a known screen ID",
                    )
                if copy_contract and presentation == "feedback":
                    _validate_copy_item(
                        flow.get("feedback"),
                        f"{flow_path}.feedback",
                        problems,
                        require_approved=copy_is_frozen,
                    )
                if interactive_contract and _nonempty(origin) and _nonempty(trigger):
                    flow_keys.append((origin, trigger))

    if interactive_contract:
        screens_by_id = {
            screen.get("id"): screen
            for screen in screens
            if isinstance(screen, dict) and _nonempty(screen.get("id"))
        }
        for origin, actions in actions_by_screen.items():
            for trigger in actions:
                count = flow_keys.count((origin, trigger))
                if count != 1:
                    _add(
                        problems,
                        f"wireframe-data.actions.{origin}.{trigger}",
                        f"must match exactly one outgoing flow (found {count})",
                    )
        for origin, trigger in set(flow_keys):
            count = actions_by_screen.get(origin, []).count(trigger)
            if count < 1:
                _add(
                    problems,
                    f"wireframe-data.flows.{origin}.{trigger}",
                    f"must match exactly one visible region action or repeat across distinct regions (found {count})",
                )
                continue
            screen = screens_by_id.get(origin)
            regions_for_trigger = action_regions_by_screen.get(origin, {}).get(trigger, set())
            layouts = screen.get("responsiveLayouts", {}) if isinstance(screen, dict) else {}
            has_visible_binding = any(
                isinstance(layout, dict)
                and any(
                    region_id not in (
                        set(layout.get("hidden", []))
                        if isinstance(layout.get("hidden", []), list)
                        else set()
                    )
                    for region_id in regions_for_trigger
                )
                for layout in layouts.values()
            ) if isinstance(layouts, dict) else False
            if not has_visible_binding:
                _add(
                    problems,
                    f"wireframe-data.flows.{origin}.{trigger}",
                    "must retain a visible region action in at least one responsive target",
                )

    if isinstance(responsive_by_surface, dict) and responsive_by_surface:
        declared_surface_ids = {
            key for key in responsive_by_surface if isinstance(key, str)
        }
        if declared_surface_ids != seen_screens:
            missing = sorted(seen_screens - declared_surface_ids)
            extra = sorted(declared_surface_ids - seen_screens)
            detail: list[str] = []
            if missing:
                detail.append("missing " + ", ".join(missing))
            if extra:
                detail.append("unknown " + ", ".join(extra))
            _add(
                problems,
                "wireframe-data.responsiveBySurface",
                "must contain exactly one entry per screen: " + "; ".join(detail),
            )

    if require_filled:
        def walk(value: Any, path: str) -> None:
            if isinstance(value, str) and PLACEHOLDER_RE.search(value):
                _add(problems, path, "contains an unfilled <placeholder>")
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    walk(item, f"{path}[{index}]")
            elif isinstance(value, dict):
                for key, item in value.items():
                    walk(item, f"{path}.{key}")

        walk(data, "wireframe-data")

    return problems


def validate(
    html_path: Path,
    *,
    require_filled: bool = False,
    require_copy_approved: bool = False,
    require_approved: bool = False,
    prd_path: Path | None = None,
) -> list[str]:
    problems: list[str] = []
    try:
        html = html_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return [f"{html_path}: cannot read HTML: {exc}"]

    parser = ResourceParser()
    parser.feed(html)
    parser.close()
    if parser.duplicate_attributes:
        return [
            f"{html_path}: must not contain duplicate HTML attributes: "
            + ", ".join(parser.duplicate_attributes)
        ]
    if parser.data_block_count == 0:
        return [f"{html_path}: missing wireframe-data application/json block"]
    if parser.data_block_count != 1 or len(parser.data_blocks) != 1:
        return [
            f"{html_path}: must contain exactly one wireframe-data "
            f"application/json block (found {parser.data_block_count})"
        ]
    try:
        data = json.loads(parser.data_blocks[0])
    except json.JSONDecodeError as exc:
        return [f"{html_path}: wireframe-data is invalid JSON: {exc}"]

    problems.extend(_validate_data(data, require_filled=require_filled))
    if not isinstance(data, dict):
        return problems
    schema = data.get("schema")

    if prd_path is not None:
        try:
            prd_text = prd_path.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            return [f"{prd_path}: cannot read PRD: {exc}"]
        web_floor = (
            3 if data.get("schema") in INTERACTIVE_WIREFRAME_SCHEMAS else 2
        )
        problems.extend(
            validate_prd_wireframe_data(prd_text, data, web_floor=web_floor)
        )

    executable_code = _strip_javascript_comments(
        "\n".join(parser.executable_scripts)
    )
    active_text_or_code = "\n".join(parser.active_text) + "\n" + executable_code
    dynamic_attributes = {
        match.group(1).lower()
        for match in DYNAMIC_ATTRIBUTE_RE.finditer(executable_code)
    }

    for required in ("page-list", "state-controls", "responsive-controls"):
        if required not in parser.active_ids:
            _add(problems, str(html_path), f"missing reviewer-shell marker {required!r}")
    for required in ("data-responsive-target", "data-layout-qa"):
        if (
            required not in parser.active_attribute_names
            and required not in dynamic_attributes
        ):
            _add(problems, str(html_path), f"missing reviewer-shell marker {required!r}")
    if RUNTIME_QA_RE.search(executable_code) is None:
        _add(problems, str(html_path), "missing reviewer-shell marker 'runLayoutQa'")
    if not any(label in active_text_or_code for label in ("Overview", "All pages")):
        _add(problems, str(html_path), "missing reviewer-shell Overview navigation")
    for required in ("textContent",):
        if required not in active_text_or_code:
            _add(problems, str(html_path), f"missing reviewer-shell marker {required!r}")

    if data.get("schema") == WIREFRAME_SCHEMA:
        for required in ("copy-inventory", "inspector"):
            if required not in parser.active_ids:
                _add(
                    problems,
                    str(html_path),
                    f"missing wireframes/4 reviewer marker {required!r}",
                )
        if "product-copy" not in parser.active_classes and "product-copy" not in executable_code:
            _add(
                problems,
                str(html_path),
                "missing wireframes/4 reviewer marker 'product-copy'",
            )
        if "copyFreeze" not in active_text_or_code:
            _add(
                problems,
                str(html_path),
                "missing wireframes/4 reviewer marker 'copyFreeze'",
            )

    if parser.link_tags:
        _add(problems, str(html_path), "must not contain <link> resources")
    external_resources = parser.external_resources + parser.external_css_resources
    if external_resources:
        _add(
            problems,
            str(html_path),
            "must not load external resources: " + ", ".join(external_resources),
        )
    if parser.css_imports:
        _add(problems, str(html_path), "must not contain CSS @import")
    if parser.active_security_surfaces:
        _add(
            problems,
            str(html_path),
            "must not contain active external or executable network surfaces: "
            + ", ".join(parser.active_security_surfaces),
        )

    claimed_copy_status = data.get("copyFreeze")
    claimed_copy_status = (
        claimed_copy_status.get("status")
        if isinstance(claimed_copy_status, dict)
        else None
    )
    if schema == WIREFRAME_SCHEMA and (
        require_approved
        or require_copy_approved
        or data.get("approvalStatus") == "approved"
        or claimed_copy_status == "approved"
    ):
        actual_shell_sha = canonical_shell_sha256(html)
        try:
            template_path = (
                Path(__file__).resolve().parents[1]
                / "assets"
                / "templates"
                / "WIREFRAMES.template.html"
            )
            canonical_shell_sha = canonical_shell_sha256(
                template_path.read_text(encoding="utf-8")
            )
        except OSError as exc:
            _add(
                problems,
                str(html_path),
                f"cannot read the canonical reviewer-shell script: {exc}",
            )
        else:
            if (
                actual_shell_sha is None
                or canonical_shell_sha is None
                or actual_shell_sha != canonical_shell_sha
            ):
                _add(
                    problems,
                    str(html_path),
                    "approved wireframes/4 must use the exact canonical shell outside "
                    "the product JSON block (expected sha256 "
                    f"{canonical_shell_sha}, found {actual_shell_sha})",
                )

    if require_approved and data.get("approvalStatus") != "approved":
        _add(problems, "wireframe-data.approvalStatus", "must be 'approved'")
    copy_freeze = data.get("copyFreeze")
    copy_status = copy_freeze.get("status") if isinstance(copy_freeze, dict) else None
    if require_copy_approved and schema != WIREFRAME_SCHEMA:
        _add(
            problems,
            "wireframe-data.schema",
            "must be 'wireframes/4' for the Copy Freeze Gate",
        )
    if require_approved and schema != WIREFRAME_SCHEMA:
        _add(
            problems,
            "wireframe-data.schema",
            "must be 'wireframes/4' when structural approval is required",
        )
    if schema == WIREFRAME_SCHEMA and copy_status != "approved":
        if data.get("approvalStatus") == "approved":
            _add(
                problems,
                "wireframe-data.copyFreeze.status",
                "must be 'approved' before structural approvalStatus can be 'approved'",
            )
        elif require_copy_approved or require_approved:
            _add(problems, "wireframe-data.copyFreeze.status", "must be 'approved'")

    return problems


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", required=True, type=Path)
    parser.add_argument("--prd", type=Path, help="cross-check the PRD UI-* surface contract")
    parser.add_argument("--require-filled", action="store_true")
    parser.add_argument(
        "--require-copy-approved",
        action="store_true",
        help="require a schema-4 Copy Freeze before structural approval",
    )
    parser.add_argument("--require-approved", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    problems = validate(
        args.html,
        require_filled=args.require_filled,
        require_copy_approved=args.require_copy_approved,
        require_approved=args.require_approved,
        prd_path=args.prd,
    )
    if problems:
        for problem in problems:
            print(f"FAIL {problem}", file=sys.stderr)
        return 1
    print(f"PASS {args.html} is a valid self-contained wireframe projection")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
