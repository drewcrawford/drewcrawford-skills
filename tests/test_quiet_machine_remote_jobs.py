import argparse
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "skills/quiet-machine/scripts/remote_agent.py"
SPEC = importlib.util.spec_from_file_location("quiet_machine_remote_jobs", SCRIPT)
agent = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(agent)


class BinaryStdout:
    def __init__(self):
        self.buffer = io.BytesIO()


class StateTests(unittest.TestCase):
    def test_retention_is_monotonic_but_each_job_replaces_hard_deadline(self):
        with mock.patch.object(agent, "labels", return_value={
            "quiet-machine-retain-until": "200",
            "quiet-machine-hard-expiry": "300",
        }), mock.patch.object(agent, "server_id", return_value="42"), \
             mock.patch.object(agent, "request") as request:
            agent.set_labels(**{"quiet-machine-retain-until": 100,
                                "quiet-machine-hard-expiry": 250})
        body = request.call_args.args[2]
        self.assertEqual(body["labels"]["quiet-machine-retain-until"], "200")
        self.assertEqual(body["labels"]["quiet-machine-hard-expiry"], "250")

    def test_atomic_state_updates_preserve_job_history_fields(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.object(agent, "JOBS", Path(td)):
            agent.write_state("petrucci-01", {
                "job_id": "petrucci-01", "state": "queued",
                "command": ["cargo", "bench"], "server_id": 42,
            })
            state = agent.write_state("petrucci-01", {"state": "running"})
            self.assertEqual(state["command"], ["cargo", "bench"])
            self.assertEqual(state["server_id"], 42)
            self.assertEqual(json.loads(agent.state_path("petrucci-01").read_text()), state)

    def test_invalid_job_id_cannot_escape_job_root(self):
        with self.assertRaises(ValueError):
            agent.job_dir("../../token")

    def test_missing_supervisor_becomes_infrastructure_loss(self):
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(agent, "JOBS", Path(td)), \
             mock.patch.object(agent, "_identity_alive", return_value=False):
            agent.write_state("lost", {
                "job_id": "lost", "state": "running", "created_at_unix": 1,
                "supervisor": {"pid": 12}, "exit_code": None,
            })
            state = agent.reconcile_state("lost")
            self.assertEqual(state["state"], "infrastructure_lost")
            self.assertEqual(state["terminal_reason"], "supervisor_disappeared")

    def test_missing_supervisor_drains_live_transient_unit_before_terminal_state(self):
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(agent, "JOBS", Path(td)), \
             mock.patch.object(agent, "_identity_alive", return_value=False), \
             mock.patch.object(agent, "_unit_active", return_value=True), \
             mock.patch.object(agent, "_terminate_unit") as terminate:
            agent.write_state("lost-unit", {
                "job_id": "lost-unit", "state": "running", "created_at_unix": 1,
                "supervisor": {"pid": 12}, "unit": "quiet-machine-job-lost-unit",
            })
            state = agent.reconcile_state("lost-unit")
        terminate.assert_called_once_with("quiet-machine-job-lost-unit")
        self.assertEqual(state["state"], "infrastructure_lost")

    def test_completion_resolves_concurrent_cancel_as_cancelled(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.object(agent, "JOBS", Path(td)):
            agent.write_state("race", {
                "job_id": "race", "state": "running", "created_at_unix": 1,
                "artifact_location": None, "cancel_requested": True,
                "affinity": {},
            })
            agent._final_state("race", "success", 0, 1, {})
            state = agent.read_state("race")
            self.assertEqual(state["state"], "cancelled")
            self.assertIsNone(state["exit_code"])
            self.assertEqual(state["terminal_reason"], "cancellation_requested")


class DetachedTests(unittest.TestCase):
    def test_deferred_launch_holds_lock_and_marks_vm_busy_before_sync(self):
        with tempfile.TemporaryDirectory() as td:
            jobs = Path(td) / "jobs"
            global_lock = (Path(td) / "global.lock").open("a+")
            args = argparse.Namespace(
                job_id="reserved", command=["benchmark"], cwd="/not-yet-synced",
                timeout=30, retain_until=100, defer_start=True,
                reservation_timeout=600, cpus=None, helper_cpus=None,
            )
            worker = mock.Mock(pid=321)
            output = io.StringIO()
            with mock.patch.object(agent, "JOBS", jobs), \
                 mock.patch.object(agent, "lock", return_value=global_lock), \
                 mock.patch.object(agent, "set_labels") as labels, \
                 mock.patch.object(agent, "_pid_identity", return_value={"pid": 321}), \
                 mock.patch.object(agent.subprocess, "Popen", return_value=worker), \
                 contextlib.redirect_stdout(output):
                self.assertEqual(agent.start_detached(args), 0)
            state = json.loads((jobs / "reserved/state.json").read_text())
            self.assertEqual(state["state"], "reserved")
            self.assertEqual(json.loads(output.getvalue())["event"], "job_reserved")
            self.assertEqual(labels.call_args.kwargs["quiet-machine-state"], "busy")

    def test_detach_uses_supplied_id_and_passes_durable_locks(self):
        with tempfile.TemporaryDirectory() as td:
            jobs = Path(td) / "jobs"
            global_lock = (Path(td) / "global.lock").open("a+")
            args = argparse.Namespace(job_id="bench-7", command=["echo", "ok"],
                                      cwd="/work", timeout=30, retain_until=100)
            worker = mock.Mock(pid=321)
            output = io.StringIO()
            with mock.patch.object(agent, "JOBS", jobs), \
                 mock.patch.object(agent, "lock", return_value=global_lock), \
                 mock.patch.object(agent, "set_labels"), \
                 mock.patch.object(agent, "_pid_identity", return_value={"pid": 321}), \
                 mock.patch.object(agent.subprocess, "Popen", return_value=worker) as popen, \
                 contextlib.redirect_stdout(output):
                self.assertEqual(agent.start_detached(args), 0)
            state = json.loads((jobs / "bench-7/state.json").read_text())
            self.assertEqual(state["job_id"], "bench-7")
            self.assertEqual(state["command"], ["echo", "ok"])
            self.assertIn("pass_fds", popen.call_args.kwargs)
            self.assertEqual(json.loads(output.getvalue())["event"], "job_started")

    def test_existing_job_id_is_never_reused(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.object(agent, "JOBS", Path(td)):
            agent.job_dir("same").mkdir(parents=True)
            args = argparse.Namespace(job_id="same")
            with self.assertRaisesRegex(ValueError, "already exists"):
                agent.start_detached(args)

    def test_wait_emits_one_machine_readable_completion_record(self):
        done = {"job_id": "j", "state": "success", "exit_code": 0}
        output = io.StringIO()
        with mock.patch.object(agent, "reconcile_state", return_value=done), \
             mock.patch.object(agent, "_wait_completion") as wait, \
             contextlib.redirect_stdout(output):
            self.assertEqual(agent.wait_job(argparse.Namespace(job_id="j")), 0)
        wait.assert_called_once_with("j")
        lines = output.getvalue().splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["event"], "job_completed")
        self.assertEqual(json.loads(lines[0])["state"], "success")

    def test_worker_records_affinity_fingerprint_telemetry_and_terminal_reason(self):
        class Process:
            pid = 456

            def __init__(self):
                self.polls = 0

            def poll(self):
                self.polls += 1
                return None if self.polls == 1 else 0

            def wait(self, timeout=None):
                return 0

        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            global_fd = os.open(base / "global.lock", os.O_RDWR | os.O_CREAT)
            complete_fd = os.open(base / "complete.lock", os.O_RDWR | os.O_CREAT)
            args = argparse.Namespace(
                job_id="pinned", timeout=30, retain_until=100, cwd=str(base),
                lock_fd=global_fd, complete_fd=complete_fd,
                cpus="1-2", helper_cpus="0", command=["benchmark"],
            )
            with mock.patch.object(agent, "JOBS", base / "jobs"), \
                 mock.patch.object(agent, "TASK_PID", base / "task.pid"), \
                 mock.patch.object(agent, "ACTIVE_JOB", base / "active-job"), \
                 mock.patch.object(agent, "machine_fingerprint", return_value={
                     "cloud": {"server_id": 42, "server_type": "ccx13"}}), \
                 mock.patch.object(agent, "set_labels"), \
                 mock.patch.object(agent, "ensure_user"), \
                 mock.patch.object(agent, "_pid_identity", side_effect=lambda pid: {"pid": pid}), \
                 mock.patch.object(agent, "_proc_stat", side_effect=[
                     {"total_ticks": 100, "steal_ticks": 1},
                     {"total_ticks": 200, "steal_ticks": 2}]), \
                 mock.patch.object(agent, "_network_counters", side_effect=[
                     {"received_bytes": 10, "transmitted_bytes": 20},
                     {"received_bytes": 13, "transmitted_bytes": 25}]), \
                 mock.patch.object(agent, "_unit_metrics", return_value={
                     "active_threads": 3, "active_cpus": [1, 2], "affinity": ["1-2"],
                     "read_bytes": 4, "write_bytes": 5,
                     "memory_peak_bytes": 8192, "cpu_usage_seconds": 1.5,
                     "authoritative": True}), \
                 mock.patch.object(agent, "_unit_main_pid", return_value=456), \
                 mock.patch.object(agent, "_terminate_unit"), \
                 mock.patch.object(agent.time, "sleep"), \
                 mock.patch.object(agent.subprocess, "Popen", return_value=Process()) as popen:
                agent.write_state("pinned", {
                    "job_id": "pinned", "state": "queued", "created_at_unix": 1,
                    "artifact_location": None,
                    "affinity": {"requested_task": "1-2", "requested_helper": "0"},
                })
                self.assertEqual(agent.job_worker(args), 0)
            state = json.loads((base / "jobs/pinned/state.json").read_text())
            self.assertEqual(state["state"], "success")
            self.assertEqual(state["terminal_reason"], "exit_zero")
            self.assertEqual(state["server_id"], 42)
            self.assertEqual(state["affinity"]["effective_task"], ["1,2"])
            self.assertEqual(state["telemetry"]["active_threads"], {"max": 3})
            self.assertEqual(state["telemetry"]["active_cores"]["max"], 2)
            self.assertEqual(state["telemetry"]["task_cpu_seconds"], 1.5)
            self.assertEqual(state["telemetry"]["peak_rss_bytes"], 8192)
            self.assertTrue(state["telemetry"]["authoritative_cgroup_counters"])
            argv = popen.call_args.args[0]
            self.assertEqual(argv[0], "systemd-run")
            self.assertIn("--property=KillMode=control-group", argv)
            self.assertIn("--property=RuntimeMaxSec=30s", argv)
            self.assertIn("--property=CPUAccounting=yes", argv)
            self.assertIn("--setenv=QUIET_MACHINE_HELPER_CPUS=0", argv)
            self.assertTrue(any(value.startswith("--setenv=PATH=/home/quiet/.cargo/bin:")
                                for value in argv))
            self.assertEqual(argv[argv.index("taskset"):argv.index("taskset") + 3],
                             ["taskset", "--cpu-list", "1-2"])

    def test_equivalent_kernel_affinity_ranges_match_requested_lists(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.object(agent, "JOBS", Path(td)):
            agent.write_state("affinity", {
                "job_id": "affinity", "state": "running", "artifact_location": None,
                "affinity": {"requested_task": "2,3", "requested_helper": "0,1"},
            })
            agent._final_state("affinity", "success", 0, 1, {
                "effective_affinity": ["2-3", "0-1"],
            })
            affinity = agent.read_state("affinity")["affinity"]
        self.assertEqual(affinity["effective_task"], ["2,3"])
        self.assertEqual(affinity["effective_helper"], ["0,1"])
        self.assertTrue(affinity["matches_request"])

    def test_cgroup_accounting_captures_lifetime_cpu_memory_and_io(self):
        with tempfile.TemporaryDirectory() as td:
            group = Path(td)
            (group / "cpu.stat").write_text("usage_usec 2500000\nuser_usec 2000000\n")
            (group / "memory.current").write_text("4096\n")
            (group / "memory.peak").write_text("1048576\n")
            (group / "io.stat").write_text(
                "8:0 rbytes=10 wbytes=20 rios=1 wios=2\n8:1 rbytes=3 wbytes=4\n")
            metrics = agent._cgroup_accounting(group)
        self.assertTrue(metrics["authoritative"])
        self.assertEqual(metrics["cpu_usage_seconds"], 2.5)
        self.assertEqual(metrics["memory_peak_bytes"], 1048576)
        self.assertEqual(metrics["read_bytes"], 13)
        self.assertEqual(metrics["write_bytes"], 24)

    def test_cgroup_pid_enumeration_includes_nested_helper_scope(self):
        with tempfile.TemporaryDirectory() as td:
            group = Path(td)
            nested = group / "helper"
            nested.mkdir()
            (group / "cgroup.procs").write_text("10\n")
            (nested / "cgroup.procs").write_text("20\n21\n")
            self.assertEqual(agent._cgroup_pids(group), {10, 20, 21})


class LogAndArtifactTests(unittest.TestCase):
    def test_follow_drains_complete_log_without_duplication(self):
        with tempfile.TemporaryDirectory() as td, mock.patch.object(agent, "JOBS", Path(td)):
            agent.write_state("j", {"job_id": "j", "state": "success"})
            (agent.job_dir("j") / "complete.lock").touch()
            (agent.job_dir("j") / "output.log").write_bytes(b"first\nlast\n")
            output = BinaryStdout()
            with mock.patch.object(agent.sys, "stdout", output):
                agent.logs_job(argparse.Namespace(job_id="j", follow=True))
            self.assertEqual(output.buffer.getvalue(), b"first\nlast\n")

    def test_artifact_manifest_supports_incremental_listing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "out"
            root.mkdir()
            (root / "checkpoint.json").write_text("{}")
            state = {"job_id": "j", "state": "running", "artifact_location": str(root)}
            manifest = agent.artifact_manifest(state)
            self.assertEqual(manifest["files"][0]["path"], "checkpoint.json")
            self.assertEqual(manifest["files"][0]["size"], 2)


class CancellationTests(unittest.TestCase):
    def test_cancel_marks_request_before_signalling_and_waits_for_terminal_state(self):
        running = {"job_id": "j", "state": "running",
                   "process": {"pid": 55, "start_ticks": 1, "boot_id": "b"}}
        cancelled = {"job_id": "j", "state": "cancelled", "exit_code": None}
        output = io.StringIO()
        with mock.patch.object(agent, "reconcile_state", side_effect=[running, cancelled]), \
             mock.patch.object(agent, "write_state", return_value={**running, "cancel_requested": True}) as write, \
             mock.patch.object(agent, "_identity_alive", return_value=True), \
             mock.patch.object(agent, "_terminate_group") as terminate, \
             mock.patch.object(agent, "_wait_completion") as wait, \
             contextlib.redirect_stdout(output):
            self.assertEqual(agent.cancel_job(argparse.Namespace(job_id="j")), 0)
        self.assertTrue(write.call_args.args[1]["cancel_requested"])
        terminate.assert_called_once_with(55)
        wait.assert_called_once_with("j")
        self.assertEqual(json.loads(output.getvalue())["state"], "cancelled")


class InteractiveShellTests(unittest.TestCase):
    def test_shell_inherits_terminal_and_restores_ready_label(self):
        handle = mock.Mock()
        proc = mock.Mock(pid=88)
        proc.wait.return_value = 0
        proc.poll.return_value = 0
        args = argparse.Namespace(timeout=30, retain_until=100, cwd="/home/quiet")
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.object(agent, "TASK_PID", Path(td) / "pid"), \
             mock.patch.object(agent, "lock", return_value=handle), \
             mock.patch.object(agent, "set_labels") as labels, \
             mock.patch.object(agent, "ensure_user"), \
             mock.patch.object(agent.os, "isatty", return_value=False), \
             mock.patch.object(agent.subprocess, "Popen", return_value=proc) as popen:
            self.assertEqual(agent.interactive_shell(args), 0)
        argv = popen.call_args.args[0]
        self.assertEqual(argv[-2:], ["bash", "-il"])
        self.assertIs(popen.call_args.kwargs["preexec_fn"], os.setpgrp)
        self.assertEqual(labels.call_args_list[-1].kwargs["quiet-machine-state"], "ready")
        handle.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
