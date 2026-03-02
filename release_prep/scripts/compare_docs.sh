#!/bin/bash
set -e

# Global state for cleanup
NEEDS_POP=false
CHECKED_OUT_TAG=""

# Cleanup function to restore git state
cleanup() {
	# Restore git state if we checked out a tag
	if [ -n "$CURRENT_REF" ] && [ -n "$CHECKED_OUT_TAG" ]; then
		git checkout "$CURRENT_REF" --quiet 2>/dev/null || true
	fi
	# Pop stash if we stashed anything
	if [ "$NEEDS_POP" = true ]; then
		git stash pop --quiet 2>/dev/null || true
	fi
}

usage() {
	echo "Usage: $(basename "$0") [OPTIONS] [TAG]"
	echo ""
	echo "Compare documentation between a git tag and HEAD."
	echo ""
	echo "Arguments:"
	echo "  TAG                 Tag to compare against (default: most recent tag)"
	echo ""
	echo "Options:"
	echo "  -h, --help          Show this help message"
	echo "  -l, --list          List available tags"
	echo "  -q, --quiet         Suppress build output"
	echo ""
	echo "Output:"
	echo "  old_docs.json       Documentation at the specified tag"
	echo "  new_docs.json       Documentation at HEAD"
}

# Parse arguments
TAG_ARG=""
QUIET=false
while [[ $# -gt 0 ]]; do
	case $1 in
		-h|--help)
			usage
			exit 0
			;;
		-l|--list)
			echo "Available tags:"
			git tag --sort=-v:refname
			exit 0
			;;
		-q|--quiet)
			QUIET=true
			shift
			;;
		-*)
			echo "Error: Unknown option $1" >&2
			usage >&2
			exit 1
			;;
		*)
			TAG_ARG="$1"
			shift
			;;
	esac
done

# Get current branch/commit to return to
CURRENT_REF=$(git rev-parse --abbrev-ref HEAD)
if [ "$CURRENT_REF" = "HEAD" ]; then
	# Already in detached HEAD; fall back to exact commit so we can restore it
	CURRENT_REF=$(git rev-parse HEAD)
fi

# Get tag to compare against
if [ -n "$TAG_ARG" ]; then
	# Verify the provided tag exists
	if ! git rev-parse "$TAG_ARG" >/dev/null 2>&1; then
		echo "Error: Tag '$TAG_ARG' not found" >&2
		echo "Use -l to list available tags" >&2
		exit 1
	fi
	COMPARE_TAG="$TAG_ARG"
else
	COMPARE_TAG=$(git tag --sort=-v:refname | head -1)
	if [ -z "$COMPARE_TAG" ]; then
		echo "Error: No tags found in repository" >&2
		exit 1
	fi
fi

echo "Comparing docs: $COMPARE_TAG vs $CURRENT_REF..."

# Get crate name from Cargo.toml
CRATE_NAME=$(cargo metadata --no-deps --format-version 1 | jq -r '.packages[0].name' | tr '-' '_')

# Clean up old comparison files
rm -f old_docs.json new_docs.json

# Generate new docs
if [ "$QUIET" = true ]; then
	cargo +nightly rustdoc -- -Z unstable-options --output-format json 2>/dev/null
else
	cargo +nightly rustdoc -- -Z unstable-options --output-format json
fi
cp "target/doc/${CRATE_NAME}.json" new_docs.json

# Stash any current changes
STASH_RESULT=$(git stash push -m "doc-compare" 2>&1 || true)
if [[ ! "$STASH_RESULT" =~ "No local changes" ]]; then
	NEEDS_POP=true
fi

# Set up trap to restore git state on any exit (including errors)
trap cleanup EXIT

# Checkout the tag and generate old docs
git checkout "$COMPARE_TAG" --quiet
CHECKED_OUT_TAG=true
if [ "$QUIET" = true ]; then
	cargo +nightly rustdoc -- -Z unstable-options --output-format json 2>/dev/null
else
	cargo +nightly rustdoc -- -Z unstable-options --output-format json
fi
cp "target/doc/${CRATE_NAME}.json" old_docs.json

# Return to original ref (branch name or commit)
git checkout "$CURRENT_REF" --quiet
CHECKED_OUT_TAG=""

# Pop stash if we stashed anything
if [ "$NEEDS_POP" = true ]; then
	git stash pop --quiet
	NEEDS_POP=false
fi


# Extract named items with docs, using path for uniqueness
jq -S '
  .index | to_entries |
  map(select(.value.name != null and .value.docs != null)) |
  map({
	name: (.value.inner | keys[0] // "item") + "::" + .value.name,
	docs: (.value.docs | split("\n")[0])
  }) |
  sort_by(.name) |
  unique_by(.name)
' old_docs.json > old_docs_filtered.json

jq -S '
  .index | to_entries |
  map(select(.value.name != null and .value.docs != null)) |
  map({
	name: (.value.inner | keys[0] // "item") + "::" + .value.name,
	docs: (.value.docs | split("\n")[0])
  }) |
  sort_by(.name) |
  unique_by(.name)
' new_docs.json > new_docs_filtered.json

# Show summary
echo ""
echo "=== Summary ==="
ADDED=$(comm -13 <(jq -r '.[].name' old_docs_filtered.json | sort) <(jq -r '.[].name' new_docs_filtered.json | sort))
REMOVED=$(comm -23 <(jq -r '.[].name' old_docs_filtered.json | sort) <(jq -r '.[].name' new_docs_filtered.json | sort))

if [ -n "$ADDED" ]; then
	echo "Added:"
	echo "$ADDED" | sed 's/^/  + /'
fi

if [ -n "$REMOVED" ]; then
	echo "Removed:"
	echo "$REMOVED" | sed 's/^/  - /'
fi

MODIFIED=$(diff -u old_docs_filtered.json new_docs_filtered.json | grep -c '^@@' || true)
echo "Modified sections: $MODIFIED"
echo ""

# Show full diff
echo "=== Changes ==="
diff -u old_docs_filtered.json new_docs_filtered.json || true

rm old_docs.json
rm old_docs_filtered.json
rm -rf old_docs

rm new_docs.json
rm new_docs_filtered.json
rm -rf new_docs
