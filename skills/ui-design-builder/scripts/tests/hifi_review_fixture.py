"""Synthetic contract fixture. Its observations are not real browser evidence."""

from html import escape


def shell(manifest, page="index.html"):
    pages = list(dict.fromkeys(row["page"] for row in manifest["surfaces"]))
    sidebar = '<aside data-hifi-reviewer-shell><a data-hifi-review-view="overview" href="index.html#overview">Overview</a><nav data-hifi-page-nav>'
    sidebar += ''.join(f'<a href="{escape(name)}">{escape(name)}</a>' for name in pages)
    sidebar += '</nav><a data-hifi-review-view="design-tokens" href="index.html#design-tokens">Design Tokens</a></aside>'
    if page != "index.html":
        return sidebar
    overview = '<section data-hifi-panel="overview" hidden><h1 tabindex="-1">Overview</h1>'
    for row in manifest["surfaces"]:
        overview += (f'<article data-hifi-summary="{escape(row["id"])}" data-route="{escape(row["route"])}" '
                     f'data-states="{escape(" ".join(row["states"]))}" data-targets="{" ".join(map(str, row["responsive"]["targets"]))}">'
                     f'{escape(row["id"])}: {escape(row["route"])} — {escape(", ".join(row["states"]))}</article>')
    overview += '</section>'
    specs = '<section data-hifi-panel="design-tokens" hidden><h1 tabindex="-1">Design Tokens — candidate values</h1>'
    for source_page in pages:
        for kind, name, source, prop in (
            ("token", "ink", ":root", "--ink"),
            ("component", "button-primary", ".product-button", "color"),
            ("pattern", "feedback", ".product-feedback", "color"),
        ):
            specs += (f'<div data-hifi-spec="{kind}" data-name="{source_page}-{name}" data-source-page="{source_page}" data-source="{source}" data-property="{prop}" '
                      f'data-variant="primary" data-state="default"><span>{source_page}: {name}</span><output></output></div>')
    return sidebar + overview + specs + '</section>'


STYLE = '<style>:root{--ink:#243447}.product-button,.product-feedback{color:var(--ink)}</style>'


def add_shell(html, manifest, page="index.html"):
    # Fixtures are rebuilt after any change to manifest scope.
    import re
    html = re.sub(r'<!-- reviewer:start -->[\s\S]*?<!-- reviewer:end -->', '', html)
    html = html.replace(STYLE, '')
    html = re.sub(r' data-hifi-default-surface="[^"]*"', '', html)
    html = html.replace('</head>', STYLE + '</head>')
    if page == "index.html":
        html = html.replace('<body>', '<body data-hifi-default-surface="' + manifest["surfaces"][0]["id"] + '">')
    return html.replace('</body>', '<!-- reviewer:start -->' + shell(manifest, page) + '<!-- reviewer:end --></body>')


def observations(manifest):
    """Synthesize receipts for validator tests only."""
    from hifi_reviewer import reviewer_contract
    pages = list(dict.fromkeys(row["page"] for row in manifest["surfaces"]))
    documents = {page: add_shell('<html><head></head><body></body></html>', manifest, page) for page in pages}
    _, expected = reviewer_contract(documents, manifest)
    return dict(expected, specimens=[dict(row, sourceValue="#243447", specimenValue="#243447", displayValue="#243447") for row in expected["specimens"]])
