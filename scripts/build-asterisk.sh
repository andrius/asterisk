#!/bin/bash

# Build Asterisk Docker images with OS/architecture matrix support
# Integrates with the YAML-based configuration system

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LATEST_BUILDS_FILE="${PROJECT_DIR}/asterisk/supported-asterisk-builds.yml"

# Validate path detection
if [[ ! -d "$PROJECT_DIR" ]] || [[ ! -d "$SCRIPT_DIR" ]]; then
    echo "ERROR: Failed to detect project paths. SCRIPT_DIR=$SCRIPT_DIR, PROJECT_DIR=$PROJECT_DIR" >&2
    exit 1
fi

# Validate project structure
required_dirs=("$PROJECT_DIR/templates" "$PROJECT_DIR/configs" "$PROJECT_DIR/lib")
required_files=("$LATEST_BUILDS_FILE" "$PROJECT_DIR/CLAUDE.md")

for dir in "${required_dirs[@]}"; do
    if [[ ! -d "$dir" ]]; then
        echo "ERROR: Required directory not found: $dir" >&2
        echo "Make sure you're running this script from a valid Asterisk build project directory." >&2
        exit 1
    fi
done

for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        echo "ERROR: Required file not found: $file" >&2
        echo "Make sure you're running this script from a valid Asterisk build project directory." >&2
        exit 1
    fi
done

# Default values
DEFAULT_REGISTRY="ghcr.io/andrius/asterisk"
DEFAULT_PLATFORMS="linux/amd64,linux/arm64"
DRY_RUN=false
PUSH_IMAGES=false
FORCE_CONFIG=false
PARALLEL_BUILDS=false
VERBOSE=false
SKIP_FORMAT_DOCKERFILE=false
GIT_BUILD=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to show usage
usage() {
    cat << EOF
Usage: $0 <version> [os] [arch] [options]

Build Asterisk Docker images using YAML-based configuration system.

Arguments:
  version       Asterisk version (e.g., 22.5.2, 23.0.0-rc1) - only 11+ supported
  os           Optional: OS filter (debian only)
  arch         Optional: Architecture filter (amd64, arm64)

Options:
  --push                Push images to registry
  --registry REGISTRY   Specify registry/repository (default: none)
  --platforms PLATFORMS Override platforms (default: linux/amd64,linux/arm64)
  --dry-run            Show what would be built without building
  --force-config       Regenerate configs even if they exist
  --parallel           Build multiple configs simultaneously
  --skip-format-dockerfile  Skip dockerfmt formatting (default: format enabled)
  --git                Build from git repository instead of release
  --verbose            Enable verbose output
  --help, -h           Show this help message

Examples:
  $0 22.5.2                           # Build all OS/arch from latest-asterisk-builds.yml
  $0 22.5.2 debian                    # Build all Debian variants and architectures
  $0 22.5.2 debian amd64              # Build only Debian amd64
  $0 22.5.2 debian arm64              # Build only Debian arm64
  $0 22.5.2 --push --registry myuser/asterisk
  $0 22.5.2 --push --registry ghcr.io/myuser/asterisk
  $0 23.0.0-rc1 --dry-run             # Preview what would be built
  $0 --git trixie                     # Build from git with Debian Trixie
  $0 --git trixie --push              # Build and push git version

Matrix Resolution:
  - Versions in latest-asterisk-builds.yml: Use exact OS matrix (preserves customizations)
  - Versions not in YAML: Use metadata defaults from latest-asterisk-builds.yml
  - Custom configs in configs/ directory take precedence

EOF
    exit 0
}

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

# Function to validate Asterisk version format
validate_version() {
    local version="$1"

    # Allow git versions (git-XXXXXX), "git" keyword, and regular versions
    if [[ "$version" == "git" ]]; then
        # Special git keyword from YAML matrix
        return 0
    elif [[ "$version" =~ ^git-[a-fA-F0-9]+$ ]]; then
        # Git version format: git-<sha>
        return 0
    elif [[ "$version" =~ ^[0-9]+\.[0-9]+(\.[0-9]+)?(\.[0-9]+)?(-[a-zA-Z0-9]+)?$ ]]; then
        # Regular version format: major.minor[.patch][.subpatch][-suffix]
        return 0
    else
        log ERROR "Invalid version format: $version"
        log ERROR "Expected format: major.minor[.patch][.subpatch][-suffix] (e.g., 22.5.2, 23.0.0-rc1), git-<sha> (e.g., git-ff80666), or 'git'"
        return 1
    fi
}

# Function to check prerequisites
check_prerequisites() {
    log INFO "Checking prerequisites..."

    # Check Docker
    if ! command -v docker >/dev/null 2>&1; then
        log ERROR "Docker is not installed or not in PATH"
        return 1
    fi

    # Check Docker buildx
    if ! docker buildx version >/dev/null 2>&1; then
        log ERROR "Docker buildx is not available"
        return 1
    fi

    # Check if Docker daemon is running
    if ! docker info >/dev/null 2>&1; then
        log ERROR "Docker daemon is not running"
        return 1
    fi

    # Check Python for YAML parsing and generation
    if ! command -v python3 >/dev/null 2>&1; then
        log ERROR "Python 3 is not installed or not in PATH"
        return 1
    fi

    # Note: Using Python for YAML parsing (no need for yq)

    log SUCCESS "Prerequisites check passed"
    return 0
}

# Parse command line arguments
POSITIONAL_ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            usage
            ;;
        --push)
            PUSH_IMAGES=true
            shift
            ;;
        --registry)
            DEFAULT_REGISTRY="$2"
            shift 2
            ;;
        --platforms)
            DEFAULT_PLATFORMS="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force-config)
            FORCE_CONFIG=true
            shift
            ;;
        --parallel)
            PARALLEL_BUILDS=true
            shift
            ;;
        --skip-format-dockerfile)
            SKIP_FORMAT_DOCKERFILE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --git)
            GIT_BUILD=true
            shift
            ;;
        *)
            POSITIONAL_ARGS+=("$1")
            shift
            ;;
    esac
done

# Restore positional parameters
set -- "${POSITIONAL_ARGS[@]}"

# Handle git builds differently
if [[ "$GIT_BUILD" == true ]]; then
    # For git builds, first arg is distribution, second is arch
    DISTRIBUTION="${1:-trixie}"
    ARCH_FILTER="${2:-amd64}"

    # Get git SHA from repository
    if ! command -v git >/dev/null 2>&1; then
        log ERROR "Git is required for --git builds but not found in PATH"
        exit 1
    fi

    log INFO "Fetching latest git SHA from Asterisk repository..."
    GIT_SHA=$(git ls-remote https://github.com/asterisk/asterisk.git HEAD | cut -f1 | cut -c1-7)
    if [[ -z "$GIT_SHA" ]]; then
        log ERROR "Failed to fetch git SHA from Asterisk repository"
        exit 1
    fi

    VERSION="git-$GIT_SHA"
    OS_FILTER="debian"

    log INFO "Building git version: $VERSION (SHA: $GIT_SHA)"
    log INFO "Distribution: $DISTRIBUTION"
    log INFO "Architecture: $ARCH_FILTER"
else
    # Validate arguments for release builds
    if [[ $# -lt 1 ]]; then
        log ERROR "Version argument is required"
        usage
    fi

    VERSION="$1"
    OS_FILTER="${2:-}"
    ARCH_FILTER="${3:-}"

    # Validate version
    if ! validate_version "$VERSION"; then
        exit 1
    fi
fi

# Check prerequisites
if ! check_prerequisites; then
    exit 1
fi

log INFO "Starting Asterisk build for version: $VERSION"
[[ -n "$OS_FILTER" ]] && log INFO "OS filter: $OS_FILTER"
[[ -n "$ARCH_FILTER" ]] && log INFO "Architecture filter: $ARCH_FILTER"
[[ "$DRY_RUN" == true ]] && log INFO "DRY RUN MODE - No actual builds will be performed"

# Function to extract OS/architecture matrix for a version using Python
get_build_matrix() {
    local version="$1"
    local os_filter="$2"
    local arch_filter="$3"

    log INFO "Resolving build matrix for version $version..."

    if [[ ! -f "$LATEST_BUILDS_FILE" ]]; then
        log ERROR "YAML file not found: $LATEST_BUILDS_FILE"
        return 1
    fi

    # Use Python to parse YAML and generate build matrix
    python3 << EOF
import yaml
import sys
import os

def log_info(msg):
    print(f"\033[0;34m[INFO]\033[0m  {msg}", file=sys.stderr)

def log_debug(msg):
    if os.getenv('VERBOSE') == 'true':
        print(f"\033[0;34m[DEBUG]\033[0m {msg}", file=sys.stderr)

try:
    with open("$LATEST_BUILDS_FILE", 'r') as f:
        data = yaml.safe_load(f)

    # Find the version in latest_builds
    version_found = False
    version_data = None

    if 'latest_builds' in data:
        for build in data['latest_builds']:
            if build.get('version') == "$version":
                version_found = True
                version_data = build
                break

    # Get metadata defaults
    metadata = data.get('metadata', {})
    supported_os = metadata.get('supported_os', {'debian': ['bookworm', 'trixie']})
    supported_architectures = metadata.get('supported_architectures', ['amd64', 'arm64'])

    builds = []

    if not version_found:
        # Version not found in YAML - ERROR
        print(f"ERROR: Version $version not found in latest-asterisk-builds.yml", file=sys.stderr)
        print("", file=sys.stderr)
        print("Only validated versions can be built. Available versions:", file=sys.stderr)

        # List available versions
        if 'latest_builds' in data:
            for build in data['latest_builds']:
                version_name = build.get('version', 'unknown')
                has_matrix = 'os_matrix' in build
                status = "buildable" if has_matrix else "skipped (no os_matrix)"
                print(f"  - {version_name} ({status})", file=sys.stderr)

        print("", file=sys.stderr)
        print("To add new versions, run: ./scripts/discover-latest-versions.sh --output-yaml --updates-only", file=sys.stderr)
        sys.exit(1)

    if not version_data:
        print(f"ERROR: Version $version data is corrupted in YAML", file=sys.stderr)
        sys.exit(1)

    if 'os_matrix' not in version_data:
        # Version exists but has no os_matrix - this means SKIP building
        print(f"INFO: Version $version exists but has no os_matrix - skipping build", file=sys.stderr)
        print("This version is intentionally disabled/skipped in the configuration.", file=sys.stderr)
        sys.exit(0)  # Exit successfully but with no builds

    # Version has os_matrix - proceed with builds
    log_debug(f"Using custom OS matrix for version $version")
    os_matrix = version_data['os_matrix']

    # Extract additional_tags from version data
    additional_tags = version_data.get('additional_tags', '')
    log_debug(f"Additional tags for version $version: {additional_tags}")

    # Handle different os_matrix formats (list or single entry)
    if isinstance(os_matrix, list):
        matrix_list = os_matrix
    else:
        matrix_list = [os_matrix]

    for matrix_entry in matrix_list:
        os_name = matrix_entry.get('os', 'debian')  # default to debian if missing
        distribution = matrix_entry.get('distribution', 'trixie')
        architectures = matrix_entry.get('architectures', ['amd64', 'arm64'])
        template = matrix_entry.get('template', '')  # empty string if no template specified

        log_debug(f"Processing matrix entry: {os_name}/{distribution} with {architectures}")

        # Apply filters
        if "$os_filter" and os_name != "$os_filter":
            log_debug(f"Skipping {os_name} due to OS filter")
            continue

        # Filter architectures based on arch_filter
        filtered_architectures = []
        for arch in architectures:
            if "$arch_filter" and arch != "$arch_filter":
                log_debug(f"Skipping {arch} due to architecture filter")
                continue
            filtered_architectures.append(arch)

        # Only add build entry if we have architectures after filtering
        if filtered_architectures:
            builds.append({
                'os': os_name,
                'distribution': distribution,
                'architectures': filtered_architectures,  # Changed: now array of architectures
                'template': template,  # Include template field
                'additional_tags': additional_tags,  # Include additional_tags
                'source': 'custom_matrix'
            })

    if not builds:
        print("ERROR: No build targets found after applying filters", file=sys.stderr)
        sys.exit(1)

    # Output build matrix to stdout only
    for build in builds:
        # Convert architectures array to comma-separated string
        architectures_str = ','.join(build['architectures'])
        template_str = build['template']  # May be empty string
        additional_tags_str = build['additional_tags']  # May be empty string
        print(f"{build['os']}:{build['distribution']}:{architectures_str}:{template_str}:{build['source']}:{additional_tags_str}")

    # Count total architecture combinations for logging
    total_arch_combinations = sum(len(build['architectures']) for build in builds)
    print(f"\033[0;34m[INFO]\033[0m  Found {len(builds)} build target(s) with {total_arch_combinations} architecture(s) total", file=sys.stderr)

except Exception as e:
    print(f"ERROR: Failed to parse YAML: {e}", file=sys.stderr)
    sys.exit(1)
EOF
}

# Function to determine template type - only modern Debian versions supported
get_template_type() {
    local version="$1"

    # Extract major version number
    local major_version
    major_version=$(echo "$version" | cut -d'.' -f1)

    # Only modern Asterisk versions (11+) are supported
    if [[ "$major_version" -lt 11 ]]; then
        echo "ERROR: Legacy versions ($version) not supported. Use only Asterisk 11+ versions." >&2
        return 1
    fi

    # Only Debian builds supported
    echo "debian"
}

# Main build processing
log INFO "Parsing build matrix from $LATEST_BUILDS_FILE..."

# Export verbose flag for Python scripts
export VERBOSE="$VERBOSE"

# Handle git builds with special matrix
if [[ "$GIT_BUILD" == true ]]; then
    log INFO "Creating git build matrix..."
    # For git builds, create a simple build target
    BUILD_TARGETS=("debian:$DISTRIBUTION:$ARCH_FILTER:git-dev:git:")
    log INFO "Git build target: debian:$DISTRIBUTION:$ARCH_FILTER:git-dev:git:"
else
    # Get build matrix and capture it properly
    {
        exec 3< <(get_build_matrix "$VERSION" "$OS_FILTER" "$ARCH_FILTER" 2>&1)
        BUILD_TARGETS=()
        while IFS= read -r line <&3; do
            # Only capture lines that look like build targets (contain colons)
            # Format: os:distribution:architectures:template:source:additional_tags (6 fields, 5 colons)
            if [[ "$line" =~ ^[^:]+:[^:]+:[^:]+:[^:]*:[^:]+:[^:]*$ ]]; then
                BUILD_TARGETS+=("$line")
            fi
        done
        exec 3<&-
    } 2>&1
fi

if [[ ${#BUILD_TARGETS[@]} -eq 0 ]]; then
    log ERROR "No build targets found"
    exit 1
fi

# Display build targets
log INFO "Build targets:"
for target in "${BUILD_TARGETS[@]}"; do
    IFS=':' read -r os distribution architectures template source additional_tags <<< "$target"
    template_info=""
    if [[ -n "$template" ]]; then
        template_info=" [template: $template]"
    fi
    tags_info=""
    if [[ -n "$additional_tags" ]]; then
        tags_info=" [additional_tags: $additional_tags]"
    fi
    log INFO "  → $os/$distribution ($architectures)$template_info$tags_info [from: $source]"
done

# Function to ensure generated config exists
ensure_config() {
    local version="$1"
    local os="$2"
    local distribution="$3"
    local template="$4"  # Optional template name

    # Handle git builds with special config generation
    if [[ "$GIT_BUILD" == true ]] || [[ "$template" == "git-dev" ]]; then
        # For git builds, use consistent git-master-{distribution} config name
        local generated_config="${PROJECT_DIR}/configs/generated/asterisk-git-master-${distribution}.yml"
        local GIT_SHA=""

        log DEBUG "Creating git build config: $generated_config" >&2

        # Get git SHA - either from previous fetch or YAML metadata
        if [[ -z "$GIT_SHA" ]]; then
            # If not already set, get from YAML metadata or fetch from repo
            if [[ "$version" == "git" ]]; then
                log INFO "Fetching git SHA from YAML metadata for unified git build..." >&2
                GIT_SHA=$(grep "git_sha:" "$LATEST_BUILDS_FILE" | sed 's/.*git_sha: *"\?\([^"]*\)"\?.*/\1/' | head -1)
                if [[ -z "$GIT_SHA" || "$GIT_SHA" == "unknown" ]]; then
                    log INFO "Git SHA not available in YAML, fetching from repository..." >&2
                    GIT_SHA=$(git ls-remote https://github.com/asterisk/asterisk.git HEAD | cut -f1 | cut -c1-7)
                    if [[ -z "$GIT_SHA" ]]; then
                        log ERROR "Failed to fetch git SHA from Asterisk repository"
                        return 1
                    fi
                fi
            fi
        fi

        # Always regenerate git configs to get latest git SHA
        log INFO "Generating git config for $version ($os/$distribution) with SHA: $GIT_SHA" >&2

        # Ensure configs/generated directory exists
        mkdir -p "${PROJECT_DIR}/configs/generated"

        # Generate git config using DRYTemplateGenerator for proper version overrides
        if ! python3 -c "
import sys
import os
sys.path.insert(0, os.path.join('${PROJECT_DIR}', 'lib'))

from template_generator import DRYTemplateGenerator
import yaml

# Initialize generator
generator = DRYTemplateGenerator('${PROJECT_DIR}/templates')

# Generate config with version overrides
config = generator.generate_config('${version}', '${distribution}', 'git-dev')

# Add git-specific metadata
config['asterisk']['source']['git_sha'] = '${GIT_SHA}'
config['asterisk']['source']['git_ref'] = 'master'

# Save config
generator.save_config(config, '${generated_config}')

print('Git config generated successfully')
" >&2; then
            log ERROR "Failed to generate git config from template" >&2
            return 1
        fi

        if [[ ! -f "$generated_config" ]]; then
            log ERROR "Git config generation failed: $generated_config" >&2
            return 1
        fi

        log SUCCESS "Generated git config: $generated_config" >&2

        # Also create a symlink with workflow-expected naming for compatibility
        local workflow_config="${PROJECT_DIR}/configs/generated/asterisk-${version}-${distribution}.yml"
        if [[ "$generated_config" != "$workflow_config" ]]; then
            ln -sf "$(basename "$generated_config")" "$workflow_config" 2>/dev/null || {
                log DEBUG "Could not create symlink, copying config file instead" >&2
                cp "$generated_config" "$workflow_config"
            }
            log DEBUG "Created workflow-compatible config: $workflow_config" >&2
        fi

        echo "$generated_config"
        return 0
    fi

    # Only use modern generated config format (using actual naming pattern)
    # For git builds, use consistent git-master-{distribution} config name
    if [[ "$version" =~ ^git- ]]; then
        local generated_config="${PROJECT_DIR}/configs/generated/asterisk-git-master-${distribution}.yml"
    else
        local generated_config="${PROJECT_DIR}/configs/generated/asterisk-${version}-${distribution}.yml"
    fi

    log DEBUG "Checking for generated config: $generated_config" >&2

    # Use existing generated config if available and not forcing regeneration
    if [[ -f "$generated_config" && "$FORCE_CONFIG" == false ]]; then
        log DEBUG "Using existing generated config: $generated_config" >&2
        echo "$generated_config"
        return 0
    fi

    # Generate new config using the proper config generator
    log INFO "Generating config for $version ($os/$distribution)" >&2

    # Ensure configs/generated directory exists
    mkdir -p "${PROJECT_DIR}/configs/generated"

    # Generate config using the reusable config generation script
    log INFO "Generating config for $version ($os/$distribution)" >&2

    # Prepare arguments for config generation script
    local gen_args=("--versions" "$version")
    [[ "$FORCE_CONFIG" == true ]] && gen_args+=("--force")
    [[ "$VERBOSE" == true ]] && gen_args+=("--verbose")

    # Export environment variables for the script
    export PROJECT_DIR SCRIPT_DIR FORCE VERBOSE

    if ! "${SCRIPT_DIR}/generate-configs-from-yaml.sh" "${gen_args[@]}" >&2; then
        log ERROR "Failed to generate config from template" >&2
        return 1
    fi

    if [[ ! -f "$generated_config" ]]; then
        log ERROR "Config generation succeeded but file not found: $generated_config" >&2
        return 1
    fi

    log SUCCESS "Generated config: $generated_config" >&2
    echo "$generated_config"
    return 0
}

# Function to generate healthcheck.sh from template
generate_healthcheck() {
    local config_file="$1"
    local version="$2"
    local output_path="$3"

    log DEBUG "Generating healthcheck.sh from template using config: $config_file"

    # Try to use yq if available, otherwise fall back to Python
    if command -v yq >/dev/null 2>&1; then
        log DEBUG "Using yq for YAML processing"

        # Extract version from config using yq (get the root-level version field)
        local config_version
        config_version=$(yq eval '.version' "$config_file" 2>/dev/null)

        # Check if yq extraction was successful and returned a valid version
        if [[ $? -ne 0 ]] || [[ -z "$config_version" ]] || [[ "$config_version" == "null" ]]; then
            log DEBUG "yq extraction failed or returned invalid version ('$config_version'), falling back to Python"
            # Fall back to Python approach
            if ! python3 -c "
import sys, yaml, os
from pathlib import Path
sys.path.append('${PROJECT_DIR}/lib')
from jinja2 import Environment, FileSystemLoader

# Load config
with open('$config_file', 'r') as f:
    config = yaml.safe_load(f)

# Set up Jinja2 environment
templates_dir = Path('${PROJECT_DIR}/templates')
env = Environment(loader=FileSystemLoader(str(templates_dir)), trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)

# Render healthcheck template
template = env.get_template('partials/healthcheck.sh.j2')
content = template.render(config=config, version='$version')

# Write to file
with open('$output_path', 'w') as f:
    f.write(content)
            "; then
                log ERROR "Failed to generate healthcheck.sh using Python fallback"
                return 1
            fi
        else
            log DEBUG "Extracted version using yq: $config_version"
            # Use sed for simple template substitution
            if ! sed "s/{{ config\.version }}/${config_version}/g" "${PROJECT_DIR}/templates/partials/healthcheck.sh.j2" > "$output_path"; then
                log ERROR "Failed to generate healthcheck.sh using sed"
                return 1
            fi
        fi

    else
        log DEBUG "yq not available, using Python fallback"

        # Python fallback with compatibility layer
        if ! python3 -c "
import sys, yaml, os
from pathlib import Path
sys.path.append('${PROJECT_DIR}/lib')
from jinja2 import Environment, FileSystemLoader

# Load config
with open('$config_file', 'r') as f:
    config = yaml.safe_load(f)

# Apply compatibility layer for templates (same as dockerfile_generator.py)
version = '$version'
build_config = config.get('build', {})
asterisk_config = config.get('asterisk', {})

# Add backward compatibility for templates expecting build.stages structure
packages_config = config.get('packages', {})
if packages_config and not build_config.get('stages'):
    build_packages = packages_config.get('build', [])
    runtime_packages = packages_config.get('runtime', [])
    build_config['stages'] = {
        'builder': {'packages': build_packages},
        'runtime': {'packages': runtime_packages, 'slim': True}
    }

# Add backward compatibility for templates expecting asterisk.addons structure
if not asterisk_config.get('addons'):
    asterisk_config['addons'] = {'version': None}

# Add backward compatibility for templates expecting asterisk.source structure
if not asterisk_config.get('source'):
    # Detect certified versions and use appropriate URL
    if '-cert' in version:
        url_template = 'https://downloads.asterisk.org/pub/telephony/certified-asterisk/releases/asterisk-{version}.tar.gz'
    else:
        url_template = 'https://downloads.asterisk.org/pub/telephony/asterisk/releases/asterisk-{version}.tar.gz'

    asterisk_config['source'] = {
        'url_template': url_template
    }

# Add backward compatibility for templates expecting features structure
if not config.get('features'):
    config['features'] = {
        'recordings': True,
        'hep': True,
        'pjsip': True,
        'ari': True
    }

# Add backward compatibility for templates expecting docker structures
docker_config = config.get('docker', {})
if not docker_config.get('healthcheck'):
    docker_config['healthcheck'] = {
        'enabled': True,
        'command': '/usr/local/bin/healthcheck.sh',
        'interval': '30s',
        'timeout': '10s',
        'start_period': '30s',
        'retries': 3
    }

if not docker_config.get('networking'):
    docker_config['networking'] = {
        'ports': ['5060/udp', '5060/tcp', '5061/tcp', '10000-10099/udp']
    }

config['docker'] = docker_config
config['build'] = build_config
config['asterisk'] = asterisk_config

# Determine build characteristics from version
if version.startswith('git-'):
    major_version = 99  # Git versions are always modern
else:
    major_version = int(version.split('.')[0])

# Set up Jinja2 environment
templates_dir = Path('${PROJECT_DIR}/templates')
env = Environment(loader=FileSystemLoader(str(templates_dir)), trim_blocks=True, lstrip_blocks=True, keep_trailing_newline=True)

# Render healthcheck template
template = env.get_template('partials/healthcheck.sh.j2')
try:
    content = template.render(config=config, version=version)
    # Write to file
    with open('$output_path', 'w') as f:
        f.write(content)
except Exception as e:
    print(f'Template rendering failed: {e}', file=sys.stderr)
    # Create a minimal healthcheck as fallback
    content = '''#!/bin/bash
# Minimal healthcheck for Asterisk ''' + version + '''
exec asterisk -rx \"core show uptime\" > /dev/null
'''
    with open('$output_path', 'w') as f:
        f.write(content)
        "; then
            log ERROR "Failed to generate healthcheck.sh using Python"
            return 1
        fi
    fi

    # Make executable
    if ! chmod +x "$output_path"; then
        log ERROR "Failed to make healthcheck.sh executable"
        return 1
    fi

    if [[ ! -f "$output_path" ]]; then
        log ERROR "healthcheck.sh was not created: $output_path"
        return 1
    fi

    log DEBUG "Generated healthcheck.sh successfully: $output_path"
    return 0
}

# Function to generate Dockerfile and healthcheck.sh in version-specific directory
generate_dockerfile() {
    local config_file="$1"
    local version="$2"
    local os="$3"
    local distribution="$4"

    # Create version-specific directory
    # For git builds, use consistent git-master-{distribution} directory
    if [[ "$version" =~ ^git- ]]; then
        local version_tag="git-master-${distribution}"
    else
        local version_tag="${version}-${distribution}"
    fi
    local build_dir="${PROJECT_DIR}/asterisk/${version_tag}"
    local dockerfile_path="${build_dir}/Dockerfile"
    local healthcheck_path="${build_dir}/healthcheck.sh"

    log INFO "Creating build directory: asterisk/${version_tag}" >&2
    if ! mkdir -p "$build_dir"; then
        log ERROR "Failed to create build directory: $build_dir" >&2
        return 1
    fi

    log INFO "Generating Dockerfile and healthcheck.sh for: $version_tag" >&2

    # Generate Dockerfile (without extension)
    local dockerfile_args=("$config_file" --output "$dockerfile_path" --templates-dir "${PROJECT_DIR}/templates/dockerfile")
    if [[ "$SKIP_FORMAT_DOCKERFILE" == true ]]; then
        dockerfile_args+=(--skip-format-dockerfile)
    fi

    log DEBUG "Running: python3 ${SCRIPT_DIR}/generate-dockerfile.py ${dockerfile_args[*]}" >&2
    if ! python3 "${SCRIPT_DIR}/generate-dockerfile.py" "${dockerfile_args[@]}" >&2; then
        log ERROR "Failed to generate Dockerfile from $config_file" >&2
        return 1
    fi

    if [[ ! -f "$dockerfile_path" ]]; then
        log ERROR "Dockerfile was not created: $dockerfile_path" >&2
        return 1
    fi

    # Generate build.sh from template
    local buildsh_path="${build_dir}/build.sh"
    log DEBUG "Generating build.sh script for: $version_tag" >&2
    if ! python3 -c "
import sys
sys.path.insert(0, '${PROJECT_DIR}/lib')
from dockerfile_generator import DockerfileGenerator
generator = DockerfileGenerator('${PROJECT_DIR}/templates')
generator.generate_build_script('$config_file', '$buildsh_path')
" 2>&1; then
        log ERROR "Failed to generate build.sh from $config_file" >&2
        return 1
    fi

    if [[ ! -f "$buildsh_path" ]]; then
        log ERROR "build.sh was not created: $buildsh_path" >&2
        return 1
    fi

    # Generate healthcheck.sh from template
    if ! generate_healthcheck "$config_file" "$version" "$healthcheck_path" >&2; then
        return 1
    fi

    log SUCCESS "Generated Dockerfile, build.sh, and healthcheck.sh in: asterisk/${version_tag}/" >&2
    echo "$build_dir"
    return 0
}

# Function to build Docker image (multi-architecture)
build_image() {
    local build_dir="$1"
    local version="$2"
    local os="$3"
    local distribution="$4"
    local architectures="$5"  # Now comma-separated list: "amd64,arm64"
    local additional_tags="$6"  # Comma-separated list of additional tags

    # Generate primary image tag (no arch-specific tags for multi-arch manifests)
    local primary_tag="${version}_${os}-${distribution}"

    if [[ -n "$DEFAULT_REGISTRY" ]]; then
        primary_tag="${DEFAULT_REGISTRY}:${primary_tag}"
    fi

    # Convert architecture list to Docker platforms format
    local platforms=""
    IFS=',' read -ra arch_array <<< "$architectures"
    for arch in "${arch_array[@]}"; do
        if [[ -n "$platforms" ]]; then
            platforms="${platforms},linux/${arch}"
        else
            platforms="linux/${arch}"
        fi
    done

    local build_args=()
    build_args+=("--file" "$build_dir/Dockerfile")  # Absolute path to Dockerfile
    build_args+=("--platform" "$platforms")         # Multi-platform support
    build_args+=("--tag" "$primary_tag")

    # Add additional tags if specified
    if [[ -n "$additional_tags" ]]; then
        log DEBUG "Processing additional tags: $additional_tags"
        IFS=',' read -ra tags_array <<< "$additional_tags"
        for tag in "${tags_array[@]}"; do
            # Trim whitespace
            tag=$(echo "$tag" | xargs)
            if [[ -n "$tag" ]]; then
                if [[ -n "$DEFAULT_REGISTRY" ]]; then
                    full_tag="${DEFAULT_REGISTRY}:${tag}"
                else
                    full_tag="$tag"
                fi
                build_args+=("--tag" "$full_tag")
                log DEBUG "Added additional tag: $full_tag"
            fi
        done
    fi

    if [[ "$PUSH_IMAGES" == true ]]; then
        build_args+=("--push")
    else
        # For multi-arch builds, --load doesn't work with multiple platforms
        # We need to either push or use --output type=docker for single platform
        if [[ "${#arch_array[@]}" -eq 1 ]]; then
            build_args+=("--load")
        else
            log WARN "Multi-arch builds require --push to registry (cannot load locally)"
            log WARN "Skipping local load for multi-arch build: $primary_tag"
        fi
    fi

    # Add build context (version-specific directory)
    build_args+=("$build_dir")

    # Show all tags that will be built
    local all_tags="$primary_tag"
    if [[ -n "$additional_tags" ]]; then
        IFS=',' read -ra tags_array <<< "$additional_tags"
        for tag in "${tags_array[@]}"; do
            tag=$(echo "$tag" | xargs)
            if [[ -n "$tag" ]]; then
                if [[ -n "$DEFAULT_REGISTRY" ]]; then
                    all_tags="$all_tags, ${DEFAULT_REGISTRY}:${tag}"
                else
                    all_tags="$all_tags, $tag"
                fi
            fi
        done
    fi

    log INFO "Building multi-arch image with tags: $all_tags ($platforms)"
    log DEBUG "Docker build command: docker buildx build ${build_args[*]}"

    # Execute build
    if ! docker buildx build "${build_args[@]}"; then
        log ERROR "Failed to build image: $primary_tag"
        return 1
    fi

    log SUCCESS "Built multi-arch image with tags: $all_tags ($platforms)"

    if [[ "$PUSH_IMAGES" == true ]]; then
        log SUCCESS "Pushed multi-arch image with tags: $all_tags"
    fi

    return 0
}

# Function to setup buildx builder
setup_buildx() {
    log INFO "Setting up Docker buildx builder..."

    # Check if buildx builder exists
    if ! docker buildx ls | grep -q "asterisk-builder"; then
        log INFO "Creating buildx builder: asterisk-builder"
        if ! docker buildx create --name asterisk-builder --use; then
            log ERROR "Failed to create buildx builder"
            return 1
        fi
    else
        log DEBUG "Using existing buildx builder: asterisk-builder"
        docker buildx use asterisk-builder
    fi

    # Bootstrap the builder
    if ! docker buildx inspect --bootstrap >/dev/null 2>&1; then
        log ERROR "Failed to bootstrap buildx builder"
        return 1
    fi

    log SUCCESS "Buildx builder ready"
    return 0
}

# Build processing
log INFO "Build matrix resolution complete - proceeding with config generation..."

# Setup buildx
if ! setup_buildx; then
    exit 1
fi

# Track build results
SUCCESSFUL_BUILDS=()
FAILED_BUILDS=()

# Process each build target
for target in "${BUILD_TARGETS[@]}"; do
    IFS=':' read -r os distribution architectures template source additional_tags <<< "$target"

    log INFO ""
    log INFO "=========================================="
    if [[ -n "$additional_tags" ]]; then
        log INFO "Processing: $VERSION ($os/$distribution [$architectures]) +tags: $additional_tags"
    else
        log INFO "Processing: $VERSION ($os/$distribution [$architectures])"
    fi
    log INFO "=========================================="

    # Generate/find config (config is per distribution, not per architecture)
    config_file=$(ensure_config "$VERSION" "$os" "$distribution" "$template")
    if [[ $? -ne 0 ]]; then
        log ERROR "Failed to ensure config for $target"
        FAILED_BUILDS+=("$target:config_generation")
        continue
    fi

    # Generate Dockerfile and healthcheck.sh (per distribution)
    build_dir=$(generate_dockerfile "$config_file" "$VERSION" "$os" "$distribution")
    if [[ $? -ne 0 ]]; then
        log ERROR "Failed to generate Dockerfile for $target"
        FAILED_BUILDS+=("$target:dockerfile_generation")
        continue
    fi

    # Skip Docker build in dry-run mode (but files are already generated)
    if [[ "$DRY_RUN" == true ]]; then
        log INFO "DRY RUN - Skipping Docker build for $target (files generated in $build_dir)"
        SUCCESSFUL_BUILDS+=("$target")
        continue
    fi

    # Build multi-arch image
    if build_image "$build_dir" "$VERSION" "$os" "$distribution" "$architectures" "$additional_tags"; then
        SUCCESSFUL_BUILDS+=("$target")
        log SUCCESS "Build completed: $target"
    else
        FAILED_BUILDS+=("$target:build_failed")
        log ERROR "Build failed: $target"
    fi

    # Files remain in asterisk/${version}-${distribution}/ directory for reuse
done

# Build summary
log INFO ""
log INFO "=========================================="
log INFO "BUILD SUMMARY"
log INFO "=========================================="
log INFO "Total targets: ${#BUILD_TARGETS[@]}"
log SUCCESS "Successful builds: ${#SUCCESSFUL_BUILDS[@]}"
log ERROR "Failed builds: ${#FAILED_BUILDS[@]}"

if [[ ${#SUCCESSFUL_BUILDS[@]} -gt 0 ]]; then
    log INFO ""
    log INFO "Successful builds:"
    for build in "${SUCCESSFUL_BUILDS[@]}"; do
        IFS=':' read -r os distribution architectures template source additional_tags <<< "$build"
        if [[ -n "$additional_tags" ]]; then
            log SUCCESS "  ✓ $VERSION ($os/$distribution [$architectures]) +tags: $additional_tags"
        else
            log SUCCESS "  ✓ $VERSION ($os/$distribution [$architectures])"
        fi
    done
fi

if [[ ${#FAILED_BUILDS[@]} -gt 0 ]]; then
    log INFO ""
    log ERROR "Failed builds:"
    for build in "${FAILED_BUILDS[@]}"; do
        IFS=':' read -r os distribution architectures template source additional_tags reason <<< "$build"
        log ERROR "  ✗ $VERSION ($os/$distribution [$architectures]) - $reason"
    done
fi

# Exit with appropriate code
if [[ ${#FAILED_BUILDS[@]} -gt 0 ]]; then
    exit 1
else
    log SUCCESS "All builds completed successfully!"
    exit 0
fi