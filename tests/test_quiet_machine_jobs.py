import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "skills/quiet-machine/scripts/quiet_machine_jobs.py"
SPEC = importlib.util.spec_from_file_location("quiet_machine_jobs", SCRIPT)
jobs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(jobs)


class JobIndexTests(unittest.TestCase):
    def test_stable_shape_and_round_trip(self):
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.dict(os.environ, {"QUIET_MACHINE_STATE_DIR": td}):
            job_id = jobs.new_job_id(0)
            self.assertRegex(job_id, jobs.JOB_ID)
            jobs.save({"job_id": job_id, "state": "running", "created_at": 1})
            self.assertEqual(jobs.load(job_id)["state"], "running")
            jobs.update(job_id, state="success", exit_code=0)
            self.assertEqual(jobs.all_jobs()[0]["state"], "success")
            self.assertEqual(Path(jobs.job_path(job_id)).stat().st_mode & 0o777, 0o600)

    def test_invalid_and_unknown_ids_are_actionable(self):
        with self.assertRaises(jobs.JobIndexError):
            jobs.validate_job_id("../../token")
        with tempfile.TemporaryDirectory() as td, \
             mock.patch.dict(os.environ, {"QUIET_MACHINE_STATE_DIR": td}), \
             self.assertRaisesRegex(jobs.JobIndexError, "unknown"):
            jobs.load("qm-19700101T000000Z-0123456789ab")

    def test_terminal_exit_mapping(self):
        self.assertEqual(jobs.exit_code({"state": "success", "exit_code": 0}), 0)
        self.assertEqual(jobs.exit_code({"state": "timeout"}), 124)
        self.assertEqual(jobs.exit_code({"state": "cancelled"}), 130)
        self.assertEqual(jobs.exit_code({"state": "infrastructure_lost"}), 125)
        self.assertEqual(jobs.exit_code({"state": "failure", "exit_code": 7}), 7)


if __name__ == "__main__":
    unittest.main()
