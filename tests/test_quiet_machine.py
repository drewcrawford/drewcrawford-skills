import importlib.util
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "skills/quiet-machine/scripts/quiet_machine.py"
SPEC = importlib.util.spec_from_file_location("quiet_machine", SCRIPT)
qm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qm)

REMOTE_SCRIPT = Path(__file__).resolve().parents[1] / "skills/quiet-machine/scripts/remote_agent.py"
REMOTE_SPEC = importlib.util.spec_from_file_location("quiet_machine_remote", REMOTE_SCRIPT)
remote_agent = importlib.util.module_from_spec(REMOTE_SPEC)
REMOTE_SPEC.loader.exec_module(remote_agent)


class DurationTests(unittest.TestCase):
    def test_common_durations(self):
        self.assertEqual(qm.duration("30m"), 1800)
        self.assertEqual(qm.duration("2h"), 7200)
        self.assertEqual(qm.duration("1.5m"), 90)

    def test_bad_duration_is_cli_error(self):
        with self.assertRaises(Exception):
            qm.duration("30")
        with self.assertRaises(Exception):
            qm.duration("0m")


class RetentionTests(unittest.TestCase):
    def test_rounds_to_creation_relative_boundary_with_guard(self):
        self.assertEqual(qm.retention(1000, 1100, 1800, 3600, 60), 4540)

    def test_long_request_rounds_up_again(self):
        self.assertEqual(qm.retention(1000, 1100, 5400, 3600, 60), 8140)

    def test_guard_never_precedes_task_start(self):
        self.assertEqual(qm.retention(1000, 1001, 1, 3600, 4000), 1001)


class FingerprintTests(unittest.TestCase):
    def test_setup_content_changes_fingerprint(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            script = root / "setup.sh"
            script.write_text("echo one\n")
            profile = {"name": "x", "setup_script": "setup.sh", "ssh_private_key": "ignored"}
            first = qm.profile_hash(profile, root, "10")
            script.write_text("echo two\n")
            second = qm.profile_hash(profile, root, "10")
            self.assertNotEqual(first, second)

    def test_local_secret_paths_do_not_change_fingerprint(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            profile = {"name": "x", "ssh_private_key": "/one", "credential_file": "/secret"}
            first = qm.profile_hash(profile, root, "10")
            profile.update(ssh_private_key="/two", credential_file="/other")
            self.assertEqual(first, qm.profile_hash(profile, root, "10"))


class CredentialTests(unittest.TestCase):
    def test_rejects_world_readable_token(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            token = root / "token"
            token.write_text("secret\n")
            token.chmod(0o644)
            with self.assertRaises(qm.Failure):
                qm.read_token({"credential_file": str(token)}, root)
            token.chmod(0o600)
            self.assertEqual(qm.read_token({"credential_file": str(token)}, root), "secret")


class ParserTests(unittest.TestCase):
    def test_run_command_after_separator(self):
        args = qm.build_parser().parse_args(["run", "--profile", "rust", "--time", "30m", "--", "cargo", "test"])
        self.assertEqual(args.command, ["--", "cargo", "test"])
        self.assertFalse(args.apply)


class PoolTests(unittest.TestCase):
    def test_busy_candidate_is_skipped_for_next_idle_server(self):
        machines = [
            {"id": 1, "public_net": {"ipv4": {"ip": "one"}}, "labels": {"quiet-machine-profile": "fp", "quiet-machine-state": "ready"}},
            {"id": 2, "public_net": {"ipv4": {"ip": "two"}}, "labels": {"quiet-machine-profile": "fp", "quiet-machine-state": "ready"}},
        ]
        results = [mock.Mock(returncode=75), mock.Mock(returncode=0)]
        with mock.patch.object(qm, "servers", return_value=machines), mock.patch.object(qm, "remote", side_effect=results):
            selected = qm.candidate("token", {"ssh_private_key": "key"}, Path("."), "fp")
        self.assertEqual(selected["id"], 2)

    def test_no_idle_candidate_requests_new_machine(self):
        machines = [{"id": 1, "labels": {"quiet-machine-profile": "fp", "quiet-machine-state": "busy"}}]
        with mock.patch.object(qm, "servers", return_value=machines):
            self.assertIsNone(qm.candidate("token", {}, Path("."), "fp"))


class SecretTests(unittest.TestCase):
    def test_bootstrap_assets_do_not_contain_local_token(self):
        token = "test-token-that-must-not-leak"
        for path in (qm.REMOTE_AGENT, qm.SERVICE):
            self.assertNotIn(token, path.read_text())


class ReaperTests(unittest.TestCase):
    def test_idle_expired_machine_deletes_firewall_then_itself(self):
        handle = mock.Mock()
        calls = []

        def request(method, path, body=None):
            calls.append((method, path))
            if path.startswith("/firewalls?"):
                return {"firewalls": [{"id": 9}]}
            return {}

        with mock.patch.object(remote_agent, "labels", return_value={"quiet-machine-retain-until": "10", "quiet-machine-hard-expiry": "20"}), \
             mock.patch.object(remote_agent, "lock", return_value=handle), \
             mock.patch.object(remote_agent, "server_id", return_value="42"), \
             mock.patch.object(remote_agent, "request", side_effect=request), \
             mock.patch.object(remote_agent.time, "time", return_value=11):
            self.assertTrue(remote_agent.reap_once())
        self.assertIn(("DELETE", "/firewalls/9"), calls)
        self.assertIn(("DELETE", "/servers/42"), calls)

    def test_busy_machine_waits_until_hard_deadline(self):
        with mock.patch.object(remote_agent, "labels", return_value={"quiet-machine-retain-until": "10", "quiet-machine-hard-expiry": "20"}), \
             mock.patch.object(remote_agent, "lock", return_value=None), \
             mock.patch.object(remote_agent.time, "time", return_value=11):
            self.assertFalse(remote_agent.reap_once())

    def test_failed_setup_marks_machine_for_repair(self):
        args = mock.Mock(profile="fp")
        with mock.patch.object(remote_agent, "run_locked", return_value=7), \
             mock.patch.object(remote_agent, "set_labels") as labels:
            self.assertEqual(remote_agent.setup(args), 7)
        labels.assert_called_with(**{"quiet-machine-state": "needs-repair"})


if __name__ == "__main__":
    unittest.main()
