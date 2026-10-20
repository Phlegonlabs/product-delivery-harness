"""A single-keyframe no-op cannot borrow credit from another effect on its owner.

Synthetic Kiln Timer fixture only. Required when PDH_REQUIRE_BROWSER_TESTS=1.
An implicit-end property renders the underlying value, so a no-op such as
[{transform: "none"}] would otherwise sample the change that a real effect on
the same element and property produces. The approved two-keyframe effects
still settle.
"""

from pathlib import Path
import sys
import unittest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS.parents[0]))
sys.path.append(str(TESTS))

import runtime_fixture as fixture  # noqa: E402
import test_runtime_motion_browser as base  # noqa: E402
from test_runtime_motion_browser import NEGATIVE  # noqa: E402

SETTLE = "return Promise.all(anims.map(a => a.finished))"
LATER = 'marks.forEach(mark => anims.push(mark.animate([{transform: "none"}], {duration: 900}))); '
EARLIER = 'const marks = Array.from(stage.querySelectorAll(".kiln-mark"));'


def sources():
    script = fixture.PRODUCT_SCRIPT
    return {
        "shared after": ("kiln-rise", script.replace(SETTLE, LATER + SETTLE)),
        "shared before": ("kiln-rise", script.replace(EARLIER, EARLIER + " const early = marks.map(mark => mark.animate("
                                                      '[{transform: "none"}], {duration: 900}));')
                          .replace(SETTLE, "anims.push(...early); " + SETTLE)),
        "approved two keyframes": ("kiln-rise", script),
    }


class SharedPropertyCreditTests(unittest.TestCase):
    setUpClass = classmethod(base.RuntimeBrowserTests.setUpClass.__func__)
    tearDownClass = classmethod(base.RuntimeBrowserTests.tearDownClass.__func__)
    require, gallery, run_node = (base.RuntimeBrowserTests.require, base.RuntimeBrowserTests.gallery,
                                  base.RuntimeBrowserTests.run_node)

    def test_single_keyframe_noop_cannot_share_a_real_change(self):
        self.require()
        items = [{"name": name, "variant": variant, "stay": False, "url": self.gallery("shared-" + name, script).resolve().as_uri()}
                 for name, (variant, script) in sources().items()]
        out = self.run_node(NEGATIVE, {"items": items})
        for name in ("shared after", "shared before"):
            with self.subTest(name):
                self.assertEqual("invalid", out[name]["seen"][-1], (out[name]["seen"], out[name]["status"]))
                self.assertNotIn("settled", out[name]["seen"])
                self.assertEqual([], out[name]["errors"])
        self.assertEqual("settled", out["approved two keyframes"]["seen"][-1], out["approved two keyframes"])


if __name__ == "__main__":
    unittest.main()
