# Stuck Detection and Escalation Skill

This skill helps Claude Code agents recognize when they're stuck and need assistance from a more experienced agent or human.

**⚠️ Important**: This skill and its scripts are currently **Claude Code specific**. The export scripts read from `~/.claude/history.jsonl`, which is only created by Claude Code. For other AI assistants (ChatGPT, Gemini, etc.), the scripts would need to be adapted to their session storage formats.

## 📋 Overview

The skill monitors for patterns that indicate an agent is stuck:
- Time-based (working on same issue for 15+ minutes)
- Failure patterns (multiple test timeouts, repeated errors)
- Behavioral patterns (trying same approach with minor variations)
- Self-awareness ("I'm overcomplicating this")

## 🎯 Trigger Conditions

Based on analysis of real stuck agent behavior, the skill triggers on:

### Quantitative Triggers
- **3+ test runs** that hang or require KillShell
- **3+ different approaches** attempted without success
- **5+ similar edits** to same code section
- **15+ minutes** on the same error
- **10+ compilation attempts** in a loop

### Qualitative Triggers
- Agent says "I'm overcomplicating this"
- Agent says "Let me try a completely different approach" repeatedly
- Multiple "Still waiting..." with no progress
- Recognition of analysis paralysis

## 📁 Files in this Skill

```
stuck/
├── SKILL.md                    # Main skill definition (required)
├── README.md                    # This documentation file
├── export_transcript.sh         # Bash script to export session transcript
└── analyze_stuck_patterns.py   # Python analyzer to detect stuck patterns
```

## 🔧 How It Works

1. **Detection**: The agent recognizes stuck patterns
2. **Stop Work**: Agent immediately stops attempting to solve the problem
3. **Request User Action**: Agent asks user to Ctrl+C and run export scripts
4. **User Exports Data**: User manually runs scripts to capture session
5. **Escalation**: User provides exported data to a senior agent
6. **Handoff**: Senior agent reviews the exported data and diagnoses issue

## 🚀 Usage

### For Agents

The skill will be automatically available to Claude Code. When stuck, the agent should:

1. Recognize the stuck pattern
2. Stop immediately (no "one more try")
3. Present escalation request to user with clear instructions to:
   - Press Ctrl+C (to flush history to disk)
   - Run the export scripts manually
   - Provide artifacts to a new agent session

### For Humans

To manually check if an agent is stuck:

```bash
# Run the pattern analyzer
python3 stuck/scripts/analyze_stuck_patterns.py

# Export the current session
./stuck/scripts/export_transcript.sh
```

**Important Note on Transcript Export**: The `history.jsonl` file is **NOT written while Claude Code is running**. Messages only appear after:
- You interrupt the session with Ctrl+C
- The session ends naturally

There is no incremental writing - you MUST interrupt the session to export the current conversation.

### For Senior Agents

When reviewing an escalation:

1. Read the diagnostic files created by the stuck agent
2. Review the transcript for context
3. Identify:
   - Root cause of the blocking issue
   - Whether the approach was fundamentally flawed
   - What information/knowledge was missing
   - Recommended solution path

## 📊 Pattern Analysis

The analyzer checks for:

- **Time patterns**: How long on same task
- **Error patterns**: Repetitive errors
- **Behavioral patterns**: Approach changes, compilation loops
- **Command patterns**: KillShell usage, test timeouts
- **Language patterns**: Self-aware stuck phrases

## 💡 Example Stuck Scenarios

### Scenario 1: Arc Ownership Issue
- Pattern: 6+ attempts to fix "cannot move out of Arc"
- Time: 20 minutes
- Solution: Redesign data structure instead of fighting ownership

### Scenario 2: Async Test Hangs
- Pattern: 4 test runs timeout, each killed
- Time: 25 minutes
- Solution: Fix async/await race condition

### Scenario 3: Over-Engineering
- Pattern: Progressively complex solutions to simple problem
- Trigger: "I'm overcomplicating this"
- Solution: Step back and simplify approach

## 🔍 Diagnostic Information

The skill captures:

1. **Session transcript** (conversation history)
2. **Error patterns** (repeated errors)
3. **Command history** (what was tried)
4. **Git status** (code changes)
5. **Time metrics** (how long stuck)
6. **Pattern analysis** (what indicates stuck)

## 🎓 Learning from Escalations

Each escalation provides learning opportunity:

1. **Pattern Recognition**: What indicated being stuck?
2. **Root Cause**: Why did the approach fail?
3. **Missing Knowledge**: What information would have helped?
4. **Better Approach**: How should it be solved?

## 🔄 Continuous Improvement

This skill should be updated based on:

- New stuck patterns observed
- False positives (triggered when not actually stuck)
- False negatives (didn't trigger when stuck)
- Feedback from senior agents on escalations

## 📈 Success Metrics

The skill is successful when:

- Agents recognize being stuck within 15 minutes
- Escalations include sufficient diagnostic information
- Senior agents can quickly identify the root cause
- Time-to-resolution improves after escalation

## 🤝 Contributing

To improve this skill:

1. Add new patterns to SKILL.md when discovered
2. Update analyzer with new detection logic
3. Improve transcript export methods
4. Share learnings from escalations

### 🔮 Future Extensions for Other AI Assistants

To support other AI coding assistants, we would need:

**For ChatGPT/OpenAI**:
- Script to export from their session format
- Potentially use browser automation or API if available

**For Google Gemini**:
- Script to capture Gemini conversation history
- May need different storage location detection

**For Local Models**:
- Depends on the interface being used (Continue, Cursor, etc.)
- Each would need its own export mechanism

**Universal Approach**:
- Consider having the agent output a structured summary that can be copied
- Use a common intermediate format for all assistants
- Possibly integrate with IDE history if available

Remember: Asking for help quickly is better than struggling for hours. This skill helps agents fail fast and learn faster.