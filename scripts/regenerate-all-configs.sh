#!/bin/bash

# Regenerate all configs from templates for every supported version
# This script loops through all versions in supported-asterisk-builds.yml
# and calls build-asterisk.sh with --force-config --dry-run to generate configs only

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LATEST_BUILDS_FILE="${PROJECT_DIR}/asterisk/supported-asterisk-builds.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to log messages
log() {
    local level="$1"
    shift
    case "$level" in
        INFO)  echo -e "${BLUE}[INFO]${NC}  $*" ;;
        WARN)  echo -e "${YELLOW}[WARN]${NC}  $*" >&2 ;;
        ERROR) echo -e "${RED}[ERROR]${NC} $*" >&2 ;;
        SUCCESS) echo -e "${GREEN}[SUCCESS]${NC} $*" ;;
    esac
}

# Function to show usage
usage() {
    cat << EOF
Usage: $0 [options]

Regenerate all configs from templates for every supported Asterisk version.
This script reads asterisk/supported-asterisk-builds.yml and generates configs
for all versions that have an os_matrix defined.

Options:
  --dry-run    Show what would be regenerated without doing it
  --help, -h   Show this help message

Examples:
  $0           # Regenerate all configs
  $0 --dry-run # Preview what would be regenerated

EOF
    exit 0
}

# Default values
DRY_RUN=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            usage
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            log ERROR "Unknown option: $1"
            usage
            ;;
    esac
done

# Check if files exist
if [[ ! -f "$LATEST_BUILDS_FILE" ]]; then
    log ERROR "Supported builds file not found: $LATEST_BUILDS_FILE"
    exit 1
fi

if [[ ! -f "$SCRIPT_DIR/build-asterisk.sh" ]]; then
    log ERROR "Build script not found: $SCRIPT_DIR/build-asterisk.sh"
    exit 1
fi

log INFO "Regenerating all configs from templates..."
[[ "$DRY_RUN" == true ]] && log INFO "DRY RUN MODE - No configs will be generated"

# Extract versions from YAML that have os_matrix
export LATEST_BUILDS_FILE
versions=$(python3 << EOF
import yaml
import sys
import os

try:
    builds_file = "$LATEST_BUILDS_FILE"
    with open(builds_file, 'r') as f:
        data = yaml.safe_load(f)

    if 'latest_builds' not in data:
        print("ERROR: No 'latest_builds' section found in YAML", file=sys.stderr)
        sys.exit(1)

    versions = []
    for build in data['latest_builds']:
        version = build.get('version', 'unknown')
        if 'os_matrix' in build:
            versions.append(version)

    for version in versions:
        print(version)

except Exception as e:
    print(f"ERROR: Failed to parse YAML: {e}", file=sys.stderr)
    sys.exit(1)
EOF
)

if [[ -z "$versions" ]]; then
    log ERROR "No versions found with os_matrix in $LATEST_BUILDS_FILE"
    exit 1
fi

# Count versions
version_count=$(echo "$versions" | wc -l)
log INFO "Found $version_count versions to process"

# Show versions if dry run
if [[ "$DRY_RUN" == true ]]; then
    log INFO "Would regenerate configs for these versions:"
    echo "$versions" | while read -r version; do
        log INFO "  → $version"
    done
    exit 0
fi

# Process each version
successful=0
failed=0

# Convert to array to avoid subshell issues
readarray -t version_array <<< "$versions"

for version in "${version_array[@]}"; do
    [[ -z "$version" ]] && continue  # Skip empty lines

    log INFO "Processing: $version"

    # Generate config and all build assets using the proper template system
    # This ensures consistency with build-asterisk.sh and uses the DRY template architecture
    if "$SCRIPT_DIR/build-asterisk.sh" "$version" --force-config --dry-run >/dev/null 2>&1; then
        log SUCCESS "Generated all files for: $version"
        ((successful++))
    else
        log ERROR "Config generation failed: $version"
        ((failed++))
    fi

    # Add a small delay and progress indicator
    sleep 0.1
    log INFO "Completed $((successful + failed)) of ${#version_array[@]} versions"
done

# Final summary
log INFO ""
log INFO "Config regeneration completed"
log INFO "Successful: $successful, Failed: $failed"
log SUCCESS "Check configs/generated/ directory for generated files"