# Gitea Build Monitor - Examples

This document provides concrete examples of using the Gitea Build Monitor skill.

## Example 1: Check Recent Builds

**Scenario:** User wants to see the latest build status for a repository.

**User asks:** "Show me the recent builds for Metropolis/Metropolis"

**Command:**
```bash
python scripts/gitea_builds.py Metropolis Metropolis
```

**Output:**
```
Fetching build status for Metropolis/Metropolis on branch 'main' (checking last 10 commits)...

Run ID   SHA       Branch          Status     Jobs   Commit Message
--------------------------------------------------------------------------------------------------------------
215      5a6119a   main            ✗ failure  6      Re-enable old builds
214      54b390c   main            ✓ success  1      Add web/index.html
213      6f352ad   main            ✓ success  1      Remove bad compile?
212      3fb71c6   main            ✗ failure  1      Try using github-script?
211      81fac6a   main            ✗ failure  1      Try using github-script?
```

**Claude should respond:** "I can see the recent builds for Metropolis/Metropolis. The most recent run (215) failed with 6 jobs, where one job had failures. Runs 214 and 213 succeeded, but 212 and 211 failed as well. Would you like me to check the details of run 215 to see which job failed?"

---

## Example 2: Diagnose a Failed Build

**Scenario:** User wants to know why a specific build failed.

**User asks:** "Run 215 failed, what went wrong?"

**Command:**
```bash
python scripts/gitea_builds.py Metropolis Metropolis --run 215
```

**Output:**
```
Run #215 - Commit 5a6119a
Commit message: Re-enable old builds

Job ID   Status     Description                                        Duration
----------------------------------------------------------------------------------------------------
0        ✓ success  / Release build (ubuntu-latest . +nightly wasm32-unknown-unknown ) (push) Successful in 54s
1        ✓ success  / Release build (macos-latest .   ) (push)         Successful in 3m56s
2        ✓ success  / Release build (ubuntu-latest .   ) (push)        Successful in 6m34s
3        ✓ success  / Release build (ubuntu-latest .  aarch64-unknown-linux-gnu ) (push) Successful in 7m8s
4        ✓ success  / Release build (windows-latest .   ) (push)       Successful in 12m54s
5        ✗ failure  / Release build (windows-latest .  aarch64-pc-windows-msvc ) (push) Failing after 6m39s

View logs for jobs:
  Job view URL: http://gitea.mermaid-gecko.ts.net:3000/Metropolis/Metropolis/actions/runs/215/jobs/0
  Or navigate to: http://gitea.mermaid-gecko.ts.net:3000/Metropolis/Metropolis/actions/runs/215
```

**Claude should respond:** "Run 215 has 6 jobs, and job 5 failed. It's the Windows ARM64 build (aarch64-pc-windows-msvc) that's failing after 6m39s. All other platforms built successfully:
- Ubuntu/wasm32 (54s) ✓
- macOS (3m56s) ✓
- Ubuntu/x64 (6m34s) ✓
- Ubuntu/ARM64 (7m8s) ✓
- Windows/x64 (12m54s) ✓
- Windows/ARM64 (6m39s) ✗

You can view the logs at: http://gitea.mermaid-gecko.ts.net:3000/Metropolis/Metropolis/actions/runs/215"

---

## Example 3: Download Job Logs

**Scenario:** User wants to download logs from a build for debugging or archival.

**User asks:** "Download the logs for run 215 so I can analyze the Windows ARM64 failure"

**Command:**
```bash
python scripts/gitea_builds.py Metropolis Metropolis --run 215 --download-logs
```

**Output:**
```
Run #215 - Commit 5a6119a
Commit message: Re-enable old builds

Job ID   Status     Description                                        Duration
----------------------------------------------------------------------------------------------------
0        ✓ success  / Release build (ubuntu-latest . +nightly wasm32-unknown-unknown ) (push) Successful in 54s
1        ✓ success  / Release build (macos-latest .   ) (push)         Successful in 3m56s
2        ✓ success  / Release build (ubuntu-latest .   ) (push)        Successful in 6m34s
3        ✓ success  / Release build (ubuntu-latest .  aarch64-unknown-linux-gnu ) (push) Successful in 7m8s
4        ✓ success  / Release build (windows-latest .   ) (push)       Successful in 12m54s
5        ✗ failure  / Release build (windows-latest .  aarch64-pc-windows-msvc ) (push) Failing after 6m39s

View or download logs:
  Job view URL: http://gitea.mermaid-gecko.ts.net:3000/Metropolis/Metropolis/actions/runs/215/jobs/0
  Navigate to: http://gitea.mermaid-gecko.ts.net:3000/Metropolis/Metropolis/actions/runs/215
  Download logs: python scripts/gitea_builds.py Metropolis Metropolis --run 215 --download-logs

Downloading logs for run #215 (run ID: 1234) to logs/run_215/
--------------------------------------------------------------------------------
  Downloading job 1001 (Release build (ubuntu-latest . +nightly wasm32-unkn... ✓ (15234 bytes)
  Downloading job 1002 (Release build (macos-latest .   ))... ✓ (42156 bytes)
  Downloading job 1003 (Release build (ubuntu-latest .   ))... ✓ (38421 bytes)
  Downloading job 1004 (Release build (ubuntu-latest .  aarch64-unknown-lin... ✓ (41823 bytes)
  Downloading job 1005 (Release build (windows-latest .   ))... ✓ (45612 bytes)
  Downloading job 1006 (Release build (windows-latest .  aarch64-pc-windows... ✓ (38945 bytes)

Successfully downloaded 6/6 log files to logs/run_215/
```

**Files created:**
```
logs/run_215/
├── 1001_Release_build__ubuntu-latest____nightly_wasm32-unknown-unknown__.log
├── 1002_Release_build__macos-latest____.log
├── 1003_Release_build__ubuntu-latest____.log
├── 1004_Release_build__ubuntu-latest___aarch64-unknown-linux-gnu_.log
├── 1005_Release_build__windows-latest____.log
└── 1006_Release_build__windows-latest___aarch64-pc-windows-msvc_.log
```

**Claude should respond:** "I've downloaded all 6 job logs for run 215 into the `logs/run_215/` directory. Each job has its own log file named with the job ID and description. You can now examine the Windows ARM64 failure log at `logs/run_215/1006_Release_build__windows-latest___aarch64-pc-windows-msvc_.log` to see what went wrong."

---

## Example 4: Wait for Build to Complete

**Scenario:** User wants to wait for a currently running build to finish.

**User asks:** "Wait for run 216 to finish and let me know if it passes"

**Command:**
```bash
python scripts/gitea_builds.py Metropolis Metropolis --run 216 --wait
```

**Output (during execution):**
```
Waiting for run #216 to complete (timeout: 3600s, polling every 10s)...

[0s] Run #216 status:
  Job 0: ● running    / Release build (ubuntu-latest . +nightly wasm32-unknown-unk
  Job 1: ○ pending    / Release build (macos-latest .   ) (push)
  Job 2: ○ pending    / Release build (ubuntu-latest .   ) (push)

[120s] Run #216 status:
  Job 0: ✓ success    / Release build (ubuntu-latest . +nightly wasm32-unknown-unk
  Job 1: ● running    / Release build (macos-latest .   ) (push)
  Job 2: ● running    / Release build (ubuntu-latest .   ) (push)

[480s] Run #216 status:
  Job 0: ✓ success    / Release build (ubuntu-latest . +nightly wasm32-unknown-unk
  Job 1: ✓ success    / Release build (macos-latest .   ) (push)
  Job 2: ✓ success    / Release build (ubuntu-latest .   ) (push)

================================================================================
✓ Run #216 completed successfully after 480s
```

**Exit code:** 0

**Claude should respond:** "Run 216 completed successfully! All 3 jobs passed after about 8 minutes. The build is ready to deploy."

---

## Example 5: Wait with Timeout

**Scenario:** User wants to wait for a build but with a shorter timeout.

**User asks:** "Wait for run 217 to complete but timeout after 10 minutes"

**Command:**
```bash
python scripts/gitea_builds.py Metropolis Metropolis --run 217 --wait --timeout 600
```

**If build completes successfully:**
```
✓ Run #217 completed successfully after 540s
```
Exit code: 0

**If build fails:**
```
✗ Run #217 completed with failures after 420s
```
Exit code: 1

**If timeout reached:**
```
✗ Timeout reached after 600s
```
Exit code: 127

---

## Example 6: Check Specific Branch

**Scenario:** User wants to check builds on a feature branch.

**User asks:** "Are the builds passing on the develop branch?"

**Command:**
```bash
python scripts/gitea_builds.py Metropolis Metropolis --branch develop
```

**Output:**
```
Fetching build status for Metropolis/Metropolis on branch 'develop' (checking last 10 commits)...

Run ID   SHA       Branch          Status     Jobs   Commit Message
--------------------------------------------------------------------------------------------------------------
220      7a8b9c0   develop         ✓ success  6      Merge feature-x into develop
219      6d7e8f1   develop         ✓ success  6      Add unit tests
218      5c6d7e2   develop         ✗ failure  6      WIP: refactoring
```

**Claude should respond:** "The develop branch looks good! The two most recent builds (220 and 219) are passing successfully. There was a failure in run 218 but that appears to be a work-in-progress commit. The latest merge (run 220) is all green with 6 successful jobs."

---

## Example 7: CI/CD Automation Script

**Scenario:** User wants to create a deployment script that waits for builds.

**User asks:** "Create a script that waits for build 225 and deploys if successful"

**Claude should create:**
```bash
#!/bin/bash
# deployment_script.sh

set -e

BUILD_RUN_ID=225
OWNER="Metropolis"
REPO="Metropolis"

echo "Waiting for build $BUILD_RUN_ID to complete..."

if python scripts/gitea_builds.py "$OWNER" "$REPO" --run "$BUILD_RUN_ID" --wait --timeout 1800; then
    echo "✓ Build succeeded! Starting deployment..."

    # Your deployment commands here
    ./deploy.sh

    echo "✓ Deployment complete!"
    exit 0
else
    exit_code=$?

    if [ $exit_code -eq 127 ]; then
        echo "✗ Build timed out after 30 minutes"
    else
        echo "✗ Build failed, not deploying"
    fi

    exit $exit_code
fi
```

---

## Example 8: Check Multiple Commits

**Scenario:** User wants to see build history for more commits.

**User asks:** "Show me the last 20 builds for Metropolis/Metropolis"

**Command:**
```bash
python scripts/gitea_builds.py Metropolis Metropolis --commits 20
```

This will check the last 20 commits for build information instead of the default 10.

---

## Example 9: Monitoring Running Build

**Scenario:** A build is currently running and user wants live updates.

**User asks:** "Monitor run 230 and show me updates"

**Command:**
```bash
python scripts/gitea_builds.py Metropolis Metropolis --run 230 --wait --timeout 3600
```

The script will poll every 10 seconds and show status changes as jobs progress from pending → running → success/failure.

---

## Example 10: Rerun Failed Workflow

**⚠️ IMPORTANT:** The rerun functionality requires Gitea PR #35382, which is **not yet merged** as of November 2025. This feature will be available in a future Gitea version (estimated v1.26+). Track progress at: https://github.com/go-gitea/gitea/pull/35382

**Scenario:** User fixed an issue and wants to rerun the entire failed workflow.

**User asks:** "I pushed a fix for the ARM64 issue. Please rerun run 215"

**Command:**
```bash
python scripts/gitea_builds.py Metropolis Metropolis --run 215 --rerun
```

**Output:**
```
Rerunning workflow run #215 (run ID: 1234)...
✓ Successfully triggered rerun of workflow run #215

View progress at: http://gitea.mermaid-gecko.ts.net:3000/Metropolis/Metropolis/actions/runs/215
```

**Claude should respond:** "I've successfully triggered a rerun of workflow run #215. All 6 jobs will be executed again. You can monitor the progress at the URL above, or use the --wait flag to wait for completion:
```bash
python scripts/gitea_builds.py Metropolis Metropolis --run 215 --wait
```"

---

## Example 11: Rerun Specific Failed Job

**Scenario:** Only one job failed, and user wants to rerun just that specific job.

**User asks:** "Only the Windows ARM64 build failed. Just rerun job 1006 from run 215"

**Command:**
```bash
python scripts/gitea_builds.py Metropolis Metropolis --run 215 --rerun-job 1006
```

**Output:**
```
Rerunning job 1006 from run #215 (run ID: 1234)...
✓ Successfully triggered rerun of job 1006

View progress at: http://gitea.mermaid-gecko.ts.net:3000/Metropolis/Metropolis/actions/runs/215
```

**Claude should respond:** "I've triggered a rerun of just job 1006 (the Windows ARM64 build) from run 215. The other 5 jobs won't be rerun since they already succeeded. You can watch the progress at the provided URL."

---

## Example 12: Rerun and Wait Pattern

**Scenario:** User wants to rerun a workflow and wait for it to complete.

**User asks:** "Rerun the failed build 215 and let me know when it finishes"

**Commands (sequential):**
```bash
# First, trigger the rerun
python scripts/gitea_builds.py Metropolis Metropolis --run 215 --rerun

# Then wait for it (note: this waits for the original run, not the new one)
# The new run will have a new run number
```

**Claude should respond:** "I've triggered the rerun. Note that the rerun will create a new workflow run with a new run number. To wait for the new run to complete, we'll need to:

1. First identify the new run number (it will be the most recent run)
2. Then use --wait on that new run

Let me check the latest runs to find the new run number..."

**Then execute:**
```bash
python scripts/gitea_builds.py Metropolis Metropolis
```

---

## Example 13: Quick Status Check

**Scenario:** User just wants a yes/no on whether latest build passed.

**User asks:** "Did the latest build pass?"

**Command:**
```bash
python scripts/gitea_builds.py Metropolis Metropolis
```

**Claude should:** Look at the first line of output and respond simply: "No, the latest build (run 215) failed. Would you like me to check what went wrong?"

---

## Example 14: Integration Testing Script

**Scenario:** Run tests only if build passes.

**User asks:** "Create a script that runs integration tests only if build 240 passes"

**Claude should create:**
```bash
#!/bin/bash

echo "Checking if build 240 passed..."

if python scripts/gitea_builds.py Metropolis Metropolis --run 240 --wait --timeout 900; then
    echo "Build passed! Running integration tests..."
    npm run test:integration
else
    echo "Build failed or timed out. Skipping integration tests."
    exit 1
fi
```

---

## Example 15: Automated Rerun and Deploy Script

**Scenario:** Create a script that automatically reruns failed builds and deploys on success.

**User asks:** "Create a deployment script that checks if the latest build passed, reruns it if failed, and deploys on success"

**Claude should create:**
```bash
#!/bin/bash
# smart_deploy.sh - Intelligent deployment with auto-retry

set -e

OWNER="Metropolis"
REPO="Metropolis"

echo "Checking latest build status..."

# Get latest run and check status
OUTPUT=$(python scripts/gitea_builds.py "$OWNER" "$REPO" | head -5)
LATEST_RUN=$(echo "$OUTPUT" | grep -oP 'Run ID\s+\K\d+' | head -1)
STATUS=$(echo "$OUTPUT" | grep "$LATEST_RUN" | grep -oP '(success|failure)')

echo "Latest run: $LATEST_RUN - Status: $STATUS"

if [ "$STATUS" = "failure" ]; then
    echo "Build failed. Attempting automatic rerun..."

    if python scripts/gitea_builds.py "$OWNER" "$REPO" --run "$LATEST_RUN" --rerun; then
        echo "Rerun triggered successfully. Waiting for completion..."

        # Wait a bit for the new run to start
        sleep 10

        # Get the new run number (should be latest now)
        NEW_OUTPUT=$(python scripts/gitea_builds.py "$OWNER" "$REPO" | head -5)
        NEW_RUN=$(echo "$NEW_OUTPUT" | grep -oP 'Run ID\s+\K\d+' | head -1)

        echo "New run #$NEW_RUN started. Waiting for completion..."

        if python scripts/gitea_builds.py "$OWNER" "$REPO" --run "$NEW_RUN" --wait --timeout 1800; then
            echo "✓ Rerun succeeded! Proceeding with deployment..."
            ./deploy.sh
            echo "✓ Deployment complete!"
        else
            echo "✗ Rerun failed. Deployment aborted."
            exit 1
        fi
    else
        echo "✗ Failed to trigger rerun. Deployment aborted."
        exit 1
    fi
elif [ "$STATUS" = "success" ]; then
    echo "✓ Latest build passed! Deploying..."
    ./deploy.sh
    echo "✓ Deployment complete!"
else
    echo "✗ Could not determine build status. Deployment aborted."
    exit 1
fi
```

**Explanation:** This script demonstrates:
1. Checking if the latest build passed or failed
2. Automatically triggering a rerun if it failed
3. Waiting for the rerun to complete
4. Deploying only if the build succeeds

---

## Common Troubleshooting Examples

### Run not found
```bash
python scripts/gitea_builds.py Metropolis Metropolis --run 999
```
Output: `Run #999 not found in last 10 commits`

**Solution:** Increase commit search limit:
```bash
python scripts/gitea_builds.py Metropolis Metropolis --run 999 --commits 50
```

### Connection issues
If you see connection errors, verify Tailscale is running:
```bash
tailscale status
```

The Gitea instance requires Tailscale network access.
