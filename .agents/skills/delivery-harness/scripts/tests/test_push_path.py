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

from harness_authorization import (  # noqa: E402
    authorization_covers,
    is_explicit_remote_intent,
)
from harness_core import ManifestError  # noqa: E402
from harness_transition import _require_non_default_integration_branch  # noqa: E402

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
    scope = {
        "run_id": "RUN-1",
        "mission_ids": ["M1"],
        "targets": targets,
        "plan_revision": 1,
        "plan_digest_sha256": DIGEST,
    }
    if expires_when == "wave_closed":
        scope.update({"wave_id": "B01", "batch_base_sha": SHA})
    return {
        "schema_version": 10,
        "run_id": "RUN-1",
        "status": status,
        "closed_waves": [],
        "plan": {"revision": 1, "digest_sha256": DIGEST},
        "observed": {"git": {"default_branch": "refs/heads/main"}},
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
                "scope": scope,
            }
        },
    }


class OrdinaryPushPathTests(unittest.TestCase):
    def test_explicit_remote_intent_covers_the_work_branch_push(self) -> None:
        run = run_with_push()
        self.assertTrue(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/add-search"
            )
        )

    def test_local_execution_intent_does_not_cover_push(self) -> None:
        run = run_with_push()
        run["authorizations"]["push"]["source"] = "user: implement the approved plan"
        self.assertFalse(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/add-search"
            )
        )

    def test_push_requires_the_resolved_integration_branch(self) -> None:
        run = run_with_push(
            targets=["branch:refs/heads/codex/other"]
        )
        self.assertFalse(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/other"
            )
        )

    def test_push_fails_closed_when_default_branch_is_unknown(self) -> None:
        run = run_with_push()
        del run["observed"]
        self.assertFalse(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/add-search"
            )
        )

    def test_push_rejects_an_observed_non_main_default_branch(self) -> None:
        run = run_with_push(
            branch="refs/heads/release",
            targets=["branch:refs/heads/release"],
        )
        run["observed"]["git"]["default_branch"] = "refs/heads/release"
        self.assertFalse(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/release"
            )
        )

    def test_local_action_is_not_blocked_by_unknown_default_branch(self) -> None:
        run = run_with_push()
        del run["observed"]
        run["authorizations"]["create_local_commits"] = {
            "authorized": True,
            "source": "user: implement the approved plan",
            "scope": {
                "run_id": "RUN-1",
                "mission_ids": ["M1"],
                "targets": ["branch:refs/heads/codex/add-search"],
                "plan_revision": 1,
                "plan_digest_sha256": DIGEST,
            },
            "expires_when": "explicit_revocation",
        }
        self.assertTrue(
            authorization_covers(
                run,
                "create_local_commits",
                "M1",
                "branch:refs/heads/codex/add-search",
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

    def test_completed_push_does_not_bypass_current_safety(self) -> None:
        run = run_with_push(status="complete", expires_when="run_complete")
        del run["observed"]
        run["authorizations"]["push"]["source"] = "user: build it"
        self.assertFalse(
            authorization_covers(
                run,
                "push",
                "M1",
                "branch:refs/heads/codex/add-search",
                preserve_completed_run_expiry=True,
            )
        )

    def test_completed_push_preserves_safe_run_complete_evidence(self) -> None:
        run = run_with_push(status="complete", expires_when="run_complete")
        self.assertTrue(
            authorization_covers(
                run,
                "push",
                "M1",
                "branch:refs/heads/codex/add-search",
                preserve_completed_run_expiry=True,
            )
        )

    def test_completed_push_requires_every_current_safety_fact(self) -> None:
        cases = []

        missing_default = run_with_push(status="complete", expires_when="run_complete")
        del missing_default["observed"]
        cases.append(missing_default)

        wrong_target = run_with_push(status="complete", expires_when="run_complete")
        cases.append(wrong_target)
        wrong_target["authorizations"]["push"]["scope"]["targets"] = [
            "branch:refs/heads/codex/other"
        ]

        stale_head = run_with_push(status="complete", expires_when="run_complete")
        stale_head["authorizations"]["push"]["authorized_head_sha"] = "c" * 40
        cases.append(stale_head)

        for run in cases:
            with self.subTest(run=run):
                self.assertFalse(
                    authorization_covers(
                        run,
                        "push",
                        "M1",
                        "branch:refs/heads/codex/add-search",
                        preserve_completed_run_expiry=True,
                    )
                )

    def test_push_intent_parser_rejects_ambiguous_or_forbidden_prose(self) -> None:
        for source in (
            "describe the remote API for branch metadata",
            "push forbidden by repository policy",
            "do not touch remote state",
            "this is not authorizing a push",
            "the push endpoint is available",
            "ship the branch",
            "approval is required before the push",
            "permission is needed to publish",
            "authorization is pending before publishing",
            "publish after permission is granted",
            "the request to publish is pending",
            "I request permission to push the branch",
            "publish when approved",
            "push after the checks pass",
        ):
            with self.subTest(source=source):
                self.assertFalse(is_explicit_remote_intent(source))

    def test_push_intent_parser_accepts_only_explicit_action_attestations(self) -> None:
        for source in (
            "push the verified branch",
            "implement and push the verified branch",
            "please publish the accepted branch",
            "publish the accepted branch",
            "I authorize you to push the branch",
            "I approve the push",
            "I request a publish",
            "approve the push",
            "request a publish",
        ):
            with self.subTest(source=source):
                self.assertTrue(is_explicit_remote_intent(source))

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
    """RUN pushes cannot bypass post-RUN protected-branch promotion."""

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

    def test_push_targeting_development_is_refused_for_current_runs(self) -> None:
        run = run_with_push(
            branch="refs/heads/development",
            targets=["branch:refs/heads/development"],
        )
        self.assertFalse(
            authorization_covers(run, "push", "M1", "branch:refs/heads/development")
        )

    def test_development_target_anywhere_in_scope_poisons_current_grant(self) -> None:
        run = run_with_push(
            targets=["branch:refs/heads/codex/add-search", "branch:development"]
        )
        self.assertFalse(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/add-search"
            )
        )

    def test_transition_rejects_development_as_the_run_integration_branch(self) -> None:
        run = run_with_push(branch="refs/heads/development")
        with self.assertRaisesRegex(ManifestError, "protected promotion branch"):
            _require_non_default_integration_branch(run)

    def test_protected_branch_guards_are_case_insensitive(self) -> None:
        for branch in ("refs/heads/Development", "refs/heads/MAIN"):
            with self.subTest(branch=branch):
                run = run_with_push(branch=branch, targets=[f"branch:{branch}"])
                self.assertFalse(
                    authorization_covers(run, "push", "M1", f"branch:{branch}")
                )
                with self.assertRaisesRegex(ManifestError, "protected promotion branch"):
                    _require_non_default_integration_branch(run)


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

        A null wave has no current identity to which the grant can bind, so
        the grant is refused. What matters is that asking the question returns
        an answer instead of raising AttributeError out of the validator.
        """
        run = run_with_push(expires_when="wave_closed")
        run["active_wave"] = None
        self.assertFalse(
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
        run["active_wave"] = {
            "wave_id": "B01",
            "status": "proposed",
            "batch_base_sha": SHA,
        }
        self.assertTrue(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/add-search"
            )
        )

    def test_wave_grant_does_not_replay_into_a_later_wave(self) -> None:
        run = run_with_push(expires_when="wave_closed")
        run["active_wave"] = {
            "wave_id": "B01",
            "status": "proposed",
            "batch_base_sha": "c" * 40,
        }
        self.assertFalse(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/add-search"
            )
        )
        run["active_wave"].update({"wave_id": "B02", "batch_base_sha": SHA})
        self.assertFalse(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/add-search"
            )
        )

    def test_closed_wave_pair_cannot_be_reopened_or_replayed(self) -> None:
        run = run_with_push(expires_when="wave_closed")
        run["active_wave"] = {
            "wave_id": "B01",
            "status": "proposed",
            "batch_base_sha": SHA,
        }
        self.assertTrue(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/add-search"
            )
        )

        run["closed_waves"].append({"wave_id": "B01", "batch_base_sha": SHA})
        run["active_wave"]["status"] = "closed"
        self.assertFalse(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/add-search"
            )
        )

        # Re-proposing the same pair must not revive the old grant. A fresh
        # base identity is a new wave and needs a renewed scope.
        run["active_wave"]["status"] = "proposed"
        self.assertFalse(
            authorization_covers(
                run, "push", "M1", "branch:refs/heads/codex/add-search"
            )
        )
        run["active_wave"]["batch_base_sha"] = "c" * 40
        run["authorizations"]["push"]["scope"]["batch_base_sha"] = "c" * 40
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
