#!/usr/bin/env python3
"""
GitHub Actions Build Status Script

This script connects to GitHub and lists recent workflow runs
for a specified repository, showing their status and relevant IDs.
"""

import requests
import sys
import re
import time
import os
import zipfile
import io
from datetime import datetime
from typing import Optional, List


class GitHubClient:
    def __init__(self, token: str):
        """
        Initialize GitHub client.

        Args:
            token: Personal access token for authentication
        """
        self.base_url = "https://api.github.com"
        self.token = token
        self.headers = {
            'Authorization': f'Bearer {token}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28'
        }

    def list_repos(self):
        """List all repositories accessible by the authenticated user."""
        url = f"{self.base_url}/user/repos"
        response = requests.get(url, headers=self.headers, params={'per_page': 100})
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
        url = f"{self.base_url}/repos/{owner}/{repo}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def get_topics(self, owner: str, repo: str) -> List[str]:
        """
        Get repository topics (tags).

        Args:
            owner: Repository owner
            repo: Repository name

        Returns:
            List of topic names
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/topics"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json().get('names', [])

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
        url = f"{self.base_url}/repos/{owner}/{repo}/commits"
        params = {'per_page': limit}
        if branch:
            params['sha'] = branch
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_actions_runs(self, owner: str, repo: str, per_page: int = 30) -> List[dict]:
        """
        Get workflow runs for a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            per_page: Number of results per page (default: 30)

        Returns:
            List of workflow runs
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/actions/runs"
        response = requests.get(url, headers=self.headers, params={'per_page': per_page})
        response.raise_for_status()
        data = response.json()
        return data.get('workflow_runs', [])

    def get_run_jobs(self, owner: str, repo: str, run_id: int) -> List[dict]:
        """
        Get jobs for a specific workflow run.

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Run ID

        Returns:
            List of jobs
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/actions/runs/{run_id}/jobs"
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
            job_id: Job ID

        Returns:
            Log content as a string
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/actions/jobs/{job_id}/logs"
        response = requests.get(url, headers=self.headers, allow_redirects=True)
        response.raise_for_status()
        return response.text

    def download_run_logs_zip(self, owner: str, repo: str, run_id: int) -> bytes:
        """
        Download all logs for a workflow run as a zip file.

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Run ID

        Returns:
            Zip file content as bytes
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/actions/runs/{run_id}/logs"
        response = requests.get(url, headers=self.headers, allow_redirects=True)
        response.raise_for_status()
        return response.content

    def rerun_workflow(self, owner: str, repo: str, run_id: int) -> dict:
        """
        Rerun an entire workflow run.

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Run ID

        Returns:
            API response as a dictionary
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/actions/runs/{run_id}/rerun"
        response = requests.post(url, headers=self.headers)
        response.raise_for_status()
        return response.json() if response.text else {}

    def rerun_failed_jobs(self, owner: str, repo: str, run_id: int) -> dict:
        """
        Rerun only failed jobs in a workflow run.

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Run ID

        Returns:
            API response as a dictionary
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/actions/runs/{run_id}/rerun-failed-jobs"
        response = requests.post(url, headers=self.headers)
        response.raise_for_status()
        return response.json() if response.text else {}

    def cancel_workflow(self, owner: str, repo: str, run_id: int) -> dict:
        """
        Cancel a workflow run.

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Run ID

        Returns:
            API response as a dictionary
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/actions/runs/{run_id}/cancel"
        response = requests.post(url, headers=self.headers)
        response.raise_for_status()
        return response.json() if response.text else {}


def format_status(status: str, conclusion: Optional[str] = None) -> str:
    """Format status with indicators."""
    if status == 'completed':
        conclusion_map = {
            'success': '✓',
            'failure': '✗',
            'cancelled': '⊗',
            'skipped': '−',
            'timed_out': '⏱',
            'action_required': '!',
            'neutral': '○',
        }
        return conclusion_map.get(conclusion, '?')

    status_map = {
        'queued': '○',
        'in_progress': '●',
        'waiting': '◐',
        'pending': '○',
    }
    return status_map.get(status, status)


def format_datetime(dt_str: str) -> str:
    """Format datetime string to readable format."""
    try:
        dt = datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return dt_str


def format_duration(start_str: str, end_str: Optional[str]) -> str:
    """Calculate and format duration between two timestamps."""
    try:
        start = datetime.fromisoformat(start_str.replace('Z', '+00:00'))
        if end_str:
            end = datetime.fromisoformat(end_str.replace('Z', '+00:00'))
        else:
            end = datetime.now(start.tzinfo)

        duration = end - start
        seconds = int(duration.total_seconds())

        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            return f"{seconds // 60}m {seconds % 60}s"
        else:
            return f"{seconds // 3600}h {(seconds % 3600) // 60}m"
    except:
        return "N/A"


def download_run_logs(client: GitHubClient, owner: str, repo: str, run_id: int,
                      output_dir: str = "logs") -> int:
    """
    Download logs for all jobs in a run.

    Args:
        client: GitHubClient instance
        owner: Repository owner
        repo: Repository name
        run_id: Run ID
        output_dir: Base directory for logs (default: "logs")

    Returns:
        Number of logs successfully downloaded
    """
    run_dir = os.path.join(output_dir, f"run_{run_id}")
    os.makedirs(run_dir, exist_ok=True)

    print(f"\nDownloading logs for run #{run_id} to {run_dir}/")
    print("-" * 80)

    try:
        # Try to download the zip file containing all logs
        print("  Downloading run logs archive...", end=' ')
        zip_content = client.download_run_logs_zip(owner, repo, run_id)

        # Extract the zip file
        with zipfile.ZipFile(io.BytesIO(zip_content)) as zf:
            zf.extractall(run_dir)
            file_count = len(zf.namelist())
            print(f"✓ ({file_count} files)")

        print(f"\nSuccessfully downloaded logs to {run_dir}/")
        return file_count

    except requests.exceptions.RequestException as e:
        print(f"✗ Error downloading logs archive: {e}")

        # Fallback: try to download individual job logs
        print("\nFalling back to individual job log downloads...")
        jobs = client.get_run_jobs(owner, repo, run_id)

        if not jobs:
            print(f"No jobs found for run #{run_id}")
            return 0

        success_count = 0
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

        print(f"\nSuccessfully downloaded {success_count}/{len(jobs)} log files to {run_dir}/")
        return success_count


def print_topics(client: GitHubClient, owner: str, repo: str):
    """Print repository topics (tags)."""
    topics = client.get_topics(owner, repo)

    if not topics:
        print(f"No topics found for {owner}/{repo}")
        return

    print(f"\nTopics for {owner}/{repo}:")
    print("-" * 40)
    for topic in topics:
        print(f"  {topic}")
    print(f"\nTotal: {len(topics)} topics")


def print_builds_summary(client: GitHubClient, owner: str, repo: str, branch: Optional[str] = None):
    """Print summary of workflow runs."""
    runs = client.get_actions_runs(owner, repo)

    if not runs:
        print("No workflow runs found.")
        return

    # Filter by branch if specified
    if branch:
        runs = [r for r in runs if r.get('head_branch') == branch]

    print(f"\n{'Run ID':<12} {'#':<6} {'SHA':<9} {'Branch':<20} {'Status':<12} {'Jobs':<6} {'Duration':<10} {'Event':<12}")
    print("-" * 110)

    for run in runs[:20]:  # Show last 20 runs
        run_id = run['id']
        run_number = run['run_number']
        sha = run['head_sha'][:7]
        head_branch = run['head_branch'][:18]
        status = run['status']
        conclusion = run.get('conclusion', '')
        event = run['event']

        # Get job count
        try:
            jobs = client.get_run_jobs(owner, repo, run_id)
            job_count = len(jobs)
        except:
            job_count = '?'

        # Calculate duration
        started_at = run.get('run_started_at', run['created_at'])
        completed_at = run.get('updated_at') if status == 'completed' else None
        duration = format_duration(started_at, completed_at)

        status_icon = format_status(status, conclusion)
        display_status = conclusion if status == 'completed' else status

        print(f"{run_id:<12} #{run_number:<5} {sha:<9} {head_branch:<20} {status_icon} {display_status:<10} {job_count:<6} {duration:<10} {event:<12}")

    print(f"\nTotal runs shown: {min(len(runs), 20)}")
    print(f"\nTo see details for a specific run:")
    print(f"  python {sys.argv[0]} {owner} {repo} --run <run_id>")


def print_run_details(client: GitHubClient, owner: str, repo: str, run_id: int):
    """Print detailed information about a specific run."""
    # Get run info
    runs = client.get_actions_runs(owner, repo)
    run = next((r for r in runs if r['id'] == run_id), None)

    if not run:
        # Try to get the run directly
        try:
            url = f"{client.base_url}/repos/{owner}/{repo}/actions/runs/{run_id}"
            response = requests.get(url, headers=client.headers)
            response.raise_for_status()
            run = response.json()
        except:
            print(f"Run #{run_id} not found")
            return

    # Get jobs for this run
    jobs = client.get_run_jobs(owner, repo, run_id)

    print(f"\nRun #{run_id} (run number: #{run['run_number']})")
    print(f"Workflow: {run['name']}")
    print(f"Branch: {run['head_branch']}")
    print(f"Commit: {run['head_sha'][:7]} - {run['head_commit']['message'].split(chr(10))[0]}")
    print(f"Event: {run['event']}")
    print(f"Status: {run['status']} ({run.get('conclusion', 'N/A')})")

    started_at = run.get('run_started_at', run['created_at'])
    completed_at = run.get('updated_at') if run['status'] == 'completed' else None
    print(f"Duration: {format_duration(started_at, completed_at)}")

    print(f"\n{'Job ID':<12} {'Status':<12} {'Duration':<10} {'Name'}")
    print("-" * 80)

    for job in sorted(jobs, key=lambda j: j['id']):
        job_id = job['id']
        job_name = job.get('name', 'Unknown')
        status = job['status']
        conclusion = job.get('conclusion', '')

        # Calculate job duration
        started_at = job.get('started_at')
        completed_at = job.get('completed_at')
        if started_at:
            duration = format_duration(started_at, completed_at)
        else:
            duration = 'N/A'

        status_icon = format_status(status, conclusion)
        display_status = conclusion if status == 'completed' else status

        print(f"{job_id:<12} {status_icon} {display_status:<10} {duration:<10} {job_name}")

    print(f"\nView run: https://github.com/{owner}/{repo}/actions/runs/{run_id}")
    print(f"Download logs: python {sys.argv[0]} {owner} {repo} --run {run_id} --download-logs")


def rerun_workflow_run(client: GitHubClient, owner: str, repo: str, run_id: int,
                       failed_only: bool = False) -> bool:
    """
    Rerun a workflow run.

    Args:
        client: GitHubClient instance
        owner: Repository owner
        repo: Repository name
        run_id: Run ID
        failed_only: If True, only rerun failed jobs

    Returns:
        True if rerun was successful, False otherwise
    """
    try:
        if failed_only:
            print(f"\nRerunning failed jobs from run #{run_id}...")
            client.rerun_failed_jobs(owner, repo, run_id)
            print(f"✓ Successfully triggered rerun of failed jobs")
        else:
            print(f"\nRerunning workflow run #{run_id}...")
            client.rerun_workflow(owner, repo, run_id)
            print(f"✓ Successfully triggered rerun of workflow run #{run_id}")

        print(f"\nView progress at: https://github.com/{owner}/{repo}/actions/runs/{run_id}")
        return True

    except requests.exceptions.HTTPError as e:
        print(f"\n✗ Error: Failed to rerun workflow")
        if hasattr(e, 'response') and e.response is not None:
            if e.response.status_code == 403:
                print("  Reason: Permission denied. Check your token permissions.")
            elif e.response.status_code == 422:
                print("  Reason: Cannot rerun this workflow. It may still be running or not eligible for rerun.")
            else:
                print(f"  Response: {e.response.text}")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        return False


def wait_for_run(client: GitHubClient, owner: str, repo: str, run_id: int,
                 timeout: int = 3600, poll_interval: int = 10) -> int:
    """
    Wait for a run to complete, polling every poll_interval seconds.

    Args:
        client: GitHubClient instance
        owner: Repository owner
        repo: Repository name
        run_id: Run ID to wait for
        timeout: Maximum time to wait in seconds (default: 3600)
        poll_interval: Time between polls in seconds (default: 10)

    Returns:
        0 if run completes successfully
        1 if run completes with failures
        127 if timeout is reached
    """
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
            # Get run status
            url = f"{client.base_url}/repos/{owner}/{repo}/actions/runs/{run_id}"
            response = requests.get(url, headers=client.headers)
            response.raise_for_status()
            run = response.json()

            # Get jobs for this run
            jobs = client.get_run_jobs(owner, repo, run_id)

            # Check job statuses
            job_statuses = {}
            all_completed = run['status'] == 'completed'

            for job in jobs:
                job_id = job['id']
                status = job['status']
                conclusion = job.get('conclusion', '')
                job_statuses[job_id] = (status, conclusion)

            # Display status update if changed
            if job_statuses != last_status_display or iteration == 0:
                print(f"\n[{int(elapsed)}s] Run #{run_id} status: {run['status']}")
                for job_id in sorted(job_statuses.keys()):
                    status, conclusion = job_statuses[job_id]
                    status_icon = format_status(status, conclusion)
                    # Find job name for display
                    job_info = next((j for j in jobs if j['id'] == job_id), None)
                    job_name = job_info.get('name', f'Job {job_id}') if job_info else f'Job {job_id}'
                    job_name = job_name[:60]  # Truncate long names
                    display_status = conclusion if status == 'completed' else status
                    print(f"  Job {job_id}: {status_icon} {display_status:<12} {job_name}")
                last_status_display = job_statuses.copy()

            # Check if run is completed
            if all_completed:
                print(f"\n{'='*80}")
                conclusion = run.get('conclusion', '')
                if conclusion in ['failure', 'timed_out', 'cancelled']:
                    print(f"✗ Run #{run_id} completed with {conclusion} after {int(elapsed)}s")
                    return 1
                else:
                    print(f"✓ Run #{run_id} completed successfully after {int(elapsed)}s")
                    return 0

        except requests.exceptions.RequestException as e:
            print(f"Warning: Error fetching status: {e}")

        # Wait before next poll
        time.sleep(poll_interval)
        iteration += 1


def main():
    # Configuration - get token from environment
    GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")

    if not GITHUB_TOKEN:
        print("Error: GITHUB_TOKEN environment variable not set")
        print("Please set it with: export GITHUB_TOKEN=your_token_here")
        sys.exit(1)

    # Parse command line arguments
    if len(sys.argv) < 3:
        print("Usage: python github_builds.py <owner> <repo> [options]")
        print("\nOptions:")
        print("  --run <run_id>       Show details for a specific run")
        print("  --wait               Wait for a run to complete (requires --run)")
        print("  --download-logs      Download logs for all jobs in a run (requires --run)")
        print("  --rerun              Rerun a workflow (requires --run)")
        print("  --rerun-failed       Rerun only failed jobs (requires --run)")
        print("  --timeout <seconds>  Timeout for --wait (default: 3600)")
        print("  --branch <branch>    Filter by specific branch")
        print("  --topics             Show repository topics (tags)")
        print("\nExamples:")
        print("  python github_builds.py drewcrawford wasm_safe_mutex")
        print("  python github_builds.py drewcrawford wasm_safe_mutex --run 19609289127")
        print("  python github_builds.py drewcrawford wasm_safe_mutex --run 19609289127 --download-logs")
        print("  python github_builds.py drewcrawford wasm_safe_mutex --run 19609289127 --wait")
        print("  python github_builds.py drewcrawford wasm_safe_mutex --run 19609289127 --rerun")
        print("  python github_builds.py drewcrawford wasm_safe_mutex --run 19609289127 --rerun-failed")
        print("  python github_builds.py drewcrawford wasm_safe_mutex --branch main")
        print("  python github_builds.py drewcrawford wasm_safe_mutex --topics")
        print("\nExit codes (when using --wait):")
        print("  0   - Run completed successfully")
        print("  1   - Run completed with failures")
        print("  127 - Timeout reached")
        print("\nEnvironment variables:")
        print("  GITHUB_TOKEN - Required. Your GitHub personal access token")
        print("\nListing your repositories:")
        client = GitHubClient(GITHUB_TOKEN)
        try:
            repos = client.list_repos()
            for repo in repos[:30]:  # Limit to first 30
                print(f"  - {repo['owner']['login']}/{repo['name']}")
            if len(repos) > 30:
                print(f"  ... and {len(repos) - 30} more")
        except Exception as e:
            print(f"Error listing repositories: {e}")
        sys.exit(1)

    owner = sys.argv[1]
    repo = sys.argv[2]

    # Parse optional arguments
    run_id = None
    branch = None
    wait = False
    download_logs = False
    rerun = False
    rerun_failed = False
    timeout = 3600
    topics = False

    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == '--run' and i + 1 < len(sys.argv):
            run_id = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--branch' and i + 1 < len(sys.argv):
            branch = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--wait':
            wait = True
            i += 1
        elif sys.argv[i] == '--download-logs':
            download_logs = True
            i += 1
        elif sys.argv[i] == '--rerun':
            rerun = True
            i += 1
        elif sys.argv[i] == '--rerun-failed':
            rerun_failed = True
            i += 1
        elif sys.argv[i] == '--timeout' and i + 1 < len(sys.argv):
            timeout = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--topics':
            topics = True
            i += 1
        else:
            i += 1

    # Validate arguments
    if wait and not run_id:
        print("Error: --wait requires --run <run_id>")
        sys.exit(1)

    if download_logs and not run_id:
        print("Error: --download-logs requires --run <run_id>")
        sys.exit(1)

    if rerun and not run_id:
        print("Error: --rerun requires --run <run_id>")
        sys.exit(1)

    if rerun_failed and not run_id:
        print("Error: --rerun-failed requires --run <run_id>")
        sys.exit(1)

    # Initialize client
    client = GitHubClient(GITHUB_TOKEN)

    try:
        # Handle topics mode
        if topics:
            print_topics(client, owner, repo)
            sys.exit(0)

        # Handle wait mode
        if wait:
            exit_code = wait_for_run(client, owner, repo, run_id, timeout=timeout)
            sys.exit(exit_code)

        # Handle rerun mode
        if rerun or rerun_failed:
            success = rerun_workflow_run(client, owner, repo, run_id, failed_only=rerun_failed)
            sys.exit(0 if success else 1)

        if run_id:
            print_run_details(client, owner, repo, run_id)

            # Handle log download if requested
            if download_logs:
                download_run_logs(client, owner, repo, run_id)
        else:
            print(f"Fetching workflow runs for {owner}/{repo}...")
            print_builds_summary(client, owner, repo, branch)

    except requests.exceptions.RequestException as e:
        print(f"\nError: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
