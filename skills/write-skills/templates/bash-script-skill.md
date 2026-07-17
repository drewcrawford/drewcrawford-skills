---
name: bash-tool-name
description: Execute [tool purpose] using bash scripts for [main operations]. Use when [specific use cases], working with [system operations], or when user mentions [trigger keywords].
allowed-tools: Bash, Read, Write, Edit
---

# [Tool Name] Bash Automation

Powerful bash scripting for [primary use case].

## Prerequisites

### System Requirements
```bash
# Check system compatibility
uname -a  # Operating system
bash --version  # Bash version (4.0+ recommended)
```

### Required Tools
```bash
# Check for required commands
command -v git || echo "git not installed"
command -v jq || echo "jq not installed"
command -v curl || echo "curl not installed"
```

## Core Scripts

### Main Execution Script
```bash
#!/usr/bin/env bash
set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Configuration
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly CONFIG_FILE="${SCRIPT_DIR}/config.env"
readonly LOG_FILE="${SCRIPT_DIR}/execution.log"

# Load configuration
if [[ -f "$CONFIG_FILE" ]]; then
    source "$CONFIG_FILE"
fi

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

# Error handling
trap 'log "ERROR: Script failed at line $LINENO"' ERR

# Main function
main() {
    log "Starting execution..."

    # Your main logic here
    process_data
    validate_results
    generate_output

    log "Execution completed successfully"
}

# Run if executed directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
```

### Utility Functions
```bash
#!/usr/bin/env bash

# Color output
red() { echo -e "\033[31m$*\033[0m"; }
green() { echo -e "\033[32m$*\033[0m"; }
yellow() { echo -e "\033[33m$*\033[0m"; }

# Check command exists
require_command() {
    if ! command -v "$1" &>/dev/null; then
        red "Error: $1 is not installed"
        exit 1
    fi
}

# Retry with exponential backoff
retry_with_backoff() {
    local max_attempts=5
    local delay=1
    local attempt=0

    until "$@" || (( attempt++ >= max_attempts )); do
        echo "Command failed. Attempt $attempt/$max_attempts. Retrying in $delay seconds..."
        sleep $delay
        delay=$((delay * 2))
    done

    if (( attempt >= max_attempts )); then
        echo "Command failed after $max_attempts attempts"
        return 1
    fi
}

# Parallel execution
run_parallel() {
    local -a pids=()

    for cmd in "$@"; do
        eval "$cmd" &
        pids+=($!)
    done

    for pid in "${pids[@]}"; do
        wait "$pid" || return 1
    done
}
```

## Common Operations

### File Processing
```bash
#!/usr/bin/env bash

process_files() {
    local input_dir="${1:-./input}"
    local output_dir="${2:-./output}"

    # Create output directory
    mkdir -p "$output_dir"

    # Process each file
    find "$input_dir" -type f -name "*.txt" | while read -r file; do
        local basename=$(basename "$file" .txt)
        local output_file="$output_dir/${basename}_processed.txt"

        echo "Processing: $file"

        # Your processing logic
        sed 's/old/new/g' "$file" |
        awk '{print NR, $0}' |
        sort -n > "$output_file"

        echo "Created: $output_file"
    done
}
```

### System Monitoring
```bash
#!/usr/bin/env bash

monitor_system() {
    while true; do
        clear
        echo "=== System Monitor ==="
        echo "Time: $(date)"
        echo

        # CPU usage
        echo "CPU Usage:"
        top -bn1 | grep "Cpu(s)" | awk '{print $2 + $4"%"}'

        # Memory usage
        echo -e "\nMemory Usage:"
        free -h | grep "^Mem" | awk '{print $3 "/" $2}'

        # Disk usage
        echo -e "\nDisk Usage:"
        df -h | grep -E '^/dev/' | awk '{print $1 ": " $5}'

        # Process count
        echo -e "\nProcess Count: $(ps aux | wc -l)"

        sleep 5
    done
}
```

### Data Pipeline
```bash
#!/usr/bin/env bash

run_pipeline() {
    local input="$1"
    local temp_dir=$(mktemp -d)

    trap "rm -rf $temp_dir" EXIT

    # Stage 1: Extract
    echo "Stage 1: Extracting data..."
    extract_data "$input" > "$temp_dir/extracted.json"

    # Stage 2: Transform
    echo "Stage 2: Transforming data..."
    cat "$temp_dir/extracted.json" |
    jq '.[] | select(.status == "active")' |
    jq -s 'group_by(.category) | map({category: .[0].category, count: length})' \
    > "$temp_dir/transformed.json"

    # Stage 3: Load
    echo "Stage 3: Loading results..."
    load_to_database "$temp_dir/transformed.json"

    echo "Pipeline completed successfully"
}
```

## Advanced Features

### Interactive Menu
```bash
#!/usr/bin/env bash

show_menu() {
    echo "====================================="
    echo "     Automation Tool Menu"
    echo "====================================="
    echo "1. Process files"
    echo "2. Run tests"
    echo "3. Generate report"
    echo "4. Clean workspace"
    echo "5. Exit"
    echo "====================================="
}

main_menu() {
    while true; do
        show_menu
        read -p "Select option: " choice

        case $choice in
            1) process_files ;;
            2) run_tests ;;
            3) generate_report ;;
            4) clean_workspace ;;
            5) exit 0 ;;
            *) echo "Invalid option" ;;
        esac

        read -p "Press Enter to continue..."
        clear
    done
}
```

### Progress Bar
```bash
#!/usr/bin/env bash

progress_bar() {
    local current=$1
    local total=$2
    local width=50

    local progress=$((current * width / total))
    local percentage=$((current * 100 / total))

    printf "\r["
    printf "%${progress}s" | tr ' ' '='
    printf "%$((width - progress))s" | tr ' ' '-'
    printf "] %d%%" $percentage

    if [[ $current -eq $total ]]; then
        echo
    fi
}

# Usage example
for i in {1..100}; do
    progress_bar $i 100
    sleep 0.1
done
```

## Error Handling

### Comprehensive Error Checking
```bash
#!/usr/bin/env bash

safe_execution() {
    set -euo pipefail  # Strict mode
    trap cleanup EXIT
    trap 'error_handler $? $LINENO' ERR

    # Initialize
    init_environment

    # Execute with validation
    if validate_input "$@"; then
        execute_main_logic "$@"
    else
        echo "Validation failed" >&2
        exit 1
    fi
}

error_handler() {
    local exit_code=$1
    local line_number=$2
    echo "Error occurred at line $line_number with exit code $exit_code" >&2
    # Additional error handling
}

cleanup() {
    # Clean up temporary files
    rm -rf "${TEMP_DIR:-/tmp/unknown}"
    # Kill background processes
    jobs -p | xargs -r kill 2>/dev/null || true
}
```

## Testing Framework

### Unit Tests
```bash
#!/usr/bin/env bash

# Test framework
assert_equals() {
    if [[ "$1" != "$2" ]]; then
        echo "FAIL: Expected '$1' but got '$2'"
        return 1
    fi
}

assert_true() {
    if ! eval "$1"; then
        echo "FAIL: Assertion failed: $1"
        return 1
    fi
}

# Test suite
run_tests() {
    local passed=0
    local failed=0

    # Test 1
    echo -n "Testing function_one... "
    if output=$(function_one "input"); then
        assert_equals "$output" "expected"
        echo "PASS"
        ((passed++))
    else
        echo "FAIL"
        ((failed++))
    fi

    # Summary
    echo
    echo "Tests passed: $passed"
    echo "Tests failed: $failed"

    [[ $failed -eq 0 ]]
}
```

## Best Practices

1. **Script Structure**
   - Use shebang: `#!/usr/bin/env bash`
   - Set strict mode: `set -euo pipefail`
   - Define functions for reusability
   - Use meaningful variable names

2. **Error Handling**
   - Always check command exit codes
   - Use trap for cleanup
   - Provide informative error messages
   - Log errors for debugging

3. **Performance**
   - Avoid useless use of cat
   - Use built-in commands when possible
   - Minimize subprocess spawning
   - Consider parallel execution

4. **Portability**
   - Use env in shebang
   - Avoid bash-specific features if targeting sh
   - Test on target systems
   - Document dependencies

5. **Security**
   - Quote variables: `"$var"`
   - Validate user input
   - Avoid eval with user data
   - Use mktemp for temporary files