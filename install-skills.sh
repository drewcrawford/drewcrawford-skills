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

# Get list of existing skills before installation
existing_skills=()
if [ -d "$TARGET_DIR" ]; then
    while IFS= read -r -d '' dir; do
        existing_skills+=("$(basename "$dir")")
    done < <(find "$TARGET_DIR" -mindepth 1 -maxdepth 1 -type d -print0)
fi

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

# Build list of installed skill names
installed_names=()
for skill_path in "${skill_dirs[@]}"; do
    installed_names+=("$(basename "$skill_path")")
done

# Delete old skills that are no longer in the source
deleted_count=0
for existing in "${existing_skills[@]}"; do
    found=false
    for installed in "${installed_names[@]}"; do
        if [ "$existing" = "$installed" ]; then
            found=true
            break
        fi
    done
    if [ "$found" = false ]; then
        echo -e "${YELLOW}Deleting${NC} $existing (no longer in source)"
        rm -rf "$TARGET_DIR/$existing"
        ((deleted_count++)) || true
    fi
done

echo
echo -e "${GREEN}✓${NC} Successfully installed ${#skill_dirs[@]} skill(s)"
if [ "$deleted_count" -gt 0 ]; then
    echo -e "${YELLOW}✓${NC} Deleted $deleted_count old skill(s)"
fi
echo
echo "Installed skills:"
for skill_path in "${skill_dirs[@]}"; do
    echo "  - $(basename "$skill_path")"
done
