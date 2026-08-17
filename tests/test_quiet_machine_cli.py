import argparse
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "skills/quiet-machine/scripts/quiet_machine.py"
SPEC = importlib.util.spec_from_file_location("quiet_machine_cli", SCRIPT)
qm = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(qm)


class DurableParserTests(unittest.TestCase):
    def test_durable_job_commands_and_affinity_flags(self):
        parser = qm.build_parser()
        run = parser.parse_args([
            "run", "--profile", "bench", "--time", "2h", "--detach",
            "--events", "json", "--cpus", "0-2", "--helper-cpus", "3",
            "--", "cargo", "bench",
        ])
        self.assertTrue(run.detach)
        self.assertEqual(run.cpus, "0-2")
        self.assertEqual(run.helper_cpus, "3")
        for command in ("status", "logs", "attach", "wait", "cancel", "artifacts"):
            args = parser.parse_args([command, "qm-19700101T000000Z-0123456789ab"])
            self.assertEqual(args.job_id, "qm-19700101T000000Z-0123456789ab")


class DetachedRunTests(unittest.TestCase):
    def test_detached_run_persists_reconnection_record(self):
        server = {
            "id": 42,
            "labels": {"quiet-machine-created": "1000"},
            "public_net": {"ipv4": {"ip": "192.0.2.8"}},
        }
        profile = {
            "name": "bench", "ssh_private_key": "key",
            "ssh_source_cidr": "8.8.8.8/32", "artifact_dir": "out",
        }
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.dict(os.environ, {"QUIET_MACHINE_STATE_DIR": td}), \
             mock.patch.object(qm, "plan_for", return_value=({"id": 9}, "fp", server, 9999)), \
             mock.patch.object(qm, "remote") as remote, \
             mock.patch.object(qm, "rsync"), \
             mock.patch.object(qm, "start_local_mirror") as mirror, \
             mock.patch.object(qm.time, "time", return_value=2000), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
            remote.return_value = subprocess.CompletedProcess(
                [], 0, stdout='{"event":"job_started"}\n', stderr="")
            source = Path(td) / "source"
            source.mkdir()
            args = argparse.Namespace(
                apply=True, time=3600, command=["cargo", "bench"], detach=True,
                events="none", cpus="0-2", helper_cpus="3", source=source,
                report=None, config=Path(td) / ".quiet-machine.toml",
            )
            self.assertEqual(qm.do_run(args, profile, Path(td), "token"), 0)
            output = json.loads(stdout.getvalue())
            record = qm.jobs_index.load(output["job_id"])
        self.assertEqual(record["server_id"], 42)
        self.assertEqual(record["command"], ["cargo", "bench"])
        launch = [call for call in remote.call_args_list
                  if "--detach" in call.args[3]][0]
        self.assertIn("--job-id", launch.args[3])
        self.assertIn("--cpus", launch.args[3])
        mirror.assert_called_once_with(record["job_id"])

    def test_lost_start_acknowledgement_never_cancels_running_job(self):
        server = {"id": 42, "labels": {"quiet-machine-created": "1000"},
                  "public_net": {"ipv4": {"ip": "192.0.2.8"}}}
        profile = {"name": "bench", "ssh_private_key": "key",
                   "ssh_source_cidr": "8.8.8.8/32", "artifact_dir": "out"}

        def remote_side_effect(_profile, _base, _ip, argv, **_kwargs):
            if "start" in argv:
                return subprocess.CompletedProcess(argv, 255, stdout="", stderr="connection lost")
            if "status" in argv:
                return subprocess.CompletedProcess(
                    argv, 0, stdout=json.dumps({"job_id": job_id[0], "state": "running"}),
                    stderr="")
            return subprocess.CompletedProcess(argv, 0, stdout='{"event":"ok"}', stderr="")

        job_id = [None]
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.dict(os.environ, {"QUIET_MACHINE_STATE_DIR": td}), \
             mock.patch.object(qm, "plan_for", return_value=({"id": 9}, "fp", server, 9999)), \
             mock.patch.object(qm, "remote", side_effect=remote_side_effect) as remote, \
             mock.patch.object(qm, "rsync"), \
             mock.patch.object(qm, "start_local_mirror"), \
             mock.patch.object(qm.time, "time", return_value=2000), \
             mock.patch("sys.stdout", new_callable=io.StringIO) as stdout:
            source = Path(td) / "source"; source.mkdir()
            original = qm.jobs_index.new_job_id
            with mock.patch.object(qm.jobs_index, "new_job_id",
                                   side_effect=lambda: (job_id.__setitem__(0, original()) or job_id[0])):
                args = argparse.Namespace(
                    apply=True, time=3600, command=["benchmark"], detach=True,
                    events="none", cpus=None, helper_cpus=None, source=source,
                    report=None, config=Path(td) / ".quiet-machine.toml")
                self.assertEqual(qm.do_run(args, profile, Path(td), "token"), 0)
            result = json.loads(stdout.getvalue())
        self.assertEqual(result["state"], "running")
        self.assertFalse(any("cancel" in call.args[3] for call in remote.call_args_list))


class ProgressTests(unittest.TestCase):
    def test_json_progress_is_structured_and_stays_on_stderr(self):
        args = argparse.Namespace(events="json")
        with mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
            qm.emit_progress(args, "sync", "uploading", job_id="job")
        event = json.loads(stderr.getvalue())
        self.assertEqual(event["stage"], "sync")
        self.assertEqual(event["job_id"], "job")


class LocalMirrorTests(unittest.TestCase):
    def test_mirror_caches_terminal_state_log_and_artifacts(self):
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.dict(os.environ, {"QUIET_MACHINE_STATE_DIR": td}), \
             mock.patch.object(qm, "job_context", return_value=({}, Path(td), "token")), \
             mock.patch.object(qm, "remote_json", return_value={
                 "job_id": "qm-19700101T000000Z-0123456789ab",
                 "state": "success", "exit_code": 0}), \
             mock.patch.object(qm, "hcloud", return_value={"server_type": {}}), \
             mock.patch.object(qm, "sizing_for_state", return_value=None), \
             mock.patch.object(qm, "retrieve_job_log") as log, \
             mock.patch.object(qm, "retrieve_job_artifacts") as artifacts:
            job_id = "qm-19700101T000000Z-0123456789ab"
            qm.jobs_index.save({
                "job_id": job_id, "server_id": 42, "server_ip": "192.0.2.8",
                "retain_until": 9999999999, "artifact_location": str(Path(td) / "out"),
                "report": None, "state": "queued", "config": str(Path(td) / "config"),
                "profile": "bench",
            })
            self.assertEqual(qm.do_mirror(argparse.Namespace(job_id=job_id)), 0)
            record = qm.jobs_index.load(job_id)
        self.assertEqual(record["state"], "success")
        self.assertEqual(record["last_status"]["exit_code"], 0)
        log.assert_called_once()
        artifacts.assert_called_once()


class DryRunTests(unittest.TestCase):
    def test_pool_plan_does_not_probe_over_ssh(self):
        server = {
            "id": 42, "labels": {"quiet-machine-profile": "fp",
                                    "quiet-machine-state": "ready",
                                    "quiet-machine-created": "1000"},
            "public_net": {"ipv4": {"ip": "192.0.2.8"}},
        }
        args = argparse.Namespace(apply=False, time=60)
        profile = {"name": "bench", "image": "ubuntu", "ssh_source_cidr": "8.8.8.8/32"}
        with mock.patch.object(qm, "resolve_image", return_value={"id": 9}), \
             mock.patch.object(qm, "profile_hash", return_value="fp"), \
             mock.patch.object(qm, "servers", return_value=[server]), \
             mock.patch.object(qm, "refresh_server_firewall", return_value={"action": "none"}), \
             mock.patch.object(qm, "remote") as remote:
            _image, _fingerprint, selected, _retain = qm.plan_for(
                args, profile, Path("."), "token")
        self.assertEqual(selected["id"], 42)
        remote.assert_not_called()


if __name__ == "__main__":
    unittest.main()
