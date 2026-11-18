"""Landing gate tests: record, revoke, check and cleanup-plan decisions."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import landing_gate as subject  # noqa: E402

AGENTS_EPIC_GRANT = """# Test Repo

## Delivery Autonomy

- Landing: epic_grant
- Required checks: build, test
- Journey command: python -m pytest tests/journey
- Production smoke command: none
- Recovery: revert the landing commit
- Owner-only paths: none

## Unrelated

- Note: ignored
"""

AGENTS_OWNER_EACH_TIME = AGENTS_EPIC_GRANT.replace(
    "- Landing: epic_grant", "- Landing: owner_each_time"
)
AGENTS_NO_SECTION = "# Test Repo\n\nNo policy here.\n"
AGENTS_INTERNAL_OWNED = AGENTS_EPIC_GRANT.replace(
    "- Owner-only paths: none", "- Owner-only paths: docs/internal/"
)
FORBIDDEN_GIT_VERBS = {"clone", "fetch", "pull", "push", "merge", "tag"}
AUTO = object()


def clock(moment: str | None):
    """Fix the gate's clock; the CLI itself offers no override."""

    if moment is None:
        return contextlib.nullcontext()
    fixed = datetime.fromisoformat(moment.replace("Z", "+00:00")).astimezone(timezone.utc)
    return patch.object(subject, "_now", lambda: fixed)


def git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, encoding="utf-8", check=False
    )
    if result.returncode:
        raise AssertionError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout.strip()


def write_file(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


class LandingGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self._temps: list[tempfile.TemporaryDirectory[str]] = []

    def tearDown(self) -> None:
        for item in self._temps:
            item.cleanup()

    def _temp(self, prefix: str) -> Path:
        holder = tempfile.TemporaryDirectory(prefix=prefix)
        self._temps.append(holder)
        return Path(holder.name).resolve()

    def _fixture(self, agents: str = AGENTS_EPIC_GRANT) -> dict[str, object]:
        holder = self._temp("landing-repo-")
        remote = holder / "remote.git"
        subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(remote)], check=True)
        root = holder / "repo"
        root.mkdir()
        git(root, "init", "-q", "-b", "main")
        git(root, "config", "user.email", "test@example.com")
        git(root, "config", "user.name", "Harness Test")
        git(root, "config", "core.autocrlf", "false")
        write_file(root / "AGENTS.md", agents)
        git(root, "add", "AGENTS.md")
        git(root, "commit", "-qm", "base policy")
        base = git(root, "rev-parse", "HEAD")
        git(root, "remote", "add", "origin", str(remote))
        git(root, "checkout", "-qb", "epic-7")
        return {"root": root, "remote": remote, "base": base}

    def _commit(self, root: Path, files: dict[str, str], message: str) -> str:
        for name, text in files.items():
            write_file(root / name, text)
            git(root, "add", name)
        git(root, "commit", "-qm", message)
        return git(root, "rev-parse", "HEAD")

    def _landed(self, agents: str = AGENTS_EPIC_GRANT) -> dict[str, object]:
        fixture = self._fixture(agents)
        fixture["candidate"] = self._commit(
            Path(fixture["root"]), {"src/app.py": "print('landing')\n"}, "feature"
        )
        return fixture

    def _run(self, *argv: str) -> tuple[int, dict]:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = subject.main(list(argv))
        return code, json.loads(stdout.getvalue())

    def _sha256(self, path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _record(
        self,
        fixture: dict[str, object],
        *,
        actions: tuple[str, ...] = ("push",),
        branch: str = "refs/heads/epic-7",
        base: str | None = None,
        expires: str = "2030-01-01T00:00:00Z",
        source: str = "owner approval on 2026-11-18",
        out: Path | None = None,
    ) -> tuple[int, dict, Path]:
        if out is None:
            out = self._temp("landing-grant-") / "grant.json"
        argv = [
            "record",
            "--repo-root", str(fixture["root"]),
            "--out", str(out),
            "--remote", "origin",
            "--epic", "EPIC-7",
            "--branch", branch,
            "--base", base or str(fixture["base"]),
            "--expires", expires,
            "--repair-budget", "1",
            "--source", source,
        ]
        for action in actions:
            argv += ["--action", action]
        code, value = self._run(*argv)
        return code, value, out

    def _check(
        self,
        fixture: dict[str, object],
        grant: Path,
        candidate: str,
        action: str,
        *,
        evidence: object = AUTO,
        now: str | None = None,
        grant_sha: str | None = None,
    ) -> tuple[int, dict]:
        argv = [
            "check",
            "--repo-root", str(fixture["root"]),
            "--grant", str(grant),
            "--grant-sha256", grant_sha or self._sha256(grant),
            "--candidate", candidate,
            "--action", action,
        ]
        if evidence is AUTO:
            needs = action in ("push", "pull_request", "merge", "production_deploy")
            evidence = self._evidence(candidate) if needs else None
        if evidence is not None:
            argv += ["--evidence", str(evidence)]
        with clock(now):
            return self._run(*argv)

    def _cleanup(
        self,
        fixture: dict[str, object],
        grant: Path,
        candidate: str,
        *,
        landing: str = "exact",
        observed_main: str | None = None,
        remote_tip: str | None = None,
        now: str | None = None,
    ) -> tuple[int, dict]:
        readback_path = self._temp("landing-readback-") / "readback.json"
        write_file(
            readback_path,
            json.dumps(
                {
                    "status": "PASS",
                    "landing": landing,
                    "candidate": candidate,
                    "observed_main": observed_main or candidate,
                }
            ),
        )
        argv = [
            "cleanup-plan",
            "--repo-root", str(fixture["root"]),
            "--grant", str(grant),
            "--grant-sha256", self._sha256(grant),
            "--readback", str(readback_path),
        ]
        if remote_tip is not None:
            argv += ["--remote-tip", remote_tip]
        with clock(now):
            return self._run(*argv)

    def _evidence(
        self,
        candidate: str,
        *,
        checks_sha: str | None = None,
        results: dict[str, str] | None = None,
        review_sha: str | None = None,
        verdict: str = "PASS",
        acceptance_status: str = "pass",
        acceptance_sha: str | None = None,
        readback: dict | None = None,
        repair_rounds: object = 0,
    ) -> Path:
        value: dict = {
            "repair_rounds": repair_rounds,
            "checks": {
                "sha": checks_sha or candidate,
                "results": results if results is not None else {"build": "pass", "test": "pass"},
            },
            "review": {"sha": review_sha or candidate, "verdict": verdict},
            "acceptance": {
                "sha": acceptance_sha or candidate,
                "status": acceptance_status,
            },
        }
        if readback is not None:
            value["readback"] = readback
        path = self._temp("landing-evidence-") / "evidence.json"
        write_file(path, json.dumps(value))
        return path

    # record

    def test_record_success_and_hash(self) -> None:
        fixture = self._landed()
        code, value, grant_path = self._record(fixture, actions=("merge", "push"))
        self.assertEqual(0, code, value)
        self.assertEqual("recorded", value["status"])
        self.assertIn(subject.AUTHORITY_NOTE, value["authority"])
        data = grant_path.read_bytes()
        self.assertTrue(data.endswith(b"\n"))
        self.assertEqual(hashlib.sha256(data).hexdigest(), value["grant_sha256"])
        grant = json.loads(data)
        self.assertEqual("landing-grant/1", grant["schema"])
        self.assertEqual("refs/heads/main", grant["target"])
        self.assertEqual(["merge", "push"], grant["actions"])
        self.assertEqual(fixture["base"], grant["base"])
        self.assertEqual("refs/heads/epic-7", grant["branch"])
        self.assertEqual("2030-01-01T00:00:00Z", grant["expires"])
        self.assertEqual(1, grant["repair_budget"])
        self.assertEqual("owner approval on 2026-11-18", grant["source"])
        root = Path(fixture["root"])
        self.assertEqual(
            git(root, "remote", "get-url", "--push", "--all", "origin"), grant["repository"]
        )
        self.assertIn('"actions"', data.decode("utf-8").splitlines()[1])

    def test_record_refuses_out_inside_checkout(self) -> None:
        fixture = self._landed()
        inside = Path(fixture["root"]) / "grant.json"
        code, value, _grant = self._record(fixture, out=inside)
        self.assertEqual(1, code, value)
        self.assertEqual("REFUSED", value["status"])
        self.assertTrue(any("outside --repo-root" in reason for reason in value["reasons"]))
        self.assertFalse(inside.exists())

    def test_record_refuses_existing_out(self) -> None:
        fixture = self._landed()
        code, value, grant = self._record(fixture)
        self.assertEqual(0, code, value)
        code, value, _again = self._record(fixture, out=grant)
        self.assertEqual(1, code, value)
        self.assertEqual("REFUSED", value["status"])
        self.assertTrue(any("already exists" in reason for reason in value["reasons"]))
        self.assertEqual("landing-grant/1", json.loads(grant.read_text(encoding="utf-8"))["schema"])

    def test_record_refuses_protected_branch(self) -> None:
        fixture = self._landed()
        for branch in ("refs/heads/main", "refs/heads/development"):
            code, value, _grant = self._record(fixture, branch=branch)
            self.assertEqual(1, code, value)
            self.assertTrue(any("protected" in reason for reason in value["reasons"]), branch)

    def test_record_refuses_branch_that_is_not_a_full_ref(self) -> None:
        fixture = self._landed()
        code, value, _grant = self._record(fixture, branch="epic-7")
        self.assertEqual(1, code, value)
        self.assertTrue(any("not a full refs/heads/" in reason for reason in value["reasons"]))

    def test_record_refuses_past_expiry(self) -> None:
        fixture = self._landed()
        code, value, _grant = self._record(fixture, expires="2020-01-01T00:00:00Z")
        self.assertEqual(1, code, value)
        self.assertTrue(any("not in the future" in reason for reason in value["reasons"]))

    def test_record_refuses_unknown_action(self) -> None:
        fixture = self._landed()
        code, value, _grant = self._record(fixture, actions=("push", "deploy"))
        self.assertEqual(1, code, value)
        self.assertTrue(any("unknown actions: deploy" in reason for reason in value["reasons"]))

    def test_record_refuses_base_not_a_commit(self) -> None:
        fixture = self._landed()
        code, value, _grant = self._record(fixture, base="0" * 40)
        self.assertEqual(1, code, value)
        self.assertTrue(any("is not a commit" in reason for reason in value["reasons"]))

    def test_record_refuses_empty_source(self) -> None:
        fixture = self._landed()
        code, value, _grant = self._record(fixture, source="   ")
        self.assertEqual(1, code, value)
        self.assertTrue(any("--source" in reason for reason in value["reasons"]))

    def test_record_refuses_credentials_in_push_url(self) -> None:
        fixture = self._landed()
        root = Path(fixture["root"])
        git(root, "remote", "set-url", "origin", "https://user:secret@example.com/repo.git")
        code, value, _grant = self._record(fixture)
        self.assertEqual(1, code, value)
        self.assertTrue(any("credentials" in reason for reason in value["reasons"]))

    def test_record_accepts_a_passwordless_ssh_remote(self) -> None:
        # git@host:owner/repo.git names a user, not a credential; most
        # repositories that push over ssh use exactly this form.
        for url in ("git@example.com:owner/repo.git", "ssh://git@example.com/owner/repo.git"):
            with self.subTest(url=url):
                fixture = self._landed()
                root = Path(fixture["root"])
                git(root, "remote", "set-url", "origin", url)
                code, value, _grant = self._record(fixture)
                self.assertEqual(0, code, value)

    def test_record_refuses_an_http_user_without_a_password(self) -> None:
        fixture = self._landed()
        root = Path(fixture["root"])
        git(root, "remote", "set-url", "origin", "https://user@example.com/repo.git")
        code, value, _grant = self._record(fixture)
        self.assertEqual(1, code, value)
        self.assertTrue(any("credentials" in reason for reason in value["reasons"]))

    # check passes

    def test_check_passes_for_push(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture)
        self.assertEqual(0, code)
        code, value = self._check(fixture, grant, candidate, "push")
        self.assertEqual(0, code, value)
        self.assertEqual("PASS", value["status"])
        self.assertEqual([], value["reasons"])
        self.assertEqual("push", value["action"])
        self.assertEqual(candidate, value["candidate"])
        self.assertEqual(fixture["base"], value["policy_base"])
        self.assertEqual(self._sha256(grant), value["grant_sha256"])

    def test_check_passes_for_merge_with_full_evidence(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture, actions=("merge",))
        self.assertEqual(0, code)
        evidence = self._evidence(candidate)
        code, value = self._check(fixture, grant, candidate, "merge", evidence=evidence)
        self.assertEqual(0, code, value)
        self.assertEqual("PASS", value["status"])
        self.assertEqual([], value["reasons"])

    def test_check_passes_for_production_deploy_with_exact_readback(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture, actions=("production_deploy",))
        self.assertEqual(0, code)
        evidence = self._evidence(
            candidate,
            readback={
                "status": "PASS",
                "landing": "exact",
                "candidate": candidate,
                "observed_main": candidate,
            },
        )
        code, value = self._check(fixture, grant, candidate, "production_deploy", evidence=evidence)
        self.assertEqual(0, code, value)
        self.assertEqual("PASS", value["status"])

    def test_check_passes_review_on_ancestor_when_only_the_epic_record_changed(self) -> None:
        fixture = self._fixture()
        root = Path(fixture["root"])
        reviewed = self._commit(root, {"src/app.py": "print('landing')\n"}, "code")
        candidate = self._commit(
            root, {"docs/epics/EPIC-7.md": "# Epic\n", "docs/DOCUMENTS.md": "# Documents\n"}, "record"
        )
        code, _value, grant = self._record(fixture, actions=("merge",))
        self.assertEqual(0, code)
        evidence = self._evidence(candidate, review_sha=reviewed)
        code, value = self._check(fixture, grant, candidate, "merge", evidence=evidence)
        self.assertEqual(0, code, value)
        self.assertEqual("PASS", value["status"])

    # check refusals

    def test_check_refuses_hash_mismatch(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture)
        self.assertEqual(0, code)
        code, value = self._check(fixture, grant, candidate, "push", grant_sha="0" * 64)
        self.assertEqual(1, code, value)
        self.assertEqual("REFUSED", value["status"])
        self.assertEqual(1, len(value["reasons"]))
        self.assertIn("--grant-sha256", value["reasons"][0])

    def test_check_refuses_revoked(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture)
        self.assertEqual(0, code)
        write_file(grant.with_name(grant.name + ".revoked"), "{}\n")
        code, value = self._check(fixture, grant, candidate, "push")
        self.assertEqual(1, code, value)
        self.assertEqual(["the grant is revoked"], value["reasons"])

    def test_check_refuses_expired_via_now(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture)
        self.assertEqual(0, code)
        code, value = self._check(fixture, grant, candidate, "push", now="2031-01-01T00:00:00Z")
        self.assertEqual(1, code, value)
        self.assertEqual(1, len(value["reasons"]))
        self.assertIn("expired", value["reasons"][0])

    def test_check_refuses_action_not_granted(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture, actions=("push",))
        self.assertEqual(0, code)
        code, value = self._check(fixture, grant, candidate, "pull_request")
        self.assertEqual(1, code, value)
        self.assertEqual(1, len(value["reasons"]))
        self.assertIn("does not cover action", value["reasons"][0])

    def test_check_points_cleanup_at_cleanup_plan(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture, actions=("cleanup",))
        self.assertEqual(0, code)
        code, value = self._check(fixture, grant, candidate, "cleanup")
        self.assertEqual(1, code, value)
        self.assertTrue(any("cleanup-plan" in reason for reason in value["reasons"]))

    def test_check_refuses_grant_inside_checkout(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, outside = self._record(fixture)
        self.assertEqual(0, code)
        inside = Path(fixture["root"]) / "grant.json"
        inside.write_bytes(outside.read_bytes())
        code, value = self._check(fixture, inside, candidate, "push")
        self.assertEqual(1, code, value)
        self.assertTrue(any("inside the repository checkout" in reason for reason in value["reasons"]))

    def test_check_refuses_wrong_repository(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture)
        self.assertEqual(0, code)
        other = self._temp("landing-other-") / "other.git"
        git(Path(fixture["root"]), "remote", "set-url", "origin", str(other))
        code, value = self._check(fixture, grant, candidate, "push")
        self.assertEqual(1, code, value)
        self.assertEqual(1, len(value["reasons"]))
        self.assertIn("differs from the grant repository", value["reasons"][0])

    def test_check_refuses_stale_head(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture)
        self.assertEqual(0, code)
        moved = self._commit(Path(fixture["root"]), {"src/more.py": "more\n"}, "moved on")
        self.assertNotEqual(candidate, moved)
        code, value = self._check(fixture, grant, candidate, "push")
        self.assertEqual(1, code, value)
        self.assertEqual(1, len(value["reasons"]))
        self.assertIn("local tip", value["reasons"][0])

    def test_check_refuses_base_not_ancestor(self) -> None:
        fixture = self._fixture()
        root = Path(fixture["root"])
        git(root, "checkout", "-qb", "side")
        side = self._commit(root, {"docs/side.txt": "side\n"}, "side work")
        git(root, "checkout", "-q", "epic-7")
        candidate = self._commit(root, {"src/app.py": "print('landing')\n"}, "feature")
        code, _value, grant = self._record(fixture, base=side)
        self.assertEqual(0, code)
        code, value = self._check(fixture, grant, candidate, "push")
        self.assertEqual(1, code, value)
        self.assertTrue(any("is not an ancestor" in reason for reason in value["reasons"]))

    def test_check_refuses_landing_owner_each_time(self) -> None:
        fixture = self._landed(AGENTS_OWNER_EACH_TIME)
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture)
        self.assertEqual(0, code)
        code, value = self._check(fixture, grant, candidate, "push")
        self.assertEqual(1, code, value)
        self.assertIn("does not say `Landing: epic_grant`", value["reasons"][0])

    def test_check_refuses_missing_delivery_autonomy_section(self) -> None:
        fixture = self._landed(AGENTS_NO_SECTION)
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture)
        self.assertEqual(0, code)
        code, value = self._check(fixture, grant, candidate, "push")
        self.assertEqual(1, code, value)
        self.assertTrue(any("not eligible" in reason for reason in value["reasons"]))

    def test_check_reads_policy_at_the_base_not_the_candidate(self) -> None:
        fixture = self._landed(AGENTS_OWNER_EACH_TIME)
        root = Path(fixture["root"])
        agents = (root / "AGENTS.md").read_text(encoding="utf-8")
        write_file(root / "AGENTS.md", agents.replace("owner_each_time", "epic_grant"))
        git(root, "add", "AGENTS.md")
        git(root, "commit", "-qm", "flip policy on the candidate only")
        candidate = git(root, "rev-parse", "HEAD")
        code, _value, grant = self._record(fixture, base=str(fixture["base"]))
        self.assertEqual(0, code)
        code, value = self._check(fixture, grant, candidate, "push")
        self.assertEqual(1, code, value)
        self.assertTrue(any("not eligible" in reason for reason in value["reasons"]))

    def test_check_refuses_candidate_editing_agents_md(self) -> None:
        fixture = self._fixture()
        root = Path(fixture["root"])
        agents = (root / "AGENTS.md").read_text(encoding="utf-8")
        candidate = self._commit(
            root, {"AGENTS.md": agents + "- Extra: line\n", "src/app.py": "print('landing')\n"}, "touch owners"
        )
        code, _value, grant = self._record(fixture)
        self.assertEqual(0, code)
        code, value = self._check(fixture, grant, candidate, "push")
        self.assertEqual(1, code, value)
        matching = [reason for reason in value["reasons"] if "owner-only paths changed" in reason]
        self.assertEqual(1, len(matching))
        self.assertIn("AGENTS.md", matching[0])

    def test_check_refuses_candidate_editing_workflow_yaml(self) -> None:
        fixture = self._landed()
        root = Path(fixture["root"])
        candidate = self._commit(
            root, {".github/workflows/ci.yml": "name: ci\n"}, "add workflow"
        )
        code, _value, grant = self._record(fixture)
        self.assertEqual(0, code)
        code, value = self._check(fixture, grant, candidate, "push")
        self.assertEqual(1, code, value)
        matching = [reason for reason in value["reasons"] if "owner-only paths changed" in reason]
        self.assertEqual(1, len(matching))
        self.assertIn(".github/workflows/ci.yml", matching[0])

    def test_check_refuses_an_owner_only_file_renamed_away(self) -> None:
        # With rename detection a moved file shows only its new name, which
        # would hide that AGENTS.md left its place.
        fixture = self._fixture()
        root = Path(fixture["root"])
        git(root, "mv", "AGENTS.md", "notes.md")
        git(root, "commit", "-qm", "move the policy file")
        candidate = git(root, "rev-parse", "HEAD")
        code, _value, grant = self._record(fixture)
        self.assertEqual(0, code)
        code, value = self._check(fixture, grant, candidate, "push")
        self.assertEqual(1, code, value)
        matching = [reason for reason in value["reasons"] if "owner-only paths changed" in reason]
        self.assertEqual(1, len(matching))
        self.assertIn("AGENTS.md", matching[0])

    def test_check_refuses_merge_without_an_evidence_file(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture, actions=("merge", "push", "pull_request"))
        self.assertEqual(0, code)
        for action in ("merge", "push", "pull_request"):
            code, value = self._check(fixture, grant, candidate, action, evidence=None)
            self.assertEqual(1, code, value)
            self.assertTrue(
                any("requires the parent-observed evidence file" in reason for reason in value["reasons"]), action
            )

    def test_check_refuses_review_on_ancestor_with_rule_text_change_since(self) -> None:
        # A Markdown file outside docs/ can be a rule or a skill; a review
        # PASS does not carry across it.
        fixture = self._fixture()
        root = Path(fixture["root"])
        reviewed = self._commit(root, {"src/app.py": "print('landing')\n"}, "code")
        candidate = self._commit(root, {"skills/rules/SKILL.md": "# Rule\n"}, "rule text")
        code, _value, grant = self._record(fixture, actions=("merge",))
        self.assertEqual(0, code)
        evidence = self._evidence(candidate, review_sha=reviewed)
        code, value = self._check(fixture, grant, candidate, "merge", evidence=evidence)
        self.assertEqual(1, code, value)
        matching = [reason for reason in value["reasons"] if "after the reviewed SHA" in reason]
        self.assertEqual(1, len(matching))
        self.assertIn("skills/rules/SKILL.md", matching[0])

    def test_check_refuses_owner_only_directory_pattern(self) -> None:
        fixture = self._landed(AGENTS_INTERNAL_OWNED)
        root = Path(fixture["root"])
        candidate = self._commit(
            root, {"docs/internal/notes.md": "internal\n"}, "internal note"
        )
        code, _value, grant = self._record(fixture)
        self.assertEqual(0, code)
        code, value = self._check(fixture, grant, candidate, "push")
        self.assertEqual(1, code, value)
        matching = [reason for reason in value["reasons"] if "owner-only paths changed" in reason]
        self.assertEqual(1, len(matching))
        self.assertIn("docs/internal/notes.md", matching[0])

    def test_check_refuses_required_check_missing(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture, actions=("merge",))
        self.assertEqual(0, code)
        evidence = self._evidence(candidate, results={"build": "pass"})
        code, value = self._check(fixture, grant, candidate, "merge", evidence=evidence)
        self.assertEqual(1, code, value)
        self.assertTrue(any("required checks absent" in reason for reason in value["reasons"]))

    def test_check_refuses_required_check_failed(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture, actions=("merge",))
        self.assertEqual(0, code)
        evidence = self._evidence(candidate, results={"build": "pass", "test": "fail"})
        code, value = self._check(fixture, grant, candidate, "merge", evidence=evidence)
        self.assertEqual(1, code, value)
        self.assertTrue(any("test" in reason for reason in value["reasons"] if "required checks" in reason))

    def test_check_refuses_checks_for_another_sha(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture, actions=("merge",))
        self.assertEqual(0, code)
        evidence = self._evidence(candidate, checks_sha=str(fixture["base"]))
        code, value = self._check(fixture, grant, candidate, "merge", evidence=evidence)
        self.assertEqual(1, code, value)
        self.assertTrue(any("checks.sha" in reason for reason in value["reasons"]))

    def test_check_refuses_review_fix_required(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture, actions=("merge",))
        self.assertEqual(0, code)
        evidence = self._evidence(candidate, verdict="FIX_REQUIRED")
        code, value = self._check(fixture, grant, candidate, "merge", evidence=evidence)
        self.assertEqual(1, code, value)
        self.assertTrue(any("review.verdict" in reason for reason in value["reasons"]))

    def test_check_refuses_review_on_ancestor_with_code_change_since(self) -> None:
        fixture = self._fixture()
        root = Path(fixture["root"])
        reviewed = self._commit(root, {"src/app.py": "print('landing')\n"}, "code")
        candidate = self._commit(root, {"src/extra.py": "extra = 1\n"}, "more code")
        code, _value, grant = self._record(fixture, actions=("merge",))
        self.assertEqual(0, code)
        evidence = self._evidence(candidate, review_sha=reviewed)
        code, value = self._check(fixture, grant, candidate, "merge", evidence=evidence)
        self.assertEqual(1, code, value)
        matching = [reason for reason in value["reasons"] if "after the reviewed SHA" in reason]
        self.assertEqual(1, len(matching))
        self.assertIn("src/extra.py", matching[0])

    def test_check_refuses_acceptance_failed(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture, actions=("merge",))
        self.assertEqual(0, code)
        evidence = self._evidence(candidate, acceptance_status="fail")
        code, value = self._check(fixture, grant, candidate, "merge", evidence=evidence)
        self.assertEqual(1, code, value)
        self.assertTrue(any("acceptance.status" in reason for reason in value["reasons"]))
        evidence = self._evidence(candidate, acceptance_sha=str(fixture["base"]))
        code, value = self._check(fixture, grant, candidate, "merge", evidence=evidence)
        self.assertEqual(1, code, value)
        self.assertTrue(any("acceptance.sha" in reason for reason in value["reasons"]))

    def test_check_refuses_production_deploy_without_passing_readback(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture, actions=("production_deploy",))
        self.assertEqual(0, code)
        evidence = self._evidence(
            candidate,
            readback={"status": "BLOCKED", "landing": "unknown", "candidate": candidate},
        )
        code, value = self._check(fixture, grant, candidate, "production_deploy", evidence=evidence)
        self.assertEqual(1, code, value)
        self.assertTrue(any("promotion read-back" in reason for reason in value["reasons"]))
        evidence = self._evidence(candidate)
        code, value = self._check(fixture, grant, candidate, "production_deploy", evidence=evidence)
        self.assertEqual(1, code, value)
        self.assertTrue(any("promotion read-back" in reason for reason in value["reasons"]))
        # A read-back that names no observed main proves no landing.
        evidence = self._evidence(
            candidate, readback={"status": "PASS", "landing": "exact", "candidate": candidate}
        )
        code, value = self._check(fixture, grant, candidate, "production_deploy", evidence=evidence)
        self.assertEqual(1, code, value)
        self.assertTrue(any("observed_main is not a full" in reason for reason in value["reasons"]))

    def test_check_refuses_publishing_a_candidate_without_a_passing_review(self) -> None:
        # Review comes before push: a grant changes who names the SHA, not
        # the order of the review boundary.
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture, actions=("push", "pull_request"))
        self.assertEqual(0, code)
        evidence = self._evidence(candidate, verdict="FIX_REQUIRED")
        for action in ("push", "pull_request"):
            code, value = self._check(fixture, grant, candidate, action, evidence=evidence)
            self.assertEqual(1, code, value)
            self.assertTrue(any("review.verdict" in reason for reason in value["reasons"]), action)

    def test_check_needs_no_checks_or_acceptance_to_publish(self) -> None:
        # CI runs on the pushed branch, so checks cannot exist before push.
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture, actions=("push",))
        self.assertEqual(0, code)
        evidence = self._temp("landing-evidence-") / "review-only.json"
        write_file(evidence, json.dumps({"repair_rounds": 0, "review": {"sha": candidate, "verdict": "PASS"}}))
        code, value = self._check(fixture, grant, candidate, "push", evidence=evidence)
        self.assertEqual(0, code, value)
        code, value = self._check(fixture, grant, candidate, "review_threads", evidence=None)
        self.assertEqual(1, code, value)  # not granted here, and it needs no evidence
        self.assertEqual(1, len(value["reasons"]))

    def test_check_enforces_the_repair_budget(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture, actions=("merge", "push"))
        self.assertEqual(0, code)  # the helper records a budget of 1
        for action in ("merge", "push"):
            within = self._evidence(candidate, repair_rounds=1)
            self.assertEqual(0, self._check(fixture, grant, candidate, action, evidence=within)[0], action)
            code, value = self._check(
                fixture, grant, candidate, action, evidence=self._evidence(candidate, repair_rounds=2)
            )
            self.assertEqual(1, code, value)
            self.assertTrue(any("exceed the grant's repair budget 1" in reason for reason in value["reasons"]))
            for bad in (None, "0", True, -1):
                code, value = self._check(
                    fixture, grant, candidate, action, evidence=self._evidence(candidate, repair_rounds=bad)
                )
                self.assertEqual(1, code, (bad, value))
                self.assertTrue(any("repair_rounds must be an integer" in reason for reason in value["reasons"]))

    def test_bad_arguments_exit_2(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture)
        self.assertEqual(0, code)
        code, value = self._check(fixture, grant, candidate, "push", grant_sha="zz")
        self.assertEqual(2, code, value)
        self.assertEqual("ERROR", value["status"])
        with self.assertRaises(SystemExit) as caught:
            subject.main(
                [
                    "record", "--repo-root", str(fixture["root"]), "--out", "x.json",
                    "--remote", "origin", "--epic", "EPIC-7", "--branch", "refs/heads/epic-7",
                    "--base", str(fixture["base"]), "--action", "push",
                    "--expires", "2030-01-01T00:00:00Z", "--repair-budget", "-1",
                    "--source", "owner",
                ]
            )
        self.assertEqual(2, caught.exception.code)
        code, value = self._cleanup(fixture, grant, candidate, remote_tip="abc")
        self.assertEqual(2, code, value)

    # cleanup-plan

    def test_cleanup_plan_for_merged_branch_with_clean_worktree(self) -> None:
        fixture = self._landed()
        root = Path(fixture["root"])
        candidate = str(fixture["candidate"])
        git(root, "checkout", "-q", "main")
        worktree_path = self._temp("landing-wt-") / "wt"
        git(root, "worktree", "add", str(worktree_path), "epic-7")
        code, _value, grant = self._record(fixture, actions=("push", "merge", "cleanup"))
        self.assertEqual(0, code)
        code, value = self._cleanup(fixture, grant, candidate)
        self.assertEqual(0, code, value)
        self.assertEqual("PASS", value["status"])
        self.assertEqual([], value["refused"])
        self.assertEqual([], value["reasons"])
        self.assertEqual(
            [["git", "worktree", "remove", str(worktree_path)], ["git", "branch", "-d", "epic-7"]],
            value["commands"],
        )

    def test_cleanup_plan_refuses_dirty_worktree(self) -> None:
        fixture = self._landed()
        root = Path(fixture["root"])
        candidate = str(fixture["candidate"])
        git(root, "checkout", "-q", "main")
        worktree_path = self._temp("landing-wt-") / "wt"
        git(root, "worktree", "add", str(worktree_path), "epic-7")
        write_file(worktree_path / "scratch.txt", "dirty\n")
        code, _value, grant = self._record(fixture, actions=("cleanup",))
        self.assertEqual(0, code)
        code, value = self._cleanup(fixture, grant, candidate)
        self.assertEqual(1, code, value)
        self.assertEqual("REFUSED", value["status"])
        # All or nothing: one refused target leaves no command to run.
        self.assertEqual([], value["commands"])
        self.assertEqual(1, len(value["refused"]))
        self.assertEqual(str(worktree_path), value["refused"][0]["target"])

    def test_cleanup_plan_refuses_branch_moved_after_landing(self) -> None:
        fixture = self._landed()
        root = Path(fixture["root"])
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture, actions=("cleanup",))
        self.assertEqual(0, code)
        moved = self._commit(root, {"src/late.py": "late\n"}, "late change")
        self.assertNotEqual(candidate, moved)
        code, value = self._cleanup(fixture, grant, candidate)
        self.assertEqual(1, code, value)
        self.assertTrue(any("moved after landing" in reason for reason in value["reasons"]))
        self.assertEqual([], value["commands"])

    def test_cleanup_plan_refuses_primary_checkout(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture, actions=("cleanup",))
        self.assertEqual(0, code)
        code, value = self._cleanup(fixture, grant, candidate)
        self.assertEqual(1, code, value)
        self.assertEqual("REFUSED", value["status"])
        self.assertEqual([], value["commands"])
        self.assertEqual(1, len(value["refused"]))
        self.assertEqual("refs/heads/epic-7", value["refused"][0]["target"])
        self.assertIn("primary checkout", value["refused"][0]["reason"])

    def test_cleanup_plan_tree_equal_uses_capital_d_with_note(self) -> None:
        fixture = self._landed()
        root = Path(fixture["root"])
        candidate = str(fixture["candidate"])
        git(root, "checkout", "-q", "main")
        server = git(
            root, "commit-tree", f"{candidate}^{{tree}}", "-p", str(fixture["base"]), "-m", "server merge"
        )
        code, _value, grant = self._record(fixture, actions=("cleanup",))
        self.assertEqual(0, code)
        code, value = self._cleanup(
            fixture, grant, candidate, landing="tree_equal_S", observed_main=server
        )
        self.assertEqual(0, code, value)
        self.assertEqual("PASS", value["status"])
        self.assertEqual([["git", "branch", "-D", "epic-7"]], value["commands"])
        self.assertEqual(1, len(value["notes"]))
        self.assertIn("tree equality", value["notes"][0])

    def test_cleanup_plan_remote_tip_equal_plans_push(self) -> None:
        fixture = self._landed()
        root = Path(fixture["root"])
        candidate = str(fixture["candidate"])
        git(root, "checkout", "-q", "main")
        code, _value, grant = self._record(fixture, actions=("cleanup",))
        self.assertEqual(0, code)
        code, value = self._cleanup(fixture, grant, candidate, remote_tip=candidate)
        self.assertEqual(0, code, value)
        self.assertEqual(
            [["git", "branch", "-d", "epic-7"], ["git", "push", "origin", "--delete", "epic-7"]],
            value["commands"],
        )

    def test_cleanup_plan_remote_tip_different_refuses(self) -> None:
        fixture = self._landed()
        root = Path(fixture["root"])
        candidate = str(fixture["candidate"])
        git(root, "checkout", "-q", "main")
        code, _value, grant = self._record(fixture, actions=("cleanup",))
        self.assertEqual(0, code)
        code, value = self._cleanup(fixture, grant, candidate, remote_tip=str(fixture["base"]))
        self.assertEqual(1, code, value)
        self.assertEqual("REFUSED", value["status"])
        self.assertEqual([], value["commands"])
        self.assertEqual(1, len(value["refused"]))
        self.assertIn("remote tip", value["refused"][0]["reason"])

    def test_cleanup_plan_refuses_cleanup_not_granted(self) -> None:
        fixture = self._landed()
        root = Path(fixture["root"])
        candidate = str(fixture["candidate"])
        git(root, "checkout", "-q", "main")
        code, _value, grant = self._record(fixture, actions=("push",))
        self.assertEqual(0, code)
        code, value = self._cleanup(fixture, grant, candidate)
        self.assertEqual(1, code, value)
        self.assertTrue(any("does not cover cleanup" in reason for reason in value["reasons"]))

    def test_cleanup_plan_never_plans_force(self) -> None:
        fixture = self._landed()
        root = Path(fixture["root"])
        candidate = str(fixture["candidate"])
        git(root, "checkout", "-q", "main")
        worktree_path = self._temp("landing-wt-") / "wt"
        git(root, "worktree", "add", str(worktree_path), "epic-7")
        code, _value, grant = self._record(fixture, actions=("cleanup",))
        self.assertEqual(0, code)
        commands: list[list[str]] = []
        for remote_tip in (None, candidate):
            code, value = self._cleanup(fixture, grant, candidate, remote_tip=remote_tip)
            self.assertEqual(0, code, value)
            commands.extend(value["commands"])
        self.assertTrue(commands)
        for command in commands:
            for token in command:
                self.assertNotIn(token, ("--force", "-f"), command)

    # revoke

    def test_revoke_writes_marker_and_keeps_grant_bytes(self) -> None:
        fixture = self._landed()
        code, _value, grant = self._record(fixture)
        self.assertEqual(0, code)
        before = grant.read_bytes()
        code, value = self._run("revoke", "--grant", str(grant), "--source", "owner on 2026-11-18")
        self.assertEqual(0, code, value)
        self.assertEqual("revoked", value["status"])
        self.assertFalse(value["already_revoked"])
        marker = grant.with_name(grant.name + ".revoked")
        self.assertTrue(marker.is_file())
        payload = json.loads(marker.read_text(encoding="utf-8"))
        self.assertEqual("owner on 2026-11-18", payload["source"])
        self.assertRegex(payload["revoked_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")
        self.assertEqual(before, grant.read_bytes())
        marker_bytes = marker.read_bytes()
        code, value = self._run("revoke", "--grant", str(grant), "--source", "owner again")
        self.assertEqual(0, code, value)
        self.assertTrue(value["already_revoked"])
        self.assertEqual(marker_bytes, marker.read_bytes())
        self.assertEqual(before, grant.read_bytes())

    def test_revoke_refuses_missing_grant(self) -> None:
        missing = self._temp("landing-grant-") / "absent.json"
        code, value = self._run("revoke", "--grant", str(missing), "--source", "owner")
        self.assertEqual(1, code, value)
        self.assertEqual("REFUSED", value["status"])
        self.assertFalse(missing.with_name(missing.name + ".revoked").exists())

    # read-only guarantees

    def test_git_argv_stays_read_only(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])

        def verb(argv: tuple[object, ...]) -> str | None:
            for token in argv[1:]:
                if isinstance(token, str) and not token.startswith("-"):
                    return token
            return None

        with patch("subprocess.run", wraps=subprocess.run) as spy:
            code, _value, grant = self._record(fixture)
            self.assertEqual(0, code)
            code, value = self._check(fixture, grant, candidate, "push")
            self.assertEqual(0, code, value)
        verbs = [verb(call.args[0]) for call in spy.call_args_list]
        self.assertNotIn(None, verbs)
        self.assertEqual([], [item for item in verbs if item in FORBIDDEN_GIT_VERBS])

    # review findings on 70c87857

    def _handmade_grant(self, fixture: dict[str, object], **overrides: object) -> Path:
        code, _value, grant = self._record(fixture, actions=("cleanup", "merge", "push"))
        self.assertEqual(0, code)
        data = json.loads(grant.read_text(encoding="utf-8"))
        for key, value in overrides.items():
            if value is None:
                data.pop(key, None)
            else:
                data[key] = value
        forged = self._temp("landing-grant-") / "forged.json"
        write_file(forged, json.dumps(data, sort_keys=True, indent=2) + "\n")
        return forged

    def test_case_variants_of_a_protected_branch_are_protected(self) -> None:
        # On Windows refs/heads/Main is the same ref as refs/heads/main.
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        for branch in ("refs/heads/Main", "refs/heads/MAIN", "refs/heads/Development"):
            code, value, _grant = self._record(fixture, branch=branch)
            self.assertEqual(1, code, value)
            self.assertTrue(any("protected" in reason for reason in value["reasons"]), branch)
            forged = self._handmade_grant(fixture, branch=branch)
            code, value = self._check(fixture, forged, candidate, "push")
            self.assertEqual(1, code, value)
            self.assertEqual(["the grant file names no valid unprotected refs/heads/ branch"], value["reasons"])
            code, value = self._cleanup(fixture, forged, candidate)
            self.assertEqual(1, code, value)
            self.assertEqual([], value["commands"])

    def test_a_grant_without_its_identity_fields_is_refused(self) -> None:
        # A missing repository must not compare equal to an unreadable remote.
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        for missing in ("repository", "remote", "epic", "source", "base", "actions", "expires", "repair_budget"):
            forged = self._handmade_grant(fixture, **{missing: None})
            code, value = self._check(fixture, forged, candidate, "merge")
            self.assertEqual(1, code, (missing, value))
            self.assertEqual(1, len(value["reasons"]), missing)

    def test_cleanup_plan_is_bound_to_the_granted_repository(self) -> None:
        fixture = self._landed()
        root = Path(fixture["root"])
        candidate = str(fixture["candidate"])
        git(root, "checkout", "-q", "main")
        code, _value, grant = self._record(fixture, actions=("cleanup",))
        self.assertEqual(0, code)
        other = self._temp("landing-other-") / "other.git"
        subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(other)], check=True)
        git(root, "remote", "set-url", "origin", str(other))
        code, value = self._cleanup(fixture, grant, candidate, remote_tip=candidate)
        self.assertEqual(1, code, value)
        self.assertEqual([], value["commands"])
        self.assertTrue(any("differs from the grant repository" in reason for reason in value["reasons"]))

    def test_cleanup_plan_refuses_a_grant_inside_the_checkout(self) -> None:
        fixture = self._landed()
        root = Path(fixture["root"])
        candidate = str(fixture["candidate"])
        git(root, "checkout", "-q", "main")
        code, _value, grant = self._record(fixture, actions=("cleanup",))
        self.assertEqual(0, code)
        inside = root / "grant.json"
        inside.write_bytes(grant.read_bytes())
        code, value = self._cleanup(fixture, inside, candidate)
        self.assertEqual(1, code, value)
        self.assertEqual([], value["commands"])
        self.assertTrue(any("inside the repository checkout" in reason for reason in value["reasons"]))

    def test_cleanup_plan_refuses_a_policy_that_is_no_longer_eligible(self) -> None:
        fixture = self._landed(AGENTS_OWNER_EACH_TIME)
        root = Path(fixture["root"])
        candidate = str(fixture["candidate"])
        git(root, "checkout", "-q", "main")
        code, _value, grant = self._record(fixture, actions=("cleanup",))
        self.assertEqual(0, code)
        code, value = self._cleanup(fixture, grant, candidate)
        self.assertEqual(1, code, value)
        self.assertEqual([], value["commands"])

    def test_cleanup_plan_never_force_deletes_without_a_complete_read_back(self) -> None:
        fixture = self._landed()
        root = Path(fixture["root"])
        candidate = str(fixture["candidate"])
        git(root, "checkout", "-q", "main")
        code, _value, grant = self._record(fixture, actions=("cleanup",))
        self.assertEqual(0, code)
        sha = self._sha256(grant)
        cases = {
            "no observed main": {"status": "PASS", "landing": "exact", "candidate": candidate},
            "observed main unknown here": {
                "status": "PASS", "landing": "tree_equal_S", "candidate": candidate, "observed_main": "0" * 40,
            },
            "exact but not merged": {
                "status": "PASS", "landing": "exact", "candidate": candidate,
                "observed_main": str(fixture["base"]),
            },
        }
        for name, readback in cases.items():
            with self.subTest(name=name):
                path = self._temp("landing-readback-") / "readback.json"
                write_file(path, json.dumps(readback))
                code, value = self._run(
                    "cleanup-plan", "--repo-root", str(root), "--grant", str(grant),
                    "--grant-sha256", sha, "--readback", str(path),
                )
                self.assertEqual(1, code, value)
                self.assertEqual([], value["commands"])

    def test_a_git_error_during_ancestry_is_an_error_not_a_force_delete(self) -> None:
        fixture = self._landed()
        root = Path(fixture["root"])
        candidate = str(fixture["candidate"])
        git(root, "checkout", "-q", "main")
        code, _value, grant = self._record(fixture, actions=("cleanup",))
        self.assertEqual(0, code)
        real = subject.run_git

        def failing(repo, *args, **kwargs):
            if args[:2] == ("merge-base", "--is-ancestor"):
                return subprocess.CompletedProcess(args, 128, "", "fatal: bad object")
            return real(repo, *args, **kwargs)

        with patch.object(subject, "run_git", failing):
            code, value = self._cleanup(fixture, grant, candidate)
        self.assertEqual(2, code, value)
        self.assertEqual("ERROR", value["status"])
        self.assertNotIn("commands", value)

    def test_a_git_timeout_is_a_structured_error(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture)
        self.assertEqual(0, code)
        real = subject.run_git

        def slow(repo, *args, **kwargs):
            if args and args[0] == "diff":
                raise subprocess.TimeoutExpired(["git", *args], 30)
            return real(repo, *args, **kwargs)

        with patch.object(subject, "run_git", slow):
            code, value = self._check(fixture, grant, candidate, "push")
        self.assertEqual(2, code, value)
        self.assertEqual("ERROR", value["status"])

    def test_record_without_an_action_refuses_instead_of_raising(self) -> None:
        fixture = self._landed()
        code, value, _grant = self._record(fixture, actions=())
        self.assertEqual(1, code, value)
        self.assertTrue(any("at least one --action" in reason for reason in value["reasons"]))

    def test_the_clock_cannot_be_set_from_the_command_line(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture)
        self.assertEqual(0, code)
        argv = [
            "check", "--repo-root", str(fixture["root"]), "--grant", str(grant),
            "--grant-sha256", self._sha256(grant), "--candidate", candidate, "--action", "push",
        ]
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
            subject.main([*argv, "--now", "2019-01-01T00:00:00Z"])
        self.assertEqual(2, caught.exception.code)

    def test_owner_only_paths_ignore_case_quoting_and_depth(self) -> None:
        # A case-insensitive file system cannot hold agents.md beside AGENTS.md,
        # so the spelling variants are checked on the matcher itself.
        self.assertEqual(
            ["Claude.MD", "agents.md", "sub/Agents.Override.md"],
            subject._owner_only_paths(["agents.md", "Claude.MD", "sub/Agents.Override.md", "src/app.py"], {}),
        )
        cases = {
            "nested instruction file": "packages/api/AGENTS.md",
            "nested Claude file": "packages/api/CLAUDE.md",
            "upper-case workflow directory": ".GITHUB/WORKFLOWS/ci.yml",
            "non-ASCII workflow name": ".github/workflows/\u00e9.yml",
            "code owners": ".github/CODEOWNERS",
            "GitLab CI": ".gitlab-ci.yml",
            "CircleCI": ".circleci/config.yml",
            "Azure Pipelines": "azure-pipelines.yml",
            "Jenkins": "Jenkinsfile",
        }
        for name, path in cases.items():
            with self.subTest(name=name):
                fixture = self._landed()
                root = Path(fixture["root"])
                candidate = self._commit(root, {path: "changed\n"}, "touch " + name)
                code, _value, grant = self._record(fixture)
                self.assertEqual(0, code)
                code, value = self._check(fixture, grant, candidate, "push")
                self.assertEqual(1, code, value)
                matching = [reason for reason in value["reasons"] if "owner-only paths changed" in reason]
                self.assertEqual(1, len(matching), value)

    def test_a_directory_pattern_also_covers_the_directory_entry_itself(self) -> None:
        # A directory replaced by a submodule or symlink is reported by its
        # own name, without a trailing slash.
        fixture = self._landed(AGENTS_EPIC_GRANT.replace("- Owner-only paths: none", "- Owner-only paths: vendor/"))
        root = Path(fixture["root"])
        candidate = self._commit(root, {"vendor": "now a file\n"}, "replace the directory")
        code, _value, grant = self._record(fixture)
        self.assertEqual(0, code)
        code, value = self._check(fixture, grant, candidate, "push")
        self.assertEqual(1, code, value)
        self.assertTrue(any("owner-only paths changed: vendor" in reason for reason in value["reasons"]))

    def test_only_one_unfenced_complete_policy_section_makes_a_repository_eligible(self) -> None:
        fenced = "# Repo\n\nAn example:\n\n```markdown\n" + AGENTS_EPIC_GRANT.split("\n", 2)[2] + "```\n"
        cases = {
            "fenced example only": fenced,
            "two sections": AGENTS_EPIC_GRANT + "\n## Delivery Autonomy\n\n- Landing: owner_each_time\n",
            "repeated key": AGENTS_EPIC_GRANT.replace(
                "- Landing: epic_grant\n", "- Landing: epic_grant\n- Landing: owner_each_time\n"
            ),
            "landing line alone": "# Repo\n\n## Delivery Autonomy\n\n- Landing: epic_grant\n",
            "unfilled journey": AGENTS_EPIC_GRANT.replace("python -m pytest tests/journey", "<fill>"),
            "no required checks": AGENTS_EPIC_GRANT.replace("- Required checks: build, test", "- Required checks: none"),
        }
        for name, agents in cases.items():
            with self.subTest(name=name):
                fixture = self._landed(agents)
                candidate = str(fixture["candidate"])
                code, _value, grant = self._record(fixture)
                self.assertEqual(0, code)
                code, value = self._check(fixture, grant, candidate, "push")
                self.assertEqual(1, code, value)
                self.assertTrue(any("not eligible" in reason for reason in value["reasons"]), value)

    def test_a_review_does_not_carry_across_code_or_documents_under_docs(self) -> None:
        for path in ("docs/runtime.py", "docs/guide.md", "docs/epics/tool.py", "README.md"):
            with self.subTest(path=path):
                fixture = self._fixture()
                root = Path(fixture["root"])
                reviewed = self._commit(root, {"src/app.py": "print('landing')\n"}, "code")
                candidate = self._commit(root, {path: "changed\n"}, "after review")
                code, _value, grant = self._record(fixture, actions=("merge",))
                self.assertEqual(0, code)
                evidence = self._evidence(candidate, review_sha=reviewed)
                code, value = self._check(fixture, grant, candidate, "merge", evidence=evidence)
                self.assertEqual(1, code, value)
                self.assertTrue(any("without a review that binds it" in reason for reason in value["reasons"]))

    def test_revocation_holds_through_an_alias_of_the_grant(self) -> None:
        fixture = self._landed()
        candidate = str(fixture["candidate"])
        code, _value, grant = self._record(fixture)
        self.assertEqual(0, code)
        self.assertEqual(0, self._run("revoke", "--grant", str(grant), "--source", "owner, 2026-11-18")[0])
        alias = self._temp("landing-alias-") / "alias.json"
        try:
            alias.symlink_to(grant)
        except (OSError, NotImplementedError):
            self.skipTest("symbolic links are not available on this host")
        code, value = self._check(fixture, alias, candidate, "push")
        self.assertEqual(1, code, value)
        self.assertIn("the grant is revoked", value["reasons"])


if __name__ == "__main__":
    unittest.main()
