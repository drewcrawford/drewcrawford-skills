import os
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from gitea_builds import (
    download_run_logs,
    extract_config_path,
    load_dotfile,
    parse_cli_args,
    print_builds_summary,
    rerun_workflow_by_id,
    runner_blocked_jobs,
    wait_for_run,
)


class DotfileTests(unittest.TestCase):
    def test_loads_comments_exports_and_quoted_values(self):
        with tempfile.NamedTemporaryFile('w', delete=False) as dotfile:
            dotfile.write(
                '# Gitea settings\n'
                'export GITEA_URL="https://gitea.example.com" # instance\n'
                'GITEA_TOKEN=secret-token\n'
            )
            path = Path(dotfile.name)

        try:
            self.assertEqual(
                load_dotfile(path),
                {
                    'GITEA_URL': 'https://gitea.example.com',
                    'GITEA_TOKEN': 'secret-token',
                },
            )
        finally:
            path.unlink()

    def test_extracts_config_without_changing_other_arguments(self):
        config, args = extract_config_path(
            ['owner', 'repo', '--config', '~/.config/gitea', '--run', '42']
        )
        self.assertEqual(config, '~/.config/gitea')
        self.assertEqual(args, ['owner', 'repo', '--run', '42'])

    def test_environment_values_can_override_dotfile_values(self):
        settings = {
            'GITEA_URL': 'https://from-file.example.com',
            'GITEA_TOKEN': 'from-file',
        }
        old_url = os.environ.get('GITEA_URL')
        old_token = os.environ.get('GITEA_TOKEN')
        try:
            os.environ['GITEA_URL'] = 'https://from-environment.example.com'
            for key, value in settings.items():
                os.environ.setdefault(key, value)
            self.assertEqual(os.environ['GITEA_URL'], 'https://from-environment.example.com')
            self.assertEqual(os.environ['GITEA_TOKEN'], 'from-file')
        finally:
            if old_url is None:
                os.environ.pop('GITEA_URL', None)
            else:
                os.environ['GITEA_URL'] = old_url
            if old_token is None:
                os.environ.pop('GITEA_TOKEN', None)
            else:
                os.environ['GITEA_TOKEN'] = old_token


class CommandLineTests(unittest.TestCase):
    def test_parses_first_option_after_repository(self):
        parsed = parse_cli_args(
            ['Metropolis', 'continue', '--run', '1304', '--wait', '--timeout', '3600']
        )
        self.assertEqual(parsed['run_id'], 1304)
        self.assertTrue(parsed['wait'])
        self.assertEqual(parsed['timeout'], 3600)

    def test_parses_branch_and_commit_limit_in_documented_order(self):
        parsed = parse_cli_args(
            ['Metropolis', 'continue', '--branch', 'develop', '--commits', '20']
        )
        self.assertEqual(parsed['branch'], 'develop')
        self.assertEqual(parsed['commit_limit'], 20)

    def test_rejects_unknown_arguments_instead_of_silently_skipping_them(self):
        with self.assertRaisesRegex(ValueError, 'unknown argument'):
            parse_cli_args(['owner', 'repo', '--wat'])

    def test_wait_requires_run_id(self):
        with self.assertRaisesRegex(ValueError, '--wait requires --run'):
            parse_cli_args(['owner', 'repo', '--wait'])


class FakeClient:
    def __init__(self, run=None, runs=None, jobs=None):
        self.base_url = 'https://gitea.example.com'
        self.run = run or {}
        self.runs = runs or []
        self.jobs = jobs or []
        self.calls = []

    def get_actions_runs(self, owner, repo):
        self.calls.append(('get_actions_runs', owner, repo))
        return self.runs

    def get_actions_run(self, owner, repo, run_id):
        self.calls.append(('get_actions_run', owner, repo, run_id))
        return self.run

    def get_run_jobs(self, owner, repo, run_id):
        self.calls.append(('get_run_jobs', owner, repo, run_id))
        return self.jobs

    def download_job_logs(self, owner, repo, job_id):
        self.calls.append(('download_job_logs', owner, repo, job_id))
        return 'test log\n'

    def rerun_workflow(self, owner, repo, run_id):
        self.calls.append(('rerun_workflow', owner, repo, run_id))
        return {}

    def rerun_job(self, owner, repo, run_id, job_id):
        self.calls.append(('rerun_job', owner, repo, run_id, job_id))
        return {}


class ActionsApiTests(unittest.TestCase):
    def test_summary_displays_database_id_and_ui_run_number(self):
        sha = 'd1aaa30f00000000000000000000000000000000'
        client = FakeClient(
            runs=[{
                'id': 1147,
                'run_number': 9,
                'head_sha': sha,
                'head_branch': None,
                'status': 'completed',
                'conclusion': 'success',
            }],
            jobs=[{'id': 2337}, {'id': 2338}],
        )
        commits = [{
            'sha': sha,
            'created': '2025-12-20T23:48:01Z',
            'commit': {'message': 'bump version'},
        }]
        output = StringIO()
        with redirect_stdout(output):
            print_builds_summary(client, 'Metropolis', 'continue', commits, 'main')
        self.assertIn('1147', output.getvalue())
        self.assertIn('9', output.getvalue())
        self.assertIn(('get_run_jobs', 'Metropolis', 'continue', 1147), client.calls)

    def test_identifies_old_queued_job_without_runner(self):
        jobs = [{
            'id': 2637,
            'status': 'queued',
            'runner_id': 0,
            'labels': ['ubuntu-latest'],
            'created_at': '2020-01-01T00:00:00Z',
        }]
        blocked = runner_blocked_jobs(jobs, runner_timeout=300)
        self.assertEqual([job['id'] for job, _age in blocked], [2637])

    def test_wait_reports_runner_block_and_fails(self):
        client = FakeClient(
            run={'id': 1304, 'status': 'queued', 'conclusion': None},
            jobs=[{
                'id': 2637,
                'name': 'Build native',
                'status': 'queued',
                'conclusion': None,
                'runner_id': 0,
                'labels': ['ubuntu-latest'],
                'created_at': '2020-01-01T00:00:00Z',
            }],
        )
        output = StringIO()
        with redirect_stdout(output):
            result = wait_for_run(
                'Metropolis', 'continue', 1304, client.base_url,
                runner_timeout=300, client=client,
            )
        self.assertEqual(result, 1)
        self.assertIn('no runner accepted queued jobs', output.getvalue())
        self.assertIn('ubuntu-latest', output.getvalue())

    def test_wait_uses_run_conclusion(self):
        client = FakeClient(
            run={'id': 1147, 'status': 'completed', 'conclusion': 'success'},
            jobs=[{
                'id': 2337,
                'name': 'Build',
                'status': 'completed',
                'conclusion': 'success',
            }],
        )
        with redirect_stdout(StringIO()):
            result = wait_for_run('Metropolis', 'continue', 1147, client.base_url, client=client)
        self.assertEqual(result, 0)

    def test_download_logs_uses_database_run_id_directly(self):
        client = FakeClient(jobs=[{'id': 2637, 'name': 'Build native'}])
        with tempfile.TemporaryDirectory() as output_dir, redirect_stdout(StringIO()):
            count = download_run_logs(
                client, 'Metropolis', 'continue', 1304, output_dir=output_dir
            )
            log_path = Path(output_dir) / 'run_1304' / '2637_Build_native.log'
            self.assertEqual(log_path.read_text(), 'test log\n')
        self.assertEqual(count, 1)
        self.assertIn(('get_run_jobs', 'Metropolis', 'continue', 1304), client.calls)

    def test_rerun_uses_database_run_id_directly(self):
        client = FakeClient()
        with redirect_stdout(StringIO()):
            success = rerun_workflow_by_id(client, 'Metropolis', 'continue', 1304)
        self.assertTrue(success)
        self.assertIn(('rerun_workflow', 'Metropolis', 'continue', 1304), client.calls)


if __name__ == '__main__':
    unittest.main()
