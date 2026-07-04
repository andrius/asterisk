# GitHub Workflows Documentation

## 🎯 Overview

This repository implements an automated Asterisk release discovery and Docker image build system using GitHub Actions. The system features a **consolidated release PR strategy**: each discovery run collects every new Asterisk version into a single `asterisk-new-releases` branch and pull request, together with automatic semantic-tag promotion and two-phase deprecation of superseded versions.

### Key Features

- **🔍 Automated Discovery**: Daily scanning for new Asterisk releases from downloads.asterisk.org
- **🌿 Consolidated Release PR**: One `asterisk-new-releases` branch/PR carrying all newly discovered versions
- **🏷️ Tag Lifecycle**: Semantic tags (`latest`, `stable`, majors, certs) move automatically; superseded versions are deprecated in two phases
- **🏗️ Matrix Building**: Automated Docker image generation across multiple architectures
- **🧪 Local Testing**: Comprehensive testing with `nektos/act`, plus a pytest suite for `lib/` and `scripts/`

## 🏗️ Workflow Architecture

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   discover-releases │───▶│   build-images       │───▶│  build-single-image │
│   (Daily @ 20:00)   │    │   (Manual/On-demand) │    │  (Reusable)         │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
         │                           │                           │
         ▼                           ▼                           ▼
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│ Consolidated PR     │    │ Matrix generation    │    │ Individual builds   │
│ asterisk-new-       │    │ Multi-arch support   │    │ Docker image output │
│ releases branch     │    │ Filtered building    │    │ Health checks       │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
```

## 🎨 Consolidated Release PR Strategy

### Concept

Each discovery run gathers **all** newly found Asterisk versions into a single branch and PR:

- **Branch naming**: `asterisk-new-releases` (deleted and recreated on each run with fresh content)
- **One PR per run**: New versions, their generated configs/Dockerfiles, README table updates, and tag-lifecycle changes are reviewed together
- **Tag promotion**: `scripts/apply-tag-lifecycle.py --phase pr` moves each line's semantic tags to its newest release and marks predecessors with `superseded_by`
- **Two-phase deprecation**: superseded versions stay buildable while the PR is open; on merge, `finalize-deprecations.yml` stamps `deprecated_at` and the build matrix drops them

### Example

```bash
# Discovery finds: 22.10.1, 23.4.1
# Result: one branch, one PR

✅ Branch: asterisk-new-releases
✅ PR: consolidated "New Asterisk releases" PR containing
   - configs + Dockerfiles generated for both versions
   - latest,stable,22 moved to 22.10.1; 23 moved to 23.4.1
   - 22.9.0 / 23.3.0 marked superseded_by (deprecated_at stamped on merge)
   - README Supported/Deprecated tables regenerated
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
2. **Generate YAML**: Updates `supported-asterisk-builds.yml` with `--updates-only` flag
3. **Promote tags**: Runs `scripts/apply-tag-lifecycle.py --phase pr` (moves semantic tags, sets `superseded_by`) and regenerates the README version tables
4. **Generate artifacts**: Configs and Dockerfiles for every new version (fails loudly if any generation fails)
5. **Open PR**: Recreates the `asterisk-new-releases` branch and opens one consolidated PR

**Outputs**:
- One consolidated PR listing all new versions and tag movements
- Updated release metadata, build matrix, README tables, and generated build artifacts

### 2. build-images.yml

**Purpose**: Matrix-based building of Docker images for supported Asterisk versions.

**Triggers**:
- **Manual**: `workflow_dispatch` with filtering options

**Inputs** (defaults shown):
```yaml
push: true                    # Push to registry
registry: "andrius/asterisk"  # Target registry
max_parallel: "25"            # Concurrent builds (1/5/25/50)
filter_version: ""            # Build specific version, e.g. "22.10.1"
filter_distribution: ""       # Build specific distribution, e.g. "trixie"
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

**Inputs** (defaults shown; version/distribution required):
```yaml
version: "22.10.1"             # Asterisk version
distribution: "trixie"         # OS distribution
architectures: "amd64"         # Target architectures (comma-separated: amd64,arm64)
additional_tags: ""            # Additional Docker tags, e.g. "latest,stable,22"
push: false                    # Push to registry
registry: "andrius/asterisk"   # Target registry
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
  - version: "22.10.1"
    additional_tags: "latest,stable,22"
    os_matrix:
      - os: "debian"
        distribution: "trixie"
        architectures: ["amd64", "arm64"]
```

**Tag Types**:
- **`latest`**: Newest release of the current LTS (even-numbered) major - the newer Standard major never takes `latest`
- **`stable`**: Alias for `latest`
- **`22`**, **`23`**, ...: Major version tags, newest release of that series
- **`20-cert`** / **`22-cert`**: Certified release tags
- **`experimental`** / **`experimental-git`**: Forky-built images (latest stable + git tip on Debian 14 testing). Refreshed weekly; never carry the plain major tag; not for production.

Tags are managed by the tag-lifecycle automation (see section 7) - manual edits to `additional_tags` are normally not needed.

**Per-entry Override**: A matrix entry can override the version-level `additional_tags` so the same Asterisk version on different distributions gets different short aliases. Example:

```yaml
- version: "23.4.1"
  additional_tags: "23"            # default - applies to trixie entry
  os_matrix:
    - os: "debian"
      distribution: "trixie"
      architectures: ["amd64", "arm64"]
    - os: "debian"
      distribution: "forky"
      architectures: ["amd64", "arm64"]
      additional_tags: "experimental"   # override - forky alone gets :experimental
```

**Workflow Integration**:
- Additional tags are extracted during matrix generation
- Tags flow through build pipeline to Docker buildx
- Registry prefixing applied automatically for all tags

### 6. Scheduled Batch Builds

**Purpose**: Periodic rebuilds of supported Asterisk versions, split across the week so each batch fits within the GitHub Actions concurrency budget.

| Workflow | Schedule (UTC) | Versions | Filter |
|---|---|---|---|
| `build-batch-monday.yml` | Mon 08:00 | Legacy 1.x-10.x | `version-pattern: '^(1\.[2468]\.\|10\.)'` |
| `build-batch-tuesday.yml` | Tue 08:00 | 11.x-19.x | `version-pattern: '^1[1-9]\.'` |
| `build-batch-wednesday.yml` | Wed 08:00 | 20.x-23.x | `version-pattern: '^2[0-3]\.'` |
| `build-batch-thursday.yml` | Thu 08:00 | Certified releases | `version-pattern: 'cert'` |
| `build-batch-friday.yml` | **Fri 08:00** | **Latest stable + git on Forky** | **`filter-distribution: forky`** |
| `build-git-daily.yml` | Daily 18:00 | git tip | n/a |
| `discover-releases.yml` | Daily 20:00 | n/a | scans for new upstream releases |

Each batch workflow shares a common pattern: it calls the reusable `./.github/actions/generate-build-matrix` action with a `version-pattern` (or `filter-distribution` for forky) and then fans out to `build-single-image.yml`. Matrix generation skips deprecated versions automatically.

The Friday/forky batch builds only the latest stable Asterisk minor (currently 23.4.1) and the git tip on Debian Forky (Debian 14, currently testing). It tags those images as `experimental` and `experimental-git` respectively so users opt-in deliberately.

### 7. Tag Lifecycle & Two-Phase Deprecation

Semantic tags and deprecations are managed automatically from `asterisk/supported-asterisk-builds.yml`:

- **PR phase** (`discover-releases.yml` → `scripts/apply-tag-lifecycle.py --phase pr`): moves each line's semantic tags (`latest`/`stable` on the newest active LTS major, bare major tags, `NN-cert`, member-level `experimental`) to the newest release and sets `superseded_by` on predecessors. Superseded versions remain buildable while the PR is under review.
- **Finalize phase** (`finalize-deprecations.yml`, triggered by pushes to `asterisk/supported-asterisk-builds.yml` on main): stamps `deprecated_at` on every entry that has `superseded_by` but no date, then regenerates the README tables and commits with `[skip ci]`. `generate-build-matrix` excludes any entry with `deprecated_at`.
- Deprecation stops future builds only - published images and tags are never deleted.
- The pure planning logic lives in `lib/tag_lifecycle.py`; `scripts/apply-tag-lifecycle.py` supports `--check` and `--dry-run` for local inspection.
- `finalize-deprecations.yml` and `update-readme-versions.yml` share the `main-yaml-writer` concurrency group to serialize pushes to main.

### 8. Supporting Workflows

| Workflow | Trigger | Purpose |
|---|---|---|
| `build-new-releases.yml` | PR / push to main touching the build matrix | Builds newly added versions (dev builds on PR, full builds on merge) |
| `finalize-deprecations.yml` | push to main (build matrix) | Two-phase deprecation, see section 7 |
| `update-readme-versions.yml` | push to main (build matrix) + manual | Regenerates the README Supported/Deprecated tables |
| `test.yml` | push/PR touching `lib/`, `scripts/`, `tests/` | pytest suite (tag lifecycle + README updater) |
| `validate-generation.yml` | PR touching version files | Verifies every active version has config + Dockerfile artifacts |
| `announce-releases.yml` | called by `build-new-releases.yml` / manual | Telegram + Mastodon announcements, pushes `announced-<version>` git tags |
| `test-reusable-action.yml` | manual | Exercises the `build-asterisk-image` composite action |

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
  --env FILTER_VERSION="22.10.1"

# Verifies filtering logic works correctly
```

#### Test Additional Tags Support
```bash
# Test build with additional tags
gh act workflow_dispatch \
  -W .github/workflows/build-single-image.yml \
  -e .act/payloads/workflow_dispatch_build_single_image.json \
  --dryrun \
  --env ADDITIONAL_TAGS="latest,stable,22"

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
  -f filter_version="23.4.1" \
  -f push=false

# Build with push to registry
gh workflow run build-images.yml \
  -f filter_version="22.10.1" \
  -f filter_distribution="trixie" \
  -f push=true \
  -f registry="your-registry.com/asterisk"
```

#### Test Single Image Build
```bash
# Test individual image build
gh workflow run build-single-image.yml \
  -f version="22.10.1" \
  -f distribution="trixie" \
  -f architectures="amd64" \
  -f push=false

# Test build with additional tags
gh workflow run build-single-image.yml \
  -f version="22.10.1" \
  -f distribution="trixie" \
  -f architectures="amd64" \
  -f additional_tags="latest,stable,22" \
  -f push=true \
  -f registry="your-registry.com/asterisk"
```

### Interpreting Results

#### Successful Discovery Run
```
### Asterisk Updates Detected
- 🔀 Action: Created consolidated Pull Request
- 🎯 Branch: asterisk-new-releases
- 📦 New Versions: 22.10.1 23.4.1
- ⚙️ Next: Review and merge the consolidated PR to enable building
```

#### No New Releases
```
ℹ️ No Changes
- 🔀 Action: No updates needed
- 📊 Status: All release data is current
```

#### Release Lists Refreshed (no new buildable versions)
```
📝 Release Lists Updated
- 📊 Impact: Release lists refreshed, no new buildable versions
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