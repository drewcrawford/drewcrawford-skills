#!/usr/bin/env bash

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: server.sh [--headless]

Install dependencies when needed, then start the standalone dev-browser server.

Options:
  --headless    Launch Chromium without a visible window
  -h, --help    Show this help and exit
EOF
}

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Change to the script directory
cd "$SCRIPT_DIR"

# Parse command line arguments
HEADLESS=false
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --headless) HEADLESS=true ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Error: unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
    shift
done

if [[ ! -d node_modules ]]; then
    echo "Installing dependencies..." >&2
    npm install
fi

echo "Starting dev-browser server..." >&2
export HEADLESS=$HEADLESS
exec npx --no-install tsx scripts/start-server.ts
