#!/bin/bash
set -e

# Ensure cleanup on exit
cleanup() {
    rm -f old.txt new.txt
}
trap cleanup EXIT

usage() {
    echo "Usage: $(basename "$0") [OPTIONS] [TAG]"
    echo ""
    echo "Compare public API between a git tag and HEAD."
    echo ""
    echo "Arguments:"
    echo "  TAG                 Tag to compare against (default: most recent tag)"
    echo ""
    echo "Options:"
    echo "  -h, --help          Show this help message"
    echo "  -l, --list          List available tags"
    echo "  --abbreviated       Omit blanket-impls, auto-trait-impls, and auto-derived-impls"
    echo ""
    echo "Output:"
    echo "  old.txt             Public API at the specified tag"
    echo "  new.txt             Public API at HEAD"
}

# Parse arguments
ABBREVIATED=false
TAG_ARG=""
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
        --abbreviated)
            ABBREVIATED=true
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

# Build omit arguments
if [ "$ABBREVIATED" = true ]; then
    OMIT_ARGS="--omit blanket-impls,auto-trait-impls,auto-derived-impls"
else
    OMIT_ARGS="--omit blanket-impls"
fi

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

echo "Comparing $COMPARE_TAG to $CURRENT_REF..."

# Stash any current changes
STASH_RESULT=$(git stash push -m "public-api-compare" 2>&1 || true)
NEEDS_POP=false
if [[ ! "$STASH_RESULT" =~ "No local changes" ]]; then
    NEEDS_POP=true
fi

# Checkout the tag and generate old API
git checkout "$COMPARE_TAG" --quiet
cargo public-api $OMIT_ARGS > old.txt

# Return to original ref (branch name or commit)
git checkout "$CURRENT_REF" --quiet

# Pop stash if we stashed anything
if [ "$NEEDS_POP" = true ]; then
    git stash pop --quiet
fi

# Generate new API
cargo public-api $OMIT_ARGS > new.txt

# Show diff but don't fail script if there are differences
diff old.txt new.txt || true

# Cleanup happens automatically via trap
