"""Focused regression tests for dependency-aware CSS animation provenance."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import animation_provenance as provenance


class AnimationProvenanceTests(unittest.TestCase):
    def test_unrelated_conditional_properties_do_not_block_provenance(self):
        node = {"tag": "div", "map": {"class": "busy"}, "parent": None}
        css = ("@keyframes pulse{to{opacity:1}}.busy{animation:pulse 1s linear} "
               "@media(prefers-color-scheme:dark){:root{--paper:#111}.layout{--ink:red}}")
        self.assertEqual("source_backed", provenance.source_status(css, node))

    def test_unrelated_keyframe_properties_are_safe(self):
        node = {"tag": "div", "map": {"class": "busy"}, "parent": None}
        css = (".busy{--animation-color:#123}@keyframes pulse{"
               "from{--animation-color:blue;opacity:0}to{opacity:1}}"
               ".busy{animation:pulse 1s linear}"
               "@media(prefers-color-scheme:dark){.layout{--ink:red}}")
        self.assertEqual("source_backed", provenance.source_status(css, node))

    def test_unrelated_registration_does_not_block_provenance(self):
        node = {"tag": "div", "map": {"class": "busy"}, "parent": None}
        css = ("@property --unrelated{syntax:'<length>';inherits:true;initial-value:0px}"
               "@keyframes pulse{to{opacity:1}}.busy{animation:pulse 1s linear}")
        self.assertEqual("source_backed", provenance.source_status(css, node))

    def test_conditional_dependencies_relevant_to_the_animation_fail_closed(self):
        node = {"tag": "div", "map": {"class": "busy"}, "parent": None}
        base = "@keyframes pulse{to{transform:translateX(var(--distance))}}"
        cases = ("direct", "transitive", "fallback", "keyframe-direct",
                 "keyframe-transitive", "registered", "layered")
        css_by_case = {
            "direct": ".busy{animation:pulse 1s linear}@media(width>=600px){:root{--distance:2px}}",
            "transitive": (":root{--speed:1s}.busy{--duration:var(--speed)}"
                           ".busy{animation:pulse var(--duration) linear}"
                           "@media(width>=600px){:root{--speed:2s}}"),
            "fallback": (".busy{--present:linear;animation:pulse 1s var(--present,var(--distance))}"
                         "@media(width>=600px){:root{--distance:2px}}"),
            "keyframe-direct": ".busy{animation:pulse 1s linear}@media(width>=600px){:root{--distance:2px}}",
            "keyframe-transitive": (":root{--travel:var(--distance)}"
                                    ".busy{animation:pulse 1s linear}"
                                    "@media(width>=600px){:root{--distance:2px}}"),
            "registered": ("@property --distance{syntax:'<length>';inherits:true;initial-value:0px}"
                           ".busy{animation:pulse 1s linear}"),
            "layered": ".busy{animation:pulse 1s linear}@layer theme{:root{--distance:2px}}",
        }
        for case in cases:
            with self.subTest(case=case):
                self.assertEqual("unresolved",
                                 provenance.source_status(base + css_by_case[case], node))

    def test_conditional_animation_and_existing_failure_modes_stay_unresolved(self):
        node = {"tag": "div", "map": {"class": "busy"}, "parent": None}
        base = "@keyframes pulse{to{opacity:1}}"
        cases = (
            base + ".busy{animation:pulse 1s}@media(width>=600px){.busy{animation:none}}",
            base + ".busy{animation:var(--missing) 1s}",
            base + "@layer motion{.busy{animation:pulse 1s}}",
            base + ".busy{--motion:var(--motion);animation:var(--motion) 1s}",
            base + '.busy{animation:"pulse" 1s}',
            base + ".busy{animation:pulse 1s}.busy{all:initial}",
        )
        for css in cases:
            with self.subTest(css=css):
                self.assertEqual("unresolved", provenance.source_status(css, node))


if __name__ == "__main__":
    unittest.main()
