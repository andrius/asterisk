# GitHub Workflows Documentation

## 🎯 Overview

This repository implements an automated Asterisk release discovery and Docker image build system using GitHub Actions. The system features a **per-release branch strategy** that creates individual branches and pull requests for each new Asterisk version, enabling granular review and deployment control.

### Key Features

- **🔍 Automated Discovery**: Daily scanning for new Asterisk releases from downloads.asterisk.org
- **🌿 Per-Release Branches**: Individual `asterisk-{VERSION}` branches for each new release
- **🚫 Collision Detection**: Prevents duplicate branches and PRs
- **🏗️ Matrix Building**: Automated Docker image generation across multiple architectures
- **🧪 Local Testing**: Comprehensive testing with `nektos/act`

## 🏗️ Workflow Architecture

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   discover-releases │───▶│   build-images       │───▶│  build-single-image │
│   (Daily @ 20:00)   │    │   (Manual/On-demand) │    │  (Reusable)         │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
         │                           │                           │
         ▼                           ▼                           ▼
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│ Per-release PRs     │    │ Matrix generation    │    │ Individual builds   │
│ asterisk-22.6.0     │    │ Multi-arch support   │    │ Docker image output │
│ asterisk-23.0.0     │    │ Filtered building    │    │ Health checks       │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
```

## 🎨 Per-Release Branch Strategy

### Concept

Instead of creating bulk PRs with multiple versions, the system creates **one branch per Asterisk release**:

- **Branch naming**: `asterisk-{VERSION}`
- **Individual PRs**: Each version gets its own review process
- **Collision detection**: Skips versions with existing branches
- **Granular control**: Independent merge/close decisions

### Example Scenarios

#### Scenario 1: Multiple New Releases
```bash
# Discovery finds: 22.6.0, 23.0.0, 24.0.0-rc1
# Result: 3 separate branches and PRs

✅ Created: asterisk-22.6.0    → PR #123 "Add Asterisk 22.6.0 (Stable Release)"
✅ Created: asterisk-23.0.0    → PR #124 "Add Asterisk 23.0.0 (Stable Release)"
✅ Created: asterisk-24.0.0-rc1 → PR #125 "Add Asterisk 24.0.0-rc1 (Release Candidate)"

# Maintainer can:
# - Merge 22.6.0 + 23.0.0 immediately (stable)
# - Hold 24.0.0-rc1 for testing (RC)
```

#### Scenario 2: Collision Prevention
```bash
# Discovery finds: 22.6.0, 23.0.0, 24.0.0-rc1
# Existing branches: asterisk-22.6.0, asterisk-24.0.0-rc1

⏭️ Skipped: 22.6.0 (branch asterisk-22.6.0 already exists)
✅ Created: asterisk-23.0.0 → PR #126
⏭️ Skipped: 24.0.0-rc1 (branch asterisk-24.0.0-rc1 already exists)

# Result: Only 1 new PR created, no duplicate work
```

#### Scenario 3: Version Evolution
```bash
# Day 1: 24.0.0-rc1 discovered
✅ Created: asterisk-24.0.0-rc1 → PR #127 (under review)

# Day 5: 24.0.0 final released
✅ Created: asterisk-24.0.0 → PR #128 (new PR)

# Available options:
# - Close PR #127 (superseded by final)
# - Merge PR #128 (stable release)
```

## 📋 Workflow Details

### 1. discover-releases.yml

**Purpose**: Automated discovery of new Asterisk releases with per-release branch creation.

**Triggers**:
- **Schedule**: Daily at 20:00 UTC (`0 20 * * *`)
- **Manual**: `workflow_dispatch` (no inputs required)
- **Push**: Changes to workflow files or discovery scripts

**Process**:
1. **Fetch releases**: Updates `asterisk-releases.txt` and `asterisk-certified-releases.txt`
2. **Generate YAML**: Creates `supported-asterisk-builds.yml` with `--updates-only` flag
3. **Extract versions**: Parses `git diff` to find new versions in supported builds
4. **Process individually**: For each new version:
   - Check branch collision (local + remote)
   - Create `asterisk-{VERSION}` branch if available
   - Generate version-specific commit and PR
5. **Handle release lists**: Direct commit to main for metadata-only updates

**Outputs**:
- Individual branches: `asterisk-22.6.0`, `asterisk-23.0.0`, etc.
- Individual PRs with version-specific descriptions
- Updated release metadata files

### 2. build-images.yml

**Purpose**: Matrix-based building of Docker images for supported Asterisk versions.

**Triggers**:
- **Manual**: `workflow_dispatch` with filtering options

**Inputs**:
```yaml
push: false                    # Push to registry
registry: "docker.io/andrius/asterisk"  # Target registry
max_parallel: "5"             # Concurrent builds
filter_version: "22.5.2"      # Build specific version
filter_distribution: "trixie" # Build specific distribution
```

**Process**:
1. **Validate branch**: Ensures running on `main` branch
2. **Generate matrix**: Parses `asterisk/supported-asterisk-builds.yml`
3. **Filter matrix**: Applies version/distribution filters
4. **Build images**: Calls `build-single-image.yml` for each configuration
5. **Generate report**: Comprehensive build status summary

### 3. build-single-image.yml

**Purpose**: Reusable workflow for building individual Asterisk Docker images.

**Triggers**:
- **Workflow call**: From `build-images.yml`
- **Manual**: `workflow_dispatch` for testing

**Inputs**:
```yaml
version: "22.5.2"              # Asterisk version
distribution: "trixie"         # OS distribution
architecture: "amd64"          # Target architecture
additional_tags: "latest,stable,22.x"  # Additional Docker tags (comma-separated)
push: false                    # Push to registry
registry: "test.local/asterisk" # Target registry
```

**Process**:
1. **Validate config**: Checks `configs/generated/asterisk-{VERSION}-{DISTRIBUTION}.yml`
2. **Generate Dockerfile**: Uses Jinja2 templates from configuration
3. **Generate healthcheck**: Creates container health monitoring script
4. **Build image**: Multi-stage Docker build with buildx
5. **Test image**: Smoke tests (version check, healthcheck validation)
6. **Report results**: Image size, tags, build status

### 4. Git Version Support

**Purpose**: Build Docker images from latest Asterisk development repository.

**Usage**:
```bash
# Build from git HEAD (local)
./scripts/build-asterisk.sh --git trixie

# Build and push git version
./scripts/build-asterisk.sh --git trixie --push --registry myregistry.com/asterisk
```

**Git Version Format**: `git-{SHA}` (e.g., `git-ff80666`)

**Process**:
1. **Fetch latest SHA**: Gets current HEAD from https://github.com/asterisk/asterisk.git
2. **Generate config**: Creates `asterisk-git-master-{distribution}.yml` configuration
3. **Build image**: Uses git-dev template variant for development builds
4. **Tag image**: Creates `git-{SHA}_debian-{distribution}` tagged image

**Git Workflow Integration**:
- Git builds use special `git-dev` template with development-focused configuration
- Automatic SHA detection ensures build reproducibility
- Generated configs are automatically regenerated for each build

### 5. Additional Tags Support

**Purpose**: Apply semantic tags to Docker images for easier version management.

**Configuration**: Add `additional_tags` property to version entries in `asterisk/supported-asterisk-builds.yml`:

```yaml
latest_builds:
  - version: "22.5.2"
    additional_tags: "latest,stable,22"
    os_matrix:
      - os: "debian"
        distribution: "trixie"
        architectures: ["amd64", "arm64"]
```

**Tag Types**:
- **`latest`**: Points to the most current stable release
- **`stable`**: Alias for the latest stable production version
- **`22`**: Major version tag for Asterisk 22.x series
- **`23-rc`**: Release candidate tag for pre-releases
- **`20-cert`**: Certified release tag for certified builds

**Workflow Integration**:
- Additional tags are extracted during matrix generation
- Tags flow through build pipeline to Docker buildx
- Registry prefixing applied automatically for all tags

## 🧪 Testing with nektos/act

### Setup

#### Install nektos/act
```bash
# macOS
brew install act

# Ubuntu/Debian
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# As GitHub CLI extension
gh extension install nektos/gh-act
```

#### Verify Installation
```bash
gh act --help
# Should show comprehensive help output
```

### Test Payloads

The repository includes pre-configured test payloads in `.act/payloads/`:

```
.act/payloads/
├── workflow_dispatch_discover_releases.json     # Test release discovery
├── workflow_dispatch_build_images.json          # Test matrix building
├── workflow_dispatch_build_single_image.json    # Test single image build
├── workflow_call_build_single_image.json        # Test workflow call
├── push_trigger.json                            # Test push triggers
└── test_new_releases.json                       # Test new release simulation
```

### Testing Procedures

#### 1. Validate All Workflows
```bash
# Syntax validation
gh act --validate

# Expected output:
# time="..." level=info msg="Using docker host ..."
# (No error messages = all workflows valid)
```

#### 2. Test Individual Workflows

**Discover Releases Workflow**:
```bash
# Dry run (validation only)
gh act workflow_dispatch \
  -W .github/workflows/discover-releases.yml \
  -e .act/payloads/workflow_dispatch_discover_releases.json \
  --dryrun

# Expected: All steps succeed, no actual changes made
```

**Build Images Workflow**:
```bash
# Test matrix generation
gh act workflow_dispatch \
  -W .github/workflows/build-images.yml \
  -e .act/payloads/workflow_dispatch_build_images.json \
  --dryrun

# Expected: Matrix generation succeeds, build jobs configured
```

**Build Single Image Workflow**:
```bash
# Test single build
gh act workflow_dispatch \
  -W .github/workflows/build-single-image.yml \
  -e .act/payloads/workflow_dispatch_build_single_image.json \
  --dryrun

# Expected: Config validation, Dockerfile generation, build steps
```

#### 3. Comprehensive Test Suite

**Run All Tests**:
```bash
# Execute comprehensive test suite
./.act/test-workflows.sh

# Expected output:
# 🧪 Testing all workflows with nektos/act...
# 📋 Testing discover-releases workflow...
# 🏗️ Testing build-images workflow...
# 🔨 Testing build-single-image workflow...
# 📤 Testing push triggers...
# ✅ Validating workflow syntax...
# ✅ All workflow tests completed successfully!
```

#### 4. Debug Specific Issues

**Verbose Testing**:
```bash
# Detailed debugging output
gh act workflow_dispatch \
  -W .github/workflows/discover-releases.yml \
  -e .act/payloads/workflow_dispatch_discover_releases.json \
  --dryrun \
  --verbose

# Shows detailed step execution and environment setup
```

**Test Specific Job**:
```bash
# Test only matrix preparation job
gh act workflow_dispatch \
  -W .github/workflows/build-images.yml \
  -e .act/payloads/workflow_dispatch_build_images.json \
  --dryrun \
  -j prepare-matrix

# Isolates specific job for debugging
```

### Common Testing Scenarios

#### Test New Release Detection
```bash
# Simulate new releases being found
gh act workflow_dispatch \
  -W .github/workflows/discover-releases.yml \
  -e .act/payloads/test_new_releases.json \
  --dryrun

# Check output for version extraction and processing logic
```

#### Test Build Filtering
```bash
# Test specific version building
gh act workflow_dispatch \
  -W .github/workflows/build-images.yml \
  -e .act/payloads/workflow_dispatch_build_images.json \
  --dryrun \
  --env FILTER_VERSION="22.5.2"

# Verifies filtering logic works correctly
```

#### Test Additional Tags Support
```bash
# Test build with additional tags
gh act workflow_dispatch \
  -W .github/workflows/build-single-image.yml \
  -e .act/payloads/workflow_dispatch_build_single_image.json \
  --dryrun \
  --env ADDITIONAL_TAGS="latest,stable,22.x"

# Verify tags are processed and applied correctly
```

#### Test Git Version Builds
```bash
# Test git build functionality (local)
./scripts/build-asterisk.sh --git trixie --dry-run

# Expected output: git-{SHA} version detection and build setup
```

## 🚀 Usage Examples

### Manual Workflow Triggers

#### Trigger Release Discovery
```bash
# Manual release discovery run
gh workflow run discover-releases.yml

# Check run status
gh run list --workflow=discover-releases.yml
```

#### Build Specific Version
```bash
# Build single version
gh workflow run build-images.yml \
  -f filter_version="23.0.0" \
  -f push=false

# Build with push to registry
gh workflow run build-images.yml \
  -f filter_version="22.5.2" \
  -f filter_distribution="trixie" \
  -f push=true \
  -f registry="your-registry.com/asterisk"
```

#### Test Single Image Build
```bash
# Test individual image build
gh workflow run build-single-image.yml \
  -f version="22.5.2" \
  -f distribution="trixie" \
  -f architecture="amd64" \
  -f push=false

# Test build with additional tags
gh workflow run build-single-image.yml \
  -f version="22.5.2" \
  -f distribution="trixie" \
  -f architecture="amd64" \
  -f additional_tags="latest,stable,22.x" \
  -f push=true \
  -f registry="your-registry.com/asterisk"
```

### Interpreting Results

#### Successful Discovery Run
```
✅ New Releases Found!
- 🔀 Action: Created individual Pull Requests per release
- 🎯 Impact: New buildable Asterisk versions detected
- 📊 Versions: 22.6.0 23.0.0 24.0.0-rc1
- ⚙️ Next: Review and merge individual PRs to enable building
```

#### No New Releases
```
ℹ️ No Changes
- 🔀 Action: No updates needed
- 📊 Status: All release data is current
```

#### Partial Processing (Collision Detection)
```
🔄 Processing new versions: 22.6.0 23.0.0
⏭️ Skipping 22.6.0 - branch asterisk-22.6.0 already exists
✅ Branch asterisk-23.0.0 available - creating PR for 23.0.0
📊 Summary:
  - New versions found: 2
  - PRs created: 1
  - Skipped (branch exists): 1
```

## 🔧 Maintenance and Development

### Modifying Workflows Safely

#### 1. Test Changes Locally First
```bash
# Always test workflow changes with act before committing
gh act --validate

# Test specific workflow
gh act workflow_dispatch \
  -W .github/workflows/modified-workflow.yml \
  -e .act/payloads/test-payload.json \
  --dryrun
```

#### 2. Update Test Payloads
When modifying workflow inputs, update corresponding payload files:
```bash
# Edit payload files to match new input schema
vi .act/payloads/workflow_dispatch_build_images.json

# Test with updated payload
gh act workflow_dispatch \
  -W .github/workflows/build-images.yml \
  -e .act/payloads/workflow_dispatch_build_images.json \
  --dryrun
```

#### 3. Validate Before Deployment
```bash
# Run comprehensive test suite before merging
./.act/test-workflows.sh

# Ensure all workflows still pass validation
gh act --validate
```

### Best Practices

#### Workflow Development
- **Always use `--dryrun` during development**
- **Test all trigger conditions** (workflow_dispatch, push, schedule)
- **Validate JSON payloads** before committing
- **Use verbose output** (`--verbose`) for debugging

#### Payload Management
- **Keep payloads realistic** (use actual version numbers, valid distributions)
- **Test edge cases** (empty inputs, invalid versions)
- **Document payload purpose** in comments

#### Testing Strategy
- **Local first**: Test with act before GitHub
- **Incremental**: Test individual jobs with `-j` flag
- **Comprehensive**: Run full test suite before releases

### Troubleshooting

#### Common Issues

**Workflow Validation Fails**:
```bash
# Check YAML syntax
gh act --validate

# Look for indentation, quotes, or structure issues
# Fix and re-test
```

**Job Fails in Dry Run**:
```bash
# Run with verbose output
gh act workflow_dispatch \
  -W .github/workflows/problematic-workflow.yml \
  -e .act/payloads/test-payload.json \
  --dryrun \
  --verbose

# Check for missing dependencies, invalid paths, or logic errors
```

**Matrix Job Issues**:
```bash
# Test matrix generation separately
gh act workflow_dispatch \
  -W .github/workflows/build-images.yml \
  -e .act/payloads/workflow_dispatch_build_images.json \
  --dryrun \
  -j prepare-matrix

# Verify supported-asterisk-builds.yml parsing
```

**Path Issues**:
```bash
# Verify working directories and file paths
# Check that referenced scripts and files exist
ls -la scripts/
ls -la asterisk/
ls -la configs/generated/
```

#### Debug Environment Variables
```bash
# Print all available environment variables
gh act workflow_dispatch \
  -W .github/workflows/discover-releases.yml \
  -e .act/payloads/workflow_dispatch_discover_releases.json \
  --dryrun \
  --env DEBUG=true \
  --verbose
```

## 📚 Integration Points

### With Build System
- **Template Integration**: Workflows use templates from `templates/` directory
- **Configuration Driven**: All builds based on YAML configurations
- **Script Dependencies**: Relies on `scripts/` for core functionality

### With Repository Structure
- **Release Data**: Updates `asterisk/` directory files
- **Generated Configs**: Uses `configs/generated/` for build specifications
- **Template Processing**: Integrates with Jinja2 template system

### With External Services
- **downloads.asterisk.org**: Source of release information
- **Docker Registry**: Target for built images
- **GitHub API**: For PR creation and management

---

## 🎯 Quick Start

1. **Install nektos/act**: `gh extension install nektos/gh-act`
2. **Validate workflows**: `gh act --validate`
3. **Run test suite**: `./.act/test-workflows.sh`
4. **Test specific workflow**: `gh act workflow_dispatch -W .github/workflows/discover-releases.yml -e .act/payloads/workflow_dispatch_discover_releases.json --dryrun`

For questions or issues, consult the troubleshooting section or examine the comprehensive test outputs provided by the act testing framework.