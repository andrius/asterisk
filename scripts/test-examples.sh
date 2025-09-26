#!/bin/bash

# Example usage of the Asterisk test build system
# Demonstrates different testing modes and capabilities

set -euo pipefail

echo "=== Asterisk Test Build System Examples ==="
echo

echo "1. Quick config validation for latest version:"
echo "   scripts/test-build.sh --mode config \"23.0.0-rc2\""
echo

echo "2. Test all version 2x releases (config only):"
echo "   scripts/test-build.sh --mode config \"2*\""
echo

echo "3. Full validation of a specific version (build + container test):"
echo "   scripts/test-build.sh --mode validate \"22.5.2\""
echo

echo "4. Parallel config testing for faster validation:"
echo "   scripts/test-build.sh --mode config --parallel"
echo

echo "5. Build all images without pushing (for local testing):"
echo "   scripts/test-build.sh --mode build"
echo

echo "6. Comprehensive validation with detailed report:"
echo "   scripts/test-build.sh --mode validate --verbose"
echo

echo "Available test modes:"
echo "  config   - Fast YAML config and Dockerfile generation validation (~1-2 min)"
echo "  build    - Actually build Docker images (~30-60 min for all versions)"
echo "  validate - Build + test container startup (~45-75 min for all versions)"
echo

echo "To run a quick demonstration:"
echo "  # Test latest RC version (fast)"
read -p "Press Enter to run: scripts/test-build.sh --mode config \"23.0.0-rc2\""
scripts/test-build.sh --mode config "23.0.0-rc2"

echo
echo "Test system ready! Use the examples above to validate your Asterisk builds."