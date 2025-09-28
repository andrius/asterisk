# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Background

This project is a modern adaptation of the andrius/asterisk Docker repository, featuring an automated build system with version discovery and YAML-based configuration management. It generates optimized Docker images for Asterisk PBX across multiple operating systems and versions.

### Reference Repositories

The `./andrius-tmp/` directory contains reference implementations that informed this project's design:

- **`andrius-asterisk`** - Original andrius/asterisk repository (hub.docker.com/r/andrius/asterisk)
  - Legacy Dockerfiles for Alpine, Debian, and CentOS
  - BATS test framework for image validation
  - Manual build scripts for each Asterisk version
  - ERB templating for Alpine images

- **`manobatai-matrix`** - Automation and CI/CD patterns
  - GitHub Actions for release discovery and daily updates
  - Scripts for fetching Asterisk releases and certified versions
  - Alpine APK package building automation
  - Docker registry tag discovery

- **`asterisk-trixie`** - Debian Trixie adaptation
  - Build scripts for Debian Bookworm and Trixie
  - Simplified Dockerfile structure
  - Basic entrypoint and health checks

- **`multilayer`** - Multi-stage build optimization
  - Production (232MB) vs Development (6GB) image strategies
  - BuildKit cache mount optimizations
  - Shared library architecture (DRY principle)
  - Comprehensive health monitoring system

## Project Overview

This is a YAML-based Docker build system for Asterisk PBX that generates optimized Docker images with automated version discovery and standardized configurations. The system uses Jinja2 templates to generate Dockerfiles from YAML configurations.

## System Dependencies

The build system requires the following tools to be installed:

- **Python 3.8+** with packages: `pyyaml`, `jinja2`, `jsonschema`
- **Docker** with buildx support
- **yq** - YAML processor for configuration parsing and template processing
- **curl** - For downloading Asterisk releases and performing HTTP requests
- **bash 4.0+** - Shell scripting environment

### Installation

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-pip docker.io yq curl

# Install Python packages
pip3 install pyyaml jinja2 jsonschema

# Enable buildx (if not already available)
docker buildx create --use
```

## Scripts Overview

### Version Discovery Scripts (`scripts/`)

- **`discover-latest-versions.sh`** - Main discovery script that finds latest stable, RC, beta, and alpha versions for each major Asterisk release
- **`get-asterisk-releases.sh`** - Fetches all Asterisk releases from downloads.asterisk.org
- **`get-asterisk-certified-releases.sh`** - Fetches certified Asterisk releases

### Configuration Generators

- **`generate-dockerfile.py`** - Generates Dockerfiles from YAML configurations using Jinja2

### Data Files (`asterisk/` Directory)

- **`asterisk/asterisk-releases.txt`** - Plain text list of all Asterisk releases
- **`asterisk/asterisk-releases.yml`** - YAML format organized by major version
- **`asterisk/asterisk-certified-releases.txt`** - Plain text list of certified releases
- **`asterisk/asterisk-certified-releases.yml`** - YAML format of certified releases
- **`asterisk/supported-asterisk-builds.yml`** - Supported versions and build matrix (formerly latest-asterisk-builds.yml)

## 🚨 STRICT DEVELOPMENT RULES

**CRITICAL**: This project follows a strict template-based development approach. These rules MUST be followed:

### ❌ NEVER DO THIS:
- **NEVER manually edit files in the `asterisk/` folder** - These are auto-generated and will be overwritten
- **NEVER edit Dockerfiles, build.sh, or healthcheck.sh files directly** in `asterisk/*/` directories
- **NEVER make manual changes to generated configs** in the build directories
- **NEVER commit files from `asterisk/` directories** - they are temporary build artifacts

### ✅ ALWAYS DO THIS:
- **ALWAYS make changes through templates** in the `templates/` directory only
- **ALWAYS use `--force-config` flag** when testing template changes
- **ALWAYS regenerate from templates** when making any modifications
- **ALWAYS test the complete template → generation → build cycle**

### Template-First Workflow:
```bash
# 1. Edit template (ONLY way to make changes)
vi templates/debian-trixie.yml.template

# 2. Regenerate with --force-config
./scripts/build-asterisk.sh 22.5.2 --force-config

# 3. Verify generated files
ls -la asterisk/22.5.2-trixie/

# 4. Test Docker build
docker build -t test asterisk/22.5.2-trixie/
```

**Why These Rules Exist:**
- Ensures consistency across all builds
- Prevents configuration drift and manual errors
- Maintains declarative infrastructure-as-code approach
- Allows proper version control of the actual source (templates)

## Common Development Commands

### Build Asterisk Docker Images

The primary interface for building Docker images is the integrated build script:

```bash
# Build all configurations for a version (uses supported-asterisk-builds.yml)
./scripts/build-asterisk.sh 23.0.0-rc1

# Build specific OS/architecture combinations
./scripts/build-asterisk.sh 22.5.2 debian          # All Debian variants
./scripts/build-asterisk.sh 22.5.2 debian amd64    # Only Debian amd64
./scripts/build-asterisk.sh 23.0.0-rc1 --dry-run   # Preview what would be built

# CRITICAL: Use --force-config when testing template changes
./scripts/build-asterisk.sh 22.5.2 --force-config  # Regenerate from templates
./scripts/build-asterisk.sh 22.5.2 --verbose --force-config

# Advanced build options
./scripts/build-asterisk.sh 22.5.2 --push --registry myregistry.com/asterisk
```

**Important Notes:**
- Only versions listed in `asterisk/supported-asterisk-builds.yml` can be built
- The script enforces validated configurations for consistency
- **Files in `asterisk/` directories are AUTO-GENERATED** - never edit them manually
- **Always use `--force-config`** when testing template changes
- Generated directories: `asterisk/VERSION-DISTRIBUTION/` (e.g., `asterisk/22.5.2-trixie/`)

**Generated Files (Template-Based):**
- `Dockerfile` - Multi-stage Docker build configuration
- `build.sh` - Asterisk build script with menuselect commands
- `healthcheck.sh` - Container health monitoring script

### Version Discovery and YAML Management

```bash
# Discover latest versions and update YAML (recommended workflow)
./scripts/discover-latest-versions.sh --output-yaml --updates-only

# Full regeneration (use with caution - overwrites customizations)
./scripts/discover-latest-versions.sh --output-yaml

# Check what versions are available for building
grep -A1 "version:" asterisk/supported-asterisk-builds.yml
```

### Manual Configuration Generation (Development)

```bash
# Build modern Asterisk on Debian - configs generated automatically by build script
./scripts/build-asterisk.sh 22.5.5 debian
```

### Advanced Dockerfile Generation

```bash
# Generate single Dockerfile (automatically done by build script)
python3 scripts/generate-dockerfile.py configs/generated/asterisk-23.0.0-rc1_debian-trixie.yml --output Dockerfile --templates-dir templates/dockerfile

# Batch generate Dockerfiles for all configs
python3 scripts/generate-dockerfile.py --batch configs/generated/ --batch-output dockerfiles/

# Validate configuration only
python3 scripts/generate-dockerfile.py configs/generated/asterisk-23.0.0-rc1_debian-trixie.yml --validate
```

### Release Data Management

```bash
# Update standard releases
./scripts/get-asterisk-releases.sh > asterisk/asterisk-releases.txt

# Update certified releases
./scripts/get-asterisk-certified-releases.sh > asterisk/asterisk-certified-releases.txt

# Convert to YAML format
./scripts/discover-latest-versions.sh --output-yaml
```

## Integrated Build Pipeline

### Build Script (`scripts/build-asterisk.sh`)

The integrated build script provides a complete end-to-end pipeline from version specification to Docker image:

**Key Features:**
- **YAML-Driven**: Only builds versions explicitly listed in `asterisk/supported-asterisk-builds.yml`
- **Smart Config Resolution**: Prefers `configs/generated/` (modern format) over legacy configs
- **Multi-Platform Support**: Uses Docker buildx for cross-architecture builds
- **Automatic Healthcheck**: Generates healthcheck.sh from Jinja2 templates
- **Flexible Filtering**: Supports OS and architecture filtering

**Build Flow:**
```
Version Input → YAML Matrix Resolution → Config Resolution → Dockerfile Generation → Docker Build
```

**Version Resolution Logic:**
1. **Version NOT in YAML** → ❌ Error with available versions list
2. **Version in YAML but no `os_matrix`** → ⏭️ Skip (intentionally disabled)
3. **Version in YAML with `os_matrix`** → ✅ Build using custom configuration

**Example Output:**
```bash
$ ./scripts/build-asterisk.sh 23.0.0-rc1 --dry-run
[INFO]  Build targets:
[INFO]    → debian/trixie (amd64) [from: custom_matrix]
[INFO]  DRY RUN - Would build 1 targets
```

### Configuration Management

**Configuration Format** (`configs/*.yml`):
- Generated automatically by build script from declarative templates
- Multi-stage build configuration with optimization settings
- Comprehensive package management for different distributions
- Template-driven menuselect configuration

**Package Version Management:**
- Distribution-specific package versions (e.g., `libicu76` for Debian Trixie)
- Automatic dependency resolution based on OS and distribution
- Runtime vs build package separation for optimized image sizes

### YAML Build Matrix (`asterisk/supported-asterisk-builds.yml`)

This file controls which versions can be built and their configurations:

```yaml
latest_builds:
  - version: "22.5.2"
    os_matrix:
      - os: "debian"
        distribution: "trixie"
        architectures: ["amd64", "arm64"]

  - version: "23.0.0-rc1"
    os_matrix:
      distribution: "trixie"  # Missing os defaults to debian
      architectures: ["amd64"]

  - version: "21.10.2"  # No os_matrix = skipped/disabled
```

**Matrix Behavior:**
- **Custom matrices** preserve user customizations (like limited distributions)
- **Missing `os_matrix`** means the version is intentionally disabled
- **Version discovery** only adds new versions, never modifies existing entries

## Architecture and Design

### Core Components

1. **YAML Configuration System** (`configs/*.yml`)

   - Each config specifies Asterisk version, OS base, packages, and build settings
   - Validated against `schema/build-config.schema.json`
   - Supports modern Asterisk versions (11+)

2. **Template System** (`templates/`)

   **Declarative YAML Templates:**
   - `debian-trixie.yml.template` - Debian Trixie with hardcoded packages (libicu76, libpqxx-7.10)
   - `debian-bookworm.yml.template` - Debian Bookworm with hardcoded packages (libicu72, libpqxx-6.4)

   **Jinja2 Templates:**
   - `dockerfile/multi-stage.dockerfile.j2` - Production multi-stage Docker builds
   - `dockerfile/single-stage.dockerfile.j2` - Development single-stage builds
   - `partials/build.sh.j2` - Asterisk build script with menuselect commands
   - `partials/healthcheck.sh.j2` - Container health monitoring

3. **Generator Libraries** (`lib/`)

   - `dockerfile_generator.py` - Main Dockerfile generation engine using Jinja2
   - `menuselect.py` - Asterisk menuselect configuration generator
   - ~~`packages.py`~~ - **REMOVED**: Package resolution now hardcoded in declarative templates

4. **Version Discovery System**
   - Fetches releases from downloads.asterisk.org
   - Priority-based selection: stable > rc > beta > alpha
   - Supports modern Asterisk versions (11+)

### Template Variable System

Templates use these placeholders:

- `{{VERSION}}` - Asterisk version

### Configuration Structure

YAML configurations follow this schema:

```yaml
version: "22.5.5" # Asterisk version
base: # OS configuration
  os: "debian"
  distribution: "trixie"
  image: "debian:trixie"
packages: # Dependencies
  build: [...] # Build-time packages
  runtime: [...] # Runtime packages
asterisk: # Asterisk-specific settings
  menuselect: # Module selection
  configure_options: [] # ./configure flags
docker: # Docker metadata
  tags: [] # Image tags
  ports: [] # Exposed ports
```

## Key Implementation Details

### Version Detection Logic

- Only modern Asterisk versions (11+) are supported
- Legacy versions (1.2-1.8) have been archived for future consideration

### Multi-Stage Docker Builds

- The Dockerfile generator supports both single-stage and multi-stage builds
- Multi-stage builds separate build dependencies from runtime for smaller images
- Template selection is automatic based on configuration

### Declarative Package Management

- ~~`lib/packages.py`~~ **REMOVED**: Package resolution now handled declaratively
- **Hardcoded packages** in distribution-specific templates (debian-trixie.yml.template, debian-bookworm.yml.template)
- **Version-specific requirements** explicitly defined per distribution (e.g., libicu76 vs libicu72)
- **Runtime dependencies** include essential packages like `binutils` for shared libraries

### Menuselect Configuration

- `lib/menuselect.py` generates Asterisk menuselect commands
- Configures modules, channels, apps based on YAML specification
- Handles modern Asterisk module selection (chan_pjsip, res_pjsip, etc.)

## Template Development Rules

### Declarative YAML Template Approach

This system uses **fully declarative** YAML templates with hardcoded package lists per distribution:

**✅ Current Architecture:**
- `debian-trixie.yml.template` - Debian 13 (Trixie) packages: `libicu76`, `libpqxx-7.10`, `binutils`
- `debian-bookworm.yml.template` - Debian 12 (Bookworm) packages: `libicu72`, `libpqxx-6.4`, `binutils`
- `alpine.yml.template` - Alpine Linux 3.22 minimal packages
- `base.yml.template` - Generic fallback with essential runtime packages

### Build.sh Template System

**Problem Solved:** Asterisk menuselect commands exceeded shell command-line length limits (6,291+ characters)

**Solution:** External build script generation through `templates/partials/build.sh.j2`

**Features:**
- **Organized menuselect commands** by type (apps, channels, resources)
- **Error handling** with `|| warn` for missing modules
- **Color-coded logging** for build progress tracking
- **Parallelization** with configurable JOBS variable

**Example Template Usage:**
```jinja2
# Enable core applications
{% for cmd in menuselect_commands -%}
{% if 'app_' in cmd and '--enable' in cmd -%}
{{ cmd }} || warn "Module not found: $(echo '{{ cmd }}' | grep -o '[a-z_]*' | tail -1)"
{% endif -%}
{% endfor %}
```

### Template Variable System

Templates support these key variables:

- `{{VERSION}}` - Asterisk version (e.g., "22.5.2", "23.0.0-rc1")
- Distribution-specific package versions are **hardcoded** in each template
- No dynamic resolution - ensures build reproducibility

### Template Testing Workflow

```bash
# 1. Edit template
vi templates/debian-trixie.yml.template

# 2. Force regeneration (REQUIRED)
./scripts/build-asterisk.sh 22.5.2 --force-config

# 3. Verify generated files
ls -la asterisk/22.5.2-trixie/
cat asterisk/22.5.2-trixie/Dockerfile  # Check packages
cat asterisk/22.5.2-trixie/build.sh    # Check menuselect commands

# 4. Test Docker build
docker build -t test asterisk/22.5.2-trixie/

# 5. Test container
docker run --rm test asterisk -V
```

### Distribution-Specific Package Management

**Debian Trixie (13):**
- ICU Library: `libicu76`
- PostgreSQL C++: `libpqxx-7.10`
- Binary utilities: `binutils` (for BFD libraries)

**Debian Bookworm (12):**
- ICU Library: `libicu72`
- PostgreSQL C++: `libpqxx-6.4`
- Binary utilities: `binutils` (for BFD libraries)

**Critical Dependencies:**
- `binutils` package **REQUIRED** for runtime BFD shared libraries
- `libjansson-dev` (build) + `libjansson4` (runtime) for JSON support
- `ca-certificates` installed separately to avoid conflicts

## Testing and Validation

### Template-Based Testing Workflow

**🚨 IMPORTANT**: Always test the complete template → generation → build cycle:

```bash
# 1. Template Validation - Check YAML syntax
python3 -c "
import yaml
template = open('templates/debian-trixie.yml.template').read()
config = template.replace('{{VERSION}}', '22.5.2')
yaml.safe_load(config)
print('✅ Template syntax valid')
"

# 2. Generation Testing - Force regeneration and validate
./scripts/build-asterisk.sh 22.5.2 --force-config --dry-run
ls -la asterisk/22.5.2-trixie/  # Verify files created

# 3. Configuration Validation - Check generated config
python3 -c "
import json, yaml, jsonschema
config = yaml.safe_load(open('configs/asterisk-22.5.2-trixie.yml'))
schema = json.load(open('schema/build-config.schema.json'))
jsonschema.validate(config, schema)
print('✅ Generated config valid')
"

# 4. Build Testing - Test Docker build
docker build --no-cache asterisk/22.5.2-trixie/

# 5. Runtime Testing - Test container functionality
docker run --rm asterisk/22.5.2-trixie:latest asterisk -V
```

### Template Validation Commands

```bash
# Validate specific template
python3 -c "
import yaml
template_content = open('templates/debian-bookworm.yml.template').read()
test_config = template_content.replace('{{VERSION}}', '22.5.2')
yaml.safe_load(test_config)
"

# Check for template variable completeness
grep -r "{{" templates/*.template | grep -v VERSION
# Should only show VERSION variables

# Validate all templates at once
for template in templates/*.yml.template; do
    echo "Validating: $template"
    python3 -c "
import yaml, sys
content = open('$template').read().replace('{{VERSION}}', '22.5.2')
try:
    yaml.safe_load(content)
    print('✅ Valid')
except Exception as e:
    print('❌ Invalid:', e)
    sys.exit(1)
"
done
```

### Build Process Validation

```bash
# Test complete build process for multiple versions
for version in 22.5.2 23.0.0-rc1; do
    echo "Testing: $version"
    ./scripts/build-asterisk.sh $version --force-config --verbose

    # Verify generated files exist and are not empty
    [ -s "asterisk/$version-trixie/Dockerfile" ] && echo "✅ Dockerfile OK"
    [ -x "asterisk/$version-trixie/build.sh" ] && echo "✅ Build script OK"
    [ -x "asterisk/$version-trixie/healthcheck.sh" ] && echo "✅ Healthcheck OK"
done
```

### Generated File Validation

```bash
# Check Dockerfile packages match template expectations
version="22.5.2"
echo "Checking packages for $version-trixie:"
grep -o "libicu[0-9]*" "asterisk/$version-trixie/Dockerfile" | head -1
grep -o "libpqxx-[0-9.]*" "asterisk/$version-trixie/Dockerfile" | head -1
grep -q "binutils" "asterisk/$version-trixie/Dockerfile" && echo "✅ binutils present"

# Verify build.sh has menuselect commands
grep -q "menuselect" "asterisk/$version-trixie/build.sh" && echo "✅ menuselect commands present"
grep -c "|| warn" "asterisk/$version-trixie/build.sh"  # Count error handling
```

## Common Workflows

### Adding Support for New Asterisk Version

1. Run version discovery: `./scripts/discover-latest-versions.sh --output-yaml --updates-only`
2. **Template-based approach**: Build uses existing templates automatically
3. Test build: `./scripts/build-asterisk.sh NEW_VERSION --force-config`
4. Verify generated files: `ls -la asterisk/NEW_VERSION-*/`

### Making Template Changes (REQUIRED for any modifications)

```bash
# 1. Edit template (ONLY way to make changes)
vi templates/debian-trixie.yml.template

# 2. Test with --force-config (REQUIRED)
./scripts/build-asterisk.sh 22.5.2 --force-config

# 3. Verify changes applied
cat asterisk/22.5.2-trixie/Dockerfile

# 4. Test Docker build
docker build -t test asterisk/22.5.2-trixie/
```

### Updating Package Dependencies

⚠️ **TEMPLATE-ONLY**: Never edit generated configs directly!

**For Debian Trixie:**
1. Edit `templates/debian-trixie.yml.template`
2. Update hardcoded package versions (e.g., `libicu76`, `libpqxx-7.10`)
3. Regenerate: `./scripts/build-asterisk.sh VERSION --force-config`
4. Test build process

**For Debian Bookworm:**
1. Edit `templates/debian-bookworm.yml.template`
2. Update hardcoded package versions (e.g., `libicu72`, `libpqxx-6.4`)
3. Regenerate: `./scripts/build-asterisk.sh VERSION --force-config`
4. Test build process

### Customizing Build Options

⚠️ **TEMPLATE-ONLY**: Never edit configs in `asterisk/` directories!

1. **Edit appropriate template** in `templates/` directory
2. **Modify `asterisk.configure_options`** array in template
3. **Adjust `asterisk.menuselect`** for module selection in template
4. **Regenerate with `--force-config`**: `./scripts/build-asterisk.sh VERSION --force-config`
5. **Test complete build**: Docker build → container test → verification

## GitHub Actions Workflows

### Available Workflows (`.github/workflows/`)

- **`discover-releases.yml`** - Daily cron job (20:00 UTC) that fetches new releases and updates release files
- **`build-images.yml`** - Builds and pushes Docker images for specified configurations

### Manual Workflow Triggers

```bash
# Trigger release discovery manually
gh workflow run discover-releases.yml

# Build specific image
gh workflow run build-images.yml -f config=asterisk-22.5.5-trixie
```

## Directory Structure

```
.
├── asterisk/         # AUTO-GENERATED: Build directories (NEVER edit manually!)
│   └── VERSION-DIST/ # Generated Dockerfiles, build.sh, healthcheck.sh
├── configs/          # YAML configuration files (legacy and generated)
├── lib/              # Python libraries for generation and processing
│   ├── dockerfile_generator.py  # Jinja2-based Dockerfile generation
│   ├── menuselect.py           # Asterisk menuselect configuration
│   └── ~~packages.py~~         # REMOVED: Package resolution now in templates
├── scripts/          # Shell and Python scripts for automation
│   └── build-asterisk.sh       # Primary build interface
├── templates/        # Configuration and Dockerfile templates (EDIT THESE!)
│   ├── debian-trixie.yml.template   # Debian 13 declarative template
│   ├── debian-bookworm.yml.template # Debian 12 declarative template
│   ├── dockerfile/   # Jinja2 Dockerfile templates
│   │   ├── multi-stage.dockerfile.j2    # Production builds
│   │   └── single-stage.dockerfile.j2   # Development builds
│   └── partials/    # Reusable template fragments
│       ├── build.sh.j2         # Asterisk build script template
│       └── healthcheck.sh.j2   # Container health monitoring
└── schema/          # JSON schemas for validation
    └── build-config.schema.json  # YAML configuration schema
```

**Key Directories:**
- **`templates/`** - ✅ **EDIT THESE** - Source of truth for all configurations
- **`asterisk/`** - ❌ **NEVER EDIT** - Auto-generated, temporary build artifacts
- **`configs/`** - 📖 **READ ONLY** - Generated from templates, do not edit manually

## Build System Features

### Intelligent Version Detection

- Supports modern Asterisk versions (11+)
- Prioritizes stable releases over pre-release versions
- Supports both standard and certified Asterisk releases
- Filters by release status: stable > rc > beta > alpha

### Multi-OS Support

- **Debian**: Full-featured builds with comprehensive package sets (bookworm, trixie)
- **Modern Asterisk**: Only versions 11+ are supported

### Package Management

Package dependencies are hardcoded in distribution-specific templates:
- Distribution-specific package versions (e.g., libicu76 for Trixie, libicu72 for Bookworm)
- Asterisk version requirements
- Build vs runtime dependencies
- SSL library compatibility (libssl3 vs libssl1.1)

### Template System

Templates support variable substitution for:
- Asterisk version
- Package lists (build and runtime) hardcoded per distribution
- Configure options and menuselect settings
- Docker metadata (tags, labels, ports)

## Testing Strategy

### Configuration Validation

All YAML configurations are validated against JSON schema before processing. The schema ensures:
- Required fields are present
- Data types are correct
- Package lists are properly formatted
- Menuselect options are valid

### Build Testing

```bash
# Test build locally
docker build -f generated/Dockerfile -t test-asterisk .

# Run container tests
docker run --rm test-asterisk asterisk -V
docker run --rm test-asterisk asterisk -rx "core show version"
```

### Health Checks

Generated images include health check scripts that verify:
- Asterisk process is running
- Core modules are loaded
- SIP stack is responsive
- Configuration files are valid

## Troubleshooting

### Common Issues

1. **Manual edits not working**: Files in `asterisk/` directories are auto-generated.
   ```bash
   # ❌ WRONG: Editing generated files
   vi asterisk/22.5.2-trixie/Dockerfile

   # ✅ CORRECT: Edit template and regenerate
   vi templates/debian-trixie.yml.template
   ./scripts/build-asterisk.sh 22.5.2 --force-config
   ```

2. **Template changes not applied**: Always use `--force-config` flag.
   ```bash
   # ❌ WRONG: Normal build after template changes
   ./scripts/build-asterisk.sh 22.5.2

   # ✅ CORRECT: Force regeneration from templates
   ./scripts/build-asterisk.sh 22.5.2 --force-config
   ```

3. **Version not found in YAML**: Only versions in `asterisk/supported-asterisk-builds.yml` can be built.
   ```bash
   # Check available versions
   ./scripts/build-asterisk.sh 99.9.9 --dry-run
   # Update YAML to add new versions
   ./scripts/discover-latest-versions.sh --output-yaml --updates-only
   ```

4. **Package version mismatches**: Distribution-specific packages hardcoded in templates.
   ```bash
   # Check available packages in target distribution
   docker run --rm debian:trixie-slim sh -c "apt-cache search libicu"

   # ✅ CORRECT: Update template with correct versions
   vi templates/debian-trixie.yml.template  # Update libicu76, libpqxx-7.10, etc.
   ./scripts/build-asterisk.sh VERSION --force-config
   ```

5. **Missing BFD libraries**: Runtime verification fails with "libbfd-*.so not found".
   ```bash
   # ✅ SOLUTION: Ensure binutils is in runtime packages
   grep -n "binutils" templates/debian-*.yml.template
   # If missing, add to template runtime packages list
   ```

6. **Shell command-line length errors**: Menuselect commands exceed limits.
   ```bash
   # ✅ SOLUTION: Build.sh template system handles this automatically
   cat asterisk/VERSION-DIST/build.sh  # Check generated build script
   # All menuselect commands moved to external script
   ```

7. **Build failures**: Review Docker build logs and generated files.
   ```bash
   # Build with verbose output
   ./scripts/build-asterisk.sh 23.0.0-rc1 --verbose --force-config

   # Check generated files
   cat asterisk/23.0.0-rc1-trixie/Dockerfile  # Verify packages
   cat asterisk/23.0.0-rc1-trixie/build.sh    # Verify build commands
   ```

### Template Debugging

**Validate Template Changes:**
```bash
# 1. Check template syntax
python3 -c "import yaml; yaml.safe_load(open('templates/debian-trixie.yml.template').read().replace('{{VERSION}}', '22.5.2'))"

# 2. Verify generated config
./scripts/build-asterisk.sh 22.5.2 --force-config
cat configs/asterisk-22.5.2-trixie.yml

# 3. Check generated Dockerfile
cat asterisk/22.5.2-trixie/Dockerfile

# 4. Test Docker build step-by-step
docker build --no-cache asterisk/22.5.2-trixie/
```

**Template Variable Issues:**
```bash
# Check for unresolved template variables
grep -n "{{" asterisk/*/Dockerfile asterisk/*/build.sh
# Should return no matches - all variables should be resolved
```

### Debug Commands

```bash
# Validate build pipeline step by step
./scripts/build-asterisk.sh 23.0.0-rc1 --dry-run --verbose

# Check config resolution
python3 -c "
import yaml
config = yaml.safe_load(open('configs/generated/asterisk-23.0.0-rc1_debian-trixie.yml'))
print('Runtime packages:', config['build']['stages']['runtime']['packages'])
"

# Test Dockerfile generation manually
python3 scripts/generate-dockerfile.py \
  configs/generated/asterisk-23.0.0-rc1_debian-trixie.yml \
  --output test.Dockerfile \
  --templates-dir templates/dockerfile

# Verify YAML matrix parsing
python3 -c "
import yaml
data = yaml.safe_load(open('asterisk/supported-asterisk-builds.yml'))
for build in data['latest_builds']:
    print(f\"{build['version']}: {'buildable' if 'os_matrix' in build else 'skipped'}\")
"

# Test package availability in target OS
docker run --rm debian:trixie-slim sh -c "
  apt-get update > /dev/null 2>&1
  apt-cache search libicu | grep -E '^libicu[0-9]+'
"
```

### Performance Optimization

**Build Speed:**
- Use `--parallel` for multiple simultaneous builds
- Docker buildx cache mounts reduce build times
- Multi-stage builds minimize final image size

**Cache Management:**
```bash
# Clean Docker build cache
docker buildx prune

# Remove old build artifacts
rm -f Dockerfile.* healthcheck.sh

# Clear Python cache
find . -name "__pycache__" -exec rm -rf {} +
```

## Validated Build Examples

### Successful Build: Asterisk 23.0.0-rc1

**Configuration Used:**
- **Version**: `23.0.0-rc1` (latest release candidate)
- **OS**: Debian Trixie
- **Architecture**: amd64
- **Config**: `configs/generated/asterisk-23.0.0-rc1_debian-trixie.yml`

**Build Command:**
```bash
./scripts/build-asterisk.sh 23.0.0-rc1 --verbose
```

**Key Validations:**
- ✅ YAML matrix resolution (custom os_matrix with amd64 only)
- ✅ Config resolution (modern generated config format)
- ✅ Package version management (libicu76 for Debian Trixie)
- ✅ Dockerfile generation with Jinja2 templates
- ✅ Healthcheck script generation from template
- ✅ Multi-stage Docker build process
- ✅ Docker buildx integration for cross-platform support

**Generated Assets:**
- `Dockerfile.23.0.0-rc1-trixie` (12.5KB, multi-stage optimized)
- `healthcheck.sh` (executable health monitoring script)
- Docker images: `23.0.0-rc1_debian-trixie`, `23.0.0-rc1_debian-trixie-amd64`

**Build Performance:**
- **Package Installation**: ~21 seconds (cached dependencies)
- **Source Download**: Asterisk 23.0.0-rc1 from downloads.asterisk.org
- **Multi-stage**: Separate builder and runtime environments
- **Image Size**: Optimized with production/development separation

### Integration Points Validated

1. **Version Discovery → Build Pipeline**
   ```bash
   # Discover new versions
   ./scripts/discover-latest-versions.sh --output-yaml --updates-only
   # Build newly discovered versions
   ./scripts/build-asterisk.sh NEW_VERSION
   ```

2. **Custom Configuration Preservation**
   - User-modified `os_matrix` entries are preserved during discovery updates
   - Manual package version fixes persist through regeneration cycles
   - Disabled versions (no `os_matrix`) remain skipped

3. **Cross-Platform Readiness**
   - Docker buildx configured for multi-platform builds
   - Architecture filtering works correctly
   - Image tagging follows consistent naming conventions

This validation confirms the build system is production-ready for automated Asterisk Docker image generation across multiple versions and platforms.

## GitHub Workflow Testing

**CRITICAL**: Always test workflow changes with `gh act` before committing:

```bash
# Run comprehensive test suite (recommended)
./.act/test-workflows.sh

# Test specific workflow
gh act workflow_dispatch -W .github/workflows/build-git-daily.yml --dryrun

# Validate all workflow syntax
gh act --validate
```

**Key Points:**
- Use `gh act` (GitHub CLI extension), not standalone `act`
- Test payloads are in `.act/payloads/` directory
- Always use `--dryrun` during development
- See README-gh-workflows.md for comprehensive testing guide