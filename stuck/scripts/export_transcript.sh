#!/bin/bash

# Export Claude Code transcript for escalation
# This script attempts multiple methods to capture the current session

set -e

# Generate timestamp for filenames
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TRANSCRIPT_FILE="stuck_transcript_${TIMESTAMP}.md"
DIAGNOSTICS_FILE="stuck_diagnostics_${TIMESTAMP}.md"

echo "🔍 Exporting Claude Code session transcript..."

# IMPORTANT: History is not written while Claude Code is running
echo "⏳ Note: Messages are NOT written to history.jsonl while Claude Code is running"
echo "   You must Ctrl+C to interrupt the session first to flush messages to disk"
echo ""

# Method 1: Try to get the current session ID and extract from history.jsonl
if [ -f ~/.claude/history.jsonl ]; then
    echo "Attempting to extract from history.jsonl..."

    # Get the most recent session ID
    SESSION_ID=$(tail -1 ~/.claude/history.jsonl | jq -r '.sessionId' 2>/dev/null || echo "")

    if [ -n "$SESSION_ID" ]; then
        echo "Found session ID: $SESSION_ID"

        # Create the transcript with full conversation
        echo "# Claude Code Session Transcript" > "$TRANSCRIPT_FILE"
        echo "## Session ID: $SESSION_ID" >> "$TRANSCRIPT_FILE"
        echo "## Export Time: $(date)" >> "$TRANSCRIPT_FILE"
        echo "## Working Directory: $(pwd)" >> "$TRANSCRIPT_FILE"
        echo "" >> "$TRANSCRIPT_FILE"
        echo "---" >> "$TRANSCRIPT_FILE"
        echo "" >> "$TRANSCRIPT_FILE"

        # Extract all messages from this session
        cat ~/.claude/history.jsonl | \
            jq -r 'select(.sessionId == "'$SESSION_ID'") |
                   "### " + (.timestamp | tostring) + "\n" + .display' \
            >> "$TRANSCRIPT_FILE" 2>/dev/null || true
    fi
fi

# Method 2: Check for debug logs (if --debug was used)
if [ -d ~/.claude/debug ]; then
    echo "Checking for debug logs..."

    # Find the most recent debug log
    LATEST_DEBUG=$(ls -t ~/.claude/debug/*.log 2>/dev/null | head -1)

    if [ -n "$LATEST_DEBUG" ]; then
        echo "Found debug log: $LATEST_DEBUG"

        # Append debug information
        echo "" >> "$TRANSCRIPT_FILE"
        echo "---" >> "$TRANSCRIPT_FILE"
        echo "## Debug Log Extract" >> "$TRANSCRIPT_FILE"
        echo "" >> "$TRANSCRIPT_FILE"

        # Get last 500 lines of debug log (adjust as needed)
        tail -500 "$LATEST_DEBUG" >> "$TRANSCRIPT_FILE" 2>/dev/null || true
    fi
fi

# Method 3: Capture current shell history for context
echo "" >> "$TRANSCRIPT_FILE"
echo "---" >> "$TRANSCRIPT_FILE"
echo "## Recent Shell Commands" >> "$TRANSCRIPT_FILE"
echo "" >> "$TRANSCRIPT_FILE"
echo '```bash' >> "$TRANSCRIPT_FILE"
history | tail -50 >> "$TRANSCRIPT_FILE" 2>/dev/null || true
echo '```' >> "$TRANSCRIPT_FILE"

# Create git status snapshot
if git rev-parse --git-dir > /dev/null 2>&1; then
    echo "" >> "$TRANSCRIPT_FILE"
    echo "---" >> "$TRANSCRIPT_FILE"
    echo "## Git Status at Escalation" >> "$TRANSCRIPT_FILE"
    echo "" >> "$TRANSCRIPT_FILE"
    echo '```' >> "$TRANSCRIPT_FILE"
    git status >> "$TRANSCRIPT_FILE" 2>/dev/null || true
    echo '```' >> "$TRANSCRIPT_FILE"

    echo "" >> "$TRANSCRIPT_FILE"
    echo "## Recent Git Commits" >> "$TRANSCRIPT_FILE"
    echo "" >> "$TRANSCRIPT_FILE"
    echo '```' >> "$TRANSCRIPT_FILE"
    git log --oneline -10 >> "$TRANSCRIPT_FILE" 2>/dev/null || true
    echo '```' >> "$TRANSCRIPT_FILE"

    echo "" >> "$TRANSCRIPT_FILE"
    echo "## Uncommitted Changes" >> "$TRANSCRIPT_FILE"
    echo "" >> "$TRANSCRIPT_FILE"
    echo '```diff' >> "$TRANSCRIPT_FILE"
    git diff HEAD >> "$TRANSCRIPT_FILE" 2>/dev/null || true
    echo '```' >> "$TRANSCRIPT_FILE"
fi

# Check if we got any content
if [ -s "$TRANSCRIPT_FILE" ]; then
    echo "✅ Transcript exported to: $TRANSCRIPT_FILE"
    echo "   Size: $(du -h "$TRANSCRIPT_FILE" | cut -f1)"
else
    echo "⚠️  Warning: Transcript file is empty or very small"
    echo "   You may need to manually copy the conversation from the Claude Code interface"
fi

echo ""
echo "📋 Next steps:"
echo "1. Review the transcript file: $TRANSCRIPT_FILE"
echo "2. Create diagnostic summary if needed"
echo "3. Share with senior agent or user for escalation"
echo ""
echo "💡 Tip: For better transcripts in future, consider running Claude Code with --debug flag"