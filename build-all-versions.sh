#!/bin/bash
set -euo pipefail

# Build All Asterisk Versions Script
# Builds all 23 versions from supported-asterisk-builds.yml with validation

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_LOG="$SCRIPT_DIR/build-all-versions.log"
SUCCESS_LOG="$SCRIPT_DIR/successful-builds.log"
FAILED_LOG="$SCRIPT_DIR/failed-builds.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TOTAL_VERSIONS=0
SUCCESSFUL_BUILDS=0
FAILED_BUILDS=0

# Initialize log files
echo "=== Asterisk Build All Versions - $(date) ===" | tee "$BUILD_LOG"
echo "=== Successful Builds - $(date) ===" > "$SUCCESS_LOG"
echo "=== Failed Builds - $(date) ===" > "$FAILED_LOG"

# Extract versions from YAML
VERSIONS=($(python3 -c "
import yaml
with open('$SCRIPT_DIR/asterisk/supported-asterisk-builds.yml') as f:
    data = yaml.safe_load(f)
versions = [build['version'] for build in data['latest_builds']]
print(' '.join(versions))
"))

TOTAL_VERSIONS=${#VERSIONS[@]}

echo -e "${BLUE}Found $TOTAL_VERSIONS versions to build${NC}" | tee -a "$BUILD_LOG"

# Function to validate built image
validate_image() {
    local version="$1"
    local image_name="$2"

    echo -e "${YELLOW}Validating image: $image_name${NC}"

    # Check if image exists
    if ! docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "^$image_name:latest$"; then
        echo -e "${RED}❌ Image not found: $image_name${NC}"
        echo "Available images:" >&2
        docker images --format "{{.Repository}}:{{.Tag}}" | grep "$image_name" >&2 || echo "No matches found" >&2
        return 1
    fi

    # Test asterisk -V command
    local asterisk_output
    if asterisk_output=$(docker run --rm "$image_name:latest" asterisk -V 2>/dev/null); then
        echo -e "${GREEN}✅ Image validation successful: $asterisk_output${NC}"
        echo "$version: $asterisk_output" >> "$SUCCESS_LOG"
        return 0
    else
        echo -e "${RED}❌ Image validation failed: asterisk -V command failed${NC}"
        return 1
    fi
}

# Function to build single version
build_version() {
    local version="$1"
    local build_num="$2"

    echo -e "\n${BLUE}=== Building $build_num/$TOTAL_VERSIONS: $version ===${NC}" | tee -a "$BUILD_LOG"

    # Get expected image name from build matrix
    local image_name
    image_name=$(python3 get-image-name.py "$version")

    # Build with force-config and timeout
    local build_start=$(date +%s)
    if timeout 1800 ./scripts/build-asterisk.sh "$version" --force-config --verbose >> "$BUILD_LOG" 2>&1; then
        local build_end=$(date +%s)
        local build_time=$((build_end - build_start))

        echo -e "${GREEN}✅ Build successful: $version (${build_time}s)${NC}" | tee -a "$BUILD_LOG"

        # Validate the built image
        if validate_image "$version" "$image_name"; then
            ((SUCCESSFUL_BUILDS++))
            echo -e "${GREEN}✅ Complete: $version${NC}"
        else
            echo -e "${YELLOW}⚠️  Build succeeded but validation failed: $version${NC}"
            echo "$version: BUILD_OK_VALIDATION_FAILED" >> "$FAILED_LOG"
            ((FAILED_BUILDS++))
        fi
    else
        local build_end=$(date +%s)
        local build_time=$((build_end - build_start))

        echo -e "${RED}❌ Build failed: $version (${build_time}s)${NC}" | tee -a "$BUILD_LOG"
        echo "$version: BUILD_FAILED" >> "$FAILED_LOG"
        ((FAILED_BUILDS++))

        # Show last few lines of error for debugging
        echo -e "${YELLOW}Last 10 lines of build output:${NC}"
        tail -n 10 "$BUILD_LOG" | grep -v "^$" || true
    fi
}

# Main build loop
echo -e "\n${BLUE}Starting sequential build of all versions...${NC}" | tee -a "$BUILD_LOG"

for i in "${!VERSIONS[@]}"; do
    version="${VERSIONS[$i]}"
    build_num=$((i + 1))

    build_version "$version" "$build_num"

    # Brief pause between builds
    sleep 2
done

# Final summary
echo -e "\n${BLUE}=== BUILD SUMMARY ===${NC}" | tee -a "$BUILD_LOG"
echo -e "${GREEN}✅ Successful builds: $SUCCESSFUL_BUILDS/$TOTAL_VERSIONS${NC}" | tee -a "$BUILD_LOG"
echo -e "${RED}❌ Failed builds: $FAILED_BUILDS/$TOTAL_VERSIONS${NC}" | tee -a "$BUILD_LOG"

if [ $FAILED_BUILDS -eq 0 ]; then
    echo -e "\n${GREEN}🎉 ALL BUILDS SUCCESSFUL!${NC}" | tee -a "$BUILD_LOG"
    exit 0
else
    echo -e "\n${YELLOW}⚠️  Some builds failed. Check $FAILED_LOG for details.${NC}" | tee -a "$BUILD_LOG"
    echo -e "${YELLOW}Failed versions:${NC}"
    cat "$FAILED_LOG" | grep -v "==="
    exit 1
fi