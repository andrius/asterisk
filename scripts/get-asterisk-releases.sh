#!/bin/bash

set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to show usage
usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Fetch all Asterisk release versions from downloads.asterisk.org"
    echo ""
    echo "Options:"
    echo "  --help, -h    Show this help message"
    echo ""
    echo "Output: List of all available Asterisk versions (one per line)"
    echo ""
    echo "Example:"
    echo "  $0 > asterisk-releases.txt"
    exit 0
}

# Function to validate release data
validate_releases() {
    local data="$1"
    local count=$(echo -n "$data" | grep -c '^')

    # Must have reasonable number of releases (all versions from 0.1.0 to latest)
    if [[ $count -lt 50 ]]; then
        echo "ERROR: Too few releases ($count), expected 50+" >&2
        return 1
    fi

    # Format validation - ensure all lines are valid version strings
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        if ! echo "$line" | grep -qE '^[0-9]+(\.[0-9]+)*(-[a-zA-Z]+[0-9]*)?(-testing)?$'; then
            echo "ERROR: Invalid version format: '$line'" >&2
            return 1
        fi
    done <<< "$data"

    # Ensure we have data (not empty/HTML error pages)
    if ! echo "$data" | grep -q '^[0-9]'; then
        echo "ERROR: No valid version data found" >&2
        return 1
    fi

    return 0
}

# Parse command line arguments
if [[ $# -gt 0 ]]; then
    case $1 in
        --help|-h)
            usage
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage
            ;;
    esac
fi

CURL_OPTIONS="--silent \
  --location \
  --connect-timeout 5 \
  --max-time 10 \
  --retry 5 \
  --retry-delay 0 \
  --retry-max-time 40 \
"

# URLs with all the Asterisk PBX releases
URLS=( \
  http://downloads.asterisk.org/pub/telephony/asterisk/releases/ \
  http://downloads.asterisk.org/pub/telephony/asterisk/ \
  http://downloads.asterisk.org/pub/telephony/asterisk/old-releases/ \
)

# Retrieve and save the list of remote files for every URL to a temporary file
URL_ID=0
for URL in "${URLS[@]}"; do
  echo -e "Source:\n$URL\n================================================================================\n\n" > "/tmp/asterisk-$URL_ID.txt"
  curl $CURL_OPTIONS "$URL" >> "/tmp/asterisk-$URL_ID.txt"
  URL_ID=$((URL_ID+1))
done
unset URL_ID

# List all the remote files, grep for asterisk-*.tar.gz, and exclude unneeded patterns
ASTERISK_RELEASES=""
for URL in "${URLS[@]}"; do
  _ASTERISK_RELEASES="$( \
    curl $CURL_OPTIONS "$URL" \
    | grep '>asterisk-\([^<]*\)\.tar\.gz<' \
    | grep -v '\-patch\|\-addons\|\-sounds\|\-digiumphones\|\.patch\|\-current' \
  )"
  ASTERISK_RELEASES+="${_ASTERISK_RELEASES}\n"
  unset _ASTERISK_RELEASES
done

# Remove asterisk- prefix and sort by semantic versioning
ASTERISK_RELEASES="$( \
  echo -e "${ASTERISK_RELEASES}" \
  | sort --unique \
  | sed -n 's/.*>asterisk-\([^<]*\)\.tar\.gz<\/a>.*/\1/p' \
  | sort --field-separator='.' --key=1,1n --key=2,2n --key=3,3n --key=4,4n \
  | grep -v '^$' \
)"

# Validate the data before writing files
if ! validate_releases "$ASTERISK_RELEASES"; then
    echo "Validation failed, not updating files" >&2
    exit 1
fi

# Write TXT file
echo -e "$ASTERISK_RELEASES" > "${SCRIPT_DIR}/../asterisk/asterisk-releases.txt"

# Generate and write YAML file
MAJOR_RELEASES=$(echo "$ASTERISK_RELEASES" | grep -oE '^[0-9]+(\.[0-9]+)*' | cut -d. -f1 | sort -n | uniq)
{
  for MAJOR in ${MAJOR_RELEASES}; do
    echo "${MAJOR}:"
    echo "$ASTERISK_RELEASES" | grep "^${MAJOR}\." | sed 's/^/  - /'
  done
} > "${SCRIPT_DIR}/../asterisk/asterisk-releases.yml"

echo "Successfully updated asterisk-releases.txt and asterisk-releases.yml" >&2
