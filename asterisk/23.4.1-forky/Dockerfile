# Multi-stage optimized Asterisk Docker build
# Asterisk 23.4.1 on Debian forky
# Generated from YAML configuration - DO NOT EDIT MANUALLY

# ==============================================================================
# STAGE 1: Build Environment
# ==============================================================================
FROM debian:forky AS asterisk-builder

LABEL maintainer="Andrius Kairiukstis <k@andrius.mobi>"
LABEL org.opencontainers.image.title="Asterisk PBX Builder"
LABEL org.opencontainers.image.description="Build stage for Asterisk 23.4.1"
LABEL org.opencontainers.image.version="23.4.1"
LABEL org.opencontainers.image.source="https://github.com/andrius/asterisk"

# Build arguments
ARG ASTERISK_VERSION=23.4.1
ARG JOBS=8
ARG DEBIAN_FRONTEND=noninteractive
ARG TARGETARCH

# Environment variables
ENV ASTERISK_VERSION=${ASTERISK_VERSION}
ENV DEBIAN_FRONTEND=${DEBIAN_FRONTEND}
ENV TMPDIR="/tmp/asterisk_build"

# Create build directories first
RUN mkdir -p \
    /usr/src/asterisk \
    ${TMPDIR} \
    && chmod 777 ${TMPDIR}

# EOL distribution setup (if needed)
# Update package lists and install ca-certificates first, then build dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && apt-get install -y --no-install-recommends \
        build-essential autoconf binutils-dev curl file libcurl4-openssl-dev \
        libedit-dev libgsm1-dev libicu-dev libjansson-dev libncurses-dev libogg-dev \
        libpopt-dev libpqxx-dev libresample1-dev libspandsp-dev libspeex-dev \
        libspeexdsp-dev libsqlite3-dev libssl-dev libtool libvorbis-dev libxml2-dev \
        libxslt1-dev make odbcinst patch pkg-config portaudio19-dev procps \
        python3-dev unixodbc unixodbc-dev uuid uuid-dev xmlstarlet libsrtp2-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p ${TMPDIR} && chmod 777 ${TMPDIR}


WORKDIR /usr/src/asterisk

# Download and extract Asterisk source
RUN curl -fsSL https://downloads.asterisk.org/pub/telephony/asterisk/releases/asterisk-23.4.1.tar.gz \
    | tar --strip-components=1 -xz


# Configure Asterisk build (skip for very old versions that don't have configure script)
RUN ./configure

# Generate menuselect configuration
RUN make menuselect/menuselect menuselect-tree menuselect.makeopts


# Copy and execute build script
COPY build.sh /usr/src/asterisk/build.sh
RUN chmod +x build.sh && ./build.sh

# Derive exact runtime shared-library packages from the freshly built binaries.
# ldd lists the full transitive closure of linked libraries; each resolved .so
# is mapped to its owning Debian package via dpkg-query. This keeps the runtime
# image correct on rolling/experimental suites (e.g. forky) where SONAME-
# versioned package names drift (libicuNN, libpqxx-N.N, the t64 transition, ...).
RUN set -eu; \
    { ldd /usr/sbin/asterisk || true; \
      for f in /usr/lib/libasterisk*.so*; do [ -e "$f" ] && ldd "$f" || true; done; \
      find /usr/lib/asterisk/modules -name '*.so' -exec ldd {} \; 2>/dev/null || true; \
    } 2>/dev/null \
    | awk '/=> \// { print $3 } /^[[:space:]]*\// { print $1 }' \
    | grep -E '^/' \
    | while read -r lib; do readlink -f "$lib" 2>/dev/null || true; done \
    | sort -u \
    | xargs -r dpkg-query -S 2>/dev/null \
    | cut -d: -f1 \
    | tr ',' '\n' \
    | sed 's/^[[:space:]]*//; s/[[:space:]]*$//' \
    | grep -E '^[a-z0-9][a-z0-9+.-]+$' \
    | sort -u > /runtime-lib-deps.txt; \
    echo "== Derived runtime library packages =="; cat /runtime-lib-deps.txt; \
    test -s /runtime-lib-deps.txt
# ==============================================================================
# STAGE 2: Runtime Environment
# ==============================================================================
FROM debian:forky AS asterisk-runtime

LABEL maintainer="Andrius Kairiukstis <k@andrius.mobi>"
LABEL org.opencontainers.image.title="Asterisk PBX Runtime"
LABEL org.opencontainers.image.description="Runtime environment for Asterisk 23.4.1"

ARG DEBIAN_FRONTEND=noninteractive
ARG TARGETARCH
ENV DEBIAN_FRONTEND=${DEBIAN_FRONTEND}

# Install runtime dependencies: non-library essentials (explicit) plus the
# shared-library packages auto-derived from the built binaries (builder stage).
COPY --from=asterisk-builder /runtime-lib-deps.txt /tmp/runtime-lib-deps.txt
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        binutils ca-certificates curl gettext-base odbcinst portaudio19-dev procps \
        python3 unixodbc uuid \
        $(cat /tmp/runtime-lib-deps.txt) \
    && rm -f /tmp/runtime-lib-deps.txt \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create asterisk user and required directories
RUN useradd --uid 1000 --system --user-group \
    --home-dir /home/asterisk --create-home \
    asterisk \
    && mkdir -p \
        /var/run/asterisk \
        /var/log/asterisk \
        /var/spool/asterisk/monitor \
        /var/spool/asterisk/outgoing \
        /var/spool/asterisk/tmp \
        /var/spool/asterisk/voicemail \
        /var/spool/asterisk/fax \
        /var/lib/asterisk/keys \
        /var/lib/asterisk/phoneprov \
        /var/lib/asterisk/sounds \
        /var/lib/asterisk/docs

# ==============================================================================
# STAGE 3: Final Production Image
# ==============================================================================
FROM asterisk-runtime AS asterisk-production

LABEL maintainer="Andrius Kairiukstis <k@andrius.mobi>"
LABEL org.opencontainers.image.title="Asterisk PBX"
LABEL org.opencontainers.image.description="Production Asterisk PBX 23.4.1"
LABEL org.opencontainers.image.version="23.4.1"
LABEL org.opencontainers.image.source="https://github.com/andrius/asterisk"
LABEL org.opencontainers.image.vendor="Andrius Kairiukstis <k@andrius.mobi>"

# Copy Asterisk binaries and configurations from builder
COPY --from=asterisk-builder /usr/sbin/asterisk /usr/sbin/asterisk
COPY --from=asterisk-builder /usr/lib/asterisk /usr/lib/asterisk
COPY --from=asterisk-builder /var/lib/asterisk /var/lib/asterisk
COPY --from=asterisk-builder /etc/asterisk /etc/asterisk

# Copy Asterisk shared libraries
COPY --from=asterisk-builder /usr/lib/libasterisk*.so* /usr/lib/

# Copy healthcheck script
COPY healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh

# Copy entrypoint script (PUID/PGID volume permission handling)
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Set proper ownership and permissions
RUN chown -R asterisk:asterisk \
    /etc/asterisk \
    /home/asterisk \
    /var/*/asterisk \
    /usr/lib*/asterisk 2>/dev/null || true \
    && chmod -R 750 /var/spool/asterisk

# Runtime verification
RUN asterisk -V || (echo "Error: Unable to run asterisk -V" && exit 1)

# Configure networking
# EXPOSE 5060/udp
# EXPOSE 5060/tcp
# EXPOSE 5061/tcp
# EXPOSE 10000-10099/udp

# Define volumes for persistent data
VOLUME ["/var/lib/asterisk/sounds", "/var/lib/asterisk/keys", "/var/lib/asterisk/phoneprov", "/var/spool/asterisk", "/var/log/asterisk", "/etc/asterisk"]

# Add health check
HEALTHCHECK --interval=30s \
    --timeout=10s \
    --start-period=30s \
    --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

# Entrypoint runs as root, adapts asterisk uid/gid to PUID/PGID, then execs CMD.
# Asterisk drops privileges itself via `-U asterisk -p` in the CMD below.
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Set working directory
WORKDIR /home/asterisk

# Default command with production settings
CMD ["/usr/sbin/asterisk", "-vvvdddf", "-T", "-W", "-U", "asterisk", "-p"]
