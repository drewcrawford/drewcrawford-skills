#!/bin/bash

# Export Claude Code transcript for escalation
# This script now reads the rich per-project JSONL logs that include tool calls,
# not just the slim history.jsonl display strings.

set -euo pipefail

# Generate timestamp for filenames
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TRANSCRIPT_FILE="stuck_transcript_${TIMESTAMP}.md"
DIAGNOSTICS_FILE="stuck_diagnostics_${TIMESTAMP}.md"

echo "🔍 Exporting Claude Code session transcript..."

# IMPORTANT: History is not written while Claude Code is running
echo "⏳ Note: Messages are NOT written to history.jsonl while Claude Code is running"
echo "   You must Ctrl+C to interrupt the session first to flush messages to disk"
echo ""

# Compute project directory used by Claude's per-project logs
PROJECT_PATH="$(pwd -P)"
PROJECT_KEY=$(printf '%s' "$PROJECT_PATH" | sed 's/[^A-Za-z0-9]/-/g')
PROJECT_LOG_DIR="$HOME/.claude/projects/$PROJECT_KEY"

# Start the transcript file
{
  echo "# Claude Code Session Transcript"
  echo "## Export Time: $(date)"
  echo "## Working Directory: $PROJECT_PATH"
  echo "## Project Log Directory: $PROJECT_LOG_DIR"
  echo ""
} > "$TRANSCRIPT_FILE"

SESSION_JSONL=""
SESSION_ID=""

# Method 1: Use the rich project logs (includes tool calls)
if [ -d "$PROJECT_LOG_DIR" ]; then
    SESSION_JSONL=$(python3 - "$PROJECT_LOG_DIR" <<'PY' || true
import os, re, sys
project_dir = sys.argv[1]
session_re = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\.jsonl$', re.IGNORECASE)
candidates = []
for name in os.listdir(project_dir):
    if session_re.match(name) and not name.startswith("agent-"):
        path = os.path.join(project_dir, name)
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        candidates.append((mtime, path))
if not candidates:
    sys.exit(1)
candidates.sort(reverse=True)
print(candidates[0][1])
PY
)

    if [ -n "$SESSION_JSONL" ] && [ -f "$SESSION_JSONL" ]; then
        SESSION_ID=$(basename "$SESSION_JSONL" .jsonl)
        {
          echo "## Session ID: $SESSION_ID"
          echo ""
          echo "---"
          echo ""
          echo "## Detailed Transcript (from project log)"
          echo ""
        } >> "$TRANSCRIPT_FILE"

        python3 - "$SESSION_JSONL" >> "$TRANSCRIPT_FILE" <<'PY'
import json, sys, textwrap

path = sys.argv[1]

def render_content(content):
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            btype = block.get("type")
            if btype == "text":
                parts.append(block.get("text", ""))
            elif btype == "tool_use":
                tool_name = block.get("name", "unknown-tool")
                tool_id = block.get("id", "")
                tool_input = block.get("input", {})
                parts.append(f"[tool_use:{tool_name} id={tool_id}] input:\n```json\n{textwrap.indent(json.dumps(tool_input, indent=2), '')}\n```")
            elif btype == "tool_result":
                parts.append(f"[tool_result for {block.get('tool_use_id','unknown')}] {block.get('content','')}")
            else:
                parts.append(f"[{btype}] {json.dumps(block, ensure_ascii=False)}")
        return "\n\n".join(part for part in parts if part.strip())
    if isinstance(content, dict):
        return json.dumps(content, indent=2, ensure_ascii=False)
    return str(content or "")

with open(path, "r", encoding="utf-8") as f:
    for line in f:
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        msg = entry.get("message", {})
        role = msg.get("role") or entry.get("type") or "unknown"
        ts = entry.get("timestamp", "")
        uuid = entry.get("uuid", "")
        model = msg.get("model")
        meta_bits = []
        if model:
            meta_bits.append(f"model={model}")
        if uuid:
            meta_bits.append(f"id={uuid}")
        if entry.get("cwd"):
            meta_bits.append(f"cwd={entry['cwd']}")
        header = f"### {ts} [{role}]"
        if meta_bits:
            header += " (" + ", ".join(meta_bits) + ")"
        print(header)
        content = msg.get("content")
        body = render_content(content)
        if body:
            print()
            print(body)
        if entry.get("toolUseResult"):
            print()
            print("Tool output metadata:")
            print("```json")
            print(json.dumps(entry["toolUseResult"], indent=2, ensure_ascii=False))
            print("```")
        print()
        print("---")
        print()
PY
    fi
else
    echo "No project log directory found at $PROJECT_LOG_DIR" >&2
fi

# Method 2: Fallback to history.jsonl (older, lacks tool calls)
if [ -z "$SESSION_ID" ] && [ -f ~/.claude/history.jsonl ]; then
    echo "Attempting to extract from history.jsonl (no tool calls)..." >&2
    SESSION_ID=$(tail -1 ~/.claude/history.jsonl | jq -r '.sessionId' 2>/dev/null || echo "")

    if [ -n "$SESSION_ID" ]; then
        {
          echo "## Session ID (history.jsonl): $SESSION_ID"
          echo ""
          echo "---"
          echo ""
        } >> "$TRANSCRIPT_FILE"

        cat ~/.claude/history.jsonl | \
            jq -r 'select(.sessionId == "'$SESSION_ID'") |
                   "### " + (.timestamp | tostring) + "\n" + .display' \
            >> "$TRANSCRIPT_FILE" 2>/dev/null || true
    fi
fi

# Method 3: Check for debug logs (if --debug was used)
if [ -d ~/.claude/debug ]; then
    echo "Checking for debug logs..."
    shopt -s nullglob
    DEBUG_FILES=(~/.claude/debug/*.log ~/.claude/debug/*.txt)
    if [ ${#DEBUG_FILES[@]} -gt 0 ]; then
        LATEST_DEBUG=$(ls -t "${DEBUG_FILES[@]}" | head -1)
        if [ -n "$LATEST_DEBUG" ]; then
            echo "Found debug log: $LATEST_DEBUG"

            # Append debug information
            {
              echo ""
              echo "---"
              echo "## Debug Log Extract"
              echo ""
              tail -500 "$LATEST_DEBUG" 2>/dev/null || true
            } >> "$TRANSCRIPT_FILE"
        fi
    fi
    shopt -u nullglob
fi

# Method 4: Capture current shell history for context
{
  echo ""
  echo "---"
  echo "## Recent Shell Commands"
  echo ""
  echo '```bash'
  history | tail -50 2>/dev/null || true
  echo '```'
} >> "$TRANSCRIPT_FILE"

# Create git status snapshot
if git rev-parse --git-dir > /dev/null 2>&1; then
    {
      echo ""
      echo "---"
      echo "## Git Status at Escalation"
      echo ""
      echo '```'
      git status 2>/dev/null || true
      echo '```'

      echo ""
      echo "## Recent Git Commits"
      echo ""
      echo '```'
      git log --oneline -10 2>/dev/null || true
      echo '```'

      echo ""
      echo "## Uncommitted Changes"
      echo ""
      echo '```diff'
      git diff HEAD 2>/dev/null || true
      echo '```'
    } >> "$TRANSCRIPT_FILE"
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
