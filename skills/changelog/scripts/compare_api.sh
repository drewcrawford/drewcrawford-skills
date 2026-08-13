#!/usr/bin/env bash

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: compare_api.sh [OPTIONS] [TAG]

Compare a Rust crate's public API at TAG with the current working tree without
stashing changes or switching the user's checkout.

Options:
  --root PATH       Crate directory (default: cwd)
  --output-dir DIR  Preserve old.txt and new.txt in DIR
  --abbreviated     Omit blanket, auto-trait, and auto-derived implementations
  -l, --list        List available tags and exit
  -h, --help        Show this help and exit
EOF
}

root=.
output_dir=
abbreviated=false
tag=
while [ "$#" -gt 0 ]; do
    case "$1" in
        --root)
            [ "$#" -ge 2 ] || { echo "Error: --root requires a path" >&2; usage >&2; exit 2; }
            root=$2
            shift 2
            ;;
        --output-dir)
            [ "$#" -ge 2 ] || { echo "Error: --output-dir requires a path" >&2; usage >&2; exit 2; }
            output_dir=$2
            shift 2
            ;;
        --abbreviated) abbreviated=true; shift ;;
        -l|--list) git -C "$root" tag --sort=-v:refname; exit 0 ;;
        -h|--help) usage; exit 0 ;;
        -*) echo "Error: unknown argument: $1" >&2; usage >&2; exit 2 ;;
        *)
            [ -z "$tag" ] || { echo "Error: only one TAG may be supplied" >&2; usage >&2; exit 2; }
            tag=$1
            shift
            ;;
    esac
done

[ -d "$root" ] || { echo "Error: root is not a directory: $root" >&2; exit 2; }
root=$(cd "$root" && pwd)
repo_root=$(git -C "$root" rev-parse --show-toplevel)
prefix=$(git -C "$root" rev-parse --show-prefix)
if [ -z "$tag" ]; then
    tag=$(git -C "$root" tag --sort=-v:refname | head -1)
    [ -n "$tag" ] || { echo "Error: no tags found in repository" >&2; exit 1; }
fi
git -C "$root" rev-parse --verify "$tag^{commit}" >/dev/null 2>&1 ||
    { echo "Error: tag or commit not found: $tag" >&2; exit 2; }

temp_root=$(mktemp -d)
worktree=$temp_root/worktree
worktree_added=false
cleanup() {
    if [ "$worktree_added" = true ]; then
        git -C "$repo_root" worktree remove --force "$worktree" >/dev/null 2>&1 || true
    fi
    rm -rf "$temp_root"
}
trap cleanup EXIT HUP INT TERM

git -C "$repo_root" worktree add --detach "$worktree" "$tag" >/dev/null
worktree_added=true
old_root=${worktree}/${prefix%/}
old_root=${old_root%/}
old_file=$temp_root/old.txt
new_file=$temp_root/new.txt

omit=(--omit blanket-impls)
if [ "$abbreviated" = true ]; then
    omit=(--omit blanket-impls,auto-trait-impls,auto-derived-impls)
fi

echo "Building public API at $tag..." >&2
(cd "$old_root" && cargo public-api "${omit[@]}") >"$old_file"
echo "Building public API from the current working tree..." >&2
(cd "$root" && cargo public-api "${omit[@]}") >"$new_file"

if [ -n "$output_dir" ]; then
    mkdir -p "$output_dir"
    cp "$old_file" "$output_dir/old.txt"
    cp "$new_file" "$output_dir/new.txt"
    echo "Saved comparison inputs to $output_dir" >&2
fi

diff -u "$old_file" "$new_file" || true
