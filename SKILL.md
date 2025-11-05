---
name: Gitea Build Monitor
description: Monitor and interact with Gitea CI/CD builds. Use when the user asks about Gitea builds, workflow runs, CI/CD status, build failures, or wants to wait for builds to complete. Also use when they mention checking build status, listing jobs, or monitoring continuous integration pipelines on Gitea.
allowed-tools: Bash, Read
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
- Asks about build logs or failures

## Quick Start

### List recent builds
```bash
python scripts/gitea_builds.py <owner> <repo>
```

### View run details
```bash
python scripts/gitea_builds.py <owner> <repo> --run <run_id>
```

### Download job logs
```bash
python scripts/gitea_builds.py <owner> <repo> --run <run_id> --download-logs
```

### Wait for build completion
```bash
python scripts/gitea_builds.py <owner> <repo> --run <run_id> --wait
```

**Exit codes for --wait:**
- `0` - Build succeeded (all jobs passed)
- `1` - Build failed
- `127` - Timeout reached

## Common Options

- `--run <run_id>` - Show specific run details
- `--download-logs` - Download logs for all jobs in a run (requires --run)
- `--wait` - Wait for run completion (requires --run)
- `--timeout <seconds>` - Wait timeout (default: 3600)
- `--commits <limit>` - Check last N commits (default: 10)
- `--branch <branch>` - Check specific branch

## Instructions for Claude

When the user asks about Gitea builds:

1. **Identify the request type:**
   - List builds → Use basic command
   - Specific run → Add `--run <run_id>`
   - Wait for completion → Add `--wait` flag
   - Different branch → Add `--branch <name>`

2. **Execute with Bash tool:**
   ```bash
   python scripts/gitea_builds.py <owner> <repo> [options]
   ```

3. **Interpret results:**
   - List view: Summarize pass/fail status
   - Run details: Identify failed jobs
   - Wait mode: Report exit code meaning

4. **Status indicators:**
   - ✓ success, ✗ failure, ○ pending, ● running

## Common Patterns

**Check recent builds:**
```bash
python scripts/gitea_builds.py Metropolis Metropolis
```

**Diagnose failure:**
```bash
python scripts/gitea_builds.py Metropolis Metropolis --run 215
```

**Download logs for debugging:**
```bash
python scripts/gitea_builds.py Metropolis Metropolis --run 215 --download-logs
```

**CI/CD automation:**
```bash
if python scripts/gitea_builds.py org repo --run 123 --wait --timeout 600; then
    echo "Deploy!"
fi
```

## Additional Resources

- [examples.md](examples.md) - Detailed usage examples
- [reference.md](reference.md) - Complete API and options reference
- [README.md](README.md) - Full documentation

## Configuration

**Pre-configured for:**
- Gitea URL: `http://gitea.mermaid-gecko.ts.net:3000`
- Authentication: Token configured in script
- Network: Requires Tailscale connection

## Requirements

```bash
pip install requests
```

Script requires Python 3.6+ and connection to Tailscale network.
