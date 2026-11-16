"""The slop scanner reports default design patterns; it is advisory and never a gate."""

import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).resolve().parent / "fixtures" / "slop-scan"
sys.path.insert(0, str(SCRIPTS))
import direction_review
import reviewer_shell
import slop_scan

ROCKET = chr(0x1F680)
CHECK = chr(0x2713)
HEART = chr(0x2764)
VS16 = chr(0xFE0F)
SHADOW = "box-shadow:0 2px 8px rgba(0,0,0,.1)"
# One page that fires every pattern the scanner can emit.
EVERYTHING = (
    "<style>:root{--g:linear-gradient(120deg,#7c3aed,#4f46e5)}"
    "body{font-family:Inter,sans-serif;background:#f5f0e8}"
    ".a,.b,.c{border-radius:16px;box-shadow:0 2px 8px rgba(0,0,0,.1)}"
    ".hero{background:var(--g);-webkit-background-clip:text;backdrop-filter:blur(10px);"
    "box-shadow:0 10px 40px rgba(124,58,237,.4)}"
    ".grid{display:grid;grid-template-columns:repeat(4,1fr)}.tag{border-radius:9999px}</style>"
    "<h2>" + ROCKET + " Title</h2><span class=tag>1</span><span class=tag>2</span><span class=tag>3</span>"
)
TAGS = "<span class=tag>1</span><span class=tag>2</span><span class=tag>3</span>"


def page(style="", body=""):
    return "<!doctype html><html><head><style>" + style + "</style></head><body>" + body + "</body></html>"


def ids(html, allow=()):
    return {row["id"]: row for row in slop_scan.scan_html(html, set(allow))["hits"]}


def run(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            code = slop_scan.main(list(argv))
        except SystemExit as exit_:
            code = exit_.code
    return code, out.getvalue(), err.getvalue()


class Asserts(unittest.TestCase):
    def assertHit(self, pattern, html):
        self.assertIn(pattern, ids(html), html[:300])

    def assertNoHit(self, pattern, html):
        self.assertNotIn(pattern, ids(html), html[:300])


class PatternTests(Asserts):
    def test_default_sans(self):
        for css in ("body{font-family:Inter,sans-serif}", "h1{font-family:'Segoe UI',Arial}",
                    "body{font:16px/1.5 system-ui}", "html{font-family:sans-serif}",
                    ":root{--f:Roboto,sans-serif}body{font-family:var(--f)}"):
            self.assertHit("default-sans", page(css))
        self.assertHit("default-sans", page(body='<p style="font-family:Poppins">x</p>'))
        for css in ("body{font-family:'Fraunces',Inter,sans-serif}", ".card{font-family:Inter}",
                    "code{font-family:monospace}", "body{font:16px/1.5 Georgia,serif}"):
            self.assertNoHit("default-sans", page(css))
        self.assertNoHit("default-sans", page(body='<a style="font-family:Inter">x</a>'))

    def test_purple_gradient(self):
        for css in ("a{background:linear-gradient(135deg,#7c3aed,#4f46e5)}",
                    "a{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%)}",
                    "a{background-image:radial-gradient(circle,hsl(270 70% 50%),#fff)}",
                    "a{background:repeating-linear-gradient(#7c3aed,#fff 4px)}",
                    ":root{--g:linear-gradient(#7c3aed,#fff)}a{background:var(--g)}",
                    ":root{--p:#8b5cf6}a{background:linear-gradient(var(--p),#fff)}"):
            self.assertHit("purple-gradient", page(css))
        for css in ("a{background:linear-gradient(#0b6e4f,#e8f5ee)}", "a{background:linear-gradient(#777,#888)}",
                    "a{background:linear-gradient(#0ea5e9,#2563eb)}",
                    "a{background:#7c3aed}", ":root{--g:linear-gradient(#7c3aed,#fff)}"):
            self.assertNoHit("purple-gradient", page(css))

    def test_gradient_text(self):
        for css in ("h1{background-clip:text}", "h1{-webkit-background-clip:text}",
                    "h1{background-clip:text,border-box}"):
            self.assertHit("gradient-text", page(css))
        self.assertNoHit("gradient-text", page("h1{background-clip:padding-box}"))

    def test_glass_blur(self):
        for css in ("a{backdrop-filter:blur(8px)}", "a{-webkit-backdrop-filter:saturate(1.4) blur(8px)}"):
            self.assertHit("glass-blur", page(css))
        for css in ("a{filter:blur(4px)}", "a{backdrop-filter:none}"):
            self.assertNoHit("glass-blur", page(css))

    def test_colored_glow(self):
        self.assertHit("colored-glow", page("a{box-shadow:0 8px 32px rgba(124,58,237,.35)}"))
        self.assertHit("colored-glow", page("a{box-shadow:0 1px 2px #000,0 0 24px hsl(200 80% 50%)}"))
        self.assertHit("colored-glow", page("a{box-shadow:0 0 2rem rgba(124,58,237,.35)}"))
        for css in ("a{box-shadow:0 4px 12px rgba(124,58,237,.3)}", "a{box-shadow:0 20px 40px rgba(0,0,0,.15)}",
                    "a{box-shadow:0 12px 32px rgba(16,24,40,.1)}", "a{box-shadow:none}"):
            self.assertNoHit("colored-glow", page(css))

    def test_beige_canvas(self):
        for css in ("body{background:#f5f0e8}", "body{background:#f6f0e6}", "html{background-color:hsl(40 30% 95%)}",
                    ":root{--bg:#f5f0e8}body{background:var(--bg)}"):
            self.assertHit("beige-canvas", page(css))
        for css in ("body{background:#fbfbfa}", "body{background:#fff}", "body{background:#1a1a1a}",
                    ".card{background:#f5f0e8}", "body{background:#e9d8b4}", "body{background:#fff4cc}",
                    "body{background:#f5f0e8 url(x.png)}"):
            self.assertNoHit("beige-canvas", page(css))

    def test_uniform_rounded_cards(self):
        three = ".a{border-radius:16px;%s}.b{border-radius:16px;%s}.c{border-radius:16px;%s}" % ((SHADOW,) * 3)
        self.assertHit("uniform-rounded-cards", page(three))
        self.assertEqual(3, ids(page(three))["uniform-rounded-cards"]["count"])
        self.assertNoHit("uniform-rounded-cards", page(three.replace(".c{border-radius:16px;" + SHADOW + "}", "")))
        self.assertNoHit("uniform-rounded-cards", page(three.replace("16px;" + SHADOW + "}.b", "20px;" + SHADOW + "}.b", 1)))
        self.assertNoHit("uniform-rounded-cards", page(three.replace("16px", "4px")))
        self.assertNoHit("uniform-rounded-cards", page(three.replace(SHADOW, "border:1px solid #ccc")))

    def test_equal_feature_tiles(self):
        for css in ("a{grid-template-columns:repeat(3,1fr)}", "a{grid-template-columns:repeat(4, minmax(0, 1fr))}"):
            self.assertHit("equal-feature-tiles", page(css))
        for css in ("a{grid-template-columns:repeat(2,1fr)}", "a{grid-template-columns:2fr 1fr}",
                    "a{grid-template-columns:repeat(3,200px)}"):
            self.assertNoHit("equal-feature-tiles", page(css))

    def test_emoji_ui(self):
        for body in ("<h2>%s Fast</h2>", "<button>%s Go</button>", "<a href=x>%s Docs</a>", "<ul><li>%s Done</li></ul>"):
            self.assertHit("emoji-ui", page(body=body % ROCKET))
        for body in ("<p>%s Fast</p>", "<h2>Fast</h2>", "<li>%s Done</li>" % CHECK):
            self.assertNoHit("emoji-ui", page(body=body % ROCKET if "%s" in body else body))
        self.assertNoHit("emoji-ui", page(body="<script>var x = '" + ROCKET + "'</script><h2>Fast</h2>"))

    def test_pill_badge_row(self):
        self.assertEqual(3, ids(page(".tag{border-radius:999px}", TAGS))["pill-badge-row"]["count"])
        self.assertHit("pill-badge-row", page(".tag{border-radius:100vmax}", TAGS))
        self.assertHit("pill-badge-row", page(".tag{border-radius:50rem}", TAGS))
        self.assertHit("pill-badge-row", page(body="<i style='border-radius:9999px'>1</i>" * 3))
        self.assertNoHit("pill-badge-row", page(".tag{border-radius:999px}", TAGS[:-len("<span class=tag>3</span>")]))
        self.assertNoHit("pill-badge-row", page(".tag{border-radius:8px}", TAGS))
        self.assertNoHit("pill-badge-row", page("button{border-radius:999px}", "<button>1</button>" * 3))
        self.assertNoHit("pill-badge-row", page(".pill{border-radius:999px}", "<a class='pill btn'>x</a>" * 3))

    def test_neutral_pages_have_no_hits(self):
        html = (FIXTURES / "neutral.html").read_text(encoding="utf-8")
        self.assertEqual({}, ids(html))
        self.assertEqual({}, ids(page()))

    def test_every_listed_pattern_can_be_emitted(self):
        emitted = set(ids(EVERYTHING))
        code, out, _ = run("--list")
        listed = {line.partition(":")[0] for line in out.partition("\n\n")[2].splitlines()}
        self.assertEqual(0, code)
        self.assertEqual(listed, emitted)
        self.assertEqual(set(slop_scan.PATTERNS), emitted)
        self.assertTrue(all(line.partition(": ")[2] for line in out.partition("\n\n")[2].splitlines()))


class ContractTests(Asserts):
    def test_list_prints_the_reads_note_before_every_pattern_id(self):
        code, out, _ = run("--list")
        note, _, patterns = out.partition("\n\n")
        self.assertEqual(0, code)
        self.assertTrue(note.startswith("Reads:"))
        for phrase in ("style attributes", "External sheets", "Named colors", "oklch", "rad or turn", ":root, html or body",
                       "Misses are expected"):
            self.assertIn(phrase, note)
        for pattern in slop_scan.PATTERNS:
            self.assertIn(pattern + ": ", patterns)
            self.assertNotIn(pattern, note)
        self.assertIn("Reads:", slop_scan.__doc__)

    def test_named_colors_and_other_color_functions_are_not_read(self):
        for css in ("a{background:linear-gradient(purple,blue)}", "a{background:linear-gradient(rebeccapurple,#fff)}",
                    "a{background:linear-gradient(oklch(0.5 0.2 290),#fff)}",
                    "a{background:linear-gradient(hsl(0.75turn 70% 50%),#fff)}",
                    "a{background:linear-gradient(hsl(4.7rad 70% 50%),#fff)}"):
            self.assertNoHit("purple-gradient", page(css))
        self.assertHit("purple-gradient", page("a{background:linear-gradient(hsl(270deg 70% 50%),#fff)}"))
        self.assertHit("purple-gradient", page("a{background:linear-gradient(hsla(270,70%,50%,.9),#fff)}"))

    def test_external_and_scripted_styles_are_not_read(self):
        html = ('<link rel=stylesheet href=x.css><script>document.body.style.fontFamily="Inter"</script>'
                "<h2>Title</h2>")
        self.assertEqual({}, ids(html))


class CssTokenizerTests(Asserts):
    def found(self, css):
        return {selector for selector, _ in slop_scan.css_rules(css)}

    def test_rule_after_import_with_a_semicolon_in_a_string_is_found(self):
        self.assertHit("default-sans", page('@import url("data:text/css,");body{font-family:Inter}'))

    def test_statement_at_rules_end_at_their_semicolon(self):
        for statement in ('@charset "utf-8";', "@namespace svg url(http://x/ns);", "@layer a, b;",
                          "@import 'x.css' layer(a);"):
            self.assertEqual({"body"}, self.found(statement + "body{color:red}"), statement)

    def test_rule_after_a_quoted_brace_is_found(self):
        self.assertHit("default-sans", page('i::before{content:"}"}body{font-family:Inter}'))
        self.assertHit("default-sans", page("i::before{content:'{'}body{font-family:Inter}"))
        self.assertHit("default-sans", page('i::before{content:"\\"}"}body{font-family:Inter}'))

    def test_comment_marker_inside_a_string_is_text(self):
        self.assertHit("default-sans", page('a{content:"/* not a comment"}body{font-family:Inter}'))

    def test_comments_are_ignored_everywhere(self):
        self.assertHit("default-sans", page("/* x */ body /* y */ {font-family:/* z */Inter}"))
        self.assertNoHit("default-sans", page("/* body{font-family:Inter} */"))

    def test_group_at_rules_are_entered(self):
        self.assertHit("default-sans", page("@media (min-width:1px){body{font-family:Inter}}"))
        self.assertHit("default-sans", page("@media screen{@supports (display:grid){body{font-family:Inter}}}"))
        self.assertHit("default-sans", page("@layer base{body{font-family:Inter}}"))
        self.assertHit("default-sans", page("@container (min-width:1px){body{font-family:Inter}}"))

    def test_other_block_at_rules_are_skipped_whole(self):
        self.assertNoHit("default-sans", page("@font-face{font-family:Inter;src:local(x)}"))
        self.assertNoHit("purple-gradient", page("@keyframes x{from{background:linear-gradient(#7c3aed,#fff)}}"))
        self.assertNoHit("default-sans", page("@page{font-family:Inter}"))
        self.assertHit("default-sans", page("@font-face{src:local(x)}@keyframes x{to{top:0}}body{font-family:Inter}"))

    def test_unterminated_text_stops_cleanly_with_what_was_parsed(self):
        for css in ("body{font-family:Inter}/* open", 'body{font-family:Inter}a{content:"open',
                    "body{font-family:Inter}a{color:red", "body{font-family:Inter}@media all{a{color:red}"):
            self.assertEqual("body", slop_scan.css_rules(css)[0][0], css)

    def test_nesting_deeper_than_64_raises(self):
        with self.assertRaises(ValueError):
            slop_scan.css_rules("@media all{" * 65)
        self.assertEqual([], slop_scan.css_rules("@media all{" * 64))


class ReviewerShellTests(Asserts):
    TRIGGERS = ('<aside data-hifi-reviewer-shell style="background:linear-gradient(#7c3aed,#4f46e5);'
                'font-family:Inter"><h2>' + ROCKET + ' Review</h2></aside>')

    def test_hifi_shell_from_real_templates_is_ignored(self):
        manifest = {"surfaces": [{"id": "UI-001", "page": "index.html", "platformGroup": "web",
                                  "responsive": {"targets": [390, 1200]}, "states": ["ready", "empty"]}]}
        html = (FIXTURES / "neutral.html").read_text(encoding="utf-8")
        html = reviewer_shell.inject_shared_css(html)
        html = reviewer_shell.inject_shell(manifest, html, "index.html")
        html = reviewer_shell.inject_runtime(html)
        self.assertIn("hifi-reviewer:css:start", html)
        self.assertIn("data-hifi-reviewer-shell", html)
        self.assertEqual({}, ids(html))

    def test_direction_shell_is_ignored(self):
        html = (FIXTURES / "neutral.html").read_text(encoding="utf-8")
        html = reviewer_shell.inject_shared_css(html)
        html = html.replace("</head>", direction_review.style_block() + "\n</head>")
        html = html.replace("<body>", "<body>\n<!-- reviewer:start -->" + self.TRIGGERS + "<!-- reviewer:end -->")
        html = html.replace("</body>", direction_review.runtime_block("pkg") + "\n</body>")
        self.assertIn("direction-reviewer:css:start", html)
        self.assertEqual({}, ids(html))

    def test_shell_markers_hide_planted_triggers_but_product_content_still_hits(self):
        planted = "<!-- reviewer:start -->" + self.TRIGGERS + "<!-- reviewer:end -->"
        self.assertEqual({}, ids(page(body=planted)))
        self.assertEqual({}, ids(page(body=self.TRIGGERS)))
        self.assertIn("emoji-ui", ids(page(body=planted + "<h1>" + ROCKET + " Product</h1>")))

    def test_uppercase_aside_and_style_are_ignored(self):
        aside = "<ASIDE data-hifi-reviewer-shell><H2>" + ROCKET + " Review</H2></ASIDE>"
        style = "<STYLE data-hifi-reviewer-css>body{font-family:Inter}</STYLE>"
        self.assertEqual({}, ids(page(body=aside)))
        self.assertEqual({}, ids("<!doctype html><html><head>" + style + "</head><body></body></html>"))
        self.assertEqual({}, ids(page(body="<!-- REVIEWER:START -->" + self.TRIGGERS + "<!-- REVIEWER:END -->")))

    def test_an_unmatched_start_marker_strips_nothing_further(self):
        for opening in ("<!-- reviewer:start -->", "<aside data-hifi-reviewer-shell>"):
            self.assertIn("emoji-ui", ids(page(body=opening + "<h1>" + ROCKET + " Product</h1>")), opening)
        unmatched = ("<style data-hifi-reviewer-css>body{font-family:Inter}",
                     "<aside data-hifi-reviewer-shell><h1>" + ROCKET + " Product</h1>",
                     "<!-- hifi-reviewer:css:start --><h1>" + ROCKET + " Product</h1>")
        for text in unmatched:
            self.assertEqual(text, slop_scan.strip_shell(text), text)
            # A closed shell before it is still removed; the unmatched one and what follows stay.
            closed = "<style data-hifi-reviewer-css>a{}</style><p>kept</p>"
            self.assertEqual("<p>kept</p>" + text, slop_scan.strip_shell(closed + text), text)
        # The parser never delivers the text of a style element that has no end tag, so an
        # unclosed reviewer style cannot leak shell CSS into the scan.
        self.assertEqual({}, ids("<html><head>" + unmatched[0]))

    def test_shell_elements_only_hide_themselves(self):
        html = page("body{font-family:Inter}", self.TRIGGERS + "<h1>" + ROCKET + " Product</h1>")
        self.assertEqual({"default-sans", "emoji-ui"}, set(ids(html)))
        self.assertEqual(1, ids(html)["emoji-ui"]["count"])


class SubjectTests(Asserts):
    def test_a_later_compound_decides_the_rule(self):
        row = slop_scan.scan_html(page("body .card{background:#f5f0e8;font-family:Inter;background-clip:text}"), set())
        self.assertEqual(["gradient-text"], [hit["id"] for hit in row["hits"]])
        self.assertEqual((1, False), (row["distinctPatterns"], row["cluster"]))

    def test_default_sans_subject_forms(self):
        for selector in ("html body", "main > p", ":root", "body:not(.x)", "body.dark", "h1, .card", ".card, h3",
                         "*", ".wrap p", "html + body", "body:hover", "BODY"):
            self.assertHit("default-sans", page(selector + "{font-family:Inter}"))
        for selector in ("body .card", "html .page", ".card", "body > .wrap", "p::first-line", "body::before",
                         "p:first-line", "h1 span", "main", "p .note"):
            self.assertNoHit("default-sans", page(selector + "{font-family:Inter}"))

    def test_beige_canvas_subject_forms(self):
        for selector in ("html body", ":root", "body:not(.x)", "html", "html.dark", ".card, body"):
            self.assertHit("beige-canvas", page(selector + "{background:#f5f0e8}"))
        for selector in ("body .card", "main > p", "p", "body::before", ".card", "html .page", "*"):
            self.assertNoHit("beige-canvas", page(selector + "{background:#f5f0e8}"))

    def test_inline_styles_belong_to_their_own_element(self):
        self.assertHit("beige-canvas", "<html style='background:#f5f0e8'><body></body></html>")
        self.assertHit("default-sans", "<h2 style='font-family:Inter'>x</h2>")
        self.assertNoHit("beige-canvas", page(body="<div style='background:#f5f0e8'></div>"))


class ElementMatchTests(Asserts):
    def pills(self, selector, body, radius="999px"):
        return ids(page("%s{border-radius:%s}" % (selector, radius), body)).get("pill-badge-row", {}).get("count", 0)

    def test_an_absent_ancestor_means_no_match(self):
        self.assertEqual(0, self.pills(".never-present .tag", TAGS))

    def test_a_present_ancestor_matches(self):
        self.assertEqual(3, self.pills(".row .tag", "<div class=row>" + TAGS + "</div>"))
        self.assertEqual(3, self.pills(".row > .tag", "<div class=row><p>" + TAGS + "</p></div>"))

    def test_ancestors_match_in_order(self):
        outer_first = "<div class=outer><div class=inner>" + TAGS + "</div></div>"
        inner_first = "<div class=inner><div class=outer>" + TAGS + "</div></div>"
        self.assertEqual(3, self.pills(".outer .inner .tag", outer_first))
        self.assertEqual(0, self.pills(".outer .inner .tag", inner_first))

    def test_attribute_presence_and_equality(self):
        badges = "<i data-badge>1</i><i data-badge>2</i><i data-badge>3</i>"
        self.assertEqual(3, self.pills("[data-badge]", badges))
        kinds = '<i data-kind="tag">1</i><i data-kind="tag">2</i><i data-kind="tag">3</i>'
        self.assertEqual(3, self.pills('[data-kind="tag"]', kinds))
        self.assertEqual(3, self.pills("[data-kind=tag]", kinds))
        self.assertEqual(3, self.pills("i[data-kind='tag']", kinds))
        self.assertEqual(0, self.pills('[data-kind="x"]', kinds.replace("tag", "y")))
        self.assertEqual(0, self.pills("[data-missing]", badges))

    def test_sibling_combinators_match_the_subject_only(self):
        self.assertEqual(3, self.pills(".absent + .tag", TAGS))
        self.assertEqual(3, self.pills(".absent ~ .tag", TAGS))

    def test_a_pseudo_element_subject_matches_nothing(self):
        self.assertEqual(0, self.pills(".tag::before", TAGS))
        self.assertEqual(0, self.pills(".tag:after", TAGS))
        self.assertEqual(3, self.pills(".tag:hover", TAGS))

    def test_tags_ids_and_classes_together(self):
        self.assertEqual(3, self.pills("span.tag", TAGS))
        self.assertEqual(0, self.pills("div.tag", TAGS))
        self.assertEqual(0, self.pills(".tag.big", TAGS))
        self.assertEqual(3, self.pills("#a, #b, #c", "<i id=a>1</i><i id=b>2</i><i id=c>3</i>"))

    def test_buttons_stay_exempt(self):
        self.assertEqual(0, self.pills("button", "<button>1</button>" * 3))
        self.assertEqual(0, self.pills("[data-badge]", "<i data-badge role=button>1</i>" * 3))
        self.assertEqual(0, self.pills(".row .tag", "<div class=row>" + "<span class='tag btn'>1</span>" * 3 + "</div>"))

    def test_unreadable_selectors_match_nothing(self):
        self.assertEqual(0, self.pills('[class*="tag"]', TAGS))
        self.assertEqual(0, self.pills("&.tag", TAGS))


class CustomPropertyTests(Asserts):
    def test_custom_property_names_are_case_sensitive(self):
        self.assertHit("purple-gradient", page(".a{--Tone:#7c3aed;background:linear-gradient(var(--Tone),#fff)}"))
        self.assertNoHit("purple-gradient", page(".a{--Tone:#7c3aed;background:linear-gradient(var(--tone),#fff)}"))
        self.assertHit("purple-gradient", page(".a{--tone:#7c3aed;BACKGROUND:linear-gradient(var(--tone),#fff)}"))

    def test_chains_resolve(self):
        css = ":root{--a:var(--b);--b:var(--c);--c:#7c3aed}.x{background:linear-gradient(var(--a),#fff)}"
        self.assertHit("purple-gradient", page(css))

    def test_a_cycle_ends_without_a_hit_or_an_error(self):
        css = ".x{--a:var(--b);--b:var(--a);background:linear-gradient(var(--a),#fff)}"
        self.assertNoHit("purple-gradient", page(css))
        self.assertNoHit("purple-gradient", page(":root{--a:var(--a)}.x{background:linear-gradient(var(--a),#fff)}"))

    def test_the_fallback_applies_when_the_variable_is_unknown(self):
        css = ".card{--tone:#7c3aed}.other{background:linear-gradient(var(--tone,#0b6e4f),#fff)}"
        self.assertNoHit("purple-gradient", page(css))
        self.assertHit("purple-gradient", page(".x{background:linear-gradient(var(--none,#7c3aed),#fff)}"))
        self.assertHit("purple-gradient", page(".x{background:linear-gradient(var(--a,var(--b,#7c3aed)),#fff)}"))

    def test_the_declaring_rule_resolves_its_own_variable(self):
        css = ".card{--tone:#7c3aed;background:linear-gradient(var(--tone),#fff)}"
        self.assertHit("purple-gradient", page(css))

    def test_the_rule_variable_wins_over_the_root_one(self):
        css = ":root{--tone:#0b6e4f}.card{--tone:#7c3aed;background:linear-gradient(var(--tone),#fff)}"
        self.assertHit("purple-gradient", page(css))
        css = ":root{--tone:#7c3aed}.card{--tone:#0b6e4f;background:linear-gradient(var(--tone),#fff)}"
        self.assertNoHit("purple-gradient", page(css))

    def test_html_and_body_rules_also_supply_variables(self):
        for subject in ("html", "body", ":root"):
            css = subject + "{--tone:#7c3aed}.x{background:linear-gradient(var(--tone),#fff)}"
            self.assertHit("purple-gradient", page(css))
        self.assertNoHit("purple-gradient", page(".card{--tone:#7c3aed}.x{background:linear-gradient(var(--tone),#fff)}"))


class FontShorthandTests(Asserts):
    FORMS = ("16px {}", "16px/1.5 {}", "16px/normal {}", "16px / 1.5 {}", "16px /1.5 {}", "16px/ 1.5 {}",
             'italic 600 1rem/1.4 "{}", sans-serif', "bold 100% {}", "12pt {}")

    def test_each_accepted_form_finds_the_family(self):
        for form in self.FORMS:
            self.assertHit("default-sans", page("body{font:%s}" % form.format("Inter")))
            self.assertNoHit("default-sans", page("body{font:%s}" % form.format("Georgia")))

    def test_size_keywords_and_missing_sizes_are_not_read(self):
        for value in ("large Inter", "Inter", "menu"):
            self.assertNoHit("default-sans", page("body{font:%s}" % value))

    def test_a_long_value_is_skipped(self):
        self.assertNoHit("default-sans", page("body{font:16px " + "x" * 600 + ",Inter}"))


class KeywordCaseTests(Asserts):
    def test_values_match_in_any_case(self):
        self.assertHit("purple-gradient", page("a{background:LINEAR-GRADIENT(RGB(124,58,237),HSL(270,70%,50%))}"))
        self.assertHit("purple-gradient", page("a{BACKGROUND:RADIAL-GRADIENT(HSLA(270DEG 70% 50%),#FFF)}"))
        self.assertHit("gradient-text", page("h1{BACKGROUND-CLIP:TEXT}"))
        self.assertHit("glass-blur", page("a{BACKDROP-FILTER:BLUR(8PX)}"))
        self.assertHit("colored-glow", page("a{BOX-SHADOW:0 8PX 32PX RGBA(124,58,237,.35)}"))
        self.assertHit("beige-canvas", page("BODY{BACKGROUND:#F5F0E8}"))
        self.assertHit("equal-feature-tiles", page("a{GRID-TEMPLATE-COLUMNS:REPEAT(3,1FR)}"))
        self.assertHit("default-sans", page("body{FONT-FAMILY:INTER}"))
        self.assertHit("default-sans", page("body{FONT:16PX/1.5 ARIAL}"))
        self.assertHit("pill-badge-row", page(".tag{BORDER-RADIUS:999PX}", TAGS))
        self.assertHit("pill-badge-row", page(".tag{border-radius:100VMAX}", TAGS))
        self.assertHit("purple-gradient", page(".a{--c:#7C3AED;background:LINEAR-GRADIENT(VAR(--c),#FFF)}"))

    def test_uppercase_class_names_stay_case_sensitive(self):
        self.assertEqual({}, ids(page(".Tag{border-radius:999px}", TAGS)))
        self.assertEqual({}, ids(page(".a{--Tone:#7c3aed}.a{background:linear-gradient(var(--TONE),#fff)}")))


class RadiusTests(Asserts):
    def cards(self, *values):
        sheet = "".join(".c%d{border-radius:%s;%s}" % (index, value, SHADOW) for index, value in enumerate(values))
        return ids(page(sheet)).get("uniform-rounded-cards", {}).get("count", 0)

    def pills(self, value, count=3):
        return ids(page(".tag{border-radius:%s}" % value, TAGS[:count * len("<span class=tag>1</span>")]))

    def test_mixed_zero_or_percent_components_are_not_cards(self):
        self.assertEqual(0, self.cards("16px 0", "16px 0", "16px 0"))
        self.assertEqual(0, self.cards("16px 50%", "16px 50%", "16px 50%"))
        self.assertEqual(0, self.cards("16px auto", "16px auto", "16px auto"))
        self.assertEqual(0, self.cards("0", "0", "0"))

    def test_equal_radii_in_any_unit_or_shorthand_form_are_one_group(self):
        self.assertEqual(3, self.cards("1rem", "16px", "16px 16px"))
        self.assertEqual(3, self.cards("16px", "16px 16px 16px", "16px 16px 16px 16px"))
        self.assertEqual(3, self.cards("16px", "16px / 16px", "1rem 1rem 1rem 1rem / 1rem"))
        self.assertEqual(0, self.cards("16px", "16px", "20px"))
        self.assertEqual(0, self.cards("16px 20px", "20px 16px", "16px"))

    def test_the_elliptical_form_needs_every_component_in_range(self):
        self.assertEqual(3, self.cards("16px / 20px", "16px / 20px", "1rem / 20px"))
        self.assertEqual(0, self.cards("16px / 40px", "16px / 40px", "16px / 40px"))
        self.assertEqual(0, self.cards("16px / 1 / 2", "16px / 1 / 2", "16px / 1 / 2"))

    def test_pill_needs_every_component_at_its_threshold(self):
        self.assertNotIn("pill-badge-row", self.pills("999px 0"))
        self.assertNotIn("pill-badge-row", self.pills("999px 50%"))
        self.assertNotIn("pill-badge-row", self.pills("50%"))
        self.assertNotIn("pill-badge-row", self.pills("0"))
        self.assertNotIn("pill-badge-row", self.pills("998px"))
        self.assertNotIn("pill-badge-row", self.pills("999px / 20px"))
        self.assertIn("pill-badge-row", self.pills("999px"))
        self.assertIn("pill-badge-row", self.pills("9999px 9999px"))
        self.assertIn("pill-badge-row", self.pills("999px 999px 999px 999px / 999px"))
        self.assertIn("pill-badge-row", self.pills("50em"))


class EmojiTests(Asserts):
    def test_default_emoji_hit_in_a_button_or_heading(self):
        for glyph in (chr(0x23F0), chr(0x2728), ROCKET, HEART + VS16, chr(0x2705), chr(0x26A1), chr(0x2B50), chr(0x1F000)):
            self.assertHit("emoji-ui", page(body="<button>%s Go</button>" % glyph))
            self.assertHit("emoji-ui", page(body="<h2>Go %s</h2>" % glyph))

    def test_plain_text_glyphs_do_not_hit(self):
        for glyph in (chr(0x2715), chr(0x2630), CHECK, chr(0x2605), chr(0x2192), chr(0xA9), HEART, chr(0x2B06),
                      chr(0x25B6), chr(0x2026)):
            self.assertNoHit("emoji-ui", page(body="<button>%s Go</button><h2>%s Title</h2>" % (glyph, glyph)))

    def test_a_bare_heart_hits_only_with_the_variation_selector(self):
        self.assertNoHit("emoji-ui", page(body="<h2>" + HEART + "</h2>"))
        self.assertHit("emoji-ui", page(body="<h2>" + HEART + VS16 + "</h2>"))
        self.assertHit("emoji-ui", page(body="<h2>" + CHECK + VS16 + "</h2>"))


class AllowAndClusterTests(unittest.TestCase):
    def report(self, html, allow=()):
        return slop_scan.scan_html(html, set(allow))

    def test_cluster_at_exactly_three(self):
        two = page("body{font-family:Inter}a{backdrop-filter:blur(4px)}")
        three = page("body{font-family:Inter}a{backdrop-filter:blur(4px)}h1{background-clip:text}")
        self.assertEqual((2, False), (self.report(two)["distinctPatterns"], self.report(two)["cluster"]))
        self.assertEqual((3, True), (self.report(three)["distinctPatterns"], self.report(three)["cluster"]))

    def test_repeated_pattern_counts_once_toward_a_cluster(self):
        html = page("body{font-family:Inter}h1{font-family:Roboto}h2{font-family:Arial}")
        report = self.report(html)
        self.assertEqual(3, report["hits"][0]["count"])
        self.assertEqual((1, False), (report["distinctPatterns"], report["cluster"]))

    def test_allow_keeps_the_hit_listed_but_uncounted(self):
        html = page("body{font-family:Inter}a{backdrop-filter:blur(4px)}h1{background-clip:text}")
        report = self.report(html, ["default-sans"])
        self.assertEqual({"default-sans": True, "glass-blur": False, "gradient-text": False},
                         {row["id"]: row["allowed"] for row in report["hits"]})
        self.assertEqual((2, False), (report["distinctPatterns"], report["cluster"]))

    def test_evidence_is_short_and_capped_at_three(self):
        html = page("".join("h%d{font-family:Inter}" % n for n in range(1, 6)))
        row = self.report(html)["hits"][0]
        self.assertEqual(5, row["count"])
        self.assertEqual(3, len(row["evidence"]))
        self.assertTrue(all(len(item) <= 90 for item in row["evidence"]))

    def test_a_long_selector_is_cut_to_exactly_ninety_characters(self):
        selector = "body" + ".very-long-class-name" * 6
        self.assertGreater(len(selector), 90)
        row = self.report(page(selector + "{font-family:Inter}"))["hits"][0]
        expected = ("%s { font-family: Inter }" % selector)[:90]
        self.assertEqual([expected], row["evidence"])
        self.assertEqual(90, len(expected))


class TimeBoundTests(unittest.TestCase):
    def hits(self, html):
        began = time.perf_counter()
        report = slop_scan.scan_html(html, set())
        self.assertLess(time.perf_counter() - began, 10)
        return {row["id"] for row in report["hits"]}

    def test_a_long_font_value_finishes(self):
        self.assertEqual(set(), self.hits(page("body{font:1px/" + "9" * 100_000 + "}")))
        self.assertEqual(set(), self.hits(page("body{font:1px/" + "9" * 100_000 + "a}")))

    def test_many_unmatched_reviewer_start_markers_finish(self):
        for opening in ("<!-- reviewer:start -->", "<!-- hifi-reviewer:css:start -->", "<aside data-hifi-reviewer-shell>"):
            self.assertIn("default-sans", self.hits(opening * 20_000 + page("body{font-family:Inter}")), opening)
        for opening in ("<style ", "<aside ", "<style data-hifi-reviewer-css "):
            self.hits(opening * 20_000 + page("body{font-family:Inter}"))

    def test_many_unclosed_comments_finish(self):
        self.assertEqual(set(), self.hits(page("/*" * 20_000)))

    def test_many_open_parentheses_and_spaces_finish(self):
        self.assertEqual(set(), self.hits(page("a{box-shadow:" + "rgb(" * 20_000 + "}")))
        self.assertEqual(set(), self.hits(page("a{background:" + "var(" + " " * 100_000 + "}")))
        self.assertEqual(set(), self.hits(page("a{color:red" + " " * 100_000 + "x}")))

    def test_a_large_font_face_block_is_skipped_and_the_next_rule_found(self):
        css = "@font-face{src:url(data:font/woff2;base64," + "AAAA" * 750_000 + ")}body{font-family:Inter}"
        self.assertEqual({"default-sans"}, self.hits(page(css)))

    def test_many_pill_rules_on_many_elements_finish(self):
        sheet = "".join(".a%d{border-radius:999px}" % number for number in range(4000))
        self.assertEqual({"pill-badge-row"}, self.hits(page(sheet, "<i class=a1></i>" * 4000)))

    def test_many_root_variables_and_rules_finish(self):
        sheet = ":root{" + "".join("--v%d:1;" % number for number in range(20_000)) + "}"
        sheet += "".join(".a%d{color:var(--v%d)}" % (number, number) for number in range(20_000))
        self.assertEqual(set(), self.hits(page(sheet)))

    def test_deeply_nested_html_finishes(self):
        self.assertEqual({"emoji-ui"}, self.hits(page(body="<li>" * 20_000 + ROCKET)))


class TempRootCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write(self, relative, text):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
        return relative

    def scan(self, *extra):
        return run("--repo-root", str(self.root), *extra)


class NeverCrashTests(TempRootCase):
    def scan_text(self, html):
        return self.scan("--page", self.write("docs/p.html", html))

    def test_unterminated_comment_string_and_block_exit_zero(self):
        for css in ("body{font-family:Inter}/* open", 'a{content:"open', "a{color:red"):
            code, out, err = self.scan_text(page(css))
            self.assertEqual((0, ""), (code, err), css)
            self.assertEqual("slop-scan/1", json.loads(out)["schema"])

    def test_deep_css_nesting_exits_two_with_one_line(self):
        html = page("@media all{" * 2000)
        path = self.root / "docs" / "p.html"
        path.parent.mkdir(parents=True)
        path.write_text(html, encoding="utf-8")
        result = subprocess.run([sys.executable, str(SCRIPTS / "slop_scan.py"), "--repo-root", str(self.root),
                                 "--page", "docs/p.html"], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(2, result.returncode)
        self.assertEqual("", result.stdout)
        self.assertEqual(1, len(result.stderr.strip().splitlines()), result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_odd_inputs_never_raise(self):
        for html in ("", "<", "<style>", "<style></style>", "<div style=>", "<a style='x'>", "<h1>\x00</h1>",
                     page("}}}{{{;;;"), page("a{;;;}b{:}c{x}"), page("@media{}@{}"), page("a{border-radius:/}"),
                     page("a{box-shadow:,,,}"), page("a{font:/}"), page("{}"), page("@"), page("a{b:c}}}"),
                     page("a{background:linear-gradient(rgb(,),hsl())}"), page("a b c d e{}" * 3)):
            code, _, err = self.scan_text(html)
            self.assertEqual((0, ""), (code, err), html[:60])


class CommandTests(TempRootCase):
    def setUp(self):
        super().setUp()
        self.cluster = self.write("docs/a.html", (FIXTURES / "cluster.html").read_text(encoding="utf-8"))
        self.neutral = self.write("docs/b.html", (FIXTURES / "neutral.html").read_text(encoding="utf-8"))

    def test_report_shape_and_exit_zero_with_clusters(self):
        code, out, _ = self.scan("--page", self.cluster, "--page", self.neutral)
        self.assertEqual(0, code)
        report = json.loads(out)
        self.assertEqual("slop-scan/1", report["schema"])
        self.assertEqual(1, report["clusters"])
        first, second = report["pages"]
        self.assertEqual((self.cluster, True), (first["path"], first["cluster"]))
        self.assertEqual(hashlib.sha256((self.root / self.cluster).read_bytes()).hexdigest(), first["sha256"])
        self.assertEqual((self.neutral, 0, False, []), (second["path"], second["distinctPatterns"],
                                                        second["cluster"], second["hits"]))
        self.assertEqual({"id", "count", "evidence", "allowed"}, set(first["hits"][0]))
        self.assertEqual([row["id"] for row in first["hits"]], sorted(row["id"] for row in first["hits"]))

    def test_output_is_deterministic(self):
        runs = {self.scan("--page", self.cluster, "--page", self.neutral, "--allow", "emoji-ui")[1] for _ in range(2)}
        self.assertEqual(1, len(runs))
        with_allow = json.loads(runs.pop())
        self.assertEqual(["emoji-ui"], with_allow["allowed"])

    def test_allow_accepts_several_ids_and_rejects_unknown_ones(self):
        code, out, _ = self.scan("--page", self.cluster, "--allow", "emoji-ui", "glass-blur")
        self.assertEqual(0, code)
        self.assertEqual(["emoji-ui", "glass-blur"], json.loads(out)["allowed"])
        code, out, err = self.scan("--page", self.cluster, "--allow", "no-such-pattern")
        self.assertEqual((2, ""), (code, out))
        self.assertIn("unknown pattern id: no-such-pattern", err)

    def test_missing_and_escaping_pages_exit_two(self):
        for bad in ("docs/missing.html", "../outside.html", "docs/../../outside.html", "/etc/hosts",
                    "docs\\a.html", "C:/Windows/win.ini"):
            code, out, err = self.scan("--page", bad)
            self.assertEqual((2, ""), (code, out), bad)
            self.assertEqual(1, len(err.strip().splitlines()), bad)
        self.assertEqual(2, run("--repo-root", str(self.root))[0])

    def test_linked_pages_are_rejected(self):
        link = self.root / "docs" / "link.html"
        try:
            os.symlink(self.root / self.cluster, link)
            self.addCleanup(os.unlink, link)
        except (OSError, NotImplementedError):
            junction = self.root / "linked"
            made = subprocess.run(["cmd", "/c", "mklink", "/J", str(junction), str(self.root / "docs")],
                                  capture_output=True) if os.name == "nt" else None
            if made is None or made.returncode != 0:
                self.skipTest("this account cannot create links")
            self.addCleanup(os.rmdir, junction)
            link = junction / "a.html"
        code, _, err = self.scan("--page", link.relative_to(self.root).as_posix())
        self.assertEqual(2, code)
        self.assertIn("links", err)

    def test_out_writes_and_refuses_overwrite(self):
        code, out, _ = self.scan("--page", self.neutral, "--out", "docs/report.json")
        self.assertEqual((0, ""), (code, out))
        written = (self.root / "docs" / "report.json").read_bytes()
        self.assertEqual("slop-scan/1", json.loads(written)["schema"])
        code, _, err = self.scan("--page", self.cluster, "--out", "docs/report.json")
        self.assertEqual(2, code)
        self.assertIn("--overwrite", err)
        self.assertEqual(written, (self.root / "docs" / "report.json").read_bytes())
        self.assertEqual(0, self.scan("--page", self.cluster, "--out", "docs/report.json", "--overwrite")[0])
        self.assertNotEqual(written, (self.root / "docs" / "report.json").read_bytes())
        self.assertEqual(2, self.scan("--page", self.neutral, "--out", "../report.json")[0])

    def test_script_runs_from_the_command_line(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / "slop_scan.py"), "--repo-root", str(self.root),
                                 "--page", self.cluster], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(json.loads(result.stdout)["pages"][0]["cluster"])


if __name__ == "__main__":
    unittest.main()
