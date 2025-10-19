#!/bin/bash

# Generate config files for Asterisk versions from supported-asterisk-builds.yml
# This script provides batch config generation that can be reused by both local builds and CI/CD

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LATEST_BUILDS_FILE="${PROJECT_DIR}/asterisk/supported-asterisk-builds.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
FORCE=false
VERSIONS_FILTER=""
VERBOSE=false

# Function to log messages
log() {
    local level="$1"
    shift
    case "$level" in
        INFO)  echo -e "${BLUE}[INFO]${NC}  $*" ;;
        WARN)  echo -e "${YELLOW}[WARN]${NC}  $*" >&2 ;;
        ERROR) echo -e "${RED}[ERROR]${NC} $*" >&2 ;;
        SUCCESS) echo -e "${GREEN}[SUCCESS]${NC} $*" ;;
        DEBUG) [[ "$VERBOSE" == true ]] && echo -e "${BLUE}[DEBUG]${NC} $*" ;;
    esac
}

# Function to show usage
usage() {
    cat << EOF
Usage: $0 [options]

Generate YAML config files for Asterisk versions from supported-asterisk-builds.yml

Options:
  --versions "VERSION..."  Generate configs only for specific versions (space-separated)
  --force                  Regenerate configs even if they already exist
  --verbose                Enable verbose output
  --help, -h               Show this help message

Examples:
  $0                                    # Generate configs for all versions
  $0 --versions "20.16.0 22.5.2"        # Generate configs for specific versions
  $0 --force                            # Regenerate all configs
  $0 --versions "20.16.0" --force       # Regenerate config for specific version

EOF
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            usage
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --versions)
            VERSIONS_FILTER="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            log ERROR "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate prerequisites
if [[ ! -f "$LATEST_BUILDS_FILE" ]]; then
    log ERROR "YAML file not found: $LATEST_BUILDS_FILE"
    exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
    log ERROR "Python 3 is required but not found in PATH"
    exit 1
fi

# Check if generate-config.py exists
if [[ ! -f "${SCRIPT_DIR}/generate-config.py" ]]; then
    log ERROR "Config generator not found: ${SCRIPT_DIR}/generate-config.py"
    exit 1
fi

log INFO "Generating configs from: $LATEST_BUILDS_FILE"
[[ -n "$VERSIONS_FILTER" ]] && log INFO "Version filter: $VERSIONS_FILTER"
[[ "$FORCE" == true ]] && log INFO "Force regeneration enabled"

# Export environment variables for Python script
export PROJECT_DIR
export SCRIPT_DIR
export VERSIONS_FILTER
export FORCE
export VERBOSE

# Generate configs using Python
python3 << 'EOF'
import yaml
import sys
import os
import subprocess

def log_info(msg):
    print(f"\033[0;34m[INFO]\033[0m  {msg}", file=sys.stderr)

def log_success(msg):
    print(f"\033[0;32m[SUCCESS]\033[0m {msg}", file=sys.stderr)

def log_error(msg):
    print(f"\033[0;31m[ERROR]\033[0m {msg}", file=sys.stderr)

def log_debug(msg):
    if os.getenv('VERBOSE') == 'true':
        print(f"\033[0;34m[DEBUG]\033[0m {msg}", file=sys.stderr)

try:
    project_dir = os.getenv('PROJECT_DIR')
    script_dir = os.getenv('SCRIPT_DIR')
    versions_filter = os.getenv('VERSIONS_FILTER', '').split()
    force = os.getenv('FORCE') == 'true'

    yaml_file = os.path.join(project_dir, 'asterisk', 'supported-asterisk-builds.yml')

    with open(yaml_file, 'r') as f:
        data = yaml.safe_load(f)

    if 'latest_builds' not in data:
        log_error("No 'latest_builds' section found in YAML")
        sys.exit(1)

    configs_to_generate = []
    skipped = []

    for build in data['latest_builds']:
        version = build.get('version')
        if not version:
            continue

        # Apply version filter if specified
        if versions_filter and version not in versions_filter:
            log_debug(f"Skipping {version} (not in filter)")
            continue

        # Skip if no os_matrix (intentionally disabled)
        if 'os_matrix' not in build:
            log_debug(f"Skipping {version} (no os_matrix - disabled)")
            skipped.append(f"{version} (no os_matrix)")
            continue

        os_matrix = build['os_matrix']
        if isinstance(os_matrix, dict):
            os_matrix = [os_matrix]

        for matrix_entry in os_matrix:
            distribution = matrix_entry.get('distribution', 'trixie')
            os_name = matrix_entry.get('os', 'debian')

            config_filename = f"asterisk-{version}-{distribution}.yml"
            config_path = os.path.join(project_dir, 'configs', 'generated', config_filename)

            # Check if config already exists
            if os.path.exists(config_path) and not force:
                log_debug(f"Config exists, skipping: {config_filename}")
                continue

            configs_to_generate.append({
                'version': version,
                'distribution': distribution,
                'os': os_name,
                'config_path': config_path,
                'config_filename': config_filename
            })

    if not configs_to_generate:
        if skipped:
            log_info(f"Skipped {len(skipped)} disabled version(s)")
            for skip in skipped:
                log_debug(f"  - {skip}")
        log_info("No configs to generate (all up to date or filtered out)")
        sys.exit(0)

    log_info(f"Generating {len(configs_to_generate)} config file(s)...")

    # Ensure output directory exists
    output_dir = os.path.join(project_dir, 'configs', 'generated')
    os.makedirs(output_dir, exist_ok=True)

    successful = []
    failed = []

    for config in configs_to_generate:
        log_info(f"Generating: {config['config_filename']}")

        # Call generate-config.py
        cmd = [
            'python3',
            os.path.join(script_dir, 'generate-config.py'),
            config['version'],
            config['distribution'],
            '--templates-dir', os.path.join(project_dir, 'templates'),
            '--output', config['config_path']
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )

            if os.path.exists(config['config_path']):
                log_success(f"Generated: {config['config_filename']}")
                successful.append(config['config_filename'])
            else:
                log_error(f"Failed to generate: {config['config_filename']} (file not created)")
                failed.append(config['config_filename'])

        except subprocess.CalledProcessError as e:
            log_error(f"Failed to generate: {config['config_filename']}")
            if e.stderr:
                log_error(f"  Error: {e.stderr.strip()}")
            failed.append(config['config_filename'])

    # Summary
    print("", file=sys.stderr)
    log_info("=" * 50)
    log_info("CONFIG GENERATION SUMMARY")
    log_info("=" * 50)
    log_success(f"Successfully generated: {len(successful)}")
    if failed:
        log_error(f"Failed: {len(failed)}")

    if successful:
        print("", file=sys.stderr)
        log_info("Successfully generated configs:")
        for config_file in successful:
            log_success(f"  ✓ {config_file}")

    if failed:
        print("", file=sys.stderr)
        log_error("Failed configs:")
        for config_file in failed:
            log_error(f"  ✗ {config_file}")
        sys.exit(1)

    sys.exit(0)

except Exception as e:
    log_error(f"Script failed: {e}")
    import traceback
    traceback.print_exc(file=sys.stderr)
    sys.exit(1)
EOF
