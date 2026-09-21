"""Synthetic contract fixture. Its observations are not real browser evidence."""

from html import escape
from pathlib import Path
import re


TEMPLATE = Path(__file__).resolve().parents[2] / "assets/templates/HIFI_REVIEWER.template.html"
_TEMPLATE = TEMPLATE.read_text(encoding="utf-8")
REVIEWER_CSS = _TEMPLATE.split("<!-- hifi-reviewer:css:start -->", 1)[1].split("<!-- hifi-reviewer:css:end -->", 1)[0]
REVIEWER_RUNTIME = _TEMPLATE.split("<!-- hifi-reviewer:runtime:start -->", 1)[1].split("<!-- hifi-reviewer:runtime:end -->", 1)[0]
STYLE = '<style>:root{--ink:#243447}.product-button,.product-input,.product-select,.product-link,.product-feedback{color:var(--ink)}@container (max-width:779px){.product-feedback{padding:14px}}</style>' + REVIEWER_CSS


def shell(manifest, page="index.html", component_types=("button", "input", "select", "a")):
    pages = list(dict.fromkeys(row["page"] for row in manifest["surfaces"]))
    targets = list(dict.fromkeys(
        str(target) for row in manifest["surfaces"] if row["page"] == page
        for target in row["responsive"]["targets"]
    ))
    sidebar = ('<aside data-hifi-reviewer-shell data-hifi-reviewer-version="2" aria-label="HiFi review controls">'
               '<a data-hifi-review-view="overview" href="index.html#overview">Overview</a>'
               '<nav data-hifi-page-nav aria-label="Product screens">')
    sidebar += ''.join(
        f'<a href="{escape(name)}"{" aria-current=\"page\"" if name == page else ""}>{escape(name.replace(".html", ""))}</a>'
        for name in pages
    )
    sidebar += '</nav><a data-hifi-review-view="design-tokens" href="index.html#design-tokens">Design Tokens</a>'
    sidebar += '<fieldset data-hifi-responsive-controls><legend>Responsive target</legend>'
    for index, target in enumerate(targets):
        sidebar += (f'<button type="button" data-hifi-target-control="{target}" aria-pressed="{str(index == 0).lower()}">'
                    f'{target}px</button>')
    sidebar += '</fieldset></aside>'
    if page != "index.html":
        return sidebar
    overview = '<section data-hifi-panel="overview" hidden><h1 tabindex="-1">Overview</h1>'
    for row in manifest["surfaces"]:
        overview += (f'<article data-hifi-summary="{escape(row["id"])}" data-route="{escape(row["route"])}" '
                     f'data-states="{escape(" ".join(row["states"]))}" data-targets="{" ".join(map(str, row["responsive"]["targets"]))}">'
                     f'<h2>{escape(row["id"])}: {escape(row["route"])}</h2><p>State coverage</p>')
        for state in row["states"]:
            normalized = str(state).strip().casefold().lstrip(":")
            if normalized in {"n/a", "na"} or normalized.endswith(":n/a") or normalized.endswith(":na"):
                overview += (f'<p data-hifi-state-coverage="{escape(row["id"] + " " + state)}" '
                             f'data-state-reason="Not applicable to this product surface">{escape(state)}: not applicable</p>')
            else:
                overview += (f'<a data-hifi-state-coverage="{escape(row["id"] + " " + state)}" '
                             f'data-state-destination="{escape(state)}" href="{escape(row["page"])}">Open {escape(state)} preview</a>')
        overview += '</article>'
    overview += '</section>'
    specs = '<section data-hifi-panel="design-tokens" hidden><h1 tabindex="-1">Design Tokens — candidate values</h1>'
    for source_page in pages:
        definitions = (
            ("token", "Ink", ":root", "--ink", "span", "ink"),
            ("pattern", "Feedback", ".product-feedback", "color", "section", "feedback"),
        )
        component_definitions = {
            "a": ("Action link", ".product-link", "color", "a", "action-link"),
            "button": ("Primary button", ".product-button", "color", "button", "primary-button"),
            "input": ("Text field", ".product-input", "color", "input", "text-field"),
            "select": ("Choice field", ".product-select", "color", "select", "choice-field"),
        }
        definitions = list(definitions)
        definitions[1:1] = [("component",) + component_defaults for component_defaults in (component_definitions[item] for item in component_types)]
        for kind, name, source, prop, element, group in definitions:
            attrs = (f'data-hifi-spec="{kind}" data-name="{escape(name)}" data-source-page="{source_page}" '
                     f'data-source="{source}" data-property="{prop}" data-variant="default" data-state="default" '
                     f'data-specimen-element="{element}"' + (f' data-shared-group="{group}"' if group else ''))
            sample = {
                "span": '<span class="product-token" data-hifi-specimen-content="Ink color specimen">Aa</span>',
                "button": '<button type="button" class="product-button" data-hifi-specimen-content="Primary button specimen">Save</button>',
                "a": '<a class="product-link" href="#design-tokens" data-hifi-specimen-content="Action link specimen">Open tokens</a>',
                "input": '<input class="product-input" value="Project" data-hifi-specimen-content="Text field specimen">',
                "select": '<select class="product-select" data-hifi-specimen-content="Choice field specimen"><option value="settings" selected>Settings</option></select>',
                "section": '<section class="product-feedback" data-hifi-specimen-content="Feedback specimen">Saved locally.</section>',
            }[element]
            if kind == "token":
                attrs += ' data-token-preview="color"'
            specs += f'<article {attrs}><h3>{escape(source_page)} — {escape(name)}</h3>{sample}<output></output><p>Source {source_page} {source} {prop}</p></article>'
    return sidebar + overview + specs + '</section>'


def add_shell(html, manifest, page="index.html", component_types=("button", "input", "select", "a")):
    """Install the same reusable reviewer fragment a site generator would inline."""
    html = re.sub(r'<!-- reviewer:start -->[\s\S]*?<!-- reviewer:end -->', '', html)
    html = html.replace(STYLE, '')
    html = re.sub(r' data-hifi-default-surface="[^"]*"', '', html)
    html = html.replace('</head>', STYLE + '</head>')
    if page == "index.html":
        html = html.replace('<body>', '<body data-hifi-default-surface="' + manifest["surfaces"][0]["id"] + '">')
    page_rows = [row for row in manifest["surfaces"] if row["page"] == page]
    page_row = page_rows[0] if page_rows else manifest["surfaces"][0]
    targets = ' '.join(str(target) for target in page_row["responsive"]["targets"])
    html = re.sub(r'<main data-ui-surface="([\w-]+)"', rf'<main data-hifi-reviewer-main><div data-hifi-canvas data-hifi-targets="{targets}" data-hifi-target="{page_row["responsive"]["targets"][0]}"><main data-ui-surface="\1"', html, count=1)
    html = html.replace('</main>', '</main></div></main>', 1)
    fragment = ('<!-- reviewer:start -->' + shell(manifest, page, component_types)
                + '<!-- reviewer:end -->' + REVIEWER_RUNTIME + '<script>connectHifiReviewer()</script>')
    return html.replace('</body>', fragment + '</body>')


def _source_html(row, component_types=("button", "input", "select", "a")):
    states = ''.join(f'<span hidden data-state="{escape(state)}" data-responsive-target="{escape(str(target))}"></span>'
                     for state in row["states"] for target in row["responsive"]["targets"])
    selection = (
        '<select class="product-select" data-retention-selected data-specimen-variant="default" data-specimen-state="default" aria-label="Retention choice"><option value="ready" selected>Ready</option></select>'
        if "select" in component_types else
        '<a class="product-link" role="button" data-retention-selected aria-selected="true" data-specimen-variant="default" data-specimen-state="default" href="#details">Refresh</a>'
        if "a" in component_types else ""
    )
    input_control = (
        '<input class="product-input" data-retention-input data-specimen-variant="default" data-specimen-state="default" value="Retained input" aria-label="Retention input">'
        if "input" in component_types else ""
    )
    button_control = (
        '<button type="button" class="product-button" data-specimen-variant="default" data-specimen-state="default">Save</button>'
        if "button" in component_types else ""
    )
    return ('<html><head></head><body><main data-ui-surface="' + escape(row["id"]) + '" data-ui-route="' + escape(row["route"]) + '">'
            '<h1 tabindex="-1">Synthetic product screen</h1>'
            + input_control
            + selection
            + button_control
            + ('<a class="product-link" data-specimen-variant="default" data-specimen-state="default" data-navigation-id="home" href="index.html">Home</a>' if "a" in component_types else "")
            + '<section class="product-feedback" data-specimen-variant="default" data-specimen-state="default">Saved locally.</section>'
            + states + '</main></body></html>')


def observations(manifest, component_types=("button", "input", "select", "a")):
    """Synthesize receipts for validator tests only."""
    from hifi_reviewer import reviewer_contract
    source_rows = {row["page"]: row for row in manifest["surfaces"]}
    documents = {page: add_shell(_source_html(source_rows[page], component_types), manifest, page, component_types) for page in source_rows}
    _, expected = reviewer_contract(documents, manifest)
    observed = dict(expected)
    observed["specimens"] = [dict(row, sourceValue="#243447", specimenValue="#243447", displayValue="#243447")
                             for row in expected["specimens"]]
    observed["retention"] = []
    for row in expected["retention"]:
        input_value = row["inputValueBefore"] if isinstance(row["inputValueBefore"], str) and row["inputValueBefore"].strip() else (
            "Retained input" if row["inputApplicable"] else None
        )
        selected_value = row["selectedValueBefore"] if isinstance(row["selectedValueBefore"], str) and row["selectedValueBefore"].strip() else (
            "ready" if row["selectedApplicable"] else None
        )
        observed["retention"].append(dict(
            row,
            inputValueBefore=input_value,
            inputValueAfter=input_value,
            selectedValueBefore=selected_value,
            selectedValueAfter=selected_value,
        ))
    return observed
