#!/bin/bash

# Test Build Script for Asterisk Docker Images
# Validates all supported Asterisk versions locally (AMD64 only, no push)
# Uses modular approach leveraging existing build infrastructure

set -euo pipefail

# Initialize project paths
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Source common build functions
# shellcheck source=../lib/build-common.sh
source "${PROJECT_DIR}/lib/build-common.sh"

# Configuration defaults
DEFAULT_ARCH="amd64"
DEFAULT_TEST_MODE="config"  # config, build, validate
PARALLEL_TESTS=false
MAX_PARALLEL=3
SKIP_EXISTING=false
TEST_TIMEOUT=300  # 5 minutes per test
DETAILED_REPORT=true

# Test modes:
# - config: Only validate configuration generation (fastest)
# - build: Actually build Docker images (slower)
# - validate: Build + container startup testing (comprehensive)

# Function to show usage
usage() {
    cat << EOF
Usage: $0 [options] [version_pattern]

Test Build Script for Asterisk Docker Images
Validates all supported versions locally without pushing to registry.

Options:
    --mode MODE         Test mode: config|build|validate (default: config)
                        config: Only validate config generation (fastest)
                        build: Actually build Docker images
                        validate: Build + test container startup

    --arch ARCH         Target architecture (default: amd64)
    --parallel          Enable parallel testing (up to $MAX_PARALLEL concurrent)
    --max-parallel N    Maximum parallel jobs (default: $MAX_PARALLEL)
    --skip-existing     Skip versions with existing Docker images
    --timeout SECONDS   Timeout per test (default: $TEST_TIMEOUT)
    --no-report         Skip detailed report generation
    --verbose           Enable verbose logging
    --help, -h          Show this help

Version Filters:
    version_pattern     Optional pattern to filter versions (e.g., "22.*", "23.0.0-rc1")
                        If not specified, tests all buildable versions

Examples:
    $0                              # Test config generation for all versions
    $0 --mode build                 # Build all versions (AMD64 only)
    $0 --mode validate "22.*"       # Full validation for v22 versions
    $0 --mode build --parallel      # Parallel builds for faster testing
    $0 --mode config "23.0.0-rc1"   # Test specific version config

Test Modes Explained:
    config:   Fast validation of YAML configs and Dockerfile generation
             Ensures templates work and all versions have valid configs
             Runtime: ~1-2 minutes for all versions

    build:    Actually builds Docker images using Docker buildx
             Validates complete build process including package installation
             Runtime: ~30-60 minutes for all versions

    validate: Full end-to-end testing including container startup
             Builds images + tests Asterisk startup and version detection
             Runtime: ~45-75 minutes for all versions

EOF
}

# Parse command line arguments
TEST_MODE="$DEFAULT_TEST_MODE"
ARCH_FILTER="$DEFAULT_ARCH"
VERSION_PATTERN=""
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --mode)
            TEST_MODE="$2"
            if [[ ! "$TEST_MODE" =~ ^(config|build|validate)$ ]]; then
                log ERROR "Invalid test mode: $TEST_MODE. Must be: config, build, or validate"
                exit 1
            fi
            shift 2
            ;;
        --arch)
            ARCH_FILTER="$2"
            shift 2
            ;;
        --parallel)
            PARALLEL_TESTS=true
            shift
            ;;
        --max-parallel)
            MAX_PARALLEL="$2"
            shift 2
            ;;
        --skip-existing)
            SKIP_EXISTING=true
            shift
            ;;
        --timeout)
            TEST_TIMEOUT="$2"
            shift 2
            ;;
        --no-report)
            DETAILED_REPORT=false
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            if [[ -z "$VERSION_PATTERN" ]]; then
                VERSION_PATTERN="$1"
            else
                log ERROR "Unexpected argument: $1"
                usage
                exit 1
            fi
            shift
            ;;
    esac
done

# Export verbose setting for common library
export VERBOSE

# Initialize and validate environment
log INFO "Initializing Asterisk Docker Build Test System"
log INFO "Test mode: $TEST_MODE"
log INFO "Architecture: $ARCH_FILTER"
[[ -n "$VERSION_PATTERN" ]] && log INFO "Version pattern: $VERSION_PATTERN"

# Initialize project paths and validate structure
if ! init_project_paths; then
    log ERROR "Failed to initialize project paths"
    exit 1
fi

# Check prerequisites based on test mode
if [[ "$TEST_MODE" == "config" ]]; then
    log INFO "Checking Python prerequisites for config testing..."
    if ! check_python_prerequisites; then
        exit 1
    fi
else
    log INFO "Checking Docker and Python prerequisites for build testing..."
    if ! check_docker_prerequisites || ! check_python_prerequisites; then
        exit 1
    fi
fi

# Get buildable versions from YAML matrix
log INFO "Loading buildable versions from YAML matrix..."
log DEBUG "Using YAML file: $LATEST_BUILDS_FILE"
mapfile -t all_versions < <(get_buildable_versions "$LATEST_BUILDS_FILE")

log DEBUG "Raw get_buildable_versions output: ${all_versions[*]}"

if [[ ${#all_versions[@]} -eq 0 ]]; then
    log ERROR "No buildable versions found in $LATEST_BUILDS_FILE"
    log DEBUG "Testing direct function call..."
    get_buildable_versions "$LATEST_BUILDS_FILE" | head -5 >&2
    exit 1
fi

log INFO "Found ${#all_versions[@]} buildable versions"

# Filter versions if pattern provided
filtered_versions=()
if [[ -n "$VERSION_PATTERN" ]]; then
    for version in "${all_versions[@]}"; do
        # Use shell pattern matching (e.g., 22.* matches 22.5.2)
        if [[ "$version" == $VERSION_PATTERN ]]; then
            filtered_versions+=("$version")
        fi
    done

    if [[ ${#filtered_versions[@]} -eq 0 ]]; then
        log ERROR "No versions match pattern: $VERSION_PATTERN"
        log INFO "Available versions:"
        printf '%s\n' "${all_versions[@]}" | sort
        exit 1
    fi

    log INFO "Filtered to ${#filtered_versions[@]} versions matching pattern: $VERSION_PATTERN"
else
    filtered_versions=("${all_versions[@]}")
fi

# Initialize build tracking
init_build_tracking

# Function to test a single version configuration
test_version_config() {
    local version="$1"
    local start_time=$(date +%s)
    local config_key="${version}_${ARCH_FILTER}"

    log INFO "Testing version: $version (mode: $TEST_MODE)"

    # Get configurations for this version
    local configs
    mapfile -t configs < <(get_version_configs "$version" "$LATEST_BUILDS_FILE" "$ARCH_FILTER")

    if [[ ${#configs[@]} -eq 0 ]]; then
        log WARN "No configurations found for version $version with architecture $ARCH_FILTER"
        record_build_result "$version" "$config_key" "skipped" "No matching configurations"
        return 0
    fi

    log DEBUG "Found ${#configs[@]} configurations for $version"

    local overall_success=true
    local error_messages=()

    # Test each configuration
    for config in "${configs[@]}"; do
        read -r os distribution architecture <<< "$config"
        local full_config_key="${version}_${os}-${distribution}_${architecture}"

        log DEBUG "Testing config: $os/$distribution/$architecture"

        case "$TEST_MODE" in
            config)
                # Test configuration generation only
                if ! test_config_generation "$version" "$os" "$distribution" "$architecture"; then
                    overall_success=false
                    error_messages+=("Config generation failed for $os/$distribution/$architecture")
                fi
                ;;
            build)
                # Test actual Docker build
                if ! test_docker_build "$version" "$os" "$distribution" "$architecture"; then
                    overall_success=false
                    error_messages+=("Docker build failed for $os/$distribution/$architecture")
                fi
                ;;
            validate)
                # Full validation: build + container testing
                if ! test_full_validation "$version" "$os" "$distribution" "$architecture"; then
                    overall_success=false
                    error_messages+=("Full validation failed for $os/$distribution/$architecture")
                fi
                ;;
        esac
    done

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    if [[ "$overall_success" == true ]]; then
        log SUCCESS "Version $version: All tests passed (${duration}s)"
        record_build_result "$version" "$config_key" "success" "" "$duration"
    else
        local error_summary
        printf -v error_summary "%s; " "${error_messages[@]}"
        log ERROR "Version $version: Tests failed (${duration}s) - ${error_summary%%; }"
        record_build_result "$version" "$config_key" "failure" "$error_summary" "$duration"
    fi
}

# Test configuration generation
test_config_generation() {
    local version="$1"
    local os="$2"
    local distribution="$3"
    local architecture="$4"

    log DEBUG "Testing config generation for $version $os/$distribution/$architecture"

    # Use dry-run mode to test config generation without building
    if run_asterisk_build "$version" "$os" "$architecture" "--verbose"; then
        log DEBUG "Config generation successful for $version"
        return 0
    else
        log ERROR "Config generation failed for $version"
        return 1
    fi
}

# Test Docker build
test_docker_build() {
    local version="$1"
    local os="$2"
    local distribution="$3"
    local architecture="$4"

    log DEBUG "Testing Docker build for $version $os/$distribution/$architecture"

    # For actual builds, we need to call the build script without --dry-run
    local build_script="${SCRIPT_DIR}/build-asterisk.sh"
    local cmd_args=(
        "$version"
        "$os"
        "$architecture"
        "--platforms" "linux/$architecture"
        "--force-config"
        "--verbose"
    )

    log DEBUG "Running actual build: $build_script ${cmd_args[*]}"

    # Use timeout to prevent hanging builds
    if timeout "$TEST_TIMEOUT" "$build_script" "${cmd_args[@]}"; then
        log DEBUG "Docker build successful for $version"
        return 0
    else
        log ERROR "Docker build failed or timed out for $version"
        return 1
    fi
}

# Test full validation (build + container startup)
test_full_validation() {
    local version="$1"
    local os="$2"
    local distribution="$3"
    local architecture="$4"

    log DEBUG "Testing full validation for $version $os/$distribution/$architecture"

    # First, test the build
    if ! test_docker_build "$version" "$os" "$distribution" "$architecture"; then
        return 1
    fi

    # Generate expected image tag
    local image_tag="${version}_${os}-${distribution}"

    # Wait a moment for image to be available
    sleep 2

    # Test container startup and comprehensive functionality
    if ! validate_image_exists "$image_tag"; then
        log ERROR "Built image not found: $image_tag"
        return 1
    fi

    # Use comprehensive validation including Asterisk functionality tests
    if ! validate_complete_image "$image_tag" "comprehensive"; then
        log ERROR "Comprehensive validation failed for $image_tag"
        return 1
    fi

    log DEBUG "Full validation successful for $version"
    return 0
}

# Function for parallel test execution
run_parallel_tests() {
    local versions=("$@")
    local pids=()
    local running_jobs=0

    for version in "${versions[@]}"; do
        # Wait if we've reached max parallel jobs
        while [[ $running_jobs -ge $MAX_PARALLEL ]]; do
            for i in "${!pids[@]}"; do
                if ! kill -0 "${pids[$i]}" 2>/dev/null; then
                    # Job finished
                    wait "${pids[$i]}"
                    unset "pids[$i]"
                    ((running_jobs--))
                fi
            done
            sleep 1
        done

        # Start new test job
        log INFO "Starting parallel test for version: $version"
        test_version_config "$version" &
        local pid=$!
        pids+=("$pid")
        ((running_jobs++))
    done

    # Wait for all remaining jobs
    log INFO "Waiting for remaining parallel jobs to complete..."
    for pid in "${pids[@]}"; do
        if [[ -n "$pid" ]]; then
            wait "$pid"
        fi
    done
}

# Main test execution
log INFO "Starting test execution for ${#filtered_versions[@]} versions"
log INFO "Test parameters: mode=$TEST_MODE, arch=$ARCH_FILTER, parallel=$PARALLEL_TESTS"

if [[ "$PARALLEL_TESTS" == true && "$TEST_MODE" != "config" ]]; then
    log INFO "Running tests in parallel (max $MAX_PARALLEL concurrent jobs)"
    run_parallel_tests "${filtered_versions[@]}"
else
    # Sequential execution
    for version in "${filtered_versions[@]}"; do
        test_version_config "$version"
    done
fi

# Generate final report
log INFO "Test execution completed"

if [[ "$DETAILED_REPORT" == true ]]; then
    echo
    log INFO "=== DETAILED TEST REPORT ==="
    echo "Test Mode: $TEST_MODE"
    echo "Architecture: $ARCH_FILTER"
    echo "Parallel Processing: $PARALLEL_TESTS"
    [[ -n "$VERSION_PATTERN" ]] && echo "Version Pattern: $VERSION_PATTERN"
    echo "Tested Versions: ${#filtered_versions[@]}"
    echo

    # Show version list
    log INFO "Tested versions:"
    printf '%s\n' "${filtered_versions[@]}" | sort | sed 's/^/  /'
    echo
fi

# Generate and display build statistics
if ! generate_build_stats; then
    log ERROR "Some tests failed. Check the detailed report above."
    exit 1
else
    log SUCCESS "All tests passed successfully!"
fi