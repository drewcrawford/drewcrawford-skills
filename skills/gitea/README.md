# Gitea Build Monitor

A Python script and portable Agent Skill to monitor Gitea CI/CD builds, view job details, and wait for builds to complete with proper exit codes for automation.

## Quick Links

- **[SKILL.md](SKILL.md)** - Instructions and activation metadata
- **[examples.md](examples.md)** - Detailed usage examples
- **[reference.md](reference.md)** - Complete API and technical documentation

---

## Two Ways to Use

### 1. As an Agent Skill (Recommended)

Install as a skill to enable natural language interaction with Gitea builds:

```bash
# Copy to the shared personal skills directory
mkdir -p ~/.agents/skills
cp -R ~/Code/skills/skills/gitea ~/.agents/skills/gitea

# Claude Code can use a symlink to the canonical copy
mkdir -p ~/.claude/skills
ln -s ~/.agents/skills/gitea ~/.claude/skills/gitea
```

After installation, restart the client if it does not detect the new skill. It activates automatically when you ask:
- "Show me recent builds for myorg/myrepo"
- "What's the status of run 215?"
- "Download the logs for run 215"
- "Wait for build 216 to complete"

No explicit invocation is required when the client supports model-driven skill activation.

### 2. As a Standalone Command-Line Tool

Use directly from the command line:

```bash
# Install dependencies
pip install -r requirements.txt

# List recent builds
scripts/gitea_builds.py myorg myrepo

# View specific run
scripts/gitea_builds.py myorg myrepo --run 215

# Wait for completion
scripts/gitea_builds.py myorg myrepo --run 215 --wait
```

---

## Features

- **List builds** - View recent workflow runs with status, branch, and commit info
- **View details** - See individual job statuses, platforms, and durations
- **Download logs** - Download job logs from CI builds for debugging and archival
- **Wait for completion** - Monitor builds with proper exit codes (0=success, 1=failure or runner-blocked, 124=timeout)
- **Rerun workflows** - Rerun failed workflows or specific jobs with a single command *(requires Gitea 1.26+)*
- **Branch filtering** - Check builds on specific branches
- **CI/CD integration** - Perfect for automation scripts
- **Visual indicators** - Clear status icons (✓ ✗ ○ ● ⊗ −)

---

## Quick Start

### Basic Commands

```bash
# List recent builds (default: last 10 commits, default branch)
scripts/gitea_builds.py <owner> <repo>

# View specific run details
scripts/gitea_builds.py <owner> <repo> --run <run_id>

# Download logs for a run
scripts/gitea_builds.py <owner> <repo> --run <run_id> --download-logs

# Wait for build to complete
scripts/gitea_builds.py <owner> <repo> --run <run_id> --wait

# Rerun failed workflow
scripts/gitea_builds.py <owner> <repo> --run <run_id> --rerun

# Rerun specific failed job
scripts/gitea_builds.py <owner> <repo> --run <run_id> --rerun-job <job_id>

# Check specific branch
scripts/gitea_builds.py <owner> <repo> --branch develop

# Custom timeout (default: 3600s)
scripts/gitea_builds.py <owner> <repo> --run <run_id> --wait --timeout 1800
```

### Exit Codes (--wait mode)

- `0` - Build completed successfully (all jobs passed)
- `1` - Build failed, was cancelled, or remained queued without a runner
- `124` - Timeout reached

### Example: CI/CD Automation

```bash
#!/bin/bash
if scripts/gitea_builds.py myorg myrepo --run 123 --wait --timeout 600; then
    echo "Build passed! Deploying..."
    ./deploy.sh
else
    echo "Build failed or timed out"
    exit 1
fi
```

---

## Documentation Structure

This skill follows the Agent Skills progressive-disclosure conventions:

```
gitea/
├── SKILL.md              # Quick reference (loaded first by Claude)
├── examples.md           # Detailed usage examples (loaded when needed)
├── reference.md          # Complete API/technical docs (loaded for deep dives)
├── README.md             # This file (user documentation)
├── requirements.txt      # Python dependencies
└── scripts/
    ├── gitea_builds.py   # Main script
    └── test_gitea_builds.py
```

Compatible agents load only the documentation they need for a specific question, keeping context efficient.

---

## Configuration

The script reads configuration from a `.gitea` dotfile when present. It looks
for `.gitea` in the current directory and then `~/.gitea`. You can also pass a
specific file with `--config` or set `GITEA_CONFIG`.

The file uses shell-style `KEY=value` settings:

```bash
GITEA_URL="https://gitea.example.com"
GITEA_TOKEN="your_personal_access_token"
```

Environment variables take precedence over values in the dotfile. The
original environment-variable configuration remains supported:

```bash
export GITEA_URL="https://gitea.example.com"
export GITEA_TOKEN="your_personal_access_token"
```

For example:

```bash
scripts/gitea_builds.py --config ~/.config/gitea myorg myrepo
```

- **GITEA_URL:** Base URL of your Gitea instance
- **GITEA_TOKEN:** Personal access token with `read:repository` scope
- **GITEA_CONFIG:** Optional path to the dotfile
- **Network:** Requires network access to your Gitea instance (VPN if it is private)

---

## Common Use Cases

### 1. Quick Status Check
**Question:** "Did the latest build pass?"

**Claude uses:**
```bash
scripts/gitea_builds.py myorg myrepo
```

### 2. Diagnose Failure
**Question:** "Why did run 215 fail?"

**Claude uses:**
```bash
scripts/gitea_builds.py myorg myrepo --run 215
```

### 3. Monitor Build
**Question:** "Wait for run 216 and deploy if it passes"

**Claude uses:**
```bash
scripts/gitea_builds.py myorg myrepo --run 216 --wait
```

### 4. Rerun Failed Build
**Question:** "Rerun run 215 since I fixed the Windows ARM64 issue"

**Claude uses:**
```bash
scripts/gitea_builds.py myorg myrepo --run 215 --rerun
```

### 5. Rerun Specific Job
**Question:** "Just rerun the Windows ARM64 job from run 215"

**Claude uses:**
```bash
scripts/gitea_builds.py myorg myrepo --run 215 --rerun-job 1006
```

### 6. Check Feature Branch
**Question:** "Are builds passing on the develop branch?"

**Claude uses:**
```bash
scripts/gitea_builds.py myorg myrepo --branch develop
```

---

## Complete Options Reference

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `--run <id>` | integer | - | Database ID from `/actions/runs/<id>` |
| `--download-logs` | flag | false | Download logs for all jobs (requires --run) |
| `--wait` | flag | false | Wait for run completion (requires --run) |
| `--rerun` | flag | false | Rerun entire workflow (requires --run) |
| `--rerun-job <id>` | integer | - | Rerun specific job (requires --run) |
| `--timeout <sec>` | integer | 3600 | Timeout for --wait in seconds |
| `--runner-timeout <sec>` | integer | 300 | Fail if a queued job remains unassigned this long |
| `--commits <n>` | integer | 10 | Number of commits to check |
| `--branch <name>` | string | default | Branch to check |

See [reference.md](reference.md) for complete API documentation.

---

## Requirements

- **Python:** 3.6 or higher
- **Dependencies:** `requests` library
- **Network:** Access to your Gitea instance (VPN if it is private)

### Installation

```bash
pip install -r requirements.txt
```

---

## Status Indicators

| Icon | Meaning | Description |
|------|---------|-------------|
| ✓ | Success | Build/job passed |
| ✗ | Failure | Build/job failed |
| ○ | Pending | Build/job queued |
| ● | Running | Build/job in progress |
| ⊗ | Cancelled | Build/job cancelled |
| − | Skipped | Build/job skipped |

---

## How It Works

The script uses Gitea's commit status API:

1. **Fetches commits** from the repository
2. **Retrieves commit statuses** (which contain CI/CD results)
3. **Extracts run/job IDs** from status target URLs
4. **Groups and displays** results in formatted tables

**API Endpoints:**
- `GET /api/v1/user/repos` - List repositories
- `GET /api/v1/repos/{owner}/{repo}/commits` - List commits
- `GET /api/v1/repos/{owner}/{repo}/statuses/{sha}` - Get build statuses
- `GET /api/v1/repos/{owner}/{repo}/actions/runs` - List workflow runs
- `GET /api/v1/repos/{owner}/{repo}/actions/runs/{run}/jobs` - Get jobs for run
- `GET /api/v1/repos/{owner}/{repo}/actions/jobs/{job}/logs` - Download job logs
- `POST /api/v1/repos/{owner}/{repo}/actions/runs/{run}/rerun` - Rerun workflow
- `POST /api/v1/repos/{owner}/{repo}/actions/runs/{run}/jobs/{job}/rerun` - Rerun specific job

See [reference.md](reference.md) for technical details.

---

## Examples

For detailed usage examples, see [examples.md](examples.md), including:

- Checking recent builds
- Diagnosing failures
- Waiting for builds
- Branch filtering
- CI/CD automation scripts
- Troubleshooting

---

## Troubleshooting

### Connection Issues

```bash
# Test connection (verify VPN if your instance is private)
ping gitea.example.com
```

### Run Not Found

```bash
# Increase commit search depth
scripts/gitea_builds.py owner repo --run 999 --commits 50
```

### Token Permissions

Ensure token has:
- `read:repository` scope (minimum)
- `read:user` scope (for listing repos)

Test token:
```bash
curl -H "Authorization: token YOUR_TOKEN" \
  http://gitea.example.com:3000/api/v1/user
```

For more troubleshooting, see [reference.md](reference.md).

---

## Development

### File Structure

```
gitea-builds/
├── SKILL.md              # Claude Code skill definition
├── examples.md           # Usage examples
├── reference.md          # API documentation
├── README.md             # User guide (this file)
├── requirements.txt      # Python dependencies
└── scripts/
    └── gitea_builds.py   # Main implementation
```

### Adding Features

1. Update `scripts/gitea_builds.py` with new functionality
2. Add examples to `examples.md`
3. Update API docs in `reference.md`
4. Update quick reference in `SKILL.md`

### Testing

```bash
# Test basic listing
scripts/gitea_builds.py myorg myrepo

# Test specific run
scripts/gitea_builds.py myorg myrepo --run 215

# Test wait mode with timeout
scripts/gitea_builds.py myorg myrepo --run 214 --wait --timeout 30
```

---

## License

[Your license here]

## Contributing

[Your contribution guidelines here]

---

## See Also

- **[SKILL.md](SKILL.md)** - Quick reference for Claude integration
- **[examples.md](examples.md)** - Detailed usage examples
- **[reference.md](reference.md)** - Complete technical documentation
