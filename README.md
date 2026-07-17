# Asterisk Docker Images

Production-ready Docker images for Asterisk PBX with advanced DRY template system, supporting 24 versions from 1.2.40 to 23.4.1 plus git development builds.

## Quick Start

```bash
# Use pre-built images from Docker Hub
docker pull andrius/asterisk:latest
docker run --rm -p 5060:5060/udp andrius/asterisk:latest

# Check Asterisk version
docker run --rm andrius/asterisk:latest asterisk -V

# Use specific version for production
docker run --rm -p 5060:5060/udp andrius/asterisk:22.10.1_debian-trixie

# Or build latest stable version locally and run locally built container
./scripts/build-asterisk.sh 22.10.1
docker run --rm -p 5060:5060/udp 22.10.1_debian-trixie

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

All supported Asterisk versions with automatic variant detection. Generated build artifacts are placed in `asterisk/VERSION-DIST/` directories (auto-generated - never edit by hand).

| Version | Tags | Distribution | Architectures |
| ------- | ---- | ------------ | ------------- |
| **git** | `testing,dev` | Trixie | amd64, arm64 |
| **git** | experimental-git | Forky | amd64, arm64 |
| **git** | `testing,dev` | Edge | amd64, arm64 |
| **23.4.1** | 23 | Trixie | amd64, arm64 |
| **23.4.1** | experimental | Forky | amd64, arm64 |
| **23.4.1** | 23 | 3.24 | amd64, arm64 |
| **23.4.1** | 23 | Edge | amd64, arm64 |
| **22.10.1** | `latest,stable,22` | Trixie | amd64, arm64 |
| **22.10.1** | `latest,stable,22` | 3.24 | amd64, arm64 |
| **22.10.1** | `latest,stable,22` | Edge | amd64, arm64 |
| **22.8-cert3** | 22-cert | Trixie | amd64, arm64 |
| **22.8-cert3** | 22-cert | 3.24 | amd64, arm64 |
| **21.12.3** | 21 | Trixie | amd64, arm64 |
| **20.20.1** | 20 | Trixie | amd64, arm64 |
| **20.20.1** | 20 | 3.24 | amd64, arm64 |
| **20.7-cert11** | 20-cert | Trixie | amd64, arm64 |
| **19.8.1** | 19 | Bookworm | amd64 |
| **18.26.4** | 18 | Trixie | amd64 |
| **18.9-cert18** | 18-cert | Trixie | amd64, arm64 |
| **17.9.4** | 17 | Bookworm | amd64 |
| **16.30.1** | 16 | Bookworm | amd64 |
| **16.8-cert14** | 16-cert | Buster | amd64 |
| **15.7.4** | 15 | Buster | amd64 |
| **14.7.8** | 14 | Buster | amd64 |
| **13.38.3** | 13 | Buster | amd64 |
| **13.21-cert6** | 13-cert | Buster | amd64 |
| **12.8.2** | 12 | Jessie | amd64 |
| **11.25.3** | 11 | Jessie | amd64 |
| **11.6-cert18** | 11-cert | Jessie | amd64 |
| **10.12.4** | 10 | Jessie | amd64 |
| **1.8.32.3** | 1.8 | Jessie | amd64 |
| **1.8.32.3** | 1.8 | 3.24 | amd64 |
| **1.6.2.24** | 1.6 | Jessie | amd64 |
| **1.6.2.24** | 1.6 | 3.24 | amd64 |
| **1.4.44** | 1.4 | Jessie | amd64 |
| **1.2.40** | 1.2 | Stretch | amd64 |

## Deprecated Versions

These versions are no longer built but kept here for historical reference. Existing images remain in the registries until manually pruned.

| Version | Deprecated | Superseded by |
| ------- | ---------- | ------------- |
| **23.3.0** | 2026-07-04 | `23.4.1` |
| **22.9.0** | 2026-07-04 | `22.10.1` |
| **22.8-cert2** | 2026-07-04 | `22.8-cert3` |
| **21.12.2** | 2026-07-04 | `21.12.3` |
| **20.19.0** | 2026-07-04 | `20.20.1` |
| **20.7-cert10** | 2026-07-04 | `20.7-cert11` |
| **23.2.2** | 2026-05-04 | `23.3.0` |
| **23.2.0** | 2026-05-04 | `23.3.0` |
| **23.1.0** | 2026-05-04 | `23.3.0` |
| **22.8.2** | 2026-05-04 | `22.9.0` |
| **22.8-cert1** | 2026-05-04 | `22.8-cert2` |
| **22.8.0** | 2026-05-04 | `22.9.0` |
| **22.7.0** | 2026-05-04 | `22.9.0` |
| **21.12.1** | 2026-05-04 | `21.12.2` |
| **21.12.0** | 2026-05-04 | `21.12.2` |
| **20.18.2** | 2026-05-04 | `20.19.0` |
| **20.18.0** | 2026-05-04 | `20.19.0` |
| **20.17.0** | 2026-05-04 | `20.19.0` |
| **20.7-cert9** | 2026-05-04 | `20.7-cert10` |
| **20.7-cert8** | 2026-05-04 | `20.7-cert10` |
| **20.7-cert7** | 2026-05-04 | `20.7-cert10` |
| **18.9-cert17** | 2026-05-04 | `18.9-cert18` |


## Additional Tags

The build system supports semantic Docker tags for easier version management. These tags are defined in the `additional_tags` property of `asterisk/supported-asterisk-builds.yml` and automatically applied during builds.

Tag placement is managed automatically. When a new release is discovered, the release PR moves each line's semantic tags to the newest version and marks the predecessor with `superseded_by` (it stays buildable during review). Once the PR merges, `finalize-deprecations.yml` stamps `deprecated_at`, which removes the old version from the build matrix. Deprecation never deletes published images or tags.

## Docker Tags Format

This project uses a dual-tagging system: **version-specific tags** in the format `{version}_{os}-{distribution}` (e.g., `22.10.1_debian-trixie`) for precise deployment, and semantic tags (e.g., `latest`, `stable`, `22`, `23`, `20-cert`) for convenient version management.

Primary tags include the full OS and distribution context, while additional semantic tags are defined per version in the build matrix using the additional_tags property. Multi-architecture builds create unified manifests under the same tag names, automatically selecting the correct architecture.

For development, use semantic tags like `andrius/asterisk:latest` or `andrius/asterisk:stable`, and for production a specific tag like `andrius/asterisk:22.10.1_debian-trixie` that guarantees exact version and environment reproducibility.

### Current Tag Meanings

- **`latest`** - Newest release of the current LTS (even-numbered) major - currently Asterisk 22. The newer Standard major (23) never takes `latest`; it moves only when a newer LTS line becomes active.
- **`stable`** - Alias for `latest`
- **`22`**, **`23`**, **`21`**, **`20`**, ... - Major version tags, each pointing at the newest release of that series
- **`20-cert`** / **`22-cert`** - Certified release tags, newest certified build of that major
- **`testing`** / **`dev`** - Latest git HEAD from the Asterisk repository
- **`experimental`** - Latest stable Asterisk built on Debian Forky (Debian 14, currently testing). Refreshed weekly. Never carries the plain major tag. **Not for production** - Forky's package set is still moving.
- **`experimental-git`** - Asterisk git tip built on Debian Forky. Same caveats as `experimental`.

### Usage Examples

```bash
# Use semantic tags for consistent deployments
docker run --rm -p 5060:5060/udp andrius/asterisk:latest

# Target specific release types
docker run --rm andrius/asterisk:stable asterisk -V
docker run --rm andrius/asterisk:23 asterisk -V
docker run --rm andrius/asterisk:20-cert asterisk -V

# Major version targeting
docker run --rm andrius/asterisk:22 asterisk -V
```

### Configuration

Additional tags are configured per version in the build matrix:

```yaml
# In asterisk/supported-asterisk-builds.yml
latest_builds:
  - version: "22.10.1"
    additional_tags: "latest,stable,22"
    os_matrix:
      - os: "debian"
        distribution: "trixie"
        architectures: ["amd64", "arm64"]
```

When building, both version-specific tags (`22.10.1_debian-trixie`) and semantic tags (`latest`, `stable`, `22`) are created for the same image.

## Alpine Images

Alongside the Debian images, an **Alpine (musl) image family** is published. These are much smaller (~70 MB vs ~230 MB) and, unlike the Debian images, are **not compiled here** - they install prebuilt, signed Asterisk `apk` packages from the sibling project [`andrius/asterisk-alpine`](https://github.com/andrius/asterisk-alpine)'s public Cloudsmith repository. Whatever that project publishes gets an image, for whatever Asterisk versions, Alpine releases, and architectures it publishes it on (open-source Opus is available on arm64 too, unlike Debian's amd64-only Digium blob).

```bash
# Newest LTS Asterisk on the current stable Alpine
docker run --rm andrius/asterisk:alpine asterisk -V

# A line, or an exact version, on the stable Alpine tree
docker run --rm andrius/asterisk:22-alpine asterisk -V
docker run --rm andrius/asterisk:22-cert-alpine asterisk -V

# Fully pinned (immutable) - exact Asterisk + exact Alpine, for reproducible deploys
docker run --rm andrius/asterisk:22.10.1-alpine-3.24 asterisk -V
```

The Alpine images share the same runtime UX as Debian: the PUID/PGID entrypoint, the healthcheck, the `-U asterisk` privilege drop, and `ASTERISK_TERMINAL_OPTS` all behave identically (`bash`, `shadow`, and `procps` are installed for parity). The in-container `asterisk` user is normalized to uid/gid `1000` with home `/home/asterisk`, matching the Debian image.

### Alpine tag lattice

Alpine tags cross two axes: the **Asterisk identity** (the `{line}` token like `22` or `22-cert`, and the full `{version}` like `22.10.1` or `22.8-cert3`) and the **Alpine identity** (implicit, minted only for the current stable Alpine tree, or explicit `-{alpine}` like `-3.24` / `-edge`). Gating the implicit tags to the stable tree is what lets `edge` coexist without stealing the generic tags.

| Tag pattern | Example | Meaning |
| ----------- | ------- | ------- |
| `alpine` | `alpine` | Newest LTS Asterisk on the current stable Alpine (the Alpine twin of `latest`) |
| `stable-alpine` | `stable-alpine` | Alias for `alpine` |
| `{line}-alpine` | `22-alpine`, `22-cert-alpine` | Newest release of that line on the **stable** Alpine tree |
| `{version}-alpine` | `22.10.1-alpine`, `22.8-cert3-alpine` | That exact Asterisk version on the stable Alpine tree |
| `{line}-alpine-{alpine}` | `22-alpine-3.24`, `22-alpine-edge` | That line pinned to a specific Alpine release |
| `{version}-alpine-{alpine}` | `22.10.1-alpine-3.24` | Fully pinned: exact Asterisk + exact Alpine (immutable) |
| `stable-alpine-{alpine}` | `stable-alpine-3.24` | The LTS latest-owner pinned to a specific Alpine release |
| `git-alpine` / `testing-alpine` / `dev-alpine` | | Asterisk git master on Alpine `edge` (bleeding edge) |

The `{version}_{os}-{distribution}` underscore twin (`22.10.1_alpine-3.24`) is published for every Alpine leg too, matching the Debian convention. Explicit `-{alpine}` tags are always minted; the unsuffixed twins (`22-alpine`, `alpine`) ride only the current stable Alpine tree, so when a new Alpine stable is released the generic tags follow it automatically and the previous one keeps its `-{alpine}`-suffixed tags.

### How Alpine versions stay current

A daily `alpine-sync` workflow probes the Cloudsmith index and opens a consolidated PR that mirrors the live picture into the build matrix: the exact `apk` pin per line, the subpackages that line actually ships, and the architectures it is built on. When the sibling publishes a new Asterisk `apk` or bumps the Alpine base, the change lands in a sync PR (and the sibling can push it in near-real-time via a repository dispatch). A new Asterisk release therefore ships on Debian on day 0 and on Alpine once the sibling publishes the `apk`; the lag is visible in the sync PR, never silent, and the last-good Alpine image keeps rebuilding meanwhile.

## Volume Permissions (PUID / PGID)

Bind-mounted host directories often have a UID/GID different from the in-container `asterisk` user (default `1000:1000`), which prevents Asterisk from writing to them. Images for Asterisk **10.x and newer** (including `git`) ship an entrypoint that adapts the in-container `asterisk` user to whatever UID/GID you supply via `PUID` / `PGID` environment variables and chowns the runtime directories before Asterisk starts.

```bash
# Bind-mount host paths, hand the container the host UID/GID
docker run -d \
  -e PUID=$(id -u) \
  -e PGID=$(id -g) \
  -v $PWD/etc-asterisk:/etc/asterisk \
  -v $PWD/var-lib-asterisk:/var/lib/asterisk \
  -v $PWD/var-log-asterisk:/var/log/asterisk \
  -v $PWD/var-spool-asterisk:/var/spool/asterisk \
  andrius/asterisk:latest
```

```yaml
# compose.yml
services:
  asterisk:
    image: andrius/asterisk:latest
    environment:
      PUID: 1000
      PGID: 1000
    volumes:
      - ./etc-asterisk:/etc/asterisk
      - ./var-lib-asterisk:/var/lib/asterisk
      - ./var-log-asterisk:/var/log/asterisk
      - ./var-spool-asterisk:/var/spool/asterisk
```

The entrypoint:

- Runs as root, calls `groupmod`/`usermod` to set the asterisk uid/gid to `PUID:PGID` (defaults `1000:1000`), then `chown -R` on `/etc/asterisk`, `/home/asterisk`, `/var/lib/asterisk`, `/var/log/asterisk`, `/var/spool/asterisk`, `/var/run/asterisk`. Asterisk then drops privileges itself via its `-U asterisk -p` CMD flags - no `gosu`/`su-exec` needed.
- If you already pin a UID via `--user N:M` (compose `user:`), the entrypoint detects it is non-root and skips chowning, matching the pre-entrypoint behaviour. In that case make sure host volumes are pre-chown'd to the matching UID.
- Pre-10.x images (1.2.x - 1.8.x) keep the original behaviour: no entrypoint, fixed UID 1000. Pre-chown host volumes (`chown -R 1000:1000 ./asterisk-config`) or use named volumes.

## CLI Background Color (`ASTERISK_TERMINAL_OPTS`)

The default CMD includes `-W` (light-background adjust). On dark terminals this can render some output black-on-dark and become unreadable. Override via the `ASTERISK_TERMINAL_OPTS` env var on Asterisk **10.x and newer**:

| Env value                       | Effect                                                |
| ------------------------------- | ----------------------------------------------------- |
| (unset)                         | Keep `-W` (existing behaviour, light-bg)              |
| `ASTERISK_TERMINAL_OPTS=""`     | Drop `-W`, let the terminal decide                    |
| `ASTERISK_TERMINAL_OPTS="-B"`   | Force black background (best for dark terminals)      |
| `ASTERISK_TERMINAL_OPTS="-n"`   | Disable colors entirely (safest for log shipping)     |

```yaml
services:
  asterisk:
    image: andrius/asterisk:23
    environment:
      ASTERISK_TERMINAL_OPTS: "-B"   # or "-n" for no color, "" to drop -W
```

The entrypoint replaces the `-W` token in the CMD with whatever you supply (space-separated multiple flags allowed). Useful for `docker logs` legibility too - colour escape codes in log output often look broken; `-n` strips them.

## Networking for SIP / UDP

By default Docker uses bridge networking, which NATs the container behind the host's IP. For UDP-based SIP that breaks AOR matching and trunk registration: the upstream side sees `172.x.x.x` as the source and the responses never make it back to the container. Symptoms include "no reply to our critical packet", `Retransmission timeout reached`, and registration that flaps every minute.

**For real SIP traffic, run the container with host networking** so the asterisk process binds the host's interfaces directly:

```bash
docker run -d --network host andrius/asterisk:23
```

```yaml
# compose.yml
services:
  asterisk:
    image: andrius/asterisk:23
    network_mode: "host"
```

Host networking is Linux-only (Docker Desktop on Mac/Windows treats it as a no-op). For multi-node Swarm, `examples/docker-swarm/` documents the trade-off between overlay/VIP networking (simple, but rewrites SIP source IPs) and host-mode (recommended).

If you must use bridge networking, you'll need to:

1. Publish 5060/udp + 5060/tcp + 5061/tcp + a sane RTP port range (`-p 10000-10199:10000-10199/udp`).
2. Set `external_media_address` and `external_signaling_address` in PJSIP transport config (or `externip` / `localnet` for chan_sip).
3. Match the published RTP range in `rtp.conf` (`rtpstart` / `rtpend`).

Don't publish more than ~1000 UDP ports through Docker's userland-proxy - it will become the bottleneck. Either narrow the RTP range or switch to host networking.

## Config Templating with `envsubst`

`envsubst` (from `gettext-base`) ships in every runtime image, so you can drop `*.conf.template` files into `/etc/asterisk/` and render them from environment variables at container start without rebuilding.

Template (`pjsip.conf.template`):

```ini
[transport-udp]
type=transport
protocol=udp
bind=0.0.0.0:5060
external_media_address=${EXTERNAL_IP}
external_signaling_address=${EXTERNAL_IP}
```

Custom entrypoint that renders templates first, then chains the image's default entrypoint:

```bash
#!/bin/bash
set -e
for tpl in /etc/asterisk/*.template; do
  [ -e "$tpl" ] || continue
  envsubst < "$tpl" > "${tpl%.template}"
done
exec /usr/local/bin/entrypoint.sh "$@"
```

Run it:

```bash
docker run -d \
  -e EXTERNAL_IP=203.0.113.42 \
  -v $PWD/pjsip.conf.template:/etc/asterisk/pjsip.conf.template \
  -v $PWD/render-and-start.sh:/usr/local/bin/render-and-start.sh:ro \
  --entrypoint /usr/local/bin/render-and-start.sh \
  andrius/asterisk:23
```

`envsubst` only substitutes plain `${VAR}` / `$VAR` references - bash parameter expansions (`${VAR%-*}`, `${VAR:-default}`) are not supported. Use `envsubst '${VAR1} ${VAR2}'` to allow-list variables and avoid accidental substitution.

## Key Features

- **DRY Template System**
- **Automatic Variant Detection**: Smart selection based on Asterisk version patterns
- **Version-Specific Module Selection**: Automatic enforcement of chan_sip removal (v21+) and chan_websocket inclusion (v23+)
- **Multi-Stage Builds**: Optimized images (unpacked image size is about 232MB)
- **Daily Release Discovery**: Automated detection and configuration of new Asterisk releases
- **Comprehensive Support**: All Asterisk versions from 1.2.x through 23.x with appropriate OS distributions
- **Modern Features**: PJSIP, WebRTC, ARI, WebSocket transport for compatible versions
- **Opus Codec Support**: Digium binary Opus codec automatically included for Asterisk 20+ on x86_64 (arm64 supports Opus passthrough)
- **PUID/PGID Volume Permissions**: Asterisk 10.x+ images adapt the asterisk user UID/GID at startup so bind-mounted host directories work without manual `chown`
- **Config Templating**: `envsubst` ships in every runtime image - drop `*.conf.template` files into `/etc/asterisk` and render from env vars without rebuilding
- **Configurable Terminal Colors**: `ASTERISK_TERMINAL_OPTS` env var on v10+ images swaps the baked-in `-W` for `-B` (dark bg), `-n` (no color), or empty
- **Supply-Chain Integrity**: every release tarball is downloaded and verified against a pinned `sha256` (`tarball_sha256` in `supported-asterisk-builds.yml`); new releases get their checksum pinned automatically at discovery time. Git builds clone at a recorded SHA (already content-addressed).

## Architecture

### DRY Template System

The build system uses template inheritance to eliminate duplication:

- **Base Templates**: Common packages and Asterisk configuration (37 build + 21 runtime packages)
- **Distribution Layer**: OS-specific package versions (libicu78 for Forky, libicu76 for Trixie, libicu72 for Bookworm)
- **Variant Layer**: Version-specific features (modern, asterisk-11, legacy, legacy-addons, git-dev)

```
templates/
├── base/                          # Common packages & configuration
│   ├── asterisk-base.yml.template
│   └── common-packages.yml
├── distributions/                 # OS-specific package versions
│   ├── debian-forky.yml           # experimental; runtime libs auto-derived (ldd+dpkg)
│   ├── debian-trixie.yml          # libicu76, libpqxx-7.10
│   ├── debian-bookworm.yml        # libicu72, libpqxx-6.4
│   ├── debian-buster.yml          # libicu63, libpqxx-6.2
│   ├── debian-jessie.yml          # libicu52, libpqxx-4.0
│   └── debian-stretch.yml         # libicu57, libpqxx-4.0
├── variants/                      # Version-specific templates
│   ├── modern.yml.template        # Asterisk 12+ with PJSIP
│   ├── asterisk-11.yml.template   # Asterisk 11.x transitional
│   ├── legacy.yml.template        # Asterisk 1.8-10.x pre-PJSIP
│   ├── legacy-addons.yml.template # Asterisk 1.2-1.6 with addons
│   └── git-dev.yml.template       # git development builds
├── dockerfile/                    # Jinja2 Dockerfile generation
└── partials/                      # Build scripts & health checks
```

### Automatic Variant Detection

| Version Range | Variant         | Features                          |
| ------------- | --------------- | --------------------------------- |
| 1.2.x - 1.6.x | `legacy-addons` | Separate addons, chan_sip only    |
| 1.8.x - 10.x  | `legacy`        | Pre-PJSIP, chan_sip               |
| 11.x          | `asterisk-11`   | Pre-PJSIP, chan_sip, transitional |
| 12.x+         | `modern`        | PJSIP, WebRTC, ARI, full features |

### Version-Specific Requirements

The build system automatically enforces version-specific module requirements during configuration generation (see `lib/template_generator.py:247` - `_apply_version_overrides()` method):

**Asterisk 21+ (PJSIP-only requirement)**:

- Automatically adds `chan_sip` to the exclude list
- As per [official deprecation](https://www.asterisk.org/asterisk-21-module-removal/), chan_sip was removed in Asterisk 21
- Only `chan_pjsip` is available for SIP communications
- Example: `asterisk/21.12.3-trixie/build.sh:96` contains `menuselect --disable chan_sip`

**Asterisk 23+ and git (WebSocket requirement)**:

- Automatically adds `chan_websocket` to the channels list
- Sets `features.websockets = true` in configuration
- Includes full WebSocket stack: `chan_websocket`, `res_http_websocket`, `res_pjsip_transport_websocket`
- Example: `asterisk/23.4.1-trixie/build.sh:81` contains `menuselect --enable chan_websocket`

**Asterisk 20+ (Opus codec)**:

- Automatically downloads and installs Digium binary Opus codec at build time
- Provides `codec_opus.so` (transcoding) and `format_ogg_opus.so` (OGG Opus file support)
- x86_64/amd64 only - Digium does not provide arm64 binaries
- arm64 images include `res_format_attr_opus.so` for Opus passthrough (no transcoding)
- Version capped at Asterisk 23 codec URL (latest available from Digium)

These overrides are applied automatically during ANY config generation:

- `./scripts/regenerate-all-configs.sh` - applies to all active versions
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
./scripts/build-asterisk.sh 22.10.1 --force-config

# Build with specific distribution
./scripts/build-asterisk.sh 19.8.1 debian bookworm

# Preview build without execution
./scripts/build-asterisk.sh 22.10.1 --dry-run

# Test configurations and builds
./scripts/test-build.sh --mode config "22.10.1"   # Fast validation
./scripts/test-build.sh --mode build "22.10.1"    # Full Docker build
./scripts/test-build.sh --mode validate "22.10.1" # Complete testing

# Generate config only
python3 scripts/generate-config.py 22.10.1 trixie
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
# Run the Python unit tests (lib/ and scripts/)
python3 -m pytest tests/

# Validate configuration
python3 scripts/generate-dockerfile.py configs/generated/asterisk-22.10.1-trixie.yml --validate

# Test health check (image name as produced by a local build)
docker run --rm 22.10.1_debian-trixie /usr/local/bin/healthcheck.sh --verbose

# Run container with shell
docker run -it --rm 22.10.1_debian-trixie /bin/bash
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

A fleet of workflows automates discovery, builds, tag lifecycle, and announcements - see [README-cicd.md](README-cicd.md) for the full pipeline. Key ones:

- **`discover-releases.yml`**: Daily release discovery at 8:00 PM UTC; opens a consolidated PR and promotes semantic tags
- **`finalize-deprecations.yml`**: Stamps `deprecated_at` when a release PR merges (two-phase deprecation)
- **`build-images.yml`** / **`build-single-image.yml`**: Automated multi-platform builds
- **`build-batch-*.yml`**: Weekly rebuild rotation (Mon-Fri, includes the Friday forky/experimental refresh)
- **`build-git-daily.yml`**: Daily git-HEAD build at 6:00 PM UTC
- **`test.yml`**: pytest suite for `lib/` and `scripts/`
- **`update-readme-versions.yml`**: Regenerates the version tables in this README

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
