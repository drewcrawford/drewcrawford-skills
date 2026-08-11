#!/bin/sh

# Install this repository's Agent Skills once, then expose them to clients that
# still use a client-specific discovery directory.

set -eu

if [ -z "${HOME:-}" ]; then
    echo "Error: HOME is not set" >&2
    exit 1
fi

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
SKILLS_DIR="$SCRIPT_DIR/skills"
AGENT_SKILLS_DIR=${AGENT_SKILLS_DIR:-"$HOME/.agents/skills"}
CLAUDE_SKILLS_DIR=${CLAUDE_SKILLS_DIR:-"$HOME/.claude/skills"}
MANIFEST="$AGENT_SKILLS_DIR/.drewcrawford-skills.manifest"
NEXT_MANIFEST="$MANIFEST.tmp.$$"

if [ -t 1 ]; then
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    NC='\033[0m'
else
    GREEN=''
    YELLOW=''
    NC=''
fi

cleanup() {
    rm -f "$NEXT_MANIFEST"
}
trap cleanup EXIT HUP INT TERM

is_valid_skill_name() {
    case "$1" in
        ''|-*|*-|*--*|*[!a-z0-9-]*) return 1 ;;
        *) return 0 ;;
    esac
}

path_exists() {
    [ -e "$1" ] || [ -L "$1" ]
}

paths_overlap() {
    case "$1/" in
        "$2/"*) return 0 ;;
        *) return 1 ;;
    esac
}

if [ "$AGENT_SKILLS_DIR" = "$CLAUDE_SKILLS_DIR" ]; then
    echo "Error: AGENT_SKILLS_DIR and CLAUDE_SKILLS_DIR must be different" >&2
    exit 1
fi
if paths_overlap "$AGENT_SKILLS_DIR" "$SKILLS_DIR" ||
   paths_overlap "$SKILLS_DIR" "$AGENT_SKILLS_DIR" ||
   paths_overlap "$CLAUDE_SKILLS_DIR" "$SKILLS_DIR" ||
   paths_overlap "$SKILLS_DIR" "$CLAUDE_SKILLS_DIR"; then
    echo "Error: install directories must not overlap the source skills directory" >&2
    exit 1
fi

mkdir -p "$AGENT_SKILLS_DIR" "$CLAUDE_SKILLS_DIR"
: > "$NEXT_MANIFEST"

# Migrate the two pre-standard names previously shipped by this repository.
# Match their declared names so similarly named, unrelated directories survive.
for legacy_name in release_prep update_config_toml; do
    legacy_path="$CLAUDE_SKILLS_DIR/$legacy_name"
    if [ -L "$legacy_path" ]; then
        printf '%bRemoving renamed Claude entry%b %s\n' "$YELLOW" "$NC" "$legacy_name"
        rm "$legacy_path"
    elif [ -f "$legacy_path/SKILL.md" ] && grep -Fqx "name: $legacy_name" "$legacy_path/SKILL.md"; then
        printf '%bRemoving renamed Claude entry%b %s\n' "$YELLOW" "$NC" "$legacy_name"
        rm -rf "$legacy_path"
    fi
done

skill_count=0
for skill_path in "$SKILLS_DIR"/*; do
    [ -f "$skill_path/SKILL.md" ] || continue

    skill_name=${skill_path##*/}
    if ! is_valid_skill_name "$skill_name"; then
        echo "Error: invalid Agent Skills directory name: $skill_name" >&2
        exit 1
    fi

    target_path="$AGENT_SKILLS_DIR/$skill_name"
    staging_path="$AGENT_SKILLS_DIR/.$skill_name.tmp.$$"

    printf '%s\n' "$skill_name" >> "$NEXT_MANIFEST"
    if path_exists "$target_path"; then
        printf '%bUpdating%b %s\n' "$YELLOW" "$NC" "$skill_name"
    else
        printf '%bInstalling%b %s\n' "$GREEN" "$NC" "$skill_name"
    fi

    rm -rf "$staging_path"
    cp -R "$skill_path" "$staging_path"
    rm -rf "$staging_path/.claude"
    find "$staging_path" -type f -name .DS_Store -exec rm -f {} \;
    rm -rf "$target_path"
    mv "$staging_path" "$target_path"

    claude_path="$CLAUDE_SKILLS_DIR/$skill_name"
    if [ -L "$claude_path" ] && [ "$(readlink "$claude_path")" = "$target_path" ]; then
        :
    else
        if path_exists "$claude_path"; then
            printf '%bReplacing Claude entry%b %s\n' "$YELLOW" "$NC" "$skill_name"
            rm -rf "$claude_path"
        fi
        ln -s "$target_path" "$claude_path"
    fi

    skill_count=$((skill_count + 1))
done

if [ "$skill_count" -eq 0 ]; then
    echo "Error: no skill directories found in $SKILLS_DIR" >&2
    exit 1
fi

# Remove only skills recorded in this installer's previous manifest. Never
# garbage-collect arbitrary directories from a shared client skills folder.
deleted_count=0
if [ -f "$MANIFEST" ]; then
    while IFS= read -r old_name; do
        is_valid_skill_name "$old_name" || continue
        if grep -Fqx "$old_name" "$NEXT_MANIFEST"; then
            continue
        fi

        old_target="$AGENT_SKILLS_DIR/$old_name"
        old_claude_path="$CLAUDE_SKILLS_DIR/$old_name"
        if [ -L "$old_claude_path" ] && [ "$(readlink "$old_claude_path")" = "$old_target" ]; then
            rm "$old_claude_path"
        fi
        if path_exists "$old_target"; then
            printf '%bRemoving retired skill%b %s\n' "$YELLOW" "$NC" "$old_name"
            rm -rf "$old_target"
            deleted_count=$((deleted_count + 1))
        fi
    done < "$MANIFEST"
fi

mv "$NEXT_MANIFEST" "$MANIFEST"
trap - EXIT HUP INT TERM

printf '\n%bInstalled %s Agent Skill(s)%b in %s\n' "$GREEN" "$skill_count" "$NC" "$AGENT_SKILLS_DIR"
printf 'Claude Code links: %s\n' "$CLAUDE_SKILLS_DIR"
if [ "$deleted_count" -gt 0 ]; then
    printf '%bRemoved %s retired skill(s)%b\n' "$YELLOW" "$deleted_count" "$NC"
fi

if [ -d "$HOME/.codex/skills" ]; then
    printf '\nNote: ~/.codex/skills is a legacy location and was left untouched.\n'
fi
