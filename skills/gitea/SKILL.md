---
name: gitea
description: Monitor and interact with Gitea CI/CD builds. Use when the user asks about Gitea builds, workflow runs, CI/CD status, build failures, or wants to wait for builds to complete. Also use when they mention checking build status, listing jobs, or monitoring continuous integration pipelines on Gitea.
compatibility: Requires Python 3, the requests package, network access to a Gitea instance, and a GITEA_TOKEN.
---
   
# Gitea Build Monitor

Monitor Gitea CI/CD builds, view job details, and wait for builds to complete with proper exit codes for automation.

## When to use this skill

Use this skill when the user:
- Asks about Gitea build status or CI/CD pipelines
- Wants to list recent workflow runs
- Needs to check if a build passed or failed
- Wants detailed job information for a specific run
- Needs to download job logs from CI builds
- Needs to wait for a build to complete (automation/CI/CD)
- Wants to rerun a failed workflow or specific job
- Asks about build logs or failures

# Launch note

Resolve all `scripts/...` paths relative to this skill's directory before
running them.


## Quick Start

### List recent builds
```bash
scripts/gitea_builds.py <owner> <repo>
```

### View run details
```bash
scripts/gitea_builds.py <owner> <repo> --run <run_id>
```

### Download job logs
```bash
scripts/gitea_builds.py <owner> <repo> --run <run_id> --download-logs
```

### Wait for build completion
```bash
scripts/gitea_builds.py <owner> <repo> --run <run_id> --wait
```

**Exit codes for --wait:**
- `0` - Build succeeded (all jobs passed)
- `1` - Build failed, was cancelled, or remained queued without a runner
- `127` - Timeout reached

### Rerun a failed workflow
```bash
scripts/gitea_builds.py <owner> <repo> --run <run_id> --rerun
```

**Note:** Requires Gitea 1.26 or newer for rerun API support.

### Rerun a specific failed job
```bash
scripts/gitea_builds.py <owner> <repo> --run <run_id> --rerun-job <job_id>
```

**Note:** Requires Gitea 1.26 or newer for rerun API support.

## Common Options

- `--run <run_id>` - Use the database ID from `/actions/runs/<run_id>` (not the smaller UI run number)
- `--download-logs` - Download logs for all jobs in a run (requires --run)
- `--wait` - Wait for run completion (requires --run)
- `--rerun` - Rerun entire workflow (requires --run)
- `--rerun-job <job_id>` - Rerun specific job (requires --run)
- `--timeout <seconds>` - Wait timeout (default: 3600)
- `--runner-timeout <seconds>` - Fail a queued, unassigned job after this many seconds (default: 300)
- `--commits <limit>` - Check last N commits (default: 10)
- `--branch <branch>` - Check specific branch

## Instructions for Claude

When the user asks about Gitea builds:

1. **Identify the request type:**
   - List builds → Use basic command
   - Specific run → Add `--run <run_id>`
   - Wait for completion → Add `--wait` flag
   - Rerun workflow → Add `--rerun` flag
   - Rerun specific job → Add `--rerun-job <job_id>`
   - Different branch → Add `--branch <name>`

2. **Execute with Bash tool:**
   ```bash
   scripts/gitea_builds.py <owner> <repo> [options]
   ```

3. **Interpret results:**
   - List view: Summarize pass/fail status
   - Run details: Identify failed jobs
   - Wait mode: Report exit code meaning
   - Rerun: Confirm workflow/job restarted

4. **Status indicators:**
   - ✓ success, ✗ failure, ○ pending, ● running

## Common Patterns

**Check recent builds:**
```bash
scripts/gitea_builds.py myorg myrepo
```

**Diagnose failure:**
```bash
scripts/gitea_builds.py myorg myrepo --run 215
```

**Download logs for debugging:**
```bash
scripts/gitea_builds.py myorg myrepo --run 215 --download-logs
```

**Rerun failed workflow:**
```bash
scripts/gitea_builds.py myorg myrepo --run 215 --rerun
```

**Rerun specific failed job:**
```bash
scripts/gitea_builds.py myorg myrepo --run 215 --rerun-job 1006
```

**CI/CD automation:**
```bash
if  scripts/gitea_builds.py org repo --run 123 --wait --timeout 600; then
    echo "Deploy!"
fi
```

## Additional Resources

- [examples.md](examples.md) - Detailed usage examples
- [reference.md](reference.md) - Complete API and options reference
- [README.md](README.md) - Full documentation

## Configuration

**Configured via a `.gitea` dotfile or environment variables:**

The script looks for `.gitea` in the current directory and then `~/.gitea`.
Use `--config <path>` or `GITEA_CONFIG` to select another file. The file uses
shell-style settings:

```bash
GITEA_URL="https://gitea.example.com"
GITEA_TOKEN="your_personal_access_token"
```

Explicit environment variables override dotfile values.

- `GITEA_URL`: Base URL of your Gitea instance (e.g. `https://gitea.example.com`)
- `GITEA_TOKEN`: Personal access token
- `GITEA_CONFIG`: Optional path to the dotfile
- Network: Requires access to your Gitea instance

## Requirements

```bash
pip install requests
```

Script requires Python 3.6+ and network access to your Gitea instance.
