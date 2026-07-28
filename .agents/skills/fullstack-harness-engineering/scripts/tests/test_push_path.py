#!/usr/bin/env python3
"""The ordinary path: cut a work branch, commit, push, done.

This is what every run actually does, so it gets its own file. Each test names
one rule the push gate enforces, and the last four are regressions for bugs the
old branch-protection model shipped.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from harness_authorization import authorization_covers  # noqa: E402

SHA = "a" * 40
DIGEST = "b" * 64


def run_with_push(
    *,
    branch: str = "refs/heads/codex/add-search",
    targets: list | str | None = None,
    expires_when: str = "explicit_revocation",
    status: str = "running",
) -> dict:
    """A minimal RUN carrying one ordinary push grant."""
    if targets is None:
        targets = ["branch:refs/heads/codex/add-search"]
    return {
        "schema_version": 10,
        "run_id": "RUN-1",
        "status": status,
        "plan": {"revision": 1, "digest_sha256": DIGEST},
        "integration": {"branch": branch, "integration_head_sha": SHA},
        "landing": {
            "mode": "integration_push",
            "remote": "origin",
            "pushed_head_sha": SHA,
            "continuity": None,
        },
        "authorizations": {
            "push": {
                "authorized": True,
                "source": "user: build it and push the branch",
                "authorized_head_sha": SHA,
                "expires_when": expires_when,
                "scope": {
                    "run_id": "RUN-1",
                    "mission_ids": ["M1"],
                    "targets": targets,
                    "plan_revision": 1,
                    "plan_digest_sha256": DIGEST,
                },
            }
        },
    }


class OrdinaryPushPathTests(unittest.TestCase):
    def test_one_execution_intent_grant_covers_the_work_branch_push(self) -> None:
        """No branch-protection evidence and no second instruction required."""
        run = run_with_push()
        self.assertTrue(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/add-search"
            )
        )

    def test_wildcard_mission_scope_covers_any_mission(self) -> None:
        run = run_with_push()
        run["authorizations"]["push"]["scope"]["mission_ids"] = ["*"]
        self.assertTrue(
            authorization_covers(
                run, "push", "M-UNLISTED", "branch:refs/heads/codex/add-search"
            )
        )

    def test_push_to_another_branch_is_not_covered(self) -> None:
        run = run_with_push()
        self.assertFalse(
            authorization_covers(run, "push", "M1", "branch:refs/heads/codex/other")
        )

    def test_grant_expires_with_the_run(self) -> None:
        run = run_with_push(expires_when="run_complete", status="complete")
        self.assertFalse(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/add-search"
            )
        )

    def test_stale_head_binding_is_refused(self) -> None:
        run = run_with_push()
        self.assertFalse(
            authorization_covers(
                run,
                "push",
                "M1",
                "branch:refs/heads/codex/add-search",
                required_head_sha="c" * 40,
            )
        )


class MainBranchGuardTests(unittest.TestCase):
    """The one branch rule the harness enforces."""

    def test_push_targeting_main_is_refused(self) -> None:
        run = run_with_push(targets=["branch:refs/heads/main"])
        self.assertFalse(authorization_covers(run, "push", "M1", "branch:refs/heads/main"))

    def test_bare_main_spelling_is_refused_too(self) -> None:
        run = run_with_push(targets=["branch:main"])
        self.assertFalse(authorization_covers(run, "push", "M1", "branch:main"))

    def test_run_whose_integration_branch_is_main_can_never_push(self) -> None:
        run = run_with_push(
            branch="refs/heads/main", targets=["branch:refs/heads/codex/add-search"]
        )
        self.assertFalse(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/add-search"
            )
        )

    def test_a_main_target_anywhere_in_scope_poisons_the_whole_grant(self) -> None:
        run = run_with_push(
            targets=["branch:refs/heads/codex/add-search", "branch:refs/heads/main"]
        )
        self.assertFalse(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/add-search"
            )
        )


class BranchSpellingRegressionTests(unittest.TestCase):
    """`codex/x` and `refs/heads/codex/x` name one branch.

    Comparing the raw strings once made an otherwise valid grant unusable, and
    the only escape was recording a second human instruction.
    """

    def test_bare_target_covers_a_full_ref_request(self) -> None:
        run = run_with_push(targets=["branch:codex/add-search"])
        self.assertTrue(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/add-search"
            )
        )

    def test_full_ref_target_covers_a_bare_request(self) -> None:
        run = run_with_push(targets=["branch:refs/heads/codex/add-search"])
        self.assertTrue(
            authorization_covers(run, "push", "M1", "branch:codex/add-search")
        )

    def test_the_spelling_shortcut_does_not_reach_a_different_branch(self) -> None:
        run = run_with_push(targets=["branch:codex/add-search"])
        self.assertFalse(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/add-search-extra"
            )
        )


class MalformedScopeTests(unittest.TestCase):
    def test_null_active_wave_does_not_crash_a_wave_scoped_grant(self) -> None:
        """The key is present with a null value, which a get() default misses.

        A null wave is not a closed wave, so the grant is still live. What
        matters is that asking the question returns an answer instead of
        raising AttributeError out of the validator.
        """
        run = run_with_push(expires_when="wave_closed")
        run["active_wave"] = None
        self.assertTrue(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/add-search"
            )
        )

    def test_closed_wave_still_expires_a_wave_scoped_grant(self) -> None:
        run = run_with_push(expires_when="wave_closed")
        run["active_wave"] = {"status": "closed"}
        self.assertFalse(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/add-search"
            )
        )

    def test_open_wave_still_covers_a_wave_scoped_grant(self) -> None:
        run = run_with_push(expires_when="wave_closed")
        run["active_wave"] = {"status": "open"}
        self.assertTrue(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/add-search"
            )
        )

    def test_string_targets_cannot_authorize_by_substring(self) -> None:
        run = run_with_push(targets="branch:refs/heads/codex/add-search-and-more")
        self.assertFalse(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/add-search"
            )
        )

    def test_string_mission_ids_cannot_authorize_by_substring(self) -> None:
        run = run_with_push()
        run["authorizations"]["push"]["scope"]["mission_ids"] = "M1-AND-OTHERS"
        self.assertFalse(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/add-search"
            )
        )


if __name__ == "__main__":
    unittest.main()
