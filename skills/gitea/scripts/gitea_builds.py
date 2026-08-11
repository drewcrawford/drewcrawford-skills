#!/usr/bin/env python3
"""
Gitea Build Status Script

This script connects to a Gitea instance and lists recent build jobs
for a specified repository, showing their status and relevant IDs.
"""

import requests
import sys
import re
import time
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from collections import defaultdict


SUCCESS_CONCLUSIONS = {'success', 'neutral', 'skipped'}
WAITING_STATUSES = {'pending', 'queued', 'waiting'}
DEFAULT_RUNNER_TIMEOUT = 300


def load_dotfile(path: Path) -> Dict[str, str]:
    """Load shell-style ``KEY=value`` settings from a dotfile.

    Blank lines and comments are ignored. Values may be wrapped in single or
    double quotes, and an optional ``export`` prefix is accepted. This keeps
    the file format useful when the same settings are also sourced by a shell
    without requiring an additional dependency such as python-dotenv.
    """
    settings = {}

    with path.open(encoding='utf-8') as dotfile:
        for line_number, line in enumerate(dotfile, start=1):
            line = line.strip()
            if not line or line.startswith('#'):
                continue

            if line.startswith('export '):
                line = line[7:].lstrip()

            if '=' not in line:
                raise ValueError(f"{path}:{line_number}: expected KEY=value")

            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip()

            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', key):
                raise ValueError(f"{path}:{line_number}: invalid setting name {key!r}")

            if value.startswith(("'", '"')):
                quote = value[0]
                closing_quote = value.find(quote, 1)
                if closing_quote == -1:
                    raise ValueError(f"{path}:{line_number}: unterminated quoted value")
                trailing = value[closing_quote + 1:].strip()
                if trailing and not trailing.startswith('#'):
                    raise ValueError(f"{path}:{line_number}: unexpected text after quoted value")
                value = value[1:closing_quote]
            elif ' #' in value:
                value = value.split(' #', 1)[0].rstrip()

            settings[key] = value

    return settings


def find_dotfile(explicit_path: Optional[str] = None) -> Optional[Path]:
    """Find the Gitea configuration dotfile, if one is available.

    An explicitly supplied path wins. Otherwise, ``GITEA_CONFIG`` is honored,
    followed by ``.gitea`` in the current directory and then the user's home
    directory.
    """
    configured_path = explicit_path or os.environ.get('GITEA_CONFIG')
    if configured_path:
        return Path(configured_path).expanduser()

    for candidate in (Path.cwd() / '.gitea', Path.home() / '.gitea'):
        if candidate.is_file():
            return candidate

    return None


def extract_config_path(args: List[str]) -> Tuple[Optional[str], List[str]]:
    """Remove the optional ``--config PATH`` argument from CLI arguments."""
    remaining = []
    config_path = None
    i = 0

    while i < len(args):
        if args[i] == '--config':
            if i + 1 >= len(args):
                raise ValueError('--config requires a path')
            config_path = args[i + 1]
            i += 2
        else:
            remaining.append(args[i])
            i += 1

    return config_path, remaining


def parse_cli_args(args: List[str]) -> Dict[str, object]:
    """Parse positional repository names and command options.

    ``args`` excludes the executable name and any ``--config`` option already
    removed by :func:`extract_config_path`.
    """
    if len(args) < 2:
        raise ValueError('owner and repo are required')

    parsed = {
        'owner': args[0],
        'repo': args[1],
        'run_id': None,
        'commit_limit': 10,
        'branch': None,
        'wait': False,
        'download_logs': False,
        'rerun': False,
        'rerun_job_id': None,
        'timeout': 3600,
        'runner_timeout': DEFAULT_RUNNER_TIMEOUT,
    }
    value_options = {
        '--run': ('run_id', int),
        '--commits': ('commit_limit', int),
        '--branch': ('branch', str),
        '--rerun-job': ('rerun_job_id', int),
        '--timeout': ('timeout', int),
        '--runner-timeout': ('runner_timeout', int),
    }
    flag_options = {
        '--wait': 'wait',
        '--download-logs': 'download_logs',
        '--rerun': 'rerun',
    }

    i = 2
    while i < len(args):
        option = args[i]
        if option in value_options:
            if i + 1 >= len(args):
                raise ValueError(f'{option} requires a value')
            key, converter = value_options[option]
            try:
                parsed[key] = converter(args[i + 1])
            except ValueError:
                raise ValueError(f'{option} requires an integer')
            i += 2
        elif option in flag_options:
            parsed[flag_options[option]] = True
            i += 1
        else:
            raise ValueError(f'unknown argument: {option}')

    for key, option in (
        ('run_id', '--run'),
        ('commit_limit', '--commits'),
        ('timeout', '--timeout'),
        ('runner_timeout', '--runner-timeout'),
    ):
        value = parsed[key]
        if value is not None and value < 0:
            raise ValueError(f'{option} must not be negative')

    run_id = parsed['run_id']
    for enabled, option in (
        (parsed['wait'], '--wait'),
        (parsed['download_logs'], '--download-logs'),
        (parsed['rerun'], '--rerun'),
        (parsed['rerun_job_id'] is not None, '--rerun-job'),
    ):
        if enabled and run_id is None:
            raise ValueError(f'{option} requires --run <run_id>')

    return parsed


class GiteaClient:
    def __init__(self, base_url: str, token: str):
        """
        Initialize Gitea client.

        Args:
            base_url: Base URL of Gitea instance (e.g., https://gitea.example.com)
            token: Personal access token for authentication
        """
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.headers = {
            'Authorization': f'token {token}',
            'Content-Type': 'application/json'
        }

    def list_repos(self):
        """List all repositories accessible by the authenticated user."""
        url = f"{self.base_url}/api/v1/user/repos"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_repo_info(self, owner: str, repo: str):
        """
        Get repository information.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            Repository metadata
        """
        url = f"{self.base_url}/api/v1/repos/{owner}/{repo}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def list_commits(self, owner: str, repo: str, limit: int = 10, branch: Optional[str] = None):
        """
        List recent commits for a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            limit: Maximum number of commits to return (default: 10)
            branch: Branch name (optional, defaults to repository default branch)

        Returns:
            List of commits
        """
        url = f"{self.base_url}/api/v1/repos/{owner}/{repo}/commits"
        params = {'limit': limit}
        if branch:
            params['sha'] = branch
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_commit_statuses(self, owner: str, repo: str, sha: str):
        """
        Get statuses for a specific commit.

        Args:
            owner: Repository owner
            repo: Repository name
            sha: Commit SHA

        Returns:
            List of commit statuses (build results)
        """
        url = f"{self.base_url}/api/v1/repos/{owner}/{repo}/statuses/{sha}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_combined_status(self, owner: str, repo: str, ref: str):
        """
        Get combined status for a commit.

        Args:
            owner: Repository owner
            repo: Repository name
            ref: Git reference (branch, tag, or commit SHA)

        Returns:
            Combined status information
        """
        url = f"{self.base_url}/api/v1/repos/{owner}/{repo}/commits/{ref}/status"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_actions_runs(self, owner: str, repo: str) -> List[dict]:
        """
        Get actions runs for a repository.

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            List of workflow runs
        """
        url = f"{self.base_url}/api/v1/repos/{owner}/{repo}/actions/runs"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        return data.get('workflow_runs', [])

    def get_actions_run(self, owner: str, repo: str, run_id: int) -> dict:
        """Get a workflow run by its database ID."""
        url = f"{self.base_url}/api/v1/repos/{owner}/{repo}/actions/runs/{run_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_run_jobs(self, owner: str, repo: str, run_id: int) -> List[dict]:
        """
        Get jobs for a specific workflow run.

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Run ID (database ID, not run_number)

        Returns:
            List of jobs
        """
        url = f"{self.base_url}/api/v1/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        data = response.json()
        return data.get('jobs', [])

    def download_job_logs(self, owner: str, repo: str, job_id: int) -> str:
        """
        Download logs for a specific job.

        Args:
            owner: Repository owner
            repo: Repository name
            job_id: Job ID (database ID, not job index)

        Returns:
            Log content as a string
        """
        url = f"{self.base_url}/api/v1/repos/{owner}/{repo}/actions/jobs/{job_id}/logs"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.text

    def rerun_workflow(self, owner: str, repo: str, run_id: int) -> dict:
        """
        Rerun an entire workflow run.

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Run ID (database ID, not run_number)

        Returns:
            API response as a dictionary
        """
        url = f"{self.base_url}/api/v1/repos/{owner}/{repo}/actions/runs/{run_id}/rerun"
        response = requests.post(url, headers=self.headers)
        response.raise_for_status()
        return response.json() if response.text else {}

    def rerun_job(self, owner: str, repo: str, run_id: int, job_id: int) -> dict:
        """
        Rerun a specific job within a workflow run.

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Run ID (database ID, not run_number)
            job_id: Job ID (database ID, not job index)

        Returns:
            API response as a dictionary
        """
        url = f"{self.base_url}/api/v1/repos/{owner}/{repo}/actions/runs/{run_id}/jobs/{job_id}/rerun"
        response = requests.post(url, headers=self.headers)
        response.raise_for_status()
        return response.json() if response.text else {}


def extract_run_job_from_url(url: str) -> Optional[tuple]:
    """
    Extract run ID and job ID from target URL.

    Args:
        url: Target URL from commit status

    Returns:
        Tuple of (run_id, job_id) or None
    """
    match = re.search(r'/actions/runs/(\d+)/jobs/(\d+)', url)
    if match:
        return (int(match.group(1)), int(match.group(2)))
    return None


def format_status(status: str) -> str:
    """Format status with color indicators."""
    status_map = {
        'success': '✓',
        'failure': '✗',
        'pending': '○',
        'queued': '○',
        'waiting': '○',
        'running': '●',
        'in_progress': '●',
        'cancelled': '⊗',
        'skipped': '−',
        'error': '✗'
    }
    return status_map.get(status.lower(), status)


def format_datetime(dt_str: str) -> str:
    """Format datetime string to readable format."""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return dt_str


def parse_datetime(dt_str: str) -> Optional[datetime]:
    """Parse an API timestamp, treating Gitea's Unix epoch sentinel as absent."""
    if not dt_str or dt_str.startswith('1970-01-01'):
        return None
    try:
        return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
    except (TypeError, ValueError):
        return None


def runner_blocked_jobs(jobs: List[dict], runner_timeout: int,
                        now: Optional[datetime] = None) -> List[Tuple[dict, int]]:
    """Return queued jobs no runner has accepted within the configured grace."""
    now = now or datetime.now(timezone.utc)
    blocked = []
    for job in jobs:
        if job.get('status') not in WAITING_STATUSES or job.get('runner_id'):
            continue
        created_at = parse_datetime(job.get('created_at', ''))
        if created_at is None:
            continue
        age = max(0, int((now - created_at).total_seconds()))
        if age >= runner_timeout:
            blocked.append((job, age))
    return blocked


def group_statuses_by_run(statuses: List[dict]) -> Dict[int, List[dict]]:
    """
    Group statuses by run ID.

    Args:
        statuses: List of commit statuses

    Returns:
        Dictionary mapping run_id to list of job statuses
    """
    runs = defaultdict(list)

    for status in statuses:
        target_url = status.get('target_url', '')
        run_job = extract_run_job_from_url(target_url)

        if run_job:
            run_id, job_id = run_job
            # Only keep the latest status for each job (highest status ID)
            existing = [s for s in runs[run_id] if extract_run_job_from_url(s.get('target_url', ''))[1] == job_id]

            if existing:
                # Replace if this status is newer (higher ID)
                if status['id'] > existing[0]['id']:
                    runs[run_id].remove(existing[0])
                    runs[run_id].append(status)
            else:
                runs[run_id].append(status)

    return runs


def download_run_logs(client: GiteaClient, owner: str, repo: str, run_id: int,
                      output_dir: str = "logs") -> int:
    """
    Download logs for all jobs in a run.

    Args:
        client: GiteaClient instance
        owner: Repository owner
        repo: Repository name
        run_id: Workflow run database ID used in the Actions URL
        output_dir: Base directory for logs (default: "logs")

    Returns:
        Number of logs successfully downloaded
    """
    run_dir = os.path.join(output_dir, f"run_{run_id}")
    os.makedirs(run_dir, exist_ok=True)

    # Get jobs for this run
    jobs = client.get_run_jobs(owner, repo, run_id)

    if not jobs:
        print(f"\nNo jobs found for run ID {run_id}")
        return 0

    success_count = 0
    print(f"\nDownloading logs for run ID {run_id} to {run_dir}/")
    print("-" * 80)

    for job in sorted(jobs, key=lambda j: j['id']):
        job_id = job['id']
        job_name = job.get('name', f'job_{job_id}')

        # Create a safe filename from the job name
        safe_name = re.sub(r'[^\w\-_]', '_', job_name)
        log_file = os.path.join(run_dir, f"{job_id}_{safe_name}.log")

        try:
            print(f"  Downloading job {job_id} ({job_name[:60]})...", end=' ')
            logs = client.download_job_logs(owner, repo, job_id)

            with open(log_file, 'w') as f:
                f.write(logs)

            file_size = len(logs)
            print(f"✓ ({file_size} bytes)")
            success_count += 1

        except requests.exceptions.RequestException as e:
            print(f"✗ Error: {e}")
            if hasattr(e, 'response') and e.response is not None and e.response.status_code == 404:
                print(f"    (Logs may not be available for this job)")

    print(f"\nSuccessfully downloaded {success_count}/{len(jobs)} log files to {run_dir}/")
    return success_count


def print_builds_summary(client: GiteaClient, owner: str, repo: str,
                         commits_data: List[dict], branch: str):
    """Print summary of builds across commits."""
    commit_map = {}

    for commit in commits_data:
        sha = commit['sha']
        message = commit['commit']['message'].split('\n')[0]  # First line only
        commit_map[sha] = {
            'message': message[:50],
            'sha_short': sha[:7],
            'created': commit['created']
        }

    runs = [
        run for run in client.get_actions_runs(owner, repo)
        if run.get('head_sha') in commit_map
        and run.get('head_branch') in (None, branch)
    ]

    print(
        f"\n{'Run ID':<8} {'#':<5} {'SHA':<9} {'Branch':<15} "
        f"{'Status':<12} {'Jobs':<6} {'Commit Message':<40}"
    )
    print("-" * 118)

    for run in sorted(runs, key=lambda item: item['id'], reverse=True):
        run_id = run['id']
        jobs = client.get_run_jobs(owner, repo, run_id)
        commit_info = commit_map[run['head_sha']]
        status = run.get('conclusion') or run.get('status', 'unknown')
        run_number = run.get('run_number', '')
        print(
            f"{run_id:<8} {run_number:<5} {commit_info['sha_short']:<9} {branch:<15} "
            f"{format_status(status)} {status:<10} {len(jobs):<6} {commit_info['message']:<40}"
        )

    if runs:
        print(f"\nTotal runs found: {len(runs)}")
        print(f"\nTo see details for a specific run:")
        print(f"  python {sys.argv[0]} {owner} {repo} --run <run_id>")
    else:
        print("No build runs found.")


def print_run_details(client: GiteaClient, owner: str, repo: str, run_id: int, base_url: str):
    """Print detailed information about a specific run."""
    run = client.get_actions_run(owner, repo, run_id)
    jobs = client.get_run_jobs(owner, repo, run_id)
    run_number = run.get('run_number')
    run_label = f"Run ID {run_id}"
    if run_number is not None:
        run_label += f" (workflow run #{run_number})"

    print(f"\n{run_label} - Commit {run.get('head_sha', '')[:7]}")
    print(f"Title: {run.get('display_title', 'No title')}")
    print(f"Status: {run.get('status', 'unknown')}; conclusion: {run.get('conclusion') or 'none'}")
    print(f"\n{'Job ID':<8} {'Status':<12} {'Job':<50} {'Details'}")
    print("-" * 110)

    for job in sorted(jobs, key=lambda item: item['id']):
        status = job.get('conclusion') or job.get('status', 'unknown')
        details = ''
        if job.get('status') in WAITING_STATUSES and not job.get('runner_id'):
            labels = ', '.join(job.get('labels') or []) or 'unspecified labels'
            details = f"Waiting for runner: {labels}"
        elif job.get('runner_id'):
            details = f"Runner {job['runner_id']}"
        print(
            f"{job['id']:<8} {format_status(status)} {status:<10} "
            f"{job.get('name', '')[:50]:<50} {details}"
        )

    print(f"\nView or download logs:")
    if jobs:
        print(f"  Job view URL: {jobs[0].get('html_url', '')}")
    print(f"  Navigate to: {base_url}/{owner}/{repo}/actions/runs/{run_id}")
    print(f"  Download logs: python {sys.argv[0]} {owner} {repo} --run {run_id} --download-logs")


def rerun_workflow_by_id(client: GiteaClient, owner: str, repo: str, run_id: int,
                         job_id: Optional[int] = None) -> bool:
    """
    Rerun a workflow (or specific job) by run database ID.

    Args:
        client: GiteaClient instance
        owner: Repository owner
        repo: Repository name
        run_id: Workflow run database ID used in the Actions URL
        job_id: Optional job ID to rerun specific job (if None, reruns entire workflow)

    Returns:
        True if rerun was successful, False otherwise
    """
    try:
        if job_id:
            print(f"\nRerunning job {job_id} from run ID {run_id}...")
            client.rerun_job(owner, repo, run_id, job_id)
            print(f"✓ Successfully triggered rerun of job {job_id}")
        else:
            print(f"\nRerunning workflow run ID {run_id}...")
            client.rerun_workflow(owner, repo, run_id)
            print(f"✓ Successfully triggered rerun of workflow run ID {run_id}")

        print(f"\nView progress at: {client.base_url}/{owner}/{repo}/actions/runs/{run_id}")
        return True

    except requests.exceptions.HTTPError as e:
        print(f"\n✗ Error: Failed to rerun workflow")
        if hasattr(e, 'response') and e.response is not None:
            if e.response.status_code == 403:
                print("  Reason: Permission denied. You may not have write access to this repository.")
            elif e.response.status_code == 404:
                print("  Reason: Run not found or rerun API endpoint unavailable.")
                print("  The rerun API requires Gitea 1.26 or newer.")
            else:
                print(f"  Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


def wait_for_run(owner: str, repo: str, run_id: int, base_url: str, timeout: int = 3600,
                 poll_interval: int = 10, runner_timeout: int = DEFAULT_RUNNER_TIMEOUT,
                 client: Optional[GiteaClient] = None) -> int:
    """
    Wait for a run to complete, polling every poll_interval seconds.

    Args:
        owner: Repository owner
        repo: Repository name
        run_id: Run ID to wait for
        base_url: Base URL of Gitea instance
        timeout: Maximum time to wait in seconds (default: 3600)
        poll_interval: Time between polls in seconds (default: 10)
        runner_timeout: Maximum queued time without an assigned runner
        client: Optional client override for tests

    Returns:
        0 if run completes successfully
        1 if run completes with failures
        127 if timeout is reached
    """
    client = client or GiteaClient(base_url, GITEA_TOKEN)
    start_time = time.time()

    print(f"Waiting for run #{run_id} to complete (timeout: {timeout}s, polling every {poll_interval}s)...")

    iteration = 0
    last_status_display = {}

    while True:
        elapsed = time.time() - start_time

        if elapsed > timeout:
            print(f"\n✗ Timeout reached after {int(elapsed)}s")
            return 127

        try:
            run = client.get_actions_run(owner, repo, run_id)
            jobs = client.get_run_jobs(owner, repo, run_id)
            job_statuses = {
                job['id']: (job.get('conclusion') or job.get('status', 'unknown'))
                for job in jobs
            }

            if job_statuses != last_status_display or iteration == 0:
                print(f"\n[{int(elapsed)}s] Run #{run_id} status:")
                for job in sorted(jobs, key=lambda item: item['id']):
                    status = job.get('conclusion') or job.get('status', 'unknown')
                    job_name = job.get('name', f"Job {job['id']}")[:60]
                    print(
                        f"  Job {job['id']}: {format_status(status)} {status:<12} "
                        f"{job_name}"
                    )
                last_status_display = job_statuses.copy()

            if run.get('status') == 'completed':
                conclusion = run.get('conclusion') or 'unknown'
                print(f"\n{'='*80}")
                if conclusion in SUCCESS_CONCLUSIONS:
                    print(f"✓ Run #{run_id} completed with {conclusion} after {int(elapsed)}s")
                    return 0
                print(f"✗ Run #{run_id} completed with {conclusion} after {int(elapsed)}s")
                return 1

            blocked_jobs = runner_blocked_jobs(jobs, runner_timeout)
            if blocked_jobs:
                print(f"\n{'='*80}")
                print(f"✗ Run #{run_id} is blocked: no runner accepted queued jobs")
                for job, age in blocked_jobs:
                    labels = ', '.join(job.get('labels') or []) or 'unspecified'
                    print(f"  Job {job['id']}: waiting {age}s for runner labels: {labels}")
                print(
                    "  Gitea may keep this run queued rather than marking it failed. "
                    "Check that a matching runner is online."
                )
                return 1

        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                print(f"✗ Run #{run_id} not found")
                return 1
            print(f"Warning: Error fetching status: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Warning: Error fetching status: {e}")

        # Wait before next poll
        time.sleep(poll_interval)
        iteration += 1


def main():
    global GITEA_TOKEN

    # Configuration - load the optional dotfile first, then let explicitly
    # exported environment variables take precedence.
    try:
        config_path, args = extract_config_path(sys.argv[1:])
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    dotfile = find_dotfile(config_path)
    if dotfile:
        try:
            for key, value in load_dotfile(dotfile).items():
                os.environ.setdefault(key, value)
        except (OSError, ValueError) as e:
            print(f"Error loading Gitea configuration from {dotfile}: {e}")
            sys.exit(1)

    GITEA_URL = os.environ.get("GITEA_URL")
    GITEA_TOKEN = os.environ.get("GITEA_TOKEN")

    if not GITEA_URL:
        print("Error: GITEA_URL environment variable not set")
        print("Please set it with: export GITEA_URL=https://gitea.example.com")
        print("Or create ~/.gitea with GITEA_URL and GITEA_TOKEN settings")
        sys.exit(1)

    if not GITEA_TOKEN:
        print("Error: GITEA_TOKEN environment variable not set")
        print("Please set it with: export GITEA_TOKEN=your_token_here")
        print("Or create ~/.gitea with GITEA_URL and GITEA_TOKEN settings")
        sys.exit(1)

    # Parse command line arguments
    if len(args) < 2:
        print("Usage: python gitea_builds.py <owner> <repo> [options]")
        print("\nOptions:")
        print("  --config <path>      Load settings from a dotfile")
        print("  --run <run_id>       Use the database ID from the Actions URL")
        print("  --wait               Wait for a run to complete (requires --run)")
        print("  --download-logs      Download logs for all jobs in a run (requires --run)")
        print("  --rerun              Rerun a failed workflow (requires --run)")
        print("  --rerun-job <job_id> Rerun a specific failed job (requires --run)")
        print("  --timeout <seconds>  Timeout for --wait (default: 3600)")
        print("  --runner-timeout <s> Fail if no runner accepts a queued job (default: 300)")
        print("  --commits <limit>    Number of commits to check (default: 10)")
        print("  --branch <branch>    Check specific branch (default: repo default branch)")
        print("\nExamples:")
        print("  python gitea_builds.py myuser myrepo")
        print("  python gitea_builds.py myuser myrepo --run 215")
        print("  python gitea_builds.py myuser myrepo --run 215 --download-logs")
        print("  python gitea_builds.py myuser myrepo --run 215 --wait")
        print("  python gitea_builds.py myuser myrepo --run 215 --wait --timeout 1800")
        print("  python gitea_builds.py myuser myrepo --run 215 --rerun")
        print("  python gitea_builds.py myuser myrepo --run 215 --rerun-job 1006")
        print("  python gitea_builds.py myuser myrepo --commits 20 --branch develop")
        print("\nExit codes (when using --wait):")
        print("  0   - Run completed successfully")
        print("  1   - Run completed with failures")
        print("  127 - Timeout reached")
        print("\nListing your repositories:")
        client = GiteaClient(GITEA_URL, GITEA_TOKEN)
        try:
            repos = client.list_repos()
            for repo in repos[:30]:  # Limit to first 30
                print(f"  - {repo['owner']['login']}/{repo['name']}")
            if len(repos) > 30:
                print(f"  ... and {len(repos) - 30} more")
        except Exception as e:
            print(f"Error listing repositories: {e}")
        sys.exit(1)

    try:
        parsed = parse_cli_args(args)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)

    owner = parsed['owner']
    repo = parsed['repo']
    run_id = parsed['run_id']
    commit_limit = parsed['commit_limit']
    branch = parsed['branch']
    wait = parsed['wait']
    download_logs = parsed['download_logs']
    rerun = parsed['rerun']
    rerun_job_id = parsed['rerun_job_id']
    timeout = parsed['timeout']
    runner_timeout = parsed['runner_timeout']

    # Initialize client
    client = GiteaClient(GITEA_URL, GITEA_TOKEN)

    try:
        # Handle wait mode
        if wait:
            exit_code = wait_for_run(
                owner, repo, run_id, GITEA_URL, timeout=timeout,
                runner_timeout=runner_timeout, client=client,
            )
            sys.exit(exit_code)

        # Handle rerun mode
        if rerun or rerun_job_id:
            success = rerun_workflow_by_id(client, owner, repo, run_id, job_id=rerun_job_id)
            sys.exit(0 if success else 1)

        if run_id:
            print_run_details(client, owner, repo, run_id, GITEA_URL)
            if download_logs:
                downloaded = download_run_logs(client, owner, repo, run_id)
                if not downloaded:
                    sys.exit(1)
            return

        # Get repository info to determine branch
        repo_info = client.get_repo_info(owner, repo)
        if not branch:
            branch = repo_info.get('default_branch', 'main')

        # Fetch commits
        commits = client.list_commits(owner, repo, limit=commit_limit, branch=branch)

        if not commits:
            print(f"No commits found for {owner}/{repo}")
            sys.exit(1)

        print(f"Fetching build status for {owner}/{repo} on branch '{branch}' (checking last {commit_limit} commits)...")
        print_builds_summary(client, owner, repo, commits, branch)

    except requests.exceptions.RequestException as e:
        print(f"\nError: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
