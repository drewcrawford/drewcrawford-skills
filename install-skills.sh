#!/usr/bin/env bash

# Install skills to ~/.claude/skills
# This script copies all skill directories to the Claude skills directory,
# replacing any existing versions.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/.claude/skills"

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "Installing skills to $TARGET_DIR"
echo

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Find all directories containing SKILL.md
skill_dirs=()
while IFS= read -r skill_file; do
    skill_dir="$(dirname "$skill_file")"
    skill_dirs+=("$skill_dir")
done < <(find "$SCRIPT_DIR" -maxdepth 2 -name "SKILL.md" -type f)

# Copy each skill directory
for skill_path in "${skill_dirs[@]}"; do
    skill_name="$(basename "$skill_path")"
    target_path="$TARGET_DIR/$skill_name"

    if [ -d "$target_path" ]; then
        echo -e "${YELLOW}Replacing${NC} $skill_name"
        rm -rf "$target_path"
    else
        echo -e "${GREEN}Installing${NC} $skill_name"
    fi

    cp -r "$skill_path" "$target_path"
done

echo
echo -e "${GREEN}✓${NC} Successfully installed ${#skill_dirs[@]} skill(s)"
echo
echo "Installed skills:"
for skill_path in "${skill_dirs[@]}"; do
    echo "  - $(basename "$skill_path")"
done
