# Asterisk Docker Images

Production-ready Docker images for Asterisk PBX with advanced DRY template system, supporting 23 versions from 1.2.40 to 23.0.0-rc2.

## Quick Start

```bash
# Build latest stable version
./scripts/build-asterisk.sh 22.5.2

# Run container with version-specific tag
docker run --rm -p 5060:5060/udp asterisk:22.5.2_debian-trixie

# Run container with semantic tag (if built with additional_tags)
docker run --rm -p 5060:5060/udp asterisk:latest

# Check Asterisk version
docker run --rm asterisk:latest asterisk -V
```

Complete examples available in [`examples/`](examples/) directory. Legacy code preserved in [`legacy` branch](https://github.com/andrius/asterisk/tree/legacy).

## Supported Versions

All 23 Asterisk versions with automatic variant detection. Build directories contain generated Dockerfiles and configurations.

| Version         | Type              | Distribution | Architectures | Additional Tags    | Build Directory                                                  |
| --------------- | ----------------- | ------------ | ------------- | ------------------ | ---------------------------------------------------------------- |
| **23.0.0-rc2**  | Release Candidate | Trixie       | amd64, arm64  | `23-rc`            | [asterisk/23.0.0-rc2-trixie](./asterisk/23.0.0-rc2-trixie)       |
| **22.5.2**      | Current Stable    | Trixie       | amd64, arm64  | `latest,stable,22` | [asterisk/22.5.2-trixie](./asterisk/22.5.2-trixie)               |
| **21.10.2**     | LTS               | Trixie       | amd64, arm64  | -                  | [asterisk/21.10.2-trixie](./asterisk/21.10.2-trixie)             |
| **20.15.2**     | Previous Stable   | Trixie       | amd64, arm64  | -                  | [asterisk/20.15.2-trixie](./asterisk/20.15.2-trixie)             |
| **20.7-cert7**  | Certified         | Trixie       | amd64, arm64  | `20-cert`          | [asterisk/20.7-cert7-trixie](./asterisk/20.7-cert7-trixie)       |
| **19.8.1**      | Legacy Stable     | Bookworm     | amd64         | -                  | [asterisk/19.8.1-bookworm](./asterisk/19.8.1-bookworm)           |
| **18.26.4**     | LTS               | Trixie       | amd64         | -                  | [asterisk/18.26.4-trixie](./asterisk/18.26.4-trixie)             |
| **18.9-cert17** | LTS Certified     | Trixie       | amd64         | -                  | [asterisk/18.9-cert17-trixie](./asterisk/18.9-cert17-trixie)     |
| **17.9.4**      | Legacy            | Bookworm     | amd64         | -                  | [asterisk/17.9.4-bookworm](./asterisk/17.9.4-bookworm)           |
| **16.30.1**     | Legacy LTS        | Bookworm     | amd64         | -                  | [asterisk/16.30.1-bookworm](./asterisk/16.30.1-bookworm)         |
| **16.8-cert14** | LTS Certified     | Bookworm     | amd64         | -                  | [asterisk/16.8-cert14-bookworm](./asterisk/16.8-cert14-bookworm) |
| **15.7.4**      | Legacy            | Buster       | amd64         | -                  | [asterisk/15.7.4-buster](./asterisk/15.7.4-buster)               |
| **14.7.8**      | Legacy            | Buster       | amd64         | -                  | [asterisk/14.7.8-buster](./asterisk/14.7.8-buster)               |
| **13.38.3**     | Legacy LTS        | Buster       | amd64         | -                  | [asterisk/13.38.3-buster](./asterisk/13.38.3-buster)             |
| **13.21-cert6** | LTS Certified     | Buster       | amd64         | -                  | [asterisk/13.21-cert6-buster](./asterisk/13.21-cert6-buster)     |
| **12.8.2**      | Legacy            | Jessie       | amd64         | -                  | [asterisk/12.8.2-jessie](./asterisk/12.8.2-jessie)               |
| **11.25.3**     | Legacy LTS        | Jessie       | amd64         | -                  | [asterisk/11.25.3-jessie](./asterisk/11.25.3-jessie)             |
| **11.6-cert18** | LTS Certified     | Jessie       | amd64         | -                  | [asterisk/11.6-cert18-jessie](./asterisk/11.6-cert18-jessie)     |
| **10.12.4**     | Legacy            | Jessie       | amd64         | -                  | [asterisk/10.12.4-jessie](./asterisk/10.12.4-jessie)             |
| **1.8.32.3**    | Historical        | Jessie       | amd64         | -                  | [asterisk/1.8.32.3-jessie](./asterisk/1.8.32.3-jessie)           |
| **1.6.2.24**    | Historical        | Jessie       | amd64         | -                  | [asterisk/1.6.2.24-jessie](./asterisk/1.6.2.24-jessie)           |
| **1.4.44**      | Historical        | Jessie       | amd64         | -                  | [asterisk/1.4.44-jessie](./asterisk/1.4.44-jessie)               |
| **1.2.40**      | Historical        | Stretch      | amd64         | -                  | [asterisk/1.2.40-stretch](./asterisk/1.2.40-stretch)             |

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

## Support

- **Issues**: [Report via GitHub Issues](https://github.com/andrius/asterisk/issues)
- **Documentation**: Available in repository
- **Legacy Reference**: See [`legacy` branch](https://github.com/andrius/asterisk/tree/legacy)
