#!/bin/bash

# Check if README.md is in sync with supported-asterisk-builds.yml
# Runs update-readme-versions.py and checks for differences
# Exit 0 = in sync, Exit 1 = out of date

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
README="${PROJECT_DIR}/README.md"
UPDATE_SCRIPT="${SCRIPT_DIR}/update-readme-versions.py"

if [[ ! -f "$README" ]]; then
    echo "ERROR: README.md not found at $README" >&2
    exit 2
fi

if [[ ! -f "$UPDATE_SCRIPT" ]]; then
    echo "ERROR: update-readme-versions.py not found at $UPDATE_SCRIPT" >&2
    exit 2
fi

# Save original README
BACKUP=$(mktemp)
trap 'cp "$BACKUP" "$README"; rm -f "$BACKUP"' EXIT
cp "$README" "$BACKUP"

# Run the update script (modifies README in-place)
python3 "$UPDATE_SCRIPT" > /dev/null 2>&1

# Compare
if diff -u "$BACKUP" "$README" > /dev/null 2>&1; then
    echo "README.md is in sync with supported-asterisk-builds.yml"
    exit 0
else
    echo "README.md is out of sync with supported-asterisk-builds.yml"
    echo ""
    diff -u "$BACKUP" "$README" || true
    echo ""
    echo "Run: python3 scripts/update-readme-versions.py"
    exit 1
fi
