---
name: GitHub Actions Monitor
description: Monitor and interact with GitHub Actions CI/CD builds. Use when the user asks about GitHub builds, workflow runs, CI/CD status, build failures, or wants to wait for builds to complete. Also use when they mention checking build status, listing jobs, or monitoring continuous integration pipelines on GitHub.
allowed-tools: Bash(~/.claude/skills/github/scripts/github_builds:*),Read(logs/**)
---

# GitHub Actions Monitor

Monitor GitHub Actions CI/CD builds, view job details, and wait for builds to complete with proper exit codes for automation.

## When to use this skill

Use this skill when the user:
- Asks about GitHub Actions build status or CI/CD pipelines
- Wants to list recent workflow runs
- Needs to check if a build passed or failed
- Wants detailed job information for a specific run
- Needs to download job logs from CI builds
- Needs to wait for a build to complete (automation/CI/CD)
- Wants to rerun a failed workflow or specific jobs
- Asks about build logs or failures
- Wants to see repository topics (tags)

## Quick Start

### List recent builds
```bash
scripts/github_builds <owner> <repo>
```

**NOTE: Using relative paths (~/.claude...) will ensure you run without permissions errors.

### View run details
```bash
scripts/github_builds <owner> <repo> --run <run_id>
```

### Download job logs
```bash
scripts/github_builds <owner> <repo> --run <run_id> --download-logs
```

### Wait for build completion
```bash
scripts/github_builds <owner> <repo> --run <run_id> --wait
```

### Get repository topics (tags)
```bash
scripts/github_builds <owner> <repo> --topics
```

**Exit codes for --wait:**
- `0` - Build succeeded (all jobs passed)
- `1` - Build failed
- `127` - Timeout reached

### Rerun a failed workflow
```bash
scripts/github_builds <owner> <repo> --run <run_id> --rerun
```

### Rerun only failed jobs
```bash
scripts/github_builds <owner> <repo> --run <run_id> --rerun-failed
```

## Common Options

- `--run <run_id>` - Show specific run details
- `--download-logs` - Download logs for all jobs in a run (requires --run)
- `--wait` - Wait for run completion (requires --run)
- `--rerun` - Rerun entire workflow (requires --run)
- `--rerun-failed` - Rerun only failed jobs (requires --run)
- `--timeout <seconds>` - Wait timeout (default: 3600)
- `--branch <branch>` - Filter by specific branch
- `--topics` - Show repository topics (tags)

## Instructions for Claude

When the user asks about GitHub Actions builds:

1. **Identify the request type:**
   - List builds → Use basic command
   - Specific run → Add `--run <run_id>`
   - Wait for completion → Add `--wait` flag
   - Rerun workflow → Add `--rerun` flag
   - Rerun failed jobs → Add `--rerun-failed` flag
   - Different branch → Add `--branch <name>`

2. **Execute with Bash tool:**
   ```bash
   scripts/github_builds <owner> <repo> [options]
   ```

3. **Interpret results:**
   - List view: Summarize pass/fail status
   - Run details: Identify failed jobs
   - Wait mode: Report exit code meaning
   - Rerun: Confirm workflow/job restarted

4. **Status indicators:**
   - ✓ success, ✗ failure, ○ pending/queued, ● in_progress, ⊗ cancelled

## Common Patterns

**Check recent builds:**
```bash
scripts/github_builds drewcrawford wasm_safe_mutex
```

**Diagnose failure:**
```bash
scripts/github_builds drewcrawford wasm_safe_mutex --run 19609289127
```

**Download logs for debugging:**
```bash
scripts/github_builds drewcrawford wasm_safe_mutex --run 19609289127 --download-logs
```

**Rerun failed workflow:**
```bash
scripts/github_builds drewcrawford wasm_safe_mutex --run 19609289127 --rerun
```

**Rerun only failed jobs:**
```bash
scripts/github_builds drewcrawford wasm_safe_mutex --run 19609289127 --rerun-failed
```

**Filter by branch:**
```bash
scripts/github_builds drewcrawford wasm_safe_mutex --branch main
```

**Get repository topics:**
```bash
scripts/github_builds drewcrawford wasm_safe_mutex --topics
```

**CI/CD automation:**
```bash
if scripts/github_builds org repo --run 123 --wait --timeout 600; then
    echo "Deploy!"
fi
```

## Configuration

**Authentication:** Token configured in script

The token needs these scopes:
- `repo` - For private repositories
- `actions` - For workflow operations (rerun, cancel)

## Requirements

```bash
pip install requests
```

Script requires Python 3.6+.
