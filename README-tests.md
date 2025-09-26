# Asterisk Docker Build Test System

This document explains the comprehensive test system for validating Asterisk Docker images locally before CI/CD deployment.

## Overview

The test system prevents build failures and configuration issues by validating all supported Asterisk versions with three levels of testing:

- **Config Mode**: Fast template and configuration validation (~1-2 minutes)
- **Build Mode**: Complete Docker image building (~30-60 minutes)
- **Validate Mode**: Full functionality testing including container startup (~45-75 minutes)

All tests run **AMD64 only** and **never push to registry** - pure local validation.

## Prerequisites

```bash
# Required tools
sudo apt install python3 python3-pip docker.io
pip3 install pyyaml jinja2 jsonschema

# Docker buildx support
docker buildx create --use
```

## Test Modes Explained

### Config Mode (Fastest - Recommended for Development)

**What it validates:**
- ✅ YAML configuration parsing and schema validation
- ✅ Jinja2 template rendering (Dockerfile, build.sh, healthcheck.sh)
- ✅ Template variable substitution (version, packages, settings)
- ✅ Configuration file generation without actual building

**Example:**
```bash
scripts/test-build.sh --mode config "22.5.2"
```

**Real output:**
```
2025-09-28 18:10:44 [INFO] Testing version: 22.5.2 (mode: config)
[INFO]  Starting Asterisk build for version: 22.5.2
[INFO]  OS filter: debian
[INFO]  Architecture filter: amd64
[INFO]  DRY RUN MODE - No actual builds will be performed
[INFO]  Build targets:
[INFO]    → debian/trixie (amd64) [from: custom_matrix]
[INFO]  DRY RUN - Would build 1 targets
2025-09-28 18:10:44 [SUCCESS] Version 22.5.2: All tests passed (0s)

=== BUILD STATISTICS ===
Total builds: 1
Successful: 1
Failed: 0
Success rate: 100%
```

**What happens under the hood:**
1. Parses `asterisk/supported-asterisk-builds.yml` matrix
2. Loads version configuration from `configs/generated/asterisk-22.5.2-trixie.yml`
3. Renders Dockerfile from `templates/dockerfile/multi-stage.dockerfile.j2`
4. Generates build script from `templates/partials/build.sh.j2`
5. Creates healthcheck from `templates/partials/healthcheck.sh.j2`
6. Validates all files were created successfully

### Build Mode (Complete Docker Building)

**What it validates:**
- ✅ All config mode validations +
- ✅ Actual Docker image building with buildx
- ✅ Package installation and dependency resolution
- ✅ Multi-stage build process execution
- ✅ Image creation and tagging success

**Example:**
```bash
scripts/test-build.sh --mode build "22.5.2"
```

**What happens under the hood:**
1. All config mode validations
2. Calls `docker buildx build` with platform `linux/amd64`
3. Downloads Asterisk source tarball
4. Installs build packages (libicu76, libpqxx-7.10, etc.)
5. Compiles Asterisk with menuselect configuration
6. Creates optimized runtime image with only necessary packages
7. Tags image as `22.5.2_debian-trixie`

**Real Docker commands executed:**
```bash
# Generated Dockerfile gets built with:
docker buildx build \
  --platform linux/amd64 \
  --tag 22.5.2_debian-trixie \
  --file Dockerfile \
  /home/ak/code/asterisk/asterisk/asterisk/22.5.2-trixie/
```

### Validate Mode (Complete End-to-End Testing)

**What it validates:**
- ✅ All build mode validations +
- ✅ **Container startup testing**
- ✅ **Asterisk functionality validation**
- ✅ **Configuration syntax checking**
- ✅ **CLI connectivity testing**
- ✅ **Image optimization analysis**

**Example:**
```bash
scripts/test-build.sh --mode validate "22.5.2"
```

**Detailed validation steps:**

#### 1. Container Startup Test
```bash
docker run --rm 22.5.2_debian-trixie asterisk -V
```
**Expected output:**
```
Asterisk 22.5.2 built by root @ buildnode on a x86_64 running Linux on 2025-09-28 18:00:00 UTC
```

#### 2. Configuration Syntax Validation
```bash
docker run --rm 22.5.2_debian-trixie asterisk -T
```
**What this tests:**
- Parses all configuration files in `/etc/asterisk/`
- Validates syntax without starting Asterisk daemon
- Checks for missing files or syntax errors
- Tests module loading configuration

#### 3. CLI Functionality Test
```bash
docker run --rm 22.5.2_debian-trixie sh -c "asterisk -rx 'core show version'"
```
**What this tests:**
- Basic Asterisk CLI connectivity
- Core module initialization
- Remote console functionality
- Essential service availability

#### 4. Image Optimization Analysis
```bash
# Size validation
docker image inspect 22.5.2_debian-trixie --format '{{.Size}}'

# Layer count analysis
docker image inspect 22.5.2_debian-trixie --format '{{len .RootFS.Layers}}'
```
**Validation criteria:**
- ✅ Image size < 2GB (optimized multi-stage build)
- ✅ Layer count < 50 (efficient Docker layers)
- ✅ No unnecessary build dependencies in final image

## Usage Examples

### Quick Development Testing
```bash
# Test latest version config only (30 seconds)
scripts/test-build.sh --mode config "23.0.0-rc2"

# Test specific version build (5-10 minutes)
scripts/test-build.sh --mode build "22.5.2"
```

### Pattern Matching
```bash
# Test all version 2x releases
scripts/test-build.sh --mode config "2*"
# Matches: 20.15.2, 20.7-cert7, 21.10.2, 22.5.2, 23.0.0-rc2

# Test all certified releases
scripts/test-build.sh --mode config "*cert*"
# Matches: 11.6-cert18, 13.21-cert6, 16.8-cert14, 18.9-cert17, 20.7-cert7
```

### Performance Optimization
```bash
# Parallel testing for faster validation
scripts/test-build.sh --mode config --parallel --max-parallel 5

# All versions with detailed logging
scripts/test-build.sh --mode config --verbose
```

### CI/CD Integration
```bash
# Validate all configs before deployment
scripts/test-build.sh --mode config

# Full validation for release candidates
scripts/test-build.sh --mode validate "23.*"
```

## Real Test Output Examples

### Successful Config Test
```
2025-09-28 18:10:44 [INFO] Initializing Asterisk Docker Build Test System
2025-09-28 18:10:44 [INFO] Test mode: config
2025-09-28 18:10:44 [INFO] Found 23 buildable versions
2025-09-28 18:10:44 [INFO] Filtered to 1 versions matching pattern: 22.5.2

2025-09-28 18:10:44 [INFO] Testing version: 22.5.2 (mode: config)
[INFO]  Build targets:
[INFO]    → debian/trixie (amd64) [from: custom_matrix]
[INFO]  DRY RUN - Would build 1 targets

2025-09-28 18:10:44 [SUCCESS] Version 22.5.2: All tests passed (0s)

=== DETAILED TEST REPORT ===
Test Mode: config
Architecture: amd64
Tested Versions: 1

=== BUILD STATISTICS ===
Total builds: 1
Successful: 1
Failed: 0
Success rate: 100%
```

### Failed Validation Example
```
2025-09-28 18:10:37 [INFO] Testing version: 1.4.44 (mode: config)
[INFO]  Build targets:
[INFO]    → debian/jessie (amd64) [template: debian-jessie-legacy-addons]
[ERROR] Config generation failed for 1.4.44

2025-09-28 18:10:37 [ERROR] Version 1.4.44: Tests failed (0s) - Config generation failed for debian/jessie/amd64

=== BUILD STATISTICS ===
Total builds: 1
Failed: 1
Success rate: 0%

=== FAILED BUILDS ===
[ERROR] FAILED: 1.4.44_1.4.44_amd64 - Config generation failed for debian/jessie/amd64
```

### Complete Validation Report
```bash
scripts/test-build.sh --mode validate "22.5.2" --verbose
```

**Generated Image Report:**
```
=== IMAGE REPORT: 22.5.2_debian-trixie ===
Size: 876.4MB (918425600 bytes)
Created: 2025-09-28
Asterisk Version: Asterisk 22.5.2 built by root @ buildnode
Container Startup: ✅ PASS
Asterisk Functionality: ✅ PASS
Image Optimization: ✅ PASS
```

## Validation Function Details

### `validate_container_startup()`
```bash
timeout 30 docker run --rm IMAGE asterisk -V >/dev/null 2>&1
```
- Tests basic container execution
- Verifies Asterisk binary functionality
- Validates runtime environment setup

### `validate_asterisk_functionality()`
```bash
# Test 1: Version check
docker run --rm IMAGE asterisk -V

# Test 2: Configuration syntax validation
docker run --rm IMAGE asterisk -T

# Test 3: CLI functionality
docker run --rm IMAGE sh -c "asterisk -rx 'core show version'"
```
- Comprehensive Asterisk functionality testing
- Configuration file parsing validation
- CLI and core module verification

### `validate_image_optimization()`
- Size analysis (< 2GB threshold)
- Layer count optimization (< 50 layers)
- Multi-stage build verification
- Runtime dependency validation

## Integration with Build Infrastructure

The test system leverages existing build scripts:

```bash
# Test system calls build-asterisk.sh with specific flags:
/scripts/build-asterisk.sh 22.5.2 debian amd64 \
  --platforms linux/amd64 \
  --dry-run \        # Config mode only
  --force-config \   # Always regenerate
  --verbose          # Detailed logging
```

**File Generation Process:**
1. `configs/asterisk-22.5.2-trixie.yml` → Configuration loaded
2. `templates/debian-trixie.yml.template` → Template resolved
3. `asterisk/22.5.2-trixie/Dockerfile` → Generated
4. `asterisk/22.5.2-trixie/build.sh` → Generated
5. `asterisk/22.5.2-trixie/healthcheck.sh` → Generated

## Troubleshooting

### Common Issues

**No versions found:**
```bash
# Check available versions
python3 -c "
import yaml
with open('asterisk/supported-asterisk-builds.yml') as f:
    data = yaml.safe_load(f)
for build in data['latest_builds']:
    print(build['version'])
"
```

**Docker buildx issues:**
```bash
# Ensure buildx is available
docker buildx version
docker buildx create --use
```

**Template errors:**
```bash
# Test template syntax
python3 -c "
import yaml
template = open('templates/debian-trixie.yml.template').read()
config = template.replace('{{VERSION}}', '22.5.2')
yaml.safe_load(config)
"
```

### Performance Tips

**For frequent testing:**
```bash
# Use config mode for development (fastest)
scripts/test-build.sh --mode config "22.5.2"

# Parallel testing for multiple versions
scripts/test-build.sh --mode config --parallel "2*"
```

**For CI/CD pipelines:**
```bash
# Full validation before releases
scripts/test-build.sh --mode validate
```

**Docker cache optimization:**
```bash
# Clean build cache if needed
docker buildx prune -f
```

## Test System Architecture

### Modular Components

1. **`lib/build-common.sh`** - Shared functions library
   - YAML parsing and version management
   - Docker validation functions
   - Build result tracking and statistics
   - Logging and error handling

2. **`scripts/test-build.sh`** - Main test orchestration
   - Three test modes (config/build/validate)
   - Pattern matching and filtering
   - Parallel processing support
   - Comprehensive reporting

3. **Integration Points:**
   - Leverages `scripts/build-asterisk.sh` infrastructure
   - Uses existing YAML matrix from `asterisk/supported-asterisk-builds.yml`
   - Validates generated configs in `configs/generated/`
   - Tests output in `asterisk/VERSION-DISTRIBUTION/` directories

### Error Prevention Strategy

The test system prevents the GitHub Actions failures we previously encountered:

1. **Silent Python failures** → Comprehensive error reporting with traceback
2. **Configuration generation issues** → Config validation mode
3. **Build process validation** → Actual build testing with timeouts
4. **Container functionality** → Startup and Asterisk CLI testing
5. **Template variable issues** → Template rendering validation

## Future Extensions

The modular design allows easy extension:

- **Security scanning**: Add container vulnerability tests
- **Performance benchmarks**: Measure startup time and resource usage
- **Network testing**: Validate SIP/RTP connectivity
- **Integration tests**: Test with external services
- **Regression testing**: Compare versions for compatibility

---

**Quick Start:**
```bash
# Test your changes quickly
scripts/test-build.sh --mode config "22.5.2"

# Full validation before commit
scripts/test-build.sh --mode validate "22.5.2"

# Test all modern versions
scripts/test-build.sh --mode config "2*" --parallel
```