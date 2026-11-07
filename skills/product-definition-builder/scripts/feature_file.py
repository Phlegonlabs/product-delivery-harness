"""Reader for the PRD feature files (`docs/product/features/*.feature`).

One feature file holds the scenarios that make a package's Test Obligations
executable. The reader keeps to the subset the contract needs: `Feature:`,
`Background:`, `Scenario:`, tags, comments and Given/When/Then/And/But steps.
Scenario Outline, Examples, doc strings and data tables are rejected with a
line number so the contract stays small and every scenario maps one-to-one
onto a delivery-acceptance scenario.

Conventions frozen by the Harness:

- every scenario carries exactly one `@TEST-...` tag (its Test Obligation);
- the scenario id is `<TEST-ID>/<slug of the scenario name>`;
- `@platform:<value>`, `@auth:<value>` and `@env:<value>` tags override the
  run profile for that scenario, take only the values in PROFILE_VALUES and
  never sit on the Feature line; any other tag is kept but not interpreted;
- Background steps are Given steps of every scenario in the file;
- And/But continue the previous keyword.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

TEST_TAG = re.compile(r"^@(TEST-(?:[A-Z][A-Z0-9]{1,4}-)?\d{3,})$")
PROFILE_TAG = re.compile(r"^@(platform|auth|env):([a-z][a-z0-9-]*)$")
STEP = re.compile(r"^(Given|When|Then|And|But)\s+(\S.*?)\s*$")
KEYWORDS = ("Given", "When", "Then")
UNSUPPORTED = ("Scenario Outline:", "Scenario Template:", "Examples:", "Scenarios:", "Rule:")
# The delivery-acceptance profile values (delivery-harness check_delivery_acceptance.py),
# copied so a bad tag fails before Product Definition Approval, not after it.
PROFILE_VALUES = {
    "platform": frozenset({
        "web", "browser-extension", "ios", "android", "macos", "windows", "linux",
        "desktop", "agent", "api", "cli",
    }),
    "auth": frozenset({"mock", "real", "none"}),
    "env": frozenset({"local", "test", "preview", "staging", "production"}),
}


class FeatureError(ValueError):
    """A feature file that does not follow the contract; the message names the line."""


@dataclass
class Step:
    keyword: str
    text: str
    line: int


@dataclass
class Scenario:
    name: str
    tags: list[str]
    steps: list[Step]
    line: int

    @property
    def test_id(self) -> str:
        return next(m.group(1) for tag in self.tags if (m := TEST_TAG.match(tag)))

    @property
    def scenario_id(self) -> str:
        return scenario_id(self.test_id, self.name)

    @property
    def profile(self) -> dict[str, str]:
        found: dict[str, str] = {}
        for tag in self.tags:
            match = PROFILE_TAG.match(tag)
            if match:
                found[match.group(1)] = match.group(2)
        return found

    def steps_for(self, keyword: str) -> list[Step]:
        return [step for step in self.steps if step.keyword == keyword]


@dataclass
class Feature:
    name: str
    tags: list[str]
    scenarios: list[Scenario]
    path: str
    background: list[Step] = field(default_factory=list)

    def test_ids(self) -> set[str]:
        return {scenario.test_id for scenario in self.scenarios}


def slug(name: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not text:
        raise FeatureError("a scenario name needs at least one letter or digit")
    return text


def scenario_id(test_id: str, name: str) -> str:
    return f"{test_id}/{slug(name)}"


def parse_feature_text(text: str, path: str = "<text>") -> Feature:
    """Parse one feature file. Raises FeatureError with `path:line` on any violation."""

    def fail(line: int, message: str) -> FeatureError:
        return FeatureError(f"{path}:{line}: {message}")

    feature: Feature | None = None
    pending_tags: list[str] = []
    current: Scenario | None = None
    in_background = False
    last_keyword: str | None = None

    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("'''", '"""')):
            raise fail(number, "doc strings are not supported")
        if line.startswith("|"):
            raise fail(number, "data tables are not supported")
        if line.startswith(UNSUPPORTED):
            raise fail(number, f"{line.split(':', 1)[0]} is not supported")

        if line.startswith("@"):
            tags = line.split()
            bad = [tag for tag in tags if not tag.startswith("@") or len(tag) < 2 or " " in tag]
            if bad:
                raise fail(number, f"malformed tag line {line!r}")
            pending_tags.extend(tags)
            continue

        if line.startswith("Feature:"):
            if feature is not None:
                raise fail(number, "a file holds one Feature")
            name = line[len("Feature:"):].strip()
            if not name:
                raise fail(number, "Feature needs a name")
            profile_tags = [tag for tag in pending_tags if tag.startswith(("@platform:", "@auth:", "@env:"))]
            if profile_tags:
                raise fail(number, f"{' '.join(profile_tags)} belongs on a Scenario, not the Feature")
            feature = Feature(name=name, tags=pending_tags, scenarios=[], path=path)
            pending_tags = []
            continue

        if feature is None:
            raise fail(number, "Feature: must come first")

        if line.startswith("Background:"):
            if pending_tags:
                raise fail(number, "Background takes no tags")
            if feature.scenarios or feature.background:
                raise fail(number, "one Background, before the first Scenario")
            in_background = True
            current = None
            last_keyword = None
            continue

        if line.startswith(("Scenario:", "Example:")):
            name = line.split(":", 1)[1].strip()
            if not name:
                raise fail(number, "Scenario needs a name")
            test_tags = [tag for tag in pending_tags if TEST_TAG.match(tag)]
            if len(test_tags) != 1:
                raise fail(number, f"Scenario {name!r} needs exactly one @TEST-... tag, found {len(test_tags)}")
            for tag in pending_tags:
                key = tag.split(":", 1)[0][1:]
                if key not in PROFILE_VALUES:
                    continue
                match = PROFILE_TAG.match(tag)
                if not match:
                    raise fail(number, f"malformed profile tag {tag!r}")
                if match.group(2) not in PROFILE_VALUES[key]:
                    raise fail(number, f"{tag} must be one of {sorted(PROFILE_VALUES[key])}")
            current = Scenario(name=name, tags=pending_tags, steps=list(feature.background), line=number)
            feature.scenarios.append(current)
            pending_tags = []
            in_background = False
            last_keyword = "Given" if feature.background else None
            continue

        match = STEP.match(line)
        if not match:
            raise fail(number, f"unexpected line {line!r}")
        if pending_tags:
            raise fail(number, "tags must precede a Scenario")
        keyword, body = match.group(1), match.group(2)
        if keyword in ("And", "But"):
            if last_keyword is None:
                raise fail(number, f"{keyword} has no previous Given/When/Then")
            keyword = last_keyword
        last_keyword = keyword
        step = Step(keyword=keyword, text=body, line=number)
        if in_background:
            if keyword != "Given":
                raise fail(number, "Background holds Given steps only")
            feature.background.append(step)
        elif current is None:
            raise fail(number, "a step must belong to a Scenario or Background")
        else:
            current.steps.append(step)

    if feature is None:
        raise fail(0, "empty feature file")
    if pending_tags:
        raise fail(0, "tags at end of file without a Scenario")
    seen: dict[str, int] = {}
    for scenario in feature.scenarios:
        if not scenario.steps_for("When") or not scenario.steps_for("Then"):
            raise fail(scenario.line, f"Scenario {scenario.name!r} needs at least one When and one Then")
        sid = scenario.scenario_id
        if sid in seen:
            raise fail(scenario.line, f"duplicate scenario id {sid} (first at line {seen[sid]})")
        seen[sid] = scenario.line
    return feature
