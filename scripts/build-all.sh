#!/bin/bash

# Build all supported Asterisk versions and push to Docker Hub
# Processes all buildable versions from asterisk/supported-asterisk-builds.yml

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LATEST_BUILDS_FILE="${PROJECT_DIR}/asterisk/supported-asterisk-builds.yml"
BUILD_SCRIPT="${SCRIPT_DIR}/build-asterisk.sh"

# Default values
DEFAULT_REGISTRY="ghcr.io/andrius/asterisk"
DRY_RUN=false
VERBOSE=false
PARALLEL=false
NO_PUSH=false
MAX_PARALLEL_JOBS=3
SKIP_VERSIONS=()
ONLY_VERSION=""
CUSTOM_REGISTRY=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log() {
    local level="$1"
    shift
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")

    case "$level" in
        ERROR)   echo -e "${timestamp} [${RED}ERROR${NC}] $*" >&2 ;;
        WARN)    echo -e "${timestamp} [${YELLOW}WARN${NC}] $*" >&2 ;;
        INFO)    echo -e "${timestamp} [${BLUE}INFO${NC}] $*" ;;
        SUCCESS) echo -e "${timestamp} [${GREEN}SUCCESS${NC}] $*" ;;
        DEBUG)   [[ "$VERBOSE" == "true" ]] && echo -e "${timestamp} [DEBUG] $*" >&2 ;;
    esac
}

# Function to show usage
usage() {
    cat << EOF
Usage: $0 [options]

Build all supported Asterisk versions and push to Docker Hub registry.
Processes buildable versions from asterisk/supported-asterisk-builds.yml.

Options:
  --dry-run                Show what would be built without executing
  --verbose               Enable verbose output
  --parallel              Build versions in parallel (max $MAX_PARALLEL_JOBS)
  --no-push               Build images locally without pushing to registry
  --registry REGISTRY     Override registry/repository (default: $DEFAULT_REGISTRY)
  --skip-version VERSION  Skip specific version (can be used multiple times)
  --only-version VERSION  Build only specific version
  --max-jobs N           Set maximum parallel jobs (default: $MAX_PARALLEL_JOBS)
  --help, -h             Show this help message

Examples:
  $0                                    # Build all supported versions and push
  $0 --dry-run                         # Preview what would be built
  $0 --no-push                         # Build locally without pushing
  $0 --parallel --verbose              # Parallel build with verbose output
  $0 --only-version 22.5.2             # Build only version 22.5.2
  $0 --skip-version 23.0.0-rc1         # Build all except 23.0.0-rc1
  $0 --registry myuser/myrepo          # Push to myuser/myrepo:tag on Docker Hub
  $0 --registry ghcr.io/user/repo     # Push to GitHub Container Registry

Current buildable versions will be determined from:
  $LATEST_BUILDS_FILE

EOF
}

# Parse buildable versions from YAML
parse_buildable_versions() {
    log INFO "Parsing buildable versions from $LATEST_BUILDS_FILE..." >&2

    if [[ ! -f "$LATEST_BUILDS_FILE" ]]; then
        log ERROR "YAML file not found: $LATEST_BUILDS_FILE"
        return 1
    fi

    # Use Python to parse YAML and extract buildable versions
    python3 -c "
import sys, yaml

try:
    with open('$LATEST_BUILDS_FILE', 'r') as f:
        data = yaml.safe_load(f)

    buildable_versions = []
    skipped_versions = []

    for build in data.get('latest_builds', []):
        version = build.get('version')
        if not version:
            continue

        if 'os_matrix' in build:
            buildable_versions.append(version)
        else:
            skipped_versions.append(version)

    print('BUILDABLE_VERSIONS=' + ':'.join(buildable_versions))
    print('SKIPPED_VERSIONS=' + ':'.join(skipped_versions))
    print('TOTAL_BUILDABLE=' + str(len(buildable_versions)), file=sys.stderr)
    print('TOTAL_SKIPPED=' + str(len(skipped_versions)), file=sys.stderr)

except Exception as e:
    print(f'ERROR: Failed to parse YAML: {e}', file=sys.stderr)
    sys.exit(1)
"
}

# Build a single version
build_version() {
    local version="$1"
    local registry="$2"
    local start_time=$(date +%s)

    log INFO "Building Asterisk $version..."

    local build_args=("$version")
    [[ "$NO_PUSH" == "false" ]] && build_args+=(--push --registry "$registry")
    [[ "$VERBOSE" == "true" ]] && build_args+=(--verbose)

    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY RUN] Would execute: $BUILD_SCRIPT ${build_args[*]}"
        return 0
    fi

    # Execute build
    if "$BUILD_SCRIPT" "${build_args[@]}"; then
        local duration=$(($(date +%s) - start_time))
        log SUCCESS "Completed Asterisk $version in ${duration}s"
        return 0
    else
        local duration=$(($(date +%s) - start_time))
        log ERROR "Failed to build Asterisk $version after ${duration}s"
        return 1
    fi
}

# Build version in background (for parallel mode)
build_version_parallel() {
    local version="$1"
    local registry="$2"
    local log_file="$3"

    {
        echo "=== Building $version (started at $(date)) ==="
        if build_version "$version" "$registry"; then
            echo "SUCCESS: $version"
        else
            echo "FAILED: $version"
            exit 1
        fi
    } &> "$log_file" &

    echo $! # Return PID
}

# Show build summary
show_summary() {
    local -a successful_builds=("$@")
    local total_successful=${#successful_builds[@]}
    local total_failed=${#FAILED_BUILDS[@]}
    local total_builds=$((total_successful + total_failed))

    echo
    echo "======================================"
    echo "BUILD SUMMARY"
    echo "======================================"
    echo "Total versions processed: $total_builds"
    echo "Successful builds: $total_successful"
    echo "Failed builds: $total_failed"
    echo

    if [[ $total_successful -gt 0 ]]; then
        log SUCCESS "Successfully built versions:"
        for version in "${successful_builds[@]}"; do
            echo "  ✅ $version"
        done
        echo
    fi

    if [[ $total_failed -gt 0 ]]; then
        log ERROR "Failed builds:"
        for version in "${FAILED_BUILDS[@]}"; do
            echo "  ❌ $version"
        done
        echo
    fi

    if [[ $total_failed -eq 0 ]]; then
        log SUCCESS "🎉 All builds completed successfully!"
        return 0
    else
        log ERROR "❌ Some builds failed. Check logs above for details."
        return 1
    fi
}

# Validate prerequisites
validate_prerequisites() {
    log INFO "Validating prerequisites..."

    # Check required files
    if [[ ! -f "$BUILD_SCRIPT" ]]; then
        log ERROR "Build script not found: $BUILD_SCRIPT"
        return 1
    fi

    if [[ ! -x "$BUILD_SCRIPT" ]]; then
        log ERROR "Build script not executable: $BUILD_SCRIPT"
        return 1
    fi

    # Check Docker
    if ! command -v docker >/dev/null 2>&1; then
        log ERROR "Docker not found. Please install Docker."
        return 1
    fi

    # Check Docker buildx
    if ! docker buildx version >/dev/null 2>&1; then
        log ERROR "Docker buildx not available. Please enable buildx."
        return 1
    fi

    # Check Python and YAML support
    if ! python3 -c "import yaml" >/dev/null 2>&1; then
        log ERROR "Python PyYAML not available. Please install: pip3 install pyyaml"
        return 1
    fi

    log SUCCESS "Prerequisites validation passed"
    return 0
}

# Function to check if all required generated configs exist
validate_generated_configs() {
    local -a versions_to_build=("$@")
    local missing_configs=()

    log INFO "Validating generated configs for buildable versions..."

    # Get the build matrix for each version to determine required configs
    for version in "${versions_to_build[@]}"; do
        # Parse the build matrix to get required OS/distribution combinations
        python3 -c "
import sys, yaml

try:
    with open('$LATEST_BUILDS_FILE', 'r') as f:
        data = yaml.safe_load(f)

    for build in data.get('latest_builds', []):
        if build.get('version') != '$version':
            continue

        if 'os_matrix' not in build:
            continue

        os_matrix = build['os_matrix']
        if isinstance(os_matrix, list):
            matrix_list = os_matrix
        else:
            matrix_list = [os_matrix]

        for matrix_entry in matrix_list:
            os_name = matrix_entry.get('os', 'debian')
            distribution = matrix_entry.get('distribution', 'trixie')
            config_path = f'configs/generated/asterisk-$version-{distribution}.yml'
            print(config_path)

except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
" | while read -r config_path; do
            if [[ -n "$config_path" ]]; then
                full_path="${PROJECT_DIR}/$config_path"
                if [[ ! -f "$full_path" ]]; then
                    missing_configs+=("$config_path")
                    log WARN "Missing generated config: $config_path"
                fi
            fi
        done
    done

    if [[ ${#missing_configs[@]} -gt 0 ]]; then
        log ERROR "Missing ${#missing_configs[@]} required generated configs"
        log ERROR "These configs must exist in configs/generated/ directory:"
        for config in "${missing_configs[@]}"; do
            echo "  ❌ $config"
        done
        log ERROR "Available configs:"
        if ls "${PROJECT_DIR}/configs/generated/"*.yml >/dev/null 2>&1; then
            ls "${PROJECT_DIR}/configs/generated/"*.yml | sed 's|.*/||' | sed 's/^/  ✅ /'
        else
            echo "  (none found)"
        fi
        return 1
    fi

    log SUCCESS "All required generated configs are available"
    return 0
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --parallel)
                PARALLEL=true
                shift
                ;;
            --no-push)
                NO_PUSH=true
                shift
                ;;
            --registry)
                CUSTOM_REGISTRY="$2"
                shift 2
                ;;
            --skip-version)
                SKIP_VERSIONS+=("$2")
                shift 2
                ;;
            --only-version)
                ONLY_VERSION="$2"
                shift 2
                ;;
            --max-jobs)
                MAX_PARALLEL_JOBS="$2"
                shift 2
                ;;
            --help|-h)
                usage
                exit 0
                ;;
            *)
                log ERROR "Unknown option: $1"
                usage >&2
                exit 1
                ;;
        esac
    done
}

# Main execution function
main() {
    local start_time=$(date +%s)

    log INFO "Starting build-all.sh for Asterisk Docker images"
    log INFO "Project directory: $PROJECT_DIR"
    log INFO "Registry: ${CUSTOM_REGISTRY:-$DEFAULT_REGISTRY}"
    [[ "$DRY_RUN" == "true" ]] && log INFO "DRY RUN MODE - no actual builds will be executed"
    [[ "$PARALLEL" == "true" ]] && log INFO "PARALLEL MODE - max $MAX_PARALLEL_JOBS concurrent builds"

    # Validate prerequisites
    if ! validate_prerequisites; then
        exit 1
    fi

    # Parse buildable versions
    local parse_output
    if ! parse_output=$(parse_buildable_versions); then
        exit 1
    fi

    # Extract variables from Python output
    eval "$parse_output"

    if [[ -z "${BUILDABLE_VERSIONS:-}" ]]; then
        log ERROR "No buildable versions found in $LATEST_BUILDS_FILE"
        exit 1
    fi

    # Convert colon-separated string to array
    IFS=':' read -ra BUILDABLE_ARRAY <<< "$BUILDABLE_VERSIONS"

    log INFO "Found ${#BUILDABLE_ARRAY[@]} buildable versions: ${BUILDABLE_ARRAY[*]}"

    if [[ "${SKIPPED_VERSIONS:-}" != "" ]]; then
        IFS=':' read -ra SKIPPED_ARRAY <<< "$SKIPPED_VERSIONS"
        log INFO "Skipped ${#SKIPPED_ARRAY[@]} versions (no os_matrix): ${SKIPPED_ARRAY[*]}"
    fi

    # Filter versions based on options
    local -a versions_to_build=()

    for version in "${BUILDABLE_ARRAY[@]}"; do
        # Apply --only-version filter
        if [[ -n "$ONLY_VERSION" && "$version" != "$ONLY_VERSION" ]]; then
            continue
        fi

        # Apply --skip-version filter
        local skip=false
        for skip_version in "${SKIP_VERSIONS[@]}"; do
            if [[ "$version" == "$skip_version" ]]; then
                skip=true
                break
            fi
        done

        if [[ "$skip" == "true" ]]; then
            log INFO "Skipping version $version (--skip-version)"
            continue
        fi

        versions_to_build+=("$version")
    done

    if [[ ${#versions_to_build[@]} -eq 0 ]]; then
        log ERROR "No versions to build after applying filters"
        exit 1
    fi

    local registry="${CUSTOM_REGISTRY:-$DEFAULT_REGISTRY}"

    log INFO "Will build ${#versions_to_build[@]} versions: ${versions_to_build[*]}"
    if [[ "$NO_PUSH" == "true" ]]; then
        log INFO "Building locally (no push)"
    else
        log INFO "Target registry: $registry"
    fi

    # Validate that all required generated configs exist
    if ! validate_generated_configs "${versions_to_build[@]}"; then
        log ERROR "Config validation failed - cannot proceed with build"
        exit 1
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        log INFO "[DRY RUN] Build commands that would be executed:"
        for version in "${versions_to_build[@]}"; do
            echo "  $BUILD_SCRIPT $version --push --registry $registry"
        done
        exit 0
    fi

    # Execute builds
    local -a successful_builds=()
    declare -ga FAILED_BUILDS=()

    if [[ "$PARALLEL" == "true" ]]; then
        log INFO "Building versions in parallel (max $MAX_PARALLEL_JOBS jobs)..."

        local -a build_pids=()
        local -A pid_to_version=()
        local temp_dir=$(mktemp -d)
        local active_jobs=0

        for version in "${versions_to_build[@]}"; do
            # Wait if we've hit the max parallel jobs
            while [[ $active_jobs -ge $MAX_PARALLEL_JOBS ]]; do
                # Check for completed jobs
                for i in "${!build_pids[@]}"; do
                    local pid="${build_pids[i]}"
                    if ! kill -0 "$pid" 2>/dev/null; then
                        # Job completed
                        local completed_version="${pid_to_version[$pid]}"
                        wait "$pid"
                        local exit_code=$?

                        if [[ $exit_code -eq 0 ]]; then
                            successful_builds+=("$completed_version")
                            log SUCCESS "Background build completed: $completed_version"
                        else
                            FAILED_BUILDS+=("$completed_version")
                            log ERROR "Background build failed: $completed_version"
                        fi

                        # Remove from tracking arrays
                        unset build_pids[i]
                        unset pid_to_version["$pid"]
                        ((active_jobs--))
                        break
                    fi
                done
                sleep 1
            done

            # Start new job
            local log_file="$temp_dir/build_${version}.log"
            local pid
            pid=$(build_version_parallel "$version" "$registry" "$log_file")

            build_pids+=("$pid")
            pid_to_version["$pid"]="$version"
            ((active_jobs++))

            log INFO "Started background build: $version (PID: $pid)"
        done

        # Wait for remaining jobs
        log INFO "Waiting for remaining builds to complete..."
        for pid in "${build_pids[@]}"; do
            local version="${pid_to_version[$pid]}"
            wait "$pid"
            local exit_code=$?

            if [[ $exit_code -eq 0 ]]; then
                successful_builds+=("$version")
                log SUCCESS "Background build completed: $version"
            else
                FAILED_BUILDS+=("$version")
                log ERROR "Background build failed: $version"
            fi
        done

        # Show logs for failed builds
        if [[ ${#FAILED_BUILDS[@]} -gt 0 ]]; then
            echo
            log ERROR "Logs for failed builds:"
            for version in "${FAILED_BUILDS[@]}"; do
                echo "=== $version ==="
                cat "$temp_dir/build_${version}.log" 2>/dev/null || echo "Log file not found"
                echo
            done
        fi

        # Clean up temp directory
        rm -rf "$temp_dir"

    else
        # Sequential builds
        log INFO "Building versions sequentially..."

        local current=1
        local total=${#versions_to_build[@]}

        for version in "${versions_to_build[@]}"; do
            log INFO "[$current/$total] Processing version: $version"

            if build_version "$version" "$registry"; then
                successful_builds+=("$version")
            else
                FAILED_BUILDS+=("$version")
            fi

            ((current++))
        done
    fi

    # Show summary
    local total_duration=$(($(date +%s) - start_time))
    echo
    log INFO "Total execution time: ${total_duration}s"

    if ! show_summary "${successful_builds[@]}"; then
        exit 1
    fi

    log SUCCESS "🚀 All builds completed successfully and pushed to $registry"
}

# Global array for failed builds (needed for parallel mode)
declare -ga FAILED_BUILDS=()

# Parse arguments and run main function
parse_args "$@"
main