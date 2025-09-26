#!/bin/bash

# Common build functions library for Asterisk Docker builds
# Provides modular functionality for build scripts and testing
# Sources functionality from existing build-asterisk.sh and build-all.sh

# Prevent multiple sourcing
if [[ "${BUILD_COMMON_LOADED:-}" == "true" ]]; then
    return 0
fi
BUILD_COMMON_LOADED=true

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logging functions (standardized across all scripts)
log() {
    local level="$1"
    shift
    local timestamp=$(date "+%Y-%m-%d %H:%M:%S")

    case "$level" in
        ERROR)   echo -e "${timestamp} [${RED}ERROR${NC}] $*" >&2 ;;
        WARN)    echo -e "${timestamp} [${YELLOW}WARN${NC}] $*" >&2 ;;
        INFO)    echo -e "${timestamp} [${BLUE}INFO${NC}] $*" ;;
        SUCCESS) echo -e "${timestamp} [${GREEN}SUCCESS${NC}] $*" ;;
        DEBUG)   [[ "${VERBOSE:-false}" == "true" ]] && echo -e "${timestamp} [${CYAN}DEBUG${NC}] $*" >&2 ;;
    esac
}

# Initialize project paths and validate structure
init_project_paths() {
    if [[ -z "${PROJECT_DIR:-}" ]]; then
        # Try to detect from calling script location
        local calling_script="${BASH_SOURCE[1]:-$0}"
        SCRIPT_DIR="$(cd "$(dirname "$calling_script")" && pwd)"
        PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

        # If we still don't have valid paths, try current directory
        if [[ ! -d "$PROJECT_DIR/templates" ]] && [[ -d "./templates" ]]; then
            PROJECT_DIR="$(pwd)"
            SCRIPT_DIR="$PROJECT_DIR/scripts"
        fi
    fi

    # Export for use in other scripts
    export SCRIPT_DIR PROJECT_DIR
    export LATEST_BUILDS_FILE="${PROJECT_DIR}/asterisk/supported-asterisk-builds.yml"

    # Validate project structure
    local required_dirs=("$PROJECT_DIR/templates" "$PROJECT_DIR/configs" "$PROJECT_DIR/lib")
    local required_files=("$LATEST_BUILDS_FILE" "$PROJECT_DIR/CLAUDE.md")

    for dir in "${required_dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            log ERROR "Required directory not found: $dir"
            log ERROR "Make sure you're running this script from a valid Asterisk build project directory."
            return 1
        fi
    done

    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            log ERROR "Required file not found: $file"
            log ERROR "Make sure you're running this script from a valid Asterisk build project directory."
            return 1
        fi
    done

    log DEBUG "Project paths initialized: PROJECT_DIR=$PROJECT_DIR"
    return 0
}

# Parse YAML matrix to get buildable versions and their configurations
parse_yaml_matrix() {
    local yaml_file="$1"
    local output_format="${2:-json}"  # json, versions, or configs

    log DEBUG "Parsing YAML matrix from: $yaml_file"

    if [[ ! -f "$yaml_file" ]]; then
        log ERROR "YAML file not found: $yaml_file"
        return 1
    fi

    # Use Python to parse YAML and extract build matrix
    python3 -c "
import sys
import yaml
import json

try:
    with open('$yaml_file', 'r') as f:
        data = yaml.safe_load(f)

    buildable_configs = []

    for build in data.get('latest_builds', []):
        version = build.get('version')
        os_matrix = build.get('os_matrix')

        # Skip versions without os_matrix (intentionally disabled)
        if not os_matrix:
            continue

        # Handle different os_matrix formats
        if isinstance(os_matrix, list):
            matrices = os_matrix
        else:
            matrices = [os_matrix]

        for matrix in matrices:
            os_name = matrix.get('os', 'debian')
            distribution = matrix.get('distribution', 'trixie')
            architectures = matrix.get('architectures', ['amd64'])

            for arch in architectures:
                config = {
                    'version': version,
                    'os': os_name,
                    'distribution': distribution,
                    'architecture': arch,
                    'config_key': f'{version}_{os_name}-{distribution}'
                }
                buildable_configs.append(config)

    output_format = '$output_format'
    if output_format == 'json':
        print(json.dumps(buildable_configs, indent=2))
    elif output_format == 'versions':
        versions = sorted(set(config['version'] for config in buildable_configs))
        for version in versions:
            print(version)
    elif output_format == 'configs':
        for config in buildable_configs:
            print(f\"{config['version']} {config['os']} {config['distribution']} {config['architecture']}\")
    else:
        print(json.dumps(buildable_configs, indent=2))

except Exception as e:
    print(f'Error parsing YAML: {e}', file=sys.stderr)
    sys.exit(1)
"
}

# Get list of buildable versions from YAML matrix
get_buildable_versions() {
    local yaml_file="${1:-$LATEST_BUILDS_FILE}"
    parse_yaml_matrix "$yaml_file" "versions"
}

# Get build configurations for a specific version
get_version_configs() {
    local version="$1"
    local yaml_file="${2:-$LATEST_BUILDS_FILE}"
    local arch_filter="${3:-}"  # Optional architecture filter

    parse_yaml_matrix "$yaml_file" "json" | python3 -c "
import sys
import json

data = json.load(sys.stdin)
version = '$version'
arch_filter = '$arch_filter'

configs = [c for c in data if c['version'] == version]
if arch_filter:
    configs = [c for c in configs if c['architecture'] == arch_filter]

for config in configs:
    print(f\"{config['os']} {config['distribution']} {config['architecture']}\")
"
}

# Validate Docker prerequisites
check_docker_prerequisites() {
    log DEBUG "Checking Docker prerequisites..."

    # Check Docker
    if ! command -v docker >/dev/null 2>&1; then
        log ERROR "Docker is not installed or not in PATH"
        return 1
    fi

    # Check Docker daemon
    if ! docker info >/dev/null 2>&1; then
        log ERROR "Docker daemon is not running"
        return 1
    fi

    # Check buildx
    if ! docker buildx version >/dev/null 2>&1; then
        log ERROR "Docker buildx is not available"
        return 1
    fi

    log SUCCESS "Docker prerequisites check passed"
    return 0
}

# Validate Python prerequisites for YAML processing
check_python_prerequisites() {
    log DEBUG "Checking Python prerequisites..."

    if ! command -v python3 >/dev/null 2>&1; then
        log ERROR "Python 3 is not installed or not in PATH"
        return 1
    fi

    # Check required Python modules
    local required_modules=("yaml" "jinja2")
    for module in "${required_modules[@]}"; do
        if ! python3 -c "import $module" >/dev/null 2>&1; then
            log ERROR "Python module '$module' is not installed"
            log INFO "Install with: pip3 install $module"
            return 1
        fi
    done

    log SUCCESS "Python prerequisites check passed"
    return 0
}

# Docker image validation functions
validate_image_exists() {
    local image_tag="$1"

    if docker image inspect "$image_tag" >/dev/null 2>&1; then
        log DEBUG "Image exists: $image_tag"
        return 0
    else
        log ERROR "Image not found: $image_tag"
        return 1
    fi
}

# Test container startup and basic functionality
validate_container_startup() {
    local image_tag="$1"
    local timeout="${2:-30}"

    log DEBUG "Testing container startup for: $image_tag"

    # Test basic container startup with Asterisk version check
    if timeout "$timeout" docker run --rm "$image_tag" asterisk -V >/dev/null 2>&1; then
        log DEBUG "Container startup successful: $image_tag"
        return 0
    else
        log ERROR "Container startup failed: $image_tag"
        return 1
    fi
}

# Get container Asterisk version
get_container_version() {
    local image_tag="$1"

    docker run --rm "$image_tag" asterisk -V 2>/dev/null | head -n1 || echo "Unknown"
}

# Get image size information
get_image_size() {
    local image_tag="$1"

    docker image inspect "$image_tag" --format '{{.Size}}' 2>/dev/null || echo "0"
}

# Advanced container validation functions
validate_asterisk_functionality() {
    local image_tag="$1"
    local timeout="${2:-60}"

    log DEBUG "Testing Asterisk functionality for: $image_tag"

    # Test 1: Asterisk version check
    if ! timeout 30 docker run --rm "$image_tag" asterisk -V >/dev/null 2>&1; then
        log ERROR "Asterisk version check failed: $image_tag"
        return 1
    fi

    # Test 2: Configuration syntax check
    if ! timeout 30 docker run --rm "$image_tag" asterisk -T >/dev/null 2>&1; then
        log ERROR "Asterisk configuration syntax check failed: $image_tag"
        return 1
    fi

    # Test 3: Module loading check (quick start/stop)
    if ! timeout "$timeout" docker run --rm "$image_tag" sh -c "asterisk -rx 'core show version' || echo 'Quick test completed'" >/dev/null 2>&1; then
        log ERROR "Asterisk quick functionality test failed: $image_tag"
        return 1
    fi

    log DEBUG "Asterisk functionality validation passed: $image_tag"
    return 0
}

# Validate Docker image layers and optimization
validate_image_optimization() {
    local image_tag="$1"

    log DEBUG "Validating image optimization for: $image_tag"

    # Get image details
    local size_bytes
    size_bytes=$(get_image_size "$image_tag")
    local size_human
    size_human=$(format_bytes "$size_bytes")

    log DEBUG "Image size: $size_human ($size_bytes bytes)"

    # Check for reasonable size (less than 2GB for most builds)
    local max_size=$((2 * 1024 * 1024 * 1024))  # 2GB in bytes
    if [[ $size_bytes -gt $max_size ]]; then
        log WARN "Image size is quite large: $size_human (exceeds 2GB)"
        return 1
    fi

    # Check image history for optimization
    local layer_count
    layer_count=$(docker image inspect "$image_tag" --format '{{len .RootFS.Layers}}' 2>/dev/null || echo "0")

    if [[ $layer_count -gt 50 ]]; then
        log WARN "Image has many layers ($layer_count), consider optimization"
    fi

    log DEBUG "Image optimization check passed: $size_human, $layer_count layers"
    return 0
}

# Generate comprehensive image report
generate_image_report() {
    local image_tag="$1"
    local output_file="${2:-}"

    local report=""
    report+="=== IMAGE REPORT: $image_tag ===\n"

    # Basic image info
    if validate_image_exists "$image_tag"; then
        local size_bytes
        size_bytes=$(get_image_size "$image_tag")
        local size_human
        size_human=$(format_bytes "$size_bytes")

        report+="Size: $size_human ($size_bytes bytes)\n"

        # Get image creation date
        local created
        created=$(docker image inspect "$image_tag" --format '{{.Created}}' 2>/dev/null | cut -d'T' -f1 || echo "Unknown")
        report+="Created: $created\n"

        # Get Asterisk version from container
        local asterisk_version
        asterisk_version=$(get_container_version "$image_tag")
        report+="Asterisk Version: $asterisk_version\n"

        # Test basic functionality
        if validate_container_startup "$image_tag"; then
            report+="Container Startup: ✅ PASS\n"
        else
            report+="Container Startup: ❌ FAIL\n"
        fi

        # Test Asterisk functionality
        if validate_asterisk_functionality "$image_tag"; then
            report+="Asterisk Functionality: ✅ PASS\n"
        else
            report+="Asterisk Functionality: ❌ FAIL\n"
        fi

        # Image optimization check
        if validate_image_optimization "$image_tag"; then
            report+="Image Optimization: ✅ PASS\n"
        else
            report+="Image Optimization: ⚠️ WARN\n"
        fi
    else
        report+="Status: ❌ IMAGE NOT FOUND\n"
    fi

    report+="================================\n"

    # Output report
    if [[ -n "$output_file" ]]; then
        echo -e "$report" >> "$output_file"
    else
        echo -e "$report"
    fi
}

# Comprehensive validation function
validate_complete_image() {
    local image_tag="$1"
    local validation_level="${2:-basic}"  # basic, standard, comprehensive

    log DEBUG "Running $validation_level validation for: $image_tag"

    # Basic validation
    if ! validate_image_exists "$image_tag"; then
        return 1
    fi

    if ! validate_container_startup "$image_tag"; then
        return 1
    fi

    # Standard validation
    if [[ "$validation_level" != "basic" ]]; then
        if ! validate_asterisk_functionality "$image_tag"; then
            return 1
        fi
    fi

    # Comprehensive validation
    if [[ "$validation_level" == "comprehensive" ]]; then
        if ! validate_image_optimization "$image_tag"; then
            log WARN "Image optimization warnings for $image_tag"
            # Don't fail on optimization warnings
        fi
    fi

    log DEBUG "Complete validation passed for: $image_tag"
    return 0
}

# Format bytes to human readable
format_bytes() {
    local bytes="$1"

    python3 -c "
size = int('$bytes')
for unit in ['B', 'KB', 'MB', 'GB']:
    if size < 1024.0:
        print(f'{size:.1f}{unit}')
        break
    size /= 1024.0
"
}

# Build result tracking (initialize as global associative arrays)
declare -gA BUILD_RESULTS
declare -gA BUILD_TIMES
declare -gA BUILD_ERRORS

# Initialize build tracking
init_build_tracking() {
    BUILD_RESULTS=()
    BUILD_TIMES=()
    BUILD_ERRORS=()
    export BUILD_START_TIME=$(date +%s)
}

# Record build result
record_build_result() {
    local version="$1"
    local config_key="$2"
    local result="$3"        # success, failure, skipped
    local error_msg="${4:-}" # Optional error message
    local build_time="${5:-0}" # Build time in seconds

    local key="${version}_${config_key}"
    BUILD_RESULTS["$key"]="$result"
    BUILD_TIMES["$key"]="$build_time"

    if [[ -n "$error_msg" ]]; then
        BUILD_ERRORS["$key"]="$error_msg"
    fi

    log DEBUG "Recorded build result: $key = $result (${build_time}s)"
}

# Generate build statistics
generate_build_stats() {
    local total=0
    local success=0
    local failure=0
    local skipped=0
    local total_time=0

    log INFO "=== BUILD STATISTICS ==="

    for key in "${!BUILD_RESULTS[@]}"; do
        local result="${BUILD_RESULTS[$key]}"
        local build_time="${BUILD_TIMES[$key]:-0}"

        ((total++))
        ((total_time += build_time))

        case "$result" in
            success) ((success++)) ;;
            failure) ((failure++)) ;;
            skipped) ((skipped++)) ;;
        esac
    done

    log INFO "Total builds: $total"
    log INFO "Successful: $success"
    log INFO "Failed: $failure"
    log INFO "Skipped: $skipped"
    log INFO "Total build time: ${total_time}s"

    if [[ $total -gt 0 ]]; then
        local success_rate=$((success * 100 / total))
        log INFO "Success rate: ${success_rate}%"
    fi

    # Show failures if any
    if [[ $failure -gt 0 ]]; then
        log WARN "=== FAILED BUILDS ==="
        for key in "${!BUILD_RESULTS[@]}"; do
            if [[ "${BUILD_RESULTS[$key]}" == "failure" ]]; then
                local error_msg="${BUILD_ERRORS[$key]:-No error message}"
                log ERROR "FAILED: $key - $error_msg"
            fi
        done
    fi

    return $failure
}

# Utility function to run build-asterisk.sh with common parameters
run_asterisk_build() {
    local version="$1"
    local os_filter="${2:-}"
    local arch_filter="${3:-amd64}"
    local additional_args="${4:-}"

    local build_script="${SCRIPT_DIR}/build-asterisk.sh"
    local cmd_args=("$version")

    # Add filters if specified
    [[ -n "$os_filter" ]] && cmd_args+=("$os_filter")
    [[ -n "$arch_filter" ]] && cmd_args+=("$arch_filter")

    # Common test parameters
    cmd_args+=(
        "--platforms" "linux/$arch_filter"
        "--dry-run"  # Don't actually build, just validate
        "--force-config"  # Always regenerate configs
    )

    # Add additional arguments
    if [[ -n "$additional_args" ]]; then
        # Split additional_args and add to array
        read -ra extra_args <<< "$additional_args"
        cmd_args+=("${extra_args[@]}")
    fi

    log DEBUG "Running: $build_script ${cmd_args[*]}"

    # Execute build command and capture result
    if "$build_script" "${cmd_args[@]}"; then
        return 0
    else
        return 1
    fi
}

# Export all functions for use in other scripts
export -f log init_project_paths parse_yaml_matrix get_buildable_versions
export -f get_version_configs check_docker_prerequisites check_python_prerequisites
export -f validate_image_exists validate_container_startup get_container_version
export -f get_image_size format_bytes init_build_tracking record_build_result
export -f generate_build_stats run_asterisk_build validate_asterisk_functionality
export -f validate_image_optimization generate_image_report validate_complete_image

# Only log if VERBOSE is explicitly set
if [[ "${VERBOSE:-}" == "true" ]]; then
    log DEBUG "build-common.sh library loaded successfully"
fi