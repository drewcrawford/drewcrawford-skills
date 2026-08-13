#!/usr/bin/env bash

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: compare_docs.sh [OPTIONS] [TAG]

Compare rustdoc JSON at TAG with the current working tree without stashing
changes or switching the user's checkout.

Options:
  --root PATH       Crate directory (default: cwd)
  --output-dir DIR  Preserve filtered old_docs.json and new_docs.json in DIR
  -q, --quiet       Suppress cargo build output
  -l, --list        List available tags and exit
  -h, --help        Show this help and exit
EOF
}

root=.
output_dir=
quiet=false
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
        -q|--quiet) quiet=true; shift ;;
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

command -v jq >/dev/null 2>&1 || { echo "Error: jq is required" >&2; exit 1; }

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

build_docs() {
    local crate_root=$1
    local destination=$2
    local metadata crate_name target_dir
    metadata=$(cd "$crate_root" && cargo metadata --no-deps --format-version 1)
    crate_name=$(jq -r --arg manifest "$crate_root/Cargo.toml"         '.packages[] | select(.manifest_path == $manifest) | .name' <<<"$metadata" | tr '-' '_')
    [ -n "$crate_name" ] && [ "$crate_name" != null ] ||
        { echo "Error: no package at $crate_root/Cargo.toml" >&2; return 1; }
    target_dir=$(jq -r '.target_directory' <<<"$metadata")
    if [ "$quiet" = true ]; then
        (cd "$crate_root" && cargo +nightly rustdoc -- -Z unstable-options --output-format json) >/dev/null 2>&1
    else
        (cd "$crate_root" && cargo +nightly rustdoc -- -Z unstable-options --output-format json) >&2
    fi
    cp "$target_dir/doc/$crate_name.json" "$destination"
}

filter_docs() {
    jq -S '
      .index | to_entries |
      map(select(.value.name != null and .value.docs != null)) |
      map({
        name: ((.value.inner | keys[0] // "item") + "::" + .value.name),
        docs: (.value.docs | split("\n")[0])
      }) |
      sort_by(.name) |
      unique_by(.name)
    ' "$1" >"$2"
}

echo "Building documentation at $tag..." >&2
build_docs "$old_root" "$temp_root/old_raw.json"
echo "Building documentation from the current working tree..." >&2
build_docs "$root" "$temp_root/new_raw.json"
filter_docs "$temp_root/old_raw.json" "$temp_root/old_docs.json"
filter_docs "$temp_root/new_raw.json" "$temp_root/new_docs.json"

if [ -n "$output_dir" ]; then
    mkdir -p "$output_dir"
    cp "$temp_root/old_docs.json" "$output_dir/old_docs.json"
    cp "$temp_root/new_docs.json" "$output_dir/new_docs.json"
    echo "Saved comparison inputs to $output_dir" >&2
fi

diff -u "$temp_root/old_docs.json" "$temp_root/new_docs.json" || true
