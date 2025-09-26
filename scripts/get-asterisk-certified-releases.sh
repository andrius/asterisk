#!/bin/bash

set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to show usage
usage() {
    echo "Usage: $0 [options]"
    echo ""
    echo "Fetch all Asterisk certified release versions from downloads.asterisk.org"
    echo ""
    echo "Options:"
    echo "  --help, -h    Show this help message"
    echo ""
    echo "Output: List of all available Asterisk certified versions (one per line)"
    echo ""
    echo "Example:"
    echo "  $0 > asterisk-certified-releases.txt"
    exit 0
}

# Function to validate certified release data
validate_certified_releases() {
    local data="$1"
    local count=$(echo -n "$data" | grep -c '^')

    # Must have reasonable number of certified releases
    if [[ $count -lt 10 ]]; then
        echo "ERROR: Too few certified releases ($count), expected 10+" >&2
        return 1
    fi

    # Format validation for each line
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        if [[ "$line" == "current" ]]; then
            continue  # "current" is valid
        elif ! echo "$line" | grep -qE '^[0-9]+\.[0-9]+-cert[0-9]+(-rc[0-9]+)?$'; then
            echo "ERROR: Invalid certified format: '$line'" >&2
            return 1
        fi
    done <<< "$data"

    # Ensure we have data (not empty/HTML error pages)
    if ! echo "$data" | grep -qE '^(current|[0-9])'; then
        echo "ERROR: No valid certified release data found" >&2
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

# URLs with all the Asterisk PBX releases (certified)
URLS=( \
  http://downloads.asterisk.org/pub/telephony/certified-asterisk/ \
  http://downloads.asterisk.org/pub/telephony/certified-asterisk/releases/ \
)

# Retrieve and save the list of remote files for every URL to a temporary file
URL_ID=0
for URL in "${URLS[@]}"; do
  echo -e "Source:\n$URL\n================================================================================\n\n" > "/tmp/asterisk-certified-$URL_ID.txt"
  curl $CURL_OPTIONS "$URL" >> "/tmp/asterisk-certified-$URL_ID.txt"
  URL_ID=$((URL_ID+1))
done
unset URL_ID

# List all the remote files, grep for asterisk-certified-*.tar.gz, and exclude unneeded patterns
ASTERISK_RELEASES=""
for URL in "${URLS[@]}"; do
  _ASTERISK_RELEASES="$( \
    curl $CURL_OPTIONS "$URL" \
    | grep '>asterisk-certified-\([^<]*\)\.tar\.gz<' \
    | grep -v '\-patch\|\-addons\|\-sounds' \
  )"
  ASTERISK_RELEASES+="${_ASTERISK_RELEASES}\n"
  unset _ASTERISK_RELEASES
done

ASTERISK_RELEASES="$( \
	echo -e "${ASTERISK_RELEASES}" \
	| sort --unique \
	| sed -n 's/.*>asterisk-certified-\([^<]*\)\.tar\.gz<\/a>.*/\1/p' \
	| sort --field-separator='.' --key=1,1n  --key=2,2n --key=3,3n --key=4,4n \
  | grep -v '^$' \
)"

# Validate the data before writing files
if ! validate_certified_releases "$ASTERISK_RELEASES"; then
    echo "Validation failed, not updating files" >&2
    exit 1
fi

# Write TXT file
echo -e "$ASTERISK_RELEASES" > "${SCRIPT_DIR}/../asterisk/asterisk-certified-releases.txt"

# Generate and write YAML file
MAJOR_RELEASES=$(echo "$ASTERISK_RELEASES" | grep -v '^current$' | grep -oE '^[0-9]+\.[0-9]+' | sort -V | uniq)
{
  for MAJOR in ${MAJOR_RELEASES}; do
    echo "${MAJOR}:"
    echo "$ASTERISK_RELEASES" | grep "^${MAJOR}" | sed 's/^/  - /'
  done
  # Add current if it exists
  if echo "$ASTERISK_RELEASES" | grep -q '^current$'; then
    echo "current:"
    echo "$ASTERISK_RELEASES" | grep '^current$' | sed 's/^/  - /'
  fi
} > "${SCRIPT_DIR}/../asterisk/asterisk-certified-releases.yml"

echo "Successfully updated asterisk-certified-releases.txt and asterisk-certified-releases.yml" >&2
