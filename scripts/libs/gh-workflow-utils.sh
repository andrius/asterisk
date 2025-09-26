#!/bin/bash
#
# GitHub CLI Workflow Utilities
# Shared library for triggering and watching GitHub workflows with proper run correlation
#

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Configuration
readonly MAX_CORRELATION_ATTEMPTS=20
readonly CORRELATION_RETRY_DELAY=3
readonly CORRELATION_TIMEOUT=60

log_with_timestamp() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    case "$level" in
        "INFO")  echo -e "${BLUE}[${timestamp}] INFO:${NC} $message" ;;
        "WARN")  echo -e "${YELLOW}[${timestamp}] WARN:${NC} $message" ;;
        "ERROR") echo -e "${RED}[${timestamp}] ERROR:${NC} $message" >&2 ;;
        "SUCCESS") echo -e "${GREEN}[${timestamp}] SUCCESS:${NC} $message" ;;
        *) echo "[$timestamp] $message" ;;
    esac
}

get_current_user() {
    gh api user --jq '.login' 2>/dev/null || {
        log_with_timestamp "ERROR" "Failed to get current GitHub user. Are you authenticated with 'gh auth login'?"
        return 1
    }
}

validate_workflow_exists() {
    local workflow="$1"

    if ! gh workflow list --json name,path | jq -r '.[].path' | grep -q "$workflow"; then
        log_with_timestamp "ERROR" "Workflow '$workflow' not found in repository"
        log_with_timestamp "INFO" "Available workflows:"
        gh workflow list --json name,path | jq -r '.[] | "  - \(.name) (\(.path))"'
        return 1
    fi
}

build_workflow_inputs() {
    local inputs_array_name="$1"
    local workflow_args=()

    # Use nameref indirection to access associative array
    local -n inputs_array_ref="$inputs_array_name"

    for key in "${!inputs_array_ref[@]}"; do
        local value="${inputs_array_ref[$key]}"
        if [[ -n "$value" ]]; then
            workflow_args+=("-f" "${key}=${value}")
        fi
    done

    printf '%s\n' "${workflow_args[@]}"
}

wait_for_run_correlation() {
    local workflow="$1"
    local actor="$2"
    local trigger_time="$3"
    local max_attempts="$4"

    log_with_timestamp "INFO" "Waiting for workflow run to appear (timeout: ${CORRELATION_TIMEOUT}s)..." >&2

    local attempt=1
    local start_time=$(date +%s)

    while [[ $attempt -le $max_attempts ]]; do
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))

        if [[ $elapsed -gt $CORRELATION_TIMEOUT ]]; then
            log_with_timestamp "ERROR" "Timeout waiting for workflow run correlation" >&2
            return 1
        fi

        # Query for runs matching our criteria
        local runs_json
        runs_json=$(gh run list \
            --workflow "$workflow" \
            --user "$actor" \
            --limit 5 \
            --json databaseId,createdAt,status,conclusion,displayTitle \
            2>/dev/null) || {
            log_with_timestamp "WARN" "Failed to query runs (attempt $attempt/$max_attempts)" >&2
            sleep $CORRELATION_RETRY_DELAY
            ((attempt++))
            continue
        }

        # Find runs created at or after our trigger time
        local matching_run_id
        matching_run_id=$(echo "$runs_json" | jq -r \
            --arg trigger_time "$trigger_time" \
            '.[] | select(.createdAt >= $trigger_time) | .databaseId' | head -1)

        if [[ -n "$matching_run_id" && "$matching_run_id" != "null" ]]; then
            log_with_timestamp "SUCCESS" "Found workflow run: $matching_run_id" >&2

            # Get run details for display
            local run_details
            run_details=$(echo "$runs_json" | jq -r \
                --arg run_id "$matching_run_id" \
                '.[] | select(.databaseId == ($run_id | tonumber)) | "\(.displayTitle) (Status: \(.status))"')

            log_with_timestamp "INFO" "Run details: $run_details" >&2
            echo "$matching_run_id"
            return 0
        fi

        log_with_timestamp "INFO" "Run not found yet (attempt $attempt/$max_attempts, elapsed: ${elapsed}s)" >&2
        sleep $CORRELATION_RETRY_DELAY
        ((attempt++))
    done

    log_with_timestamp "ERROR" "Failed to correlate workflow run after $max_attempts attempts" >&2
    log_with_timestamp "INFO" "Recent runs for workflow '$workflow':" >&2
    gh run list --workflow "$workflow" --limit 3 --json databaseId,createdAt,status,displayTitle | \
        jq -r '.[] | "  - Run \(.databaseId): \(.displayTitle) (\(.status)) at \(.createdAt)"' >&2 || true

    return 1
}

watch_workflow_run() {
    local run_id="$1"

    log_with_timestamp "INFO" "Starting watch mode for run $run_id"
    log_with_timestamp "INFO" "Run URL: https://github.com/$(gh repo view --json owner,name -q '.owner.login + "/" + .name')/actions/runs/$run_id"

    # Use gh run watch with compact output and exit status handling
    if gh run watch "$run_id" --compact --exit-status --interval 3; then
        log_with_timestamp "SUCCESS" "Workflow run $run_id completed successfully"
        return 0
    else
        local exit_code=$?
        log_with_timestamp "ERROR" "Workflow run $run_id failed (exit code: $exit_code)"
        return $exit_code
    fi
}

trigger_and_watch_workflow() {
    local workflow="$1"
    local -n inputs_ref=$2

    log_with_timestamp "INFO" "Triggering GitHub workflow: $workflow"

    # Validate workflow exists
    if ! validate_workflow_exists "$workflow"; then
        return 1
    fi

    # Get current user for correlation
    local actor
    actor=$(get_current_user) || return 1
    log_with_timestamp "INFO" "Authenticated as: $actor"

    # Record trigger time (with a small buffer for clock differences)
    local trigger_time
    trigger_time=$(date -u -d '5 seconds ago' +"%Y-%m-%dT%H:%M:%SZ")

    # Build workflow input arguments
    local workflow_args=()
    readarray -t workflow_args < <(build_workflow_inputs "inputs_ref")

    # Display input summary
    if [[ ${#workflow_args[@]} -gt 0 ]]; then
        log_with_timestamp "INFO" "Workflow inputs:"
        for ((i=1; i<${#workflow_args[@]}; i+=2)); do
            log_with_timestamp "INFO" "  ${workflow_args[i]}"
        done
    else
        log_with_timestamp "INFO" "No workflow inputs provided"
    fi

    # Trigger the workflow
    log_with_timestamp "INFO" "Triggering workflow..."
    if ! gh workflow run "$workflow" "${workflow_args[@]}"; then
        log_with_timestamp "ERROR" "Failed to trigger workflow '$workflow'"
        return 1
    fi

    log_with_timestamp "SUCCESS" "Workflow triggered successfully"

    # Wait for run correlation
    local run_id
    run_id=$(wait_for_run_correlation "$workflow" "$actor" "$trigger_time" "$MAX_CORRELATION_ATTEMPTS") || {
        log_with_timestamp "ERROR" "Failed to identify the triggered workflow run"
        return 1
    }

    # Watch the run
    watch_workflow_run "$run_id"
}

print_run_id_on_exit() {
    local run_id="$1"
    if [[ -n "$run_id" ]]; then
        log_with_timestamp "INFO" "Final run ID: $run_id"
    fi
}

# Export functions for use in other scripts
export -f log_with_timestamp
export -f get_current_user
export -f validate_workflow_exists
export -f build_workflow_inputs
export -f wait_for_run_correlation
export -f watch_workflow_run
export -f trigger_and_watch_workflow
export -f print_run_id_on_exit