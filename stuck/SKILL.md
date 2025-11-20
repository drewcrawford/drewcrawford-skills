---
name: stuck
description: Detect when stuck on a problem and escalate to user. Use when you've tried multiple approaches without success, tests keep hanging or timing out, or you've spent >15 minutes on the same error. Also use when you find yourself saying "I'm overcomplicating this" or repeating similar failed attempts.
---

# Stuck Detection and Escalation

This skill helps you recognize when you're stuck and need help from a more experienced agent or the user.

## When to Use This Skill

You should invoke this skill when you detect ANY of the following patterns:

### Time-Based Triggers
- You've been working on the same error/issue for **15+ minutes**
- You've been in a compile-fix-compile loop for **10+ minutes**
- Tests have been hanging for **5+ minutes** total across multiple runs

### Failure Pattern Triggers
- **3+ test runs** that hang or timeout (requiring KillShell)
- **3+ different approaches** to the same problem have failed
- **5+ similar edits** to the same code section without progress
- Multiple "Still waiting..." or "Checking..." messages with no resolution

### Self-Awareness Triggers
- You say phrases like:
  - "I'm overcomplicating this"
  - "Let me try a completely different approach" (for the 3rd+ time)
  - "The test is hanging again"
  - "This approach isn't working either"
- You're stuck in analysis paralysis (considering many options without committing)
- You recognize you're repeating the same flawed approach with minor variations

## What This Skill Does

1. **Stop Current Work** - Immediately cease working on the stuck task
2. **Generate Diagnostic Report** - Create a comprehensive report for escalation
3. **Export Session Transcript** - Save the full conversation history
4. **Request Escalation** - Ask the user for help or escalation to a senior agent

## Agent Self-Identification

Before following this skill, verify which environment you're running in:

Fast decision guide:
- If you see tools like `TodoWrite`, `Task`, `AskUserQuestion`, `KillShell` and a system prompt saying you're Claude Code ⇒ follow Claude Code.
- If you have a `task_boundary` tool or explicit PLANNING/EXECUTION/VERIFICATION modes ⇒ follow Antigravity.
- If your system prompt says you're Codex/GPT-5 and you have tools like `shell_command` and `apply_patch` (but none of the above) ⇒ follow OpenAI Codex CLI.
- If none of these match, use the Other AI Assistant path.

### Claude Code
**How to identify**: Your system prompt contains "You are Claude Code, Anthropic's official CLI for Claude" and you have tools like `TodoWrite`, `Task`, `AskUserQuestion`, `KillShell`.

If you're in Claude Code: Follow all instructions in this skill. The export scripts read from `~/.claude/history.jsonl`.

### OpenAI Codex CLI (GPT-5)
**How to identify**: Your system prompt says you're Codex (GPT-5). You have tools like `shell_command`, `apply_patch`, `update_plan`, `view_image`, but not `TodoWrite`, `Task`, `AskUserQuestion`, `KillShell`, or `task_boundary`.

If you're in Codex CLI:
1. Immediately stop the stuck task.
2. Prepare the status report from Step 2.
3. Save that report locally to `stuck_status.md` in the current working directory.
4. Ask the user to save/export the Codex CLI transcript manually and share it together with `stuck_status.md` to a senior agent.
5. Skip the Claude export scripts—they will not work here.

### Antigravity (Google DeepMind Advanced Agentic Coding)
**How to identify**: You have a `task_boundary` tool, or operate in PLANNING/EXECUTION/VERIFICATION modes.

If you're in Antigravity:
1. **Immediately abandon the original stuck task**
2. **Skip the export scripts** - they won't work for you
3. Dump your complete transcript directly to a markdown file in the working directory
4. Follow Step 2 (Prepare Status Report) but skip Step 3's script commands

### Other AI Assistants
**How to identify**: You don't match any of the patterns above (not Claude Code, not Antigravity, not Codex CLI).

If you're in another environment:
1. The Claude Code export scripts will fail or export an unrelated session
2. **HALT and ask the user**: "I'm running in [your environment] and need agent-specific export instructions for this skill"
3. Do NOT attempt the export scripts

## Instructions

When you detect you're stuck, follow these steps:

**Important**: As soon as a trigger matches, stop working on the task and switch to the environment-specific instructions above.

### Step 1: Stop Working
Immediately stop trying to solve the current problem. Don't attempt "one more fix."

### Step 2: Prepare Status Report
Create a concise summary including:
- **Task**: What you were trying to accomplish
- **Approaches Tried**: List each distinct approach you attempted
- **Failure Points**: Where/why each approach failed
- **Time Spent**: Approximate time on this issue
- **Pattern Detected**: Which trigger caused the escalation
- **Key Error Messages**: The most important errors encountered
- **Files Modified**: Main files you were working on

### Step 3: Request User Action for Export

Present this message to the user requesting they export the session:

```
🚨 **ESCALATION REQUEST - USER ACTION REQUIRED** 🚨

I've detected that I'm stuck on the current task and need assistance.

**Stuck Pattern Detected**: [Specify which trigger(s) matched]

**Summary**: [Your 2-3 sentence summary from Step 2]

**TO EXPORT THIS SESSION FOR REVIEW:**

1. **Press Ctrl+C** to interrupt this session (this flushes the conversation to disk)

2. **Run these commands manually** in your terminal:
   ```bash
   cd [current_working_directory]
   ./stuck/scripts/export_transcript.sh
   ./stuck/scripts/analyze_stuck_patterns.py
   ```

3. **Review the generated files**:
   - `stuck_transcript_YYYYMMDD_HHMMSS.md` - Full conversation transcript
   - Pattern analysis output from the analyzer

4. **Start a new session** with a senior agent (more expensive model) and provide:
   - The transcript file
   - The pattern analysis
   - This summary of what I was stuck on

**My Diagnostic Summary**:
[Include your full status report from Step 2 here]

**Note**: The export scripts are Claude Code specific. They read from ~/.claude/history.jsonl.
If you're using a different AI assistant in the future, you'll need different export methods.
```

## Examples

### Example 1: Test Timeout Loop
```
Trigger: 4 test runs have timed out, requiring KillShell each time
Pattern: Repeatedly trying to fix async test that hangs
Time: 25 minutes on same test
Action: Stop and escalate with timeout pattern details
```

### Example 2: Ownership/Borrowing Confusion
```
Trigger: 6 attempts to fix "cannot move out of Arc" error
Pattern: Minor variations of Arc::try_unwrap approach
Time: 20 minutes on ownership issue
Action: Stop and escalate with compilation error pattern
```

### Example 3: Self-Recognized Complexity
```
Trigger: Said "I'm overcomplicating this" twice
Pattern: Progressively more complex solutions to simple problem
Time: 18 minutes
Action: Stop and escalate noting over-engineering pattern
```

## Important Notes

- **Don't wait too long**: It's better to escalate at 15 minutes than waste an hour
- **Be specific**: The more detail in your diagnostic report, the faster the senior agent can help
- **Include context**: Always export the transcript - it contains valuable debugging information
- **Learn from escalations**: Each escalation is a learning opportunity

Remember: Recognizing when you're stuck and asking for help is a sign of good judgment, not failure. The goal is efficient problem-solving, not struggling alone.
