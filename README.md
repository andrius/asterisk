# Asterisk Docker Images

Modern Docker images for Asterisk PBX with automated builds and optimized for size and performance configurations.

Complete setup examples are available in the [`examples/`](examples/) directory.

> **📝 Legacy Code**: Original code preserved in the [legacy](https://github.com/andrius/asterisk/tree/legacy) branch.

## 📦 Currently Supported Optimized Versions

All the latest asterisk releases are supported (see the [Asterisk Versions page](https://docs.asterisk.org/About-the-Project/Asterisk-Versions/)).

IMPORTANT: Only the latest stable and release candidate versions are actively built and maintained. Due to Asterisk dependencies, we also support complilation on the old and EOL Debian distributions. Be aware of that and possible vulnerabilities when using old distributions!

Currently supported versions as defined in [`asterisk/supported-asterisk-builds.yml`](asterisk/supported-asterisk-builds.yml):

### **Asterisk 22.5.2** (Latest Stable)

- **Debian Trixie** (AMD64)
- **Debian Bookworm** (AMD64)

### **Asterisk 23.0.0-rc2** (Release Candidate)

- **Debian Trixie** (AMD64)

**More versions and distributions coming soon!**

## 🌟 Key Improvements

- **🔄 Automated Release Discovery**: Daily discovery of new Asterisk releases
- **📋 YAML-Driven Configuration**: Template-based build system
- **🏗️ Multi-Stage Builds**: Optimized production-ready images
- **🗄️ Database Integration**: Full PostgreSQL and MySQL support
- **🌐 Modern Features**: WebSocket, ARI, WebRTC, and comprehensive telephony features
- **📦 Multi-Platform Ready**: ARM64 and AMD64 architecture support
- **🔧 Template System**: Jinja2-based Dockerfile generation
- **🧪 Automated Testing**: Health checks and functionality validation

## 📋 Examples

More examples are available in the [`examples/`](examples/) directory.

### Basic Setup ([`examples/basic/`](examples/basic/))

A ready-to-use Docker Compose configuration with:

- **Production-ready Asterisk container** with SIP/RTP port configuration
- **Custom configuration templates** including PJSIP setup
- **Development overrides** for local testing and debugging
- **Volume management** for logs and configuration persistence

```bash
cd examples/basic/
cp docker-compose.override.yml.template docker-compose.override.yml
docker compose up -d
```

The basic example demonstrates proper containerization patterns and provides a starting point for production deployments.

## 🏗️ Architecture Overview

### New Build System

- **Template-Based**: All builds generated from YAML templates
- **Version Discovery**: Automatic detection of new Asterisk releases
- **Multi-Stage Optimization**: Separate builder and runtime environments
- **Package Management**: Distribution-specific dependency resolution
- **Health Monitoring**: Comprehensive container health checks

### Directory Structure

```
.
├── asterisk/                    # Build artifacts (auto-generated)
├── configs/                     # YAML configurations
├── templates/                   # Build templates
│   ├── debian-trixie.yml.template
│   ├── debian-bookworm.yml.template
│   └── dockerfile/              # Jinja2 templates
├── scripts/                     # Build automation
│   ├── build-asterisk.sh       # Main build interface
│   ├── discover-latest-versions.sh
│   └── generate-dockerfile.py
├── lib/                         # Python libraries
└── schema/                      # Validation schemas
```

## 🔄 Automation Features

### Daily Release Discovery

The system automatically:

- 🔍 Scans for new Asterisk releases
- 📝 Updates build matrices
- ⚙️ Generates configurations for new versions
- 🚀 Triggers builds via GitHub Actions

### GitHub Actions Workflows

- **`discover-releases.yml`**: Daily release discovery (20:00 UTC)
- **`build-images.yml`**: Automated multi-platform builds

## 📚 Legacy Support

While focus is on modern optimized versions, the repository maintains compatibility with all the Asterisk versions starting from 1.2, incluging LTS and Certified releases.

## 🛠️ Development

### Template System Architecture

The build system uses a sophisticated template-based approach that automatically selects the appropriate template and distribution for each Asterisk version. Templates handle both package dependencies and feature compatibility across different Asterisk eras.

#### Template Selection Matrix

| Asterisk Version         | Distribution      | Template                       | PJSIP Support | Key Features                 |
| ------------------------ | ----------------- | ------------------------------ | ------------- | ---------------------------- |
| **10.12.4**              | Jessie            | `debian-stretch-asterisk10-11` | ❌ No         | chan_sip only, SSL 1.0.0     |
| **11.25.3, 11.6-cert18** | Jessie            | `debian-buster-asterisk10-11`  | ❌ No         | chan_sip only, pre-PJSIP era |
| **12.8.2**               | Jessie            | `debian-jessie` (standard)     | ✅ Yes        | First PJSIP support          |
| **13.38.3, 13.21-cert6** | Buster            | `debian-buster` (standard)     | ✅ Yes        | Mature PJSIP                 |
| **14.7.8, 15.7.4**       | Buster            | `debian-buster` (standard)     | ✅ Yes        | Enhanced features            |
| **16.30.1**              | Bookworm          | `debian-bookworm` (standard)   | ✅ Yes        | Modern Debian                |
| **16.8-cert14**          | Trixie            | `debian-trixie` (standard)     | ✅ Yes        | Latest Debian                |
| **18.26.4, 18.9-cert17** | Trixie            | `debian-trixie` (standard)     | ✅ Yes        | WebRTC, ARI                  |
| **19.8.1, 20.15.2**      | Trixie            | `debian-trixie` (standard)     | ✅ Yes        | Modern features              |
| **21.10.2**              | Trixie            | `debian-trixie` (standard)     | ✅ Yes        | Latest LTS                   |
| **22.5.2**               | Trixie + Bookworm | `debian-trixie/bookworm`       | ✅ Yes        | Multi-platform               |
| **23.0.0-rc2**           | Trixie            | `debian-trixie` (standard)     | ✅ Yes        | Latest release               |

#### Template Types Explained

##### **1. Standard Templates**

- **Purpose**: Modern Asterisk versions (12+) with full PJSIP support
- **Naming**: `debian-{distribution}.yml.template`
- **Features**: WebRTC, ARI, PJSIP, WebSocket transport
- **Examples**: `debian-trixie.yml.template`, `debian-bookworm.yml.template`

##### **2. Specialized 10-11 Templates**

- **Purpose**: Pre-PJSIP Asterisk versions (10.x, 11.x)
- **Naming**: `debian-{distribution}-asterisk10-11.yml.template`
- **Features**: chan_sip only, no PJSIP modules, legacy compatibility
- **Examples**: `debian-stretch-asterisk10-11.yml.template`, `debian-buster-asterisk10-11.yml.template`

##### **3. Cross-Distribution Compatibility**

The system intelligently maps newer Asterisk feature sets to older distributions:

- **10.12.4** uses Stretch template on Jessie distribution (newer template, older OS)
- **11.25.3** uses Buster template on Jessie distribution (compatibility bridge)

#### Package Version Management

Each template contains hardcoded package versions specific to its target distribution:

| Package Type | Trixie       | Bookworm    | Bullseye    | Buster      | Stretch     | Jessie      |
| ------------ | ------------ | ----------- | ----------- | ----------- | ----------- | ----------- |
| **SSL**      | libssl3      | libssl3     | libssl1.1   | libssl1.1   | libssl1.1   | libssl1.0.0 |
| **ICU**      | libicu76     | libicu72    | libicu67    | libicu63    | libicu57    | libicu52    |
| **PQXX**     | libpqxx-7.10 | libpqxx-6.4 | libpqxx-6.4 | libpqxx-6.2 | libpqxx-4.0 | libpqxx-4.0 |
| **SRTP**     | libsrtp2-1   | libsrtp2-1  | libsrtp2-1  | libsrtp2-1  | libsrtp2-1  | libsrtp0    |
| **NCurses**  | libncurses6  | libncurses6 | libncurses5 | libncurses6 | libncurses5 | libncurses5 |
| **cURL**     | libcurl4     | libcurl4    | libcurl4    | libcurl4    | libcurl4    | libcurl3    |

### Template-Based Development

All modifications must be made through templates:

```bash
# Edit template (ONLY way to make changes)
vim templates/debian-trixie.yml.template

# Regenerate with --force-config
./scripts/build-asterisk.sh 22.5.2 --force-config

# Test build
docker build -t test asterisk/22.5.2-trixie/
```

### Adding New Versions

```bash
# Discover new releases
./scripts/discover-latest-versions.sh --output-yaml --updates-only

# Build newly discovered versions
./scripts/build-asterisk.sh NEW_VERSION
```

### Build an Optimized Image

```bash
# Build Asterisk 22.5.2 on Debian Trixie
./scripts/build-asterisk.sh 22.5.2

# Build specific OS variant
./scripts/build-asterisk.sh 22.5.2 debian bookworm

# Preview what would be built
./scripts/build-asterisk.sh 23.0.0-rc1 --dry-run
```

### Run Container

```bash
# Run latest optimized build
docker run --rm -p 5060:5060/udp asterisk:22.5.2_debian-trixie

# Check Asterisk version
docker run --rm asterisk:22.5.2_debian-trixie asterisk -V
```

## 🎯 Roadmap

### Phase 1: Core Optimization (Current)

- ✅ Modern Asterisk versions
- ✅ Multi-stage build optimization
- ✅ Automated release discovery

### Phase 2: Expansion (Coming Soon)

- 🔄 Alpine Linux support
- 🔄 ARM64 architecture builds
- 🔄 Additional LTS versions (18.x, 20.x)

## 🤝 Contributing

Contributions are welcome! The new system is designed for maintainability:

1. **Template Changes**: Modify templates in `templates/` directory
2. **New Features**: Extend YAML schema and build logic
3. **Version Support**: Add new OS/distribution combinations
4. **Testing**: Enhance validation and health checks

### Development Commands

```bash
# Test template changes
./scripts/build-asterisk.sh VERSION --force-config --verbose

# Validate configurations
python3 scripts/generate-dockerfile.py CONFIG.yml --validate

# Test health checks
docker run --rm IMAGE /usr/local/bin/healthcheck.sh --verbose
```

## 📄 Migration from Legacy

If you were using the original andrius/asterisk images:

### Image Tags

- **Old**: `andrius/asterisk:latest`
- **New**: `andrius/asterisk:22.5.2_debian-trixie`

### Configuration

- **Old**: Manual Dockerfile edits
- **New**: YAML-based configuration system

### Features

- **Enhanced**: Modern Asterisk features (WebRTC, ARI, PJSIP)
- **Optimized**: ~232MB production images vs ~6GB legacy
- **Automated**: Continuous updates and security patches

## 🆘 Support

- **🐛 Issues**: Report bugs via GitHub Issues
- **💬 Discussions**: Community support and questions
- **📖 Documentation**: Detailed guides in the repository
- **🏛️ Legacy**: Reference implementations in `legacy` branch

---

**Status**: 🚧 **Active Development** - Revitalizing abandoned repository with modern automation
