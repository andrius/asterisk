#!/bin/bash

# Enhanced version discovery script with correct priority: alpha < beta < rc < stable
# Refactored from manobatai-matrix/latest-release.sh

set -euo pipefail

# Function to show usage
usage() {
  echo "Usage: $0 [options]"
  echo ""
  echo "Discover latest Asterisk versions with proper priority ordering."
  echo ""
  echo "Options:"
  echo "  --help, -h         Show this help message"
  echo "  --update           Update release lists before discovery"
  echo "  --output-yaml      Generate YAML output with OS/architecture matrix"
  echo "  --yaml-file FILE   Specify output YAML file (default: supported-asterisk-builds.yml)"
  echo "  --updates-only     Only save new versions not in existing YAML file"
  echo "  --include-git      Include git version in output"
  echo "  --git-only         Only update git SHA, skip regular version discovery"
  echo ""
  echo "Priority order: alpha < beta < rc < stable"
  echo ""
  echo "Examples:"
  echo "  $0                           # Discover latest versions (text output)"
  echo "  $0 --update                  # Update releases and discover"
  echo "  $0 --output-yaml             # Generate YAML matrix output"
  echo "  $0 --output-yaml --updates-only  # Only save new versions to YAML"
  echo ""
  echo "Output: List of latest stable versions for each major release"
  echo "        With --output-yaml: YAML matrix with OS/architecture combinations"
  exit 0
}

# Parse command line arguments
UPDATE_RELEASES=false
OUTPUT_YAML=false
YAML_FILE=""
UPDATES_ONLY=false
INCLUDE_GIT=false
GIT_ONLY=false
while [[ $# -gt 0 ]]; do
  case $1 in
  --help | -h)
    usage
    ;;
  --update)
    UPDATE_RELEASES=true
    shift
    ;;
  --output-yaml)
    OUTPUT_YAML=true
    shift
    ;;
  --yaml-file)
    YAML_FILE="$2"
    shift 2
    ;;
  --updates-only)
    UPDATES_ONLY=true
    shift
    ;;
  --include-git)
    INCLUDE_GIT=true
    shift
    ;;
  --git-only)
    GIT_ONLY=true
    INCLUDE_GIT=true
    shift
    ;;
  *)
    echo "Unknown option: $1" >&2
    usage
    ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Validate path detection
if [[ ! -d "$PROJECT_DIR" ]] || [[ ! -d "$SCRIPT_DIR" ]]; then
  echo "ERROR: Failed to detect project paths. SCRIPT_DIR=$SCRIPT_DIR, PROJECT_DIR=$PROJECT_DIR" >&2
  exit 1
fi
RELEASES_FILE="${PROJECT_DIR}/asterisk/asterisk-releases.txt"
CERTIFIED_RELEASES_FILE="${PROJECT_DIR}/asterisk/asterisk-certified-releases.txt"

# Set default YAML file if not specified
if [[ -z "$YAML_FILE" ]]; then
  YAML_FILE="${PROJECT_DIR}/asterisk/supported-asterisk-builds.yml"
fi

# Update or create releases.txt
if [[ "$UPDATE_RELEASES" == "true" ]] || [[ ! -f "$RELEASES_FILE" ]]; then
  echo "Fetching latest releases..." >&2
  "${SCRIPT_DIR}/get-asterisk-releases.sh" >"$RELEASES_FILE"
fi

# Update or create certified releases.txt
if [[ "$UPDATE_RELEASES" == "true" ]] || [[ ! -f "$CERTIFIED_RELEASES_FILE" ]]; then
  echo "Fetching latest certified releases..." >&2
  "${SCRIPT_DIR}/get-asterisk-certified-releases.sh" >"$CERTIFIED_RELEASES_FILE"
fi


# Function to check if version is 1.2 or later (excludes 0.x, 1.0.x, 1.1.x versions)
is_version_supported() {
  local version="$1"

  # Remove testing suffix and cert suffix for processing
  version=${version%-testing}
  if [[ "$version" =~ -cert[0-9]+ ]]; then
    version=$(echo "$version" | cut -d '-' -f 1)
  fi

  # Exclude versions prior to 1.2
  if [[ "$version" =~ ^0\. ]] || [[ "$version" =~ ^1\.[01]\. ]]; then
    return 1 # Not supported
  fi

  return 0 # Supported
}

# Function to extract major version considering Asterisk versioning scheme
get_major_version() {
  local version="$1"

  # Remove testing suffix for processing
  version=${version%-testing}

  # For certified releases (e.g., 13.8-cert4), extract base version (13.8)
  if [[ "$version" =~ -cert[0-9]+ ]]; then
    version=$(echo "$version" | cut -d '-' -f 1)
  fi

  # For 1.x series, major version is X.Y (e.g., 1.2, 1.4, 1.6, 1.8)
  if [[ "$version" =~ ^1\. ]]; then
    echo "$version" | cut -d '.' -f 1,2
  else
    # For 10+ series, major version is just the first number (10, 11, 12, etc.)
    echo "$version" | cut -d '.' -f 1
  fi
}

# Function to get latest git SHA from Asterisk repository
get_git_sha() {
  local git_url="https://github.com/asterisk/asterisk.git"
  echo "Fetching latest Asterisk git SHA..." >&2

  # Use git ls-remote to get the latest commit SHA from master branch
  local full_sha
  full_sha=$(git ls-remote "$git_url" refs/heads/master | cut -f1)

  if [[ -n "$full_sha" ]]; then
    # Return short SHA (first 7 characters)
    echo "${full_sha:0:7}"
  else
    echo "ERROR: Failed to fetch git SHA from $git_url" >&2
    return 1
  fi
}

# Function to get current git SHA from YAML metadata
get_current_git_sha() {
  local yaml_file="$1"
  if [[ -f "$yaml_file" ]]; then
    grep "git_sha:" "$yaml_file" | sed 's/.*git_sha: *"\?\([^"]*\)"\?.*/\1/' | head -1
  else
    echo "unknown"
  fi
}

# Function to update git SHA in YAML metadata
update_git_sha_in_yaml() {
  local yaml_file="$1"
  local new_sha="$2"
  local current_time
  current_time=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

  if [[ -f "$yaml_file" ]]; then
    # Update git_sha and last_git_update in metadata
    sed -i "s/git_sha: \"[^\"]*\"/git_sha: \"$new_sha\"/" "$yaml_file"
    sed -i "s/last_git_update: \"[^\"]*\"/last_git_update: \"$current_time\"/" "$yaml_file"
    echo "Updated git SHA to $new_sha in $yaml_file" >&2
  fi
}

# Handle git-only mode (after functions are defined)
if [[ "$GIT_ONLY" == "true" ]]; then
  if [[ "$OUTPUT_YAML" == "true" ]]; then
    # Get current and latest git SHA
    current_git_sha=$(get_current_git_sha "$YAML_FILE")
    latest_git_sha=$(get_git_sha)

    if [[ "$latest_git_sha" != "$current_git_sha" ]]; then
      echo "Git SHA changed: $current_git_sha → $latest_git_sha" >&2
      update_git_sha_in_yaml "$YAML_FILE" "$latest_git_sha"
      echo "Git SHA updated in $YAML_FILE" >&2
    else
      echo "Git SHA unchanged: $current_git_sha" >&2
    fi
  else
    echo "Git-only mode requires --output-yaml flag" >&2
    exit 1
  fi
  exit 0
fi

# Associative arrays to keep track of versions
declare -A latest_regular       # Best regular version for each major version
declare -A latest_certified     # Best certified version for each major version
declare -A has_stable_regular   # Track if major version has any stable regular release
declare -A has_stable_certified # Track if major version has any stable certified release

# Function to determine version priority (higher number = higher priority)
get_version_priority() {
  local version="$1"

  if [[ "$version" == *"alpha"* ]]; then
    echo 1
  elif [[ "$version" == *"beta"* ]]; then
    echo 2
  elif [[ "$version" == *"rc"* ]]; then
    echo 3
  elif [[ "$version" == *"-testing" ]]; then
    echo 3 # Same priority as rc - testing is like a pre-release
  elif [[ "$version" =~ -cert[0-9]+ ]]; then
    echo 4 # Certified releases are stable (but tracked separately)
  else
    # Stable version (no suffix)
    echo 4
  fi
}

# Function to compare two versions
is_version_better() {
  local current="$1"
  local candidate="$2"

  local current_priority=$(get_version_priority "$current")
  local candidate_priority=$(get_version_priority "$candidate")

  # If priorities are different, higher priority wins
  if [[ $candidate_priority -gt $current_priority ]]; then
    return 0 # candidate is better
  elif [[ $candidate_priority -lt $current_priority ]]; then
    return 1 # current is better
  fi

  # Same priority, compare versions using sort -V
  if [[ $(echo -e "$current\n$candidate" | sort -V | tail -n1) == "$candidate" ]]; then
    return 0 # candidate is newer
  else
    return 1 # current is newer or same
  fi
}

# Function to process regular releases
process_regular_releases() {
  local file="$1"
  local pass="$2" # "first" or "second"

  while read version; do
    # ignore versions with -current prefix or certified releases
    if [[ "$version" == *"-current"* ]] || [[ "$version" == "current" ]] || [[ "$version" =~ -cert[0-9]+ ]]; then continue; fi

    # Skip versions prior to 1.2
    if ! is_version_supported "$version"; then continue; fi

    # extract major version using proper Asterisk versioning logic
    major=$(get_major_version "$version")

    if [[ "$pass" == "first" ]]; then
      # First pass: identify which majors have stable versions
      priority=$(get_version_priority "$version")
      if [[ $priority -eq 4 ]]; then
        has_stable_regular["$major"]=1
      fi
    else
      # Second pass: process versions with filtering logic
      # skip testing versions if stable versions exist for this major
      if [[ "$version" == *"-testing" ]] && [[ ${has_stable_regular["$major"]+_} ]]; then
        continue
      fi

      # if first time seen this major version, treat current version as the latest
      if [[ ! ${latest_regular["$major"]+_} ]]; then
        latest_regular["$major"]=$version
      else
        # check if candidate version is better than current latest
        if is_version_better "${latest_regular[$major]}" "$version"; then
          latest_regular["$major"]=$version
        fi
      fi
    fi
  done <"$file"
}

# Function to process certified releases
process_certified_releases() {
  local file="$1"
  local pass="$2" # "first" or "second"

  while read version; do
    # ignore versions with -current prefix and non-certified releases
    if [[ "$version" == *"-current"* ]] || [[ "$version" == "current" ]] || [[ ! "$version" =~ -cert[0-9]+ ]]; then continue; fi

    # Skip versions prior to 1.2
    if ! is_version_supported "$version"; then continue; fi

    # extract major version using proper Asterisk versioning logic
    major=$(get_major_version "$version")

    if [[ "$pass" == "first" ]]; then
      # First pass: identify which majors have stable certified versions
      priority=$(get_version_priority "$version")
      if [[ $priority -eq 4 ]]; then
        has_stable_certified["$major"]=1
      fi
    else
      # Second pass: process versions with filtering logic
      # if first time seen this major version, treat current version as the latest
      if [[ ! ${latest_certified["$major"]+_} ]]; then
        latest_certified["$major"]=$version
      else
        # check if candidate version is better than current latest
        if is_version_better "${latest_certified[$major]}" "$version"; then
          latest_certified["$major"]=$version
        fi
      fi
    fi
  done <"$file"
}

# Process regular releases
process_regular_releases "$RELEASES_FILE" "first"
process_regular_releases "$RELEASES_FILE" "second"

# Process certified releases
process_certified_releases "$CERTIFIED_RELEASES_FILE" "first"
process_certified_releases "$CERTIFIED_RELEASES_FILE" "second"


# Function to load existing versions from YAML file
load_existing_versions() {
  local yaml_file="$1"
  local existing_versions=()
  local in_latest_builds=false

  if [[ -f "$yaml_file" ]]; then
    # Extract versions from existing YAML file, only from latest_builds section
    while IFS= read -r line; do
      # Check if we're entering the latest_builds section
      if [[ "$line" =~ ^latest_builds:[[:space:]]*$ ]]; then
        in_latest_builds=true
        continue
      fi

      # Check if we're leaving the latest_builds section (next top-level key)
      if [[ "$in_latest_builds" == true ]] && [[ "$line" =~ ^[a-zA-Z_][a-zA-Z0-9_]*:[[:space:]]*$ ]]; then
        in_latest_builds=false
        continue
      fi

      # Extract version only if we're in the latest_builds section
      if [[ "$in_latest_builds" == true ]] && [[ "$line" =~ ^[[:space:]]*-[[:space:]]*version:[[:space:]]*[\"\']?([^\"\']+)[\"\']? ]]; then
        existing_versions+=("${BASH_REMATCH[1]}")
      fi
    done <"$yaml_file"
  fi

  printf '%s\n' "${existing_versions[@]}"
}

# Function to check if version is new
is_new_version() {
  local version="$1"
  shift
  local existing_versions=("$@")

  # Check if version is in existing versions array (exact match)
  local existing_version
  for existing_version in "${existing_versions[@]}"; do
    if [[ "$existing_version" == "$version" ]]; then
      return 1 # Not new
    fi
  done

  return 0 # New
}

# Function to generate YAML output
generate_yaml_output() {
  local output_file="$1"
  local updates_only="$2"

  # Load existing versions if we're doing updates only
  local existing_versions=()
  if [[ "$updates_only" == "true" ]]; then
    readarray -t existing_versions < <(load_existing_versions "$output_file")
  fi

  # Collect new versions to append
  local new_versions=()

  # Collect all major versions from both regular and certified releases
  local all_majors=()
  for key in "${!latest_regular[@]}"; do
    all_majors+=("$key")
  done
  for key in "${!latest_certified[@]}"; do
    if [[ ! " ${all_majors[*]} " =~ " ${key} " ]]; then
      all_majors+=("$key")
    fi
  done

  # Discover truly new versions
  for major in $(printf '%s\n' "${all_majors[@]}" | sort -V); do
    if [[ -n "${latest_regular[$major]:-}" ]]; then
      local version="${latest_regular[$major]}"
      if [[ "$updates_only" == "false" ]] || is_new_version "$version" "${existing_versions[@]}"; then
        new_versions+=("$version")
      fi
    fi
    if [[ -n "${latest_certified[$major]:-}" ]]; then
      local version="${latest_certified[$major]}"
      if [[ "$updates_only" == "false" ]] || is_new_version "$version" "${existing_versions[@]}"; then
        new_versions+=("$version")
      fi
    fi
  done

  if [[ "$updates_only" == "true" && -f "$output_file" ]]; then
    # Preserve existing file structure and append new versions only
    if [[ ${#new_versions[@]} -gt 0 ]]; then
      # Find where to insert new versions (before metadata section)
      local temp_file=$(mktemp)
      local in_metadata=false
      local metadata_started=false

      while IFS= read -r line; do
        # Check if we've reached the metadata section
        if [[ "$line" =~ ^metadata:[[:space:]]*$ ]]; then
          in_metadata=true
          metadata_started=true

          # Insert new versions before metadata
          for version in "${new_versions[@]}"; do
            echo "  - version: \"$version\""
          done
          echo ""
        fi

        # Print the line (whether it's existing content or metadata)
        echo "$line"
      done <"$output_file" >"$temp_file"

      # If no metadata section was found, append new versions at the end
      if [[ "$metadata_started" == false ]]; then
        for version in "${new_versions[@]}"; do
          echo "  - version: \"$version\""
        done >>"$temp_file"
      fi

      # Update metadata counts
      local total_versions=$((${#existing_versions[@]} + ${#new_versions[@]}))
      sed -i "s/total_versions: [0-9]*/total_versions: $total_versions/" "$temp_file"
      sed -i "s/new_versions_count: [0-9]*/new_versions_count: ${#new_versions[@]}/" "$temp_file"
      sed -i "s/generated_at: \"[^\"]*\"/generated_at: \"$(date -u '+%Y-%m-%dT%H:%M:%SZ')\"/" "$temp_file"

      mv "$temp_file" "$output_file"
    fi

    # Report results
    echo "YAML output saved to: $output_file" >&2
    echo "Total versions: $((${#existing_versions[@]} + ${#new_versions[@]}))" >&2

    if [[ ${#new_versions[@]} -eq 0 ]]; then
      echo "No new versions found. Existing file preserved." >&2
    else
      echo "New versions added: ${#new_versions[@]}" >&2
      printf 'Added: %s\n' "${new_versions[@]}" >&2
    fi
  else
    # Full mode - generate complete new file
    local supported_os=(
      "debian:stretch"
      "debian:jessie"
      "debian:buster"
      "debian:bullseye"
      "debian:bookworm"
      "debian:trixie"
    )
    local supported_architectures=("amd64" "arm64")

    {
      echo "# Latest Asterisk Build Matrix"
      echo "# Generated on $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
      echo ""
      echo "latest_builds:"

      for version in "${new_versions[@]}"; do
        echo "  - version: \"$version\""
        echo "    os_matrix:"

        for os_entry in "${supported_os[@]}"; do
          IFS=':' read -r os dist <<<"$os_entry"
          echo "      - os: \"$os\""
          echo "        distribution: \"$dist\""
          echo "        architectures:"
          for arch in "${supported_architectures[@]}"; do
            echo "          - \"$arch\""
          done
        done
        echo ""
      done

      echo "metadata:"
      echo "  generated_at: \"$(date -u '+%Y-%m-%dT%H:%M:%SZ')\""
      echo "  supported_os:"
      echo "    debian: [\"bookworm\", \"trixie\"]"
      echo "  supported_architectures: [\"amd64\", \"arm64\"]"
      echo "  total_versions: ${#new_versions[@]}"
      echo "  mode: \"full\""
    } >"$output_file"

    echo "YAML output saved to: $output_file" >&2
    echo "Versions included: ${#new_versions[@]}" >&2
  fi
}

# Collect all major versions from both regular and certified releases
all_majors=()
for key in "${!latest_regular[@]}"; do
  all_majors+=("$key")
done
for key in "${!latest_certified[@]}"; do
  if [[ ! " ${all_majors[*]} " =~ " ${key} " ]]; then
    all_majors+=("$key")
  fi
done

# Handle git SHA updates if requested
if [[ "$INCLUDE_GIT" == "true" && "$OUTPUT_YAML" == "true" ]]; then
  current_git_sha=$(get_current_git_sha "$YAML_FILE")
  latest_git_sha=$(get_git_sha)

  if [[ "$latest_git_sha" != "$current_git_sha" ]]; then
    echo "Git SHA changed: $current_git_sha → $latest_git_sha" >&2
    update_git_sha_in_yaml "$YAML_FILE" "$latest_git_sha"
  else
    echo "Git SHA unchanged: $current_git_sha" >&2
  fi
fi

# Generate output based on requested format
if [[ "$OUTPUT_YAML" == "true" ]]; then
  generate_yaml_output "$YAML_FILE" "$UPDATES_ONLY"
else
  # Sort major versions and print both regular and certified releases (original behavior)
  for major in $(printf '%s\n' "${all_majors[@]}" | sort -V); do
    if [[ -n "${latest_regular[$major]:-}" ]]; then
      echo "${latest_regular[$major]}"
    fi
    if [[ -n "${latest_certified[$major]:-}" ]]; then
      echo "${latest_certified[$major]}"
    fi
  done
fi

