# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

YAML-based Docker build system for Asterisk PBX with all the supported versions (1.2.40 to 23.x.x and a git version). Uses DRY template architecture with automated version discovery and multi-stage Docker builds.

## Build Commands

```bash
# Primary build interface
./scripts/build-asterisk.sh 22.5.2                    # Build specific version
./scripts/build-asterisk.sh 22.5.2 --force-config     # Force regeneration from templates
./scripts/build-asterisk.sh 22.5.2 --dry-run          # Preview without building
./scripts/build-asterisk.sh 22.5.2 --push --registry andrius/asterisk

# Version discovery
./scripts/discover-latest-versions.sh --output-yaml --updates-only

# Testing
./scripts/test-build.sh --mode config "22.5.2"        # Fast config validation
./scripts/test-build.sh --mode build "22.5.2"         # Full Docker build
./scripts/test-build.sh --mode validate "22.5.2"      # Complete functionality test

# GitHub Actions testing
./.act/test-workflows.sh                              # Test all workflows locally
gh act --validate                                      # Validate workflow syntax
```

## High-Level Architecture

### DRY Template System

The project uses a **three-layer template inheritance** system in `templates-dry/`:

1. **Base Layer** (`base/`) - Common packages and Asterisk configuration shared across all versions
2. **Distribution Layer** (`distributions/`) - OS-specific package versions (e.g., libicu76 for Trixie, libicu72 for Bookworm)
3. **Variant Layer** (`variants/`) - Version-specific features (modern, legacy-addons, asterisk-11)

**Template Resolution Flow:**

```
Version Input → Variant Detection → Distribution Mapping → Template Merging → Config Generation
```

### Build Pipeline Architecture

```
scripts/build-asterisk.sh
    ├── Reads asterisk/supported-asterisk-builds.yml (build matrix)
    ├── Calls scripts/generate-config.py
    │   └── Uses lib/template_generator.py (DRYTemplateGenerator)
    │       ├── Merges base + distribution + variant templates
    │       └── Outputs configs/generated/asterisk-VERSION-DIST.yml
    ├── Calls scripts/generate-dockerfile.py
    │   └── Uses lib/dockerfile_generator.py
    │       ├── Renders Jinja2 templates from templates/dockerfile/
    │       └── Outputs asterisk/VERSION-DIST/Dockerfile
    └── Executes docker buildx build
```

### Version Management System

**asterisk/supported-asterisk-builds.yml** controls everything:

- Lists 24 buildable versions with their OS matrices
- Missing `os_matrix` = intentionally disabled version
- `additional_tags` property for semantic Docker tags (latest, stable, etc.)
- Used by both local builds and GitHub Actions

**Automatic Variant Detection** (lib/template_generator.py):

- 1.2.x-1.6.x → `legacy-addons` (separate addons package)
- 1.8.x-11.x → `asterisk10` (pre-PJSIP transitional)
- 12.x+ → `modern` (PJSIP, WebRTC, ARI)

### GitHub Actions Integration

**Per-Release Branch Strategy**:

- `discover-releases.yml` creates individual `asterisk-VERSION` branches
- Each new version gets its own PR for granular review
- Collision detection prevents duplicate branches
- `build-images.yml` uses matrix from supported-asterisk-builds.yml

## Critical Development Rules

### Template-First Architecture

**NEVER edit files in `asterisk/` directories** - they are auto-generated. All changes MUST go through templates:

```bash
# WRONG ❌
vi asterisk/22.5.2-trixie/Dockerfile

# CORRECT ✅
vi templates/debian-trixie.yml.template
./scripts/build-asterisk.sh 22.5.2 --force-config
```

### Configuration Mismatch Issue

The `regenerate-all-configs.sh` script now properly uses the same template system as `build-asterisk.sh` to prevent configuration drift. Previously it used hardcoded generation which caused mismatches.

### Package Management

Packages are **hardcoded in distribution templates** for reproducibility:

- `templates/debian-trixie.yml.template`: libicu76, libpqxx-7.10
- `templates/debian-bookworm.yml.template`: libicu72, libpqxx-6.4
- Runtime packages MUST include `binutils` for BFD libraries

## Key Implementation Details

### Multi-Stage Build Optimization

- Builder stage: ~6GB with all build dependencies
- Runtime stage: ~232MB optimized image
- Uses Docker buildx cache mounts for faster rebuilds
- Healthcheck integrated via templates/partials/healthcheck.sh.j2

### Menuselect Command Handling

Problem: Asterisk menuselect commands exceed shell limits (6,291+ chars)
Solution: External build.sh generation via templates/partials/build.sh.j2

### Template Variable System

Only these variables are substituted:

- `{{VERSION}}` - Asterisk version
- `{{DISTRIBUTION}}` - OS distribution
- `{{VARIANT}}` - Build variant
- `{{ADDONS_VERSION}}` - For legacy builds only

## Common Issues & Solutions

### Version Not Building

```bash
# Check if version is in build matrix
grep "22.5.2" asterisk/supported-asterisk-builds.yml

# If missing os_matrix, it's intentionally disabled
# Add os_matrix to enable building
```

### Template Changes Not Applied

```bash
# Always use --force-config after template edits
./scripts/build-asterisk.sh VERSION --force-config
```

### Config Generation Failures

```bash
# Validate template syntax
python3 -c "import yaml; yaml.safe_load(open('templates/debian-trixie.yml.template').read().replace('{{VERSION}}', '22.5.2'))"

# Check generated config
cat configs/generated/asterisk-22.5.2-trixie.yml
```

### Package Version Issues

```bash
# Check available packages in target OS
docker run --rm debian:trixie-slim apt-cache search libicu

# Update template with correct versions
vi templates/debian-trixie.yml.template
```

## Testing Strategy

Three-tier testing approach:

1. **Config Mode** - Template/YAML validation (1-2 min)
2. **Build Mode** - Docker image building (30-60 min)
3. **Validate Mode** - Container functionality (45-75 min)

All tests use AMD64 only and never push to registry.

## Directory Structure

```
templates/           # ✅ EDIT THESE - Source of truth
├── base/           # Common configuration
├── distributions/  # OS-specific packages
├── variants/       # Version-specific features
├── dockerfile/     # Jinja2 Docker templates
└── partials/       # Build scripts and healthchecks

asterisk/           # ❌ NEVER EDIT - Auto-generated
└── VERSION-DIST/   # Generated Dockerfiles and scripts

configs/generated/  # 📖 READ ONLY - Generated YAML configs
```

## Workflow Files

- `discover-releases.yml` - Daily at 20:00 UTC, creates per-release PRs
- `build-images.yml` - Matrix builds from supported-asterisk-builds.yml
- `build-single-image.yml` - Reusable workflow for individual builds

Test workflows locally with `gh act` before committing changes.

