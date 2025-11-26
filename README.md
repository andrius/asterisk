# Asterisk Docker Images

Production-ready Docker images for Asterisk PBX with advanced DRY template system, supporting 24 versions from 1.2.40 to 23.0.0-rc2 plus git development builds.

## Quick Start

```bash
# Use pre-built images from Docker Hub
docker pull andrius/asterisk:latest
docker run --rm -p 5060:5060/udp andrius/asterisk:latest

# Check Asterisk version
docker run --rm andrius/asterisk:latest asterisk -V

# Use specific version for production
docker run --rm -p 5060:5060/udp andrius/asterisk:22.5.2_debian-trixie

# Or build latest stable version locally and run locally built container
./scripts/build-asterisk.sh 22.5.2
docker run --rm -p 5060:5060/udp 22.5.2_debian-trixie

```

Complete examples available in [`examples/`](examples/) directory. Legacy code preserved in [`legacy` branch](https://github.com/andrius/asterisk/tree/legacy).

## 📢 Stay Updated

Get notified about new Asterisk releases and Docker image updates:

### Automated Announcements

- **Telegram**: [Join @asterisk_docker](https://t.me/asterisk_docker) - Instant release notifications
- **Mastodon**: [@andrius_kai@mastodon.social](https://mastodon.social/@andrius_kai) - Federated updates

### Follow for Updates

- **X/Twitter**: [@andrius_kai](https://x.com/andrius_kai) - Release announcements and project news
- **Threads**: [@andrius_kai](https://threads.net/@andrius_kai) - Updates and discussions

### Container Registries

- 🐳 **Docker Hub**: [andrius/asterisk](https://hub.docker.com/r/andrius/asterisk) - Primary registry
- 📦 **GitHub Container Registry**: [ghcr.io/andrius/asterisk](https://github.com/andrius/asterisk/pkgs/container/asterisk) - Alternative registry

New releases are automatically announced on Telegram and Mastodon when builds complete successfully.

## Supported Versions

All supported Asterisk versions with automatic variant detection. Generated build artifacts are placed in `asterisk/VERSION-DIST/` directories (not tracked in git).

| Version | Tags | Distribution | Architectures |
| ------- | ---- | ------------ | ------------- |
| **git** | `testing,git-latest,development` | Trixie | amd64, arm64 |
| **23.1.0** | - | Trixie | amd64, arm64 |
| **23.0.0** | 23 | Trixie | amd64, arm64 |
| **22.7.0** | - | Trixie | amd64, arm64 |
| **22.6.0** | `latest,stable,22` | Trixie | amd64, arm64 |
| **21.12.0** | - | Trixie | amd64, arm64 |
| **21.11.0** | - | Trixie | amd64, arm64 |
| **20.17.0** | - | Trixie | amd64, arm64 |
| **20.16.0** | - | Trixie | amd64, arm64 |
| **20.7-cert7** | - | Trixie | amd64 |
| **19.8.1** | - | Bookworm | amd64 |
| **18.26.4** | - | Trixie | amd64 |
| **17.9.4** | - | Bookworm | amd64 |
| **16.30.1** | - | Bookworm | amd64 |
| **16.8-cert14** | - | Buster | amd64 |
| **15.7.4** | - | Buster | amd64 |
| **14.7.8** | - | Buster | amd64 |
| **13.38.3** | - | Buster | amd64 |
| **13.21-cert6** | - | Buster | amd64 |
| **12.8.2** | - | Jessie | amd64 |
| **11.25.3** | - | Jessie | amd64 |
| **11.6-cert18** | - | Jessie | amd64 |
| **10.12.4** | - | Jessie | amd64 |
| **1.8.32.3** | - | Jessie | amd64 |
| **1.6.2.24** | - | Jessie | amd64 |
| **1.4.44** | - | Jessie | amd64 |
| **1.2.40** | - | Stretch | amd64 |

## Additional Tags

The build system supports semantic Docker tags for easier version management. These tags are defined in the `additional_tags` property of `asterisk/supported-asterisk-builds.yml` and automatically applied during builds.

## Docker Tags Format

This project uses a dual-tagging system: **version-specific tags** in the format `{version}_{os}-{distribution}` (e.g., `22.5.2_debian-trixie`) for precise deployment, and semantic tags (e.g., `latest`, `stable`, `22`, `23-rc`, `20-cert`) for convenient version management.

Primary tags include the full OS and distribution context, while additional semantic tags are defined per version in the build matrix using the additional_tags property. Multi-architecture builds create unified manifests under the same tag names, automatically selecting the correct architecture.

For development, use semantic tags like `asterisk:latest` or `asterisk:stable`, and for production a specific tag like `asterisk:22.5.2_debian-trixie` that guarantee exact version and environment reproducibility.

### Current Tag Meanings

- **`latest`** - Points to the most current stable release (currently **22.5.2**)
- **`stable`** - Alias for the latest stable production version
- **`22`** - Major version tag for the Asterisk 22.x series
- **`23-rc`** - Release candidate tag for Asterisk 23.x pre-releases
- **`testing`** / **`git-latest`** / **`development`** - Latest git HEAD from Asterisk repository
- **`20-cert`** - Certified release tag for Asterisk 20.x certified builds

### Usage Examples

```bash
# Use semantic tags for consistent deployments
docker run --rm -p 5060:5060/udp asterisk:latest

# Target specific release types
docker run --rm asterisk:stable asterisk -V
docker run --rm asterisk:23-rc asterisk -V
docker run --rm asterisk:20-cert asterisk -V

# Major version targeting
docker run --rm asterisk:22 asterisk -V
```

### Configuration

Additional tags are configured per version in the build matrix:

```yaml
# In asterisk/supported-asterisk-builds.yml
latest_builds:
  - version: "22.5.2"
    additional_tags: "latest,stable,22"
    os_matrix:
      - os: "debian"
        distribution: "trixie"
        architectures: ["amd64", "arm64"]
```

When building, both version-specific tags (`22.5.2_debian-trixie`) and semantic tags (`latest`, `stable`, `22`) are created for the same image.

## Key Features

- **DRY Template System**
- **Automatic Variant Detection**: Smart selection based on Asterisk version patterns
- **Version-Specific Module Selection**: Automatic enforcement of chan_sip removal (v21+) and chan_websocket inclusion (v23+)
- **Multi-Stage Builds**: Optimized images (unpacked image size is about 232MB)
- **Daily Release Discovery**: Automated detection and configuration of new Asterisk releases
- **Comprehensive Support**: All Asterisk versions from 1.2.x through 23.x with appropriate OS distributions
- **Modern Features**: PJSIP, WebRTC, ARI, WebSocket transport for compatible versions

## Architecture

### DRY Template System

The build system uses template inheritance to eliminate duplication:

- **Base Templates**: Common packages and Asterisk configuration (37 build + 21 runtime packages)
- **Distribution Layer**: OS-specific package versions (libicu76 for Trixie, libicu72 for Bookworm)
- **Variant Layer**: Version-specific features (modern, asterisk10, legacy-addons)

```
templates/
├── base/                          # Common packages & configuration
│   ├── asterisk-base.yml.template
│   └── common-packages.yml
├── distributions/                 # OS-specific package versions
│   ├── debian-trixie.yml          # libicu76, libpqxx-7.10
│   ├── debian-bookworm.yml        # libicu72, libpqxx-6.4
│   ├── debian-buster.yml          # libicu63, libpqxx-6.2
│   ├── debian-jessie.yml          # libicu52, libpqxx-4.0
│   └── debian-stretch.yml         # libicu57, libpqxx-4.0
├── variants/                      # Version-specific templates
│   ├── modern.yml.template        # Asterisk 12+ with PJSIP
│   ├── asterisk10.yml.template    # Asterisk 1.8-11.x transitional
│   └── legacy-addons.yml.template # Asterisk 1.2-1.6 with addons
├── dockerfile/                    # Jinja2 Dockerfile generation
└── partials/                      # Build scripts & health checks
```

### Automatic Variant Detection

| Version Range | Variant         | Features                          |
| ------------- | --------------- | --------------------------------- |
| 1.2.x - 1.6.x | `legacy-addons` | Separate addons, chan_sip only    |
| 1.8.x - 11.x  | `asterisk10`    | Pre-PJSIP, chan_sip, transitional |
| 12.x+         | `modern`        | PJSIP, WebRTC, ARI, full features |

### Version-Specific Requirements

The build system automatically enforces version-specific module requirements during configuration generation (see `lib/template_generator.py:224` - `_apply_version_overrides()` method):

**Asterisk 21+ (PJSIP-only requirement)**:

- Automatically adds `chan_sip` to the exclude list
- As per [official deprecation](https://www.asterisk.org/asterisk-21-module-removal/), chan_sip was removed in Asterisk 21
- Only `chan_pjsip` is available for SIP communications
- Example: `asterisk/21.10.2-trixie/build.sh:88` contains `menuselect --disable chan_sip`

**Asterisk 23+ and git (WebSocket requirement)**:

- Automatically adds `chan_websocket` to the channels list
- Sets `features.websockets = true` in configuration
- Includes full WebSocket stack: `chan_websocket`, `res_http_websocket`, `res_pjsip_transport_websocket`
- Example: `asterisk/23.0.0-rc2-trixie/build.sh:73` contains `menuselect --enable chan_websocket`

These overrides are applied automatically during ANY config generation:

- `./scripts/regenerate-all-configs.sh` - applies to all 24 versions
- `./scripts/build-asterisk.sh VERSION --force-config` - applies to specific version
- Configuration happens at template merge time (before Dockerfile generation)

**Implementation Details**:

- Only applies to modern versions (Asterisk 12+)
- Git builds treated as latest (version 99 for comparison)
- Integrates seamlessly with DRY template system
- Preserves user customizations in templates while enforcing mandatory requirements

### Project Structure

```
.
├── asterisk/                       # Build artifacts (auto-generated)
├── configs/generated/              # Generated YAML configurations
├── templates/                      # DRY template system
├── scripts/                        # Build automation
│   ├── build-asterisk.sh           # Main build interface
│   ├── generate-config.py          # Config generation
│   └── discover-latest-versions.sh # Release discovery
├── lib/                            # Python libraries
│   ├── template_generator.py       # DRY template engine
│   └── dockerfile_generator.py     # Dockerfile generator
└── schema/                         # Validation schemas
```

## Development

⚠️ **CRITICAL**: This project uses a **template-first architecture**. NEVER edit files in `asterisk/` directories - they are auto-generated and will be overwritten. All changes must go through templates in the `templates/` directory.

### Common Tasks

```bash
# Discover new Asterisk releases
./scripts/discover-latest-versions.sh --output-yaml --updates-only

# Build specific version
./scripts/build-asterisk.sh 22.5.2 --force-config

# Build with specific distribution
./scripts/build-asterisk.sh 22.5.2 debian bookworm

# Preview build without execution
./scripts/build-asterisk.sh 22.5.2 --dry-run

# Test configurations and builds
./scripts/test-build.sh --mode config "22.5.2"   # Fast validation
./scripts/test-build.sh --mode build "22.5.2"    # Full Docker build
./scripts/test-build.sh --mode validate "22.5.2" # Complete testing

# Generate config only
python3 scripts/generate-config.py 22.5.2 trixie
```

### Template Modification

Modify templates based on scope of changes:

```bash
# Base changes (affects all versions)
vim templates/base/common-packages.yml
vim templates/base/asterisk-base.yml.template

# Distribution changes (affects specific OS)
vim templates/distributions/debian-trixie.yml

# Variant changes (affects version ranges)
vim templates/variants/modern.yml.template
```

After template changes, rebuild with `--force-config`:

```bash
./scripts/build-asterisk.sh VERSION --force-config
```

### Testing

```bash
# Validate configuration
python3 scripts/generate-dockerfile.py configs/generated/asterisk-22.5.2-trixie.yml --validate

# Test health check
docker run --rm asterisk:22.5.2_debian-trixie /usr/local/bin/healthcheck.sh --verbose

# Run container with shell
docker run -it --rm asterisk:22.5.2_debian-trixie /bin/bash
```

## Examples

### Basic Setup

```bash
cd examples/basic/
cp docker-compose.override.yml.template docker-compose.override.yml
docker compose up -d
```

The basic example includes:

- Production-ready Asterisk container
- PJSIP configuration templates
- Volume management for persistence
- Development override options

## Contributing

1. Template changes in `templates/` directory
2. New features via YAML schema extension
3. Additional OS/distribution support
4. Test coverage improvements

## GitHub Actions

- **`discover-releases.yml`**: Daily release discovery at 8:00 PM UTC
- **`build-images.yml`**: Automated multi-platform builds

## Support & Community

### Get Help

- 📋 **Issues**: [Report bugs via GitHub Issues](https://github.com/andrius/asterisk/issues)
- 📚 **Documentation**: README.md, README-cicd.md, README-tests.md in repository
- 🏛️ **Legacy Reference**: See [`legacy` branch](https://github.com/andrius/asterisk/tree/legacy)

### Follow & Connect

- 🤖 **Telegram**: [Join @asterisk_docker](https://t.me/asterisk_docker) - Automated release announcements
- 🐘 **Mastodon**: [@andrius_kai@mastodon.social](https://mastodon.social/@andrius_kai)
- 🐦 **X/Twitter**: [@andrius_kai](https://x.com/andrius_kai)
- 🧵 **Threads**: [@andrius_kai](https://threads.net/@andrius_kai)

### Container Images

- 🐳 **Docker Hub**: [andrius/asterisk](https://hub.docker.com/r/andrius/asterisk)
- 📦 **GitHub Container Registry**: [ghcr.io/andrius/asterisk](https://github.com/andrius/asterisk/pkgs/container/asterisk)
