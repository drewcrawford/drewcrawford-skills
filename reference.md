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
python scripts/gitea_builds.py <owner> <repo> [options]
```

### Required Arguments

- `<owner>` - Repository owner/organization name
- `<repo>` - Repository name

### Optional Arguments

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--run <run_id>` | integer | - | Show details for specific run |
| `--wait` | flag | false | Wait for run to complete (requires --run) |
| `--timeout <seconds>` | integer | 3600 | Timeout for --wait in seconds |
| `--commits <limit>` | integer | 10 | Number of commits to check |
| `--branch <branch>` | string | default | Branch name to check |

### Examples

```bash
# List builds (default: last 10 commits, default branch)
python scripts/gitea_builds.py Metropolis Metropolis

# View specific run
python scripts/gitea_builds.py Metropolis Metropolis --run 215

# Wait for run with custom timeout
python scripts/gitea_builds.py Metropolis Metropolis --run 215 --wait --timeout 1800

# Check specific branch with more commits
python scripts/gitea_builds.py Metropolis Metropolis --branch develop --commits 20

# Combined options
python scripts/gitea_builds.py Metropolis Metropolis --branch main --commits 50
```

---

## Exit Codes

The script uses standard Unix exit codes for automation:

| Exit Code | Meaning | When It Occurs |
|-----------|---------|----------------|
| 0 | Success | Run completed with all jobs successful (--wait mode only) |
| 1 | Failure | Run completed with job failures, or run not found |
| 127 | Timeout | --wait timeout reached before run completed |

**Note:** Exit codes are only meaningful when using `--wait` mode. Without `--wait`, the script exits with 0 on successful execution or 1 on errors.

### Checking Exit Codes in Scripts

```bash
# Bash
if python scripts/gitea_builds.py org repo --run 123 --wait; then
    echo "Success"
else
    exit_code=$?
    if [ $exit_code -eq 127 ]; then
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
elif result.returncode == 127:
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

---

## Configuration

### Gitea Connection

The script is pre-configured for a specific Gitea instance. To modify:

**File:** `scripts/gitea_builds.py`
**Lines:** 389-391

```python
GITEA_URL = "http://gitea.mermaid-gecko.ts.net:3000"
GITEA_TOKEN = "cb1fcb0b640a6822a430d7792d5978689ac8d2ab"
```

**GITEA_URL:** Base URL of your Gitea instance
**GITEA_TOKEN:** Personal access token with `read:repository` scope

### Network Requirements

- **Tailscale VPN:** Required for `gitea.mermaid-gecko.ts.net`
- **Port:** 3000 (HTTP)
- **Protocol:** HTTP (not HTTPS)

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

1. **Fetch commits** from repository via API
2. **Retrieve commit statuses** for each commit
3. **Parse target URLs** to extract run/job IDs
4. **Group by run ID** and filter latest status per job
5. **Display results** in formatted tables

### Run/Job ID Extraction

The script extracts run and job IDs from commit status `target_url` fields:

```
/Metropolis/Metropolis/actions/runs/215/jobs/5
                                    ^^^      ^
                                  run_id  job_id
```

Pattern: `/actions/runs/{run_id}/jobs/{job_id}`

### Status Polling (Wait Mode)

- **Poll interval:** 10 seconds (fixed)
- **Default timeout:** 3600 seconds (1 hour)
- **Max commits checked:** 50 (configurable)
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
info = client.get_repo_info("Metropolis", "Metropolis")
# Returns: Repository metadata dict
```

**list_commits(owner, repo, limit=10, branch=None)**
```python
commits = client.list_commits("Metropolis", "Metropolis", limit=20, branch="main")
# Returns: List of commit dicts
```

**get_commit_statuses(owner, repo, sha)**
```python
statuses = client.get_commit_statuses("Metropolis", "Metropolis", "5a6119a...")
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
Error: Failed to connect to gitea.mermaid-gecko.ts.net port 3000
```
**Solution:** Verify Tailscale connection

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
- Network access to Gitea instance
- Tailscale VPN client (for mermaid-gecko.ts.net)

---

## Security Considerations

### Token Storage

⚠️ **Warning:** The token is currently hardcoded in the script.

**For production:**
1. Store in environment variable:
   ```python
   GITEA_TOKEN = os.environ.get("GITEA_TOKEN")
   ```

2. Or use config file with restricted permissions:
   ```bash
   chmod 600 ~/.config/gitea/token
   ```

### Network Security

- Uses HTTP (not HTTPS) - acceptable for Tailscale network
- Token transmitted in Authorization header
- No SSL/TLS verification issues

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

### Tailscale Connection

```bash
tailscale status
# Should show: connected, logged in
```

### Token Issues

Test token manually:
```bash
curl -H "Authorization: token YOUR_TOKEN" \
  http://gitea.mermaid-gecko.ts.net:3000/api/v1/user
```

Should return user info, not 403 error.
