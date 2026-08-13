# Gitea Build Monitor - API Reference

Complete technical documentation for the Gitea Build Monitor script.

## Table of Contents

- [Command Line Interface](#command-line-interface)
- [Exit Codes](#exit-codes)
- [API Endpoints](#api-endpoints)
- [Configuration](#configuration)
- [Output Formats](#output-formats)
- [Technical Details](#technical-details)

---

## Command Line Interface

### Basic Syntax

```bash
scripts/gitea_builds.py <owner> <repo> [options]
```

### Required Arguments

- `<owner>` - Repository owner/organization name
- `<repo>` - Repository name

### Optional Arguments

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--run <run_id>` | integer | - | Database ID from `/actions/runs/<run_id>` |
| `--download-logs` | flag | false | Download logs for all jobs in run (requires --run) |
| `--wait` | flag | false | Wait for run to complete (requires --run) |
| `--rerun` | flag | false | Rerun entire workflow (requires --run) |
| `--rerun-job <job_id>` | integer | - | Rerun specific job (requires --run) |
| `--timeout <seconds>` | integer | 3600 | Timeout for --wait in seconds |
| `--runner-timeout <seconds>` | integer | 300 | Fail if a queued job remains unassigned this long |
| `--commits <limit>` | integer | 10 | Number of commits to check |
| `--branch <branch>` | string | default | Branch name to check |

### Examples

```bash
# List builds (default: last 10 commits, default branch)
scripts/gitea_builds.py myorg myrepo

# View specific run
scripts/gitea_builds.py myorg myrepo --run 215

# Download logs for a run
scripts/gitea_builds.py myorg myrepo --run 215 --download-logs

# Wait for run with custom timeout
scripts/gitea_builds.py myorg myrepo --run 215 --wait --timeout 1800

# Rerun failed workflow
scripts/gitea_builds.py myorg myrepo --run 215 --rerun

# Rerun specific failed job
scripts/gitea_builds.py myorg myrepo --run 215 --rerun-job 1006

# Check specific branch with more commits
scripts/gitea_builds.py myorg myrepo --branch develop --commits 20

# Combined options
scripts/gitea_builds.py myorg myrepo --branch main --commits 50
```

---

## Exit Codes

The script uses standard Unix exit codes for automation:

| Exit Code | Meaning | When It Occurs |
|-----------|---------|----------------|
| 0 | Success | Run completed successfully (--wait mode), or rerun triggered successfully (--rerun mode), or normal list/display operation completed |
| 1 | Failure | Run failed, was cancelled, exceeded the runner timeout, was not found, or an operation failed |
| 124 | Timeout | --wait timeout reached before run completed |

**Mode-specific exit codes:**
- **--wait mode:** Exit code reflects build outcome (0=success, 1=failure, 124=timeout)
- **--rerun mode:** Exit code reflects whether rerun was triggered (0=triggered, 1=failed to trigger)
- **Normal mode:** Exit code is 0 on successful execution or 1 on errors

### Checking Exit Codes in Scripts

```bash
# Bash
if scripts/gitea_builds.py org repo --run 123 --wait; then
    echo "Success"
else
    exit_code=$?
    if [ $exit_code -eq 124 ]; then
        echo "Timeout"
    else
        echo "Failure"
    fi
fi

# Python
import subprocess
result = subprocess.run(['python', 'scripts/gitea_builds.py', 'org', 'repo', '--run', '123', '--wait'])
if result.returncode == 0:
    print("Success")
elif result.returncode == 124:
    print("Timeout")
else:
    print("Failure")
```

---

## API Endpoints

The script uses the following Gitea API v1 endpoints:

### List User Repositories
```
GET /api/v1/user/repos
```
**Authentication:** Required
**Used when:** No arguments provided (listing repositories)

### Get Repository Info
```
GET /api/v1/repos/{owner}/{repo}
```
**Authentication:** Required
**Returns:** Repository metadata including default branch
**Used when:** Determining default branch

### List Commits
```
GET /api/v1/repos/{owner}/{repo}/commits
```
**Parameters:**
- `limit` (integer) - Number of commits to return
- `sha` (string) - Branch name (optional)

**Authentication:** Required
**Used when:** Fetching commit history to find builds

### Get Commit Statuses
```
GET /api/v1/repos/{owner}/{repo}/statuses/{sha}
```
**Parameters:**
- `sha` (string) - Commit SHA

**Authentication:** Required
**Returns:** Array of commit statuses (build results)
**Used when:** Retrieving build/job information

### List Workflow Runs
```
GET /api/v1/repos/{owner}/{repo}/actions/runs
```
**Authentication:** Required
**Returns:** Array of workflow runs with run numbers and IDs
**Used when:** Listing recent workflow runs

### Get Run Jobs
```
GET /api/v1/repos/{owner}/{repo}/actions/runs/{run_id}/jobs
```
**Parameters:**
- `run_id` (integer) - Workflow run database ID

**Authentication:** Required
**Returns:** Array of jobs for the specified run
**Used when:** Downloading logs (gets job IDs)

### Download Job Logs
```
GET /api/v1/repos/{owner}/{repo}/actions/jobs/{job_id}/logs
```
**Parameters:**
- `job_id` (integer) - Job database ID

**Authentication:** Required
**Returns:** Plain text log output
**Used when:** Downloading logs with --download-logs flag

**Notes:**
- Requires Gitea v1.24.0 or later
- Returns 404 if logs are not available or job doesn't exist
- Job IDs are obtained from the run jobs endpoint, not from commit statuses

### Rerun Workflow
```
POST /api/v1/repos/{owner}/{repo}/actions/runs/{run_id}/rerun
```
**Parameters:**
- `run_id` (integer) - Workflow run database ID

**Authentication:** Required (write access)
**Returns:** Empty response (or JSON response)
**Used when:** Rerunning failed workflow with --rerun flag

**Notes:**
- Requires write access to the repository and Gitea 1.26+
- Returns 404 when the endpoint is unavailable on older Gitea releases
- Creates a new workflow run with a new run number

### Rerun Specific Job
```
POST /api/v1/repos/{owner}/{repo}/actions/runs/{run_id}/jobs/{job_id}/rerun
```
**Parameters:**
- `run_id` (integer) - Workflow run database ID
- `job_id` (integer) - Job database ID

**Authentication:** Required (write access)
**Returns:** Empty response (or JSON response)
**Used when:** Rerunning specific job with --rerun-job flag

**Notes:**
- Requires write access to the repository and Gitea 1.26+
- Returns 404 when the endpoint is unavailable on older Gitea releases
- Handles job dependencies automatically
- More efficient than rerunning entire workflow when only one job failed

---

## Configuration

### Gitea Connection

The script reads its configuration from a `.gitea` dotfile or environment
variables. It checks `.gitea` in the current directory and then `~/.gitea`.
Use `--config <path>` or `GITEA_CONFIG` to select another file. Dotfiles use
shell-style `KEY=value` settings:

```bash
GITEA_URL="https://gitea.example.com"
GITEA_TOKEN="YOUR_GITEA_TOKEN"
```

Explicit environment variables override dotfile values. The environment-only
form remains supported:

```bash
export GITEA_URL="https://gitea.example.com"
export GITEA_TOKEN="YOUR_GITEA_TOKEN"
```

**GITEA_URL:** Base URL of your Gitea instance
**GITEA_TOKEN:** Personal access token with `read:repository` scope
**GITEA_CONFIG:** Optional path to the dotfile

### Network Requirements

- Network access to your Gitea instance (VPN if it is private)

### Token Permissions

Minimum required scopes:
- `read:repository` - Read repository data
- `read:user` - List user repositories (optional, for listing)

---

## Output Formats

### List View (Default)

```
Run ID   SHA       Branch          Status     Jobs   Commit Message
--------------------------------------------------------------------------------------------------------------
215      5a6119a   main            ✗ failure  6      Re-enable old builds
214      54b390c   main            ✓ success  1      Add web/index.html
```

**Columns:**
- Run ID: Unique identifier for the workflow run
- SHA: First 7 characters of commit hash
- Branch: Git branch name
- Status: Overall run status with icon
- Jobs: Total number of jobs in the run
- Commit Message: First 50 chars of commit message

### Run Details View (--run)

```
Run #215 - Commit 5a6119a
Commit message: Re-enable old builds

Job ID   Status     Description                                        Duration
----------------------------------------------------------------------------------------------------
0        ✓ success  / Release build (ubuntu-latest . +nightly wasm32-unknown-unknown ) (push) Successful in 54s
1        ✓ success  / Release build (macos-latest .   ) (push)         Successful in 3m56s
```

**Columns:**
- Job ID: Unique identifier for the job
- Status: Job status with icon
- Description: Job context/name from Gitea
- Duration: Time taken or status description

### Wait Mode View (--wait)

```
Waiting for run #215 to complete (timeout: 3600s, polling every 10s)...

[0s] Run #215 status:
  Job 0: ✓ success    / Release build (ubuntu-latest . +nightly wasm32-unknown-unk
  Job 1: ● running    / Release build (macos-latest .   ) (push)

================================================================================
✓ Run #215 completed successfully after 120s
```

Status updates only appear when job states change (efficient polling).

### Download Logs View (--download-logs)

```
Run #215 - Commit 5a6119a
Commit message: Re-enable old builds

Job ID   Status     Description                                        Duration
----------------------------------------------------------------------------------------------------
0        ✓ success  / Release build (ubuntu-latest . +nightly wasm32-unknown-unknown ) (push) Successful in 54s
1        ✓ success  / Release build (macos-latest .   ) (push)         Successful in 3m56s

View or download logs:
  Job view URL: http://gitea.example.com:3000/myorg/myrepo/actions/runs/215/jobs/0
  Navigate to: http://gitea.example.com:3000/myorg/myrepo/actions/runs/215
  Download logs: scripts/gitea_builds.py myorg myrepo --run 215 --download-logs

Downloading logs for run #215 (run ID: 1234) to logs/run_215/
--------------------------------------------------------------------------------
  Downloading job 1001 (Release build (ubuntu-latest . +nightly wasm32-unkn... ✓ (15234 bytes)
  Downloading job 1002 (Release build (macos-latest .   ))... ✓ (42156 bytes)

Successfully downloaded 2/2 log files to logs/run_215/
```

**Output Directory Structure:**
```
logs/run_<run_number>/
├── <job_id>_<sanitized_job_name>.log
├── <job_id>_<sanitized_job_name>.log
└── ...
```

**File Naming:**
- Job ID prefix ensures unique, sortable filenames
- Job names are sanitized (non-alphanumeric chars → underscores)
- Extension is `.log` for all log files

### Status Icons

| Icon | Meaning | Status |
|------|---------|--------|
| ✓ | Success | Job/run passed |
| ✗ | Failure | Job/run failed |
| ○ | Pending | Job queued |
| ● | Running | Job executing |
| ⊗ | Cancelled | Job cancelled |
| − | Skipped | Job skipped |

---

## Technical Details

### How It Works

**Basic Operation:**
1. **Fetch commits** from repository via API
2. **Retrieve commit statuses** for each commit
3. **Parse target URLs** to extract run/job IDs
4. **Group by run ID** and filter latest status per job
5. **Display results** in formatted tables

**Log Download Operation (--download-logs):**
1. **Use the run database ID** from `--run`
2. **Get jobs** for the specific run via actions API
3. **Download logs** for each job using job database IDs
4. **Save to files** in organized directory structure

**Key ID Mappings:**
- **Run number** (e.g., #215) → sequential number shown in UI
- **Run ID** (e.g., 1234) → database ID used by API
- **Job ID** (e.g., 1001) → database ID used for log downloads
- Job IDs are NOT the same as job indices in URLs (0, 1, 2...)

### Run/Job ID Extraction

The script extracts run and job IDs from commit status `target_url` fields:

```
/myorg/myrepo/actions/runs/215/jobs/5
                                    ^^^      ^
                                  run_id  job_id
```

Pattern: `/actions/runs/{run_id}/jobs/{job_id}`

### Status Polling (Wait Mode)

- **Poll interval:** 10 seconds (fixed)
- **Default timeout:** 3600 seconds (1 hour)
- **Runner timeout:** 300 seconds queued without an assigned runner
- **Efficiency:** Only displays when status changes

### Job Status Determination

A run is considered:
- **Success:** All jobs have `status: "success"`
- **Failure:** Any job has `status: "failure"` or `"error"`
- **Running:** Any job has `status: "pending"` or `"running"`
- **Mixed:** Other combinations (displayed as-is)

### Progressive Disclosure

The script follows progressive disclosure principles:
- **SKILL.md** - Quick reference, loaded first
- **examples.md** - Loaded when user needs examples
- **reference.md** - Loaded for deep technical details

Claude only loads what's needed for the current task.

---

## Python API

### GiteaClient Class

```python
from gitea_builds import GiteaClient

client = GiteaClient(
    base_url="http://gitea.example.com:3000",
    token="your_token_here"
)
```

#### Methods

**list_repos()**
```python
repos = client.list_repos()
# Returns: List of repository dicts
```

**get_repo_info(owner, repo)**
```python
info = client.get_repo_info("myorg", "myrepo")
# Returns: Repository metadata dict
```

**list_commits(owner, repo, limit=10, branch=None)**
```python
commits = client.list_commits("myorg", "myrepo", limit=20, branch="main")
# Returns: List of commit dicts
```

**get_commit_statuses(owner, repo, sha)**
```python
statuses = client.get_commit_statuses("myorg", "myrepo", "5a6119a...")
# Returns: List of commit status dicts
```

### Helper Functions

**group_statuses_by_run(statuses)**
```python
runs = group_statuses_by_run(statuses)
# Returns: Dict mapping run_id -> list of job statuses
```

**extract_run_job_from_url(url)**
```python
run_id, job_id = extract_run_job_from_url("/org/repo/actions/runs/215/jobs/5")
# Returns: Tuple of (run_id, job_id) or None
```

**format_status(status)**
```python
icon = format_status("success")  # Returns: "✓"
```

---

## Error Handling

### Common Errors

**Connection Refused**
```
Error: Failed to connect to gitea.example.com port 3000
```
**Solution:** Verify network/VPN connection to your Gitea instance

**403 Forbidden**
```
Error: 403 Client Error: Forbidden
```
**Solution:** Check token has correct permissions

**404 Not Found (Run)**
```
Run #999 not found in last 10 commits
```
**Solution:** Increase --commits limit

**404 Not Found (API)**
```
Error: 404 Client Error: Not Found for url: /api/v1/repos/{owner}/{repo}/actions/runs
```
**Solution:** This is expected - Gitea stores builds as commit statuses, not via actions API

### Debug Mode

For debugging connection issues:
```python
import requests
import logging

# Enable requests debug logging
logging.basicConfig(level=logging.DEBUG)
```

---

## Performance Considerations

### API Rate Limits

Gitea may impose rate limits. The script makes:
- 1 request per commit to fetch statuses
- Default: 10 commits = ~11 API calls
- With `--commits 50`: ~51 API calls

### Wait Mode Performance

- **Efficient polling:** 10 second intervals
- **Minimal API calls:** Only checks commits once per poll
- **Smart display:** Only outputs on status changes
- **Network friendly:** 6 requests per minute (max)

### Large Repositories

For repos with many commits:
- Use `--commits` sparingly
- Consider `--branch` to limit scope
- Wait mode checks only necessary commits

---

## Dependencies

### Python Packages

```
requests>=2.31.0
```

Install via:
```bash
pip install -r requirements.txt
```

### Python Version

- **Minimum:** Python 3.6
- **Recommended:** Python 3.9+
- **Tested on:** Python 3.9, 3.10, 3.11

### System Requirements

- Unix-like OS (macOS, Linux)
- Network access to Gitea instance (VPN client if the instance is private)

---

## Security Considerations

### Token Storage

The token is read from the `GITEA_TOKEN` environment variable:

```python
GITEA_TOKEN = os.environ.get("GITEA_TOKEN")
```

Avoid hardcoding tokens in scripts or committing them to version control. If you prefer a config file, restrict its permissions:

```bash
chmod 600 ~/.config/gitea/token
```

### Network Security

- Prefer HTTPS; plain HTTP is only acceptable on a trusted private network
- Token transmitted in Authorization header

### Allowed Tools

The skill restricts Claude to:
- `Bash` - Execute the script
- `Read` - Read documentation files

This prevents unintended file modifications.

---

## Troubleshooting

### Script Won't Execute

**Check Python version:**
```bash
python --version  # Should be 3.6+
```

**Check script permissions:**
```bash
chmod +x scripts/gitea_builds.py
```

### Import Errors

```bash
pip install requests
```

### Token Issues

Test token manually:
```bash
curl -H "Authorization: token YOUR_TOKEN" \
  https://gitea.example.com/api/v1/user
```

Should return user info, not 403 error.
