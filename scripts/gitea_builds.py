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
from datetime import datetime
from typing import Optional, Dict, List
from collections import defaultdict


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
        'running': '●',
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


def print_builds_summary(owner: str, repo: str, commits_data: List[dict], base_url: str, branch: str):
    """Print summary of builds across commits."""
    all_runs = {}
    commit_map = {}

    for commit in commits_data:
        sha = commit['sha']
        message = commit['commit']['message'].split('\n')[0]  # First line only
        commit_map[sha] = {
            'message': message[:50],
            'sha_short': sha[:7],
            'created': commit['created']
        }

    print(f"\n{'Run ID':<8} {'SHA':<9} {'Branch':<15} {'Status':<10} {'Jobs':<6} {'Commit Message':<40}")
    print("-" * 110)

    # Collect all runs from all commits
    for commit in commits_data:
        sha = commit['sha']
        client = GiteaClient(base_url, GITEA_TOKEN)
        statuses = client.get_commit_statuses(owner, repo, sha)

        runs = group_statuses_by_run(statuses)

        for run_id, jobs in runs.items():
            if run_id not in all_runs:
                all_runs[run_id] = {
                    'sha': sha,
                    'jobs': jobs,
                    'commit_info': commit_map[sha]
                }

    # Sort by run ID descending (most recent first)
    for run_id in sorted(all_runs.keys(), reverse=True):
        run_data = all_runs[run_id]
        jobs = run_data['jobs']
        commit_info = run_data['commit_info']

        # Determine overall status
        statuses = [j['status'] for j in jobs]
        if 'failure' in statuses or 'error' in statuses:
            overall_status = 'failure'
        elif 'pending' in statuses or 'running' in statuses:
            overall_status = 'running'
        elif all(s == 'success' for s in statuses):
            overall_status = 'success'
        else:
            overall_status = 'mixed'

        status_icon = format_status(overall_status)
        job_count = len(jobs)

        print(f"{run_id:<8} {commit_info['sha_short']:<9} {branch:<15} {status_icon} {overall_status:<8} {job_count:<6} {commit_info['message']:<40}")

    if all_runs:
        print(f"\nTotal runs found: {len(all_runs)}")
        print(f"\nTo see details for a specific run:")
        print(f"  python {sys.argv[0]} {owner} {repo} --run <run_id>")
    else:
        print("No build runs found.")


def print_run_details(owner: str, repo: str, run_id: int, commits_data: List[dict], base_url: str):
    """Print detailed information about a specific run."""
    client = GiteaClient(base_url, GITEA_TOKEN)

    # Find the commit with this run
    found = False
    for commit in commits_data:
        sha = commit['sha']
        statuses = client.get_commit_statuses(owner, repo, sha)

        runs = group_statuses_by_run(statuses)

        if run_id in runs:
            found = True
            jobs = runs[run_id]

            print(f"\nRun #{run_id} - Commit {sha[:7]}")
            print(f"Commit message: {commit['commit']['message'].split(chr(10))[0]}")
            print(f"\n{'Job ID':<8} {'Status':<10} {'Description':<50} {'Duration'}")
            print("-" * 100)

            for job in sorted(jobs, key=lambda j: extract_run_job_from_url(j['target_url'])[1]):
                run_id_val, job_id = extract_run_job_from_url(job['target_url'])
                status = job['status']
                description = job.get('description', 'No description')
                context = job.get('context', '')

                status_icon = format_status(status)
                print(f"{job_id:<8} {status_icon} {status:<8} {context:<50} {description}")

            print(f"\nView logs for jobs:")
            print(f"  Job view URL: {base_url}{jobs[0]['target_url']}")
            print(f"  Or navigate to: {base_url}/{owner}/{repo}/actions/runs/{run_id}")
            break

    if not found:
        print(f"Run #{run_id} not found in recent commits. Try fetching more commits.")


def wait_for_run(owner: str, repo: str, run_id: int, base_url: str, timeout: int = 3600,
                 poll_interval: int = 10, max_commits: int = 50) -> int:
    """
    Wait for a run to complete, polling every poll_interval seconds.

    Args:
        owner: Repository owner
        repo: Repository name
        run_id: Run ID to wait for
        base_url: Base URL of Gitea instance
        timeout: Maximum time to wait in seconds (default: 3600)
        poll_interval: Time between polls in seconds (default: 10)
        max_commits: Maximum number of commits to check (default: 50)

    Returns:
        0 if run completes successfully
        1 if run completes with failures
        127 if timeout is reached
    """
    client = GiteaClient(base_url, GITEA_TOKEN)
    start_time = time.time()

    print(f"Waiting for run #{run_id} to complete (timeout: {timeout}s, polling every {poll_interval}s)...")

    iteration = 0
    last_status_display = {}

    while True:
        elapsed = time.time() - start_time

        if elapsed > timeout:
            print(f"\n✗ Timeout reached after {int(elapsed)}s")
            return 127

        # Fetch recent commits to find the run
        try:
            commits = client.list_commits(owner, repo, limit=max_commits)

            found = False
            for commit in commits:
                sha = commit['sha']
                statuses = client.get_commit_statuses(owner, repo, sha)
                runs = group_statuses_by_run(statuses)

                if run_id in runs:
                    found = True
                    jobs = runs[run_id]

                    # Check job statuses
                    job_statuses = {}
                    all_completed = True
                    has_failure = False

                    for job in jobs:
                        run_id_val, job_id = extract_run_job_from_url(job['target_url'])
                        status = job['status']
                        job_statuses[job_id] = status

                        if status in ['pending', 'running']:
                            all_completed = False
                        elif status in ['failure', 'error']:
                            has_failure = True

                    # Display status update if changed
                    if job_statuses != last_status_display or iteration == 0:
                        print(f"\n[{int(elapsed)}s] Run #{run_id} status:")
                        for job_id in sorted(job_statuses.keys()):
                            status = job_statuses[job_id]
                            status_icon = format_status(status)
                            # Find job context for display
                            job_info = next((j for j in jobs if extract_run_job_from_url(j['target_url'])[1] == job_id), None)
                            context = job_info.get('context', f'Job {job_id}') if job_info else f'Job {job_id}'
                            context = context[:60]  # Truncate long contexts
                            print(f"  Job {job_id}: {status_icon} {status:<10} {context}")
                        last_status_display = job_statuses.copy()

                    # Check if all jobs are completed
                    if all_completed:
                        print(f"\n{'='*80}")
                        if has_failure:
                            print(f"✗ Run #{run_id} completed with failures after {int(elapsed)}s")
                            return 1
                        else:
                            print(f"✓ Run #{run_id} completed successfully after {int(elapsed)}s")
                            return 0

                    break

            if not found:
                print(f"✗ Run #{run_id} not found in last {max_commits} commits")
                return 1

        except requests.exceptions.RequestException as e:
            print(f"Warning: Error fetching status: {e}")

        # Wait before next poll
        time.sleep(poll_interval)
        iteration += 1


def main():
    global GITEA_TOKEN

    # Configuration
    GITEA_URL = "http://gitea.mermaid-gecko.ts.net:3000"
    GITEA_TOKEN = "cb1fcb0b640a6822a430d7792d5978689ac8d2ab"

    # Parse command line arguments
    if len(sys.argv) < 3:
        print("Usage: python gitea_builds.py <owner> <repo> [options]")
        print("\nOptions:")
        print("  --run <run_id>       Show details for a specific run")
        print("  --wait               Wait for a run to complete (requires --run)")
        print("  --timeout <seconds>  Timeout for --wait (default: 3600)")
        print("  --commits <limit>    Number of commits to check (default: 10)")
        print("  --branch <branch>    Check specific branch (default: repo default branch)")
        print("\nExamples:")
        print("  python gitea_builds.py myuser myrepo")
        print("  python gitea_builds.py myuser myrepo --run 215")
        print("  python gitea_builds.py myuser myrepo --run 215 --wait")
        print("  python gitea_builds.py myuser myrepo --run 215 --wait --timeout 1800")
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

    owner = sys.argv[1]
    repo = sys.argv[2]

    # Parse optional arguments
    run_id = None
    commit_limit = 10
    branch = None
    wait = False
    timeout = 3600

    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == '--run' and i + 1 < len(sys.argv):
            run_id = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--commits' and i + 1 < len(sys.argv):
            commit_limit = int(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == '--branch' and i + 1 < len(sys.argv):
            branch = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == '--wait':
            wait = True
            i += 1
        elif sys.argv[i] == '--timeout' and i + 1 < len(sys.argv):
            timeout = int(sys.argv[i + 1])
            i += 2
        else:
            i += 1

    # Validate arguments
    if wait and not run_id:
        print("Error: --wait requires --run <run_id>")
        sys.exit(1)

    # Initialize client
    client = GiteaClient(GITEA_URL, GITEA_TOKEN)

    try:
        # Handle wait mode
        if wait:
            exit_code = wait_for_run(owner, repo, run_id, GITEA_URL, timeout=timeout)
            sys.exit(exit_code)

        # Get repository info to determine branch
        repo_info = client.get_repo_info(owner, repo)
        if not branch:
            branch = repo_info.get('default_branch', 'main')

        # Fetch commits
        commits = client.list_commits(owner, repo, limit=commit_limit, branch=branch)

        if not commits:
            print(f"No commits found for {owner}/{repo}")
            sys.exit(1)

        if run_id:
            print_run_details(owner, repo, run_id, commits, GITEA_URL)
        else:
            print(f"Fetching build status for {owner}/{repo} on branch '{branch}' (checking last {commit_limit} commits)...")
            print_builds_summary(owner, repo, commits, GITEA_URL, branch)

    except requests.exceptions.RequestException as e:
        print(f"\nError: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Response: {e.response.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
