# Git-based Development Asterisk Docker build
# Asterisk git-None on Debian forky
# Generated from YAML configuration - DO NOT EDIT MANUALLY

# ==============================================================================
# STAGE 1: Build Environment
# ==============================================================================
FROM debian:forky AS asterisk-builder

LABEL maintainer="Andrius Kairiukstis <k@andrius.mobi>"
LABEL org.opencontainers.image.title="Asterisk PBX Builder (Git Development)"
LABEL org.opencontainers.image.description="Build stage for Asterisk git-unknown"
LABEL org.opencontainers.image.version="git-unknown"
LABEL org.opencontainers.image.source="https://github.com/asterisk/asterisk"

# Build arguments
ARG GIT_SHA=unknown
ARG JOBS=8
ARG DEBIAN_FRONTEND=noninteractive
ARG TARGETARCH

# Environment variables
ENV GIT_SHA=${GIT_SHA}
ENV DEBIAN_FRONTEND=${DEBIAN_FRONTEND}
ENV TMPDIR="/tmp/asterisk_build"

# Create build directories first
RUN mkdir -p \
    /usr/src/asterisk \
    ${TMPDIR} \
    && chmod 777 ${TMPDIR}

# EOL distribution setup (if needed)
# Install ca-certificates first, then build dependencies
RUN --mount=type=cache,target=/var/lib/apt/lists,id=apt-lists-builder-$TARGETARCH \
    --mount=type=cache,target=/var/cache/apt,id=apt-cache-builder-$TARGETARCH \
    apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && apt-get install -y --no-install-recommends \
        build-essential \autoconf \binutils-dev \curl \file \libcurl4-openssl-dev \libedit-dev \libgsm1-dev \libicu-dev \libjansson-dev \libncurses-dev \libogg-dev \libpopt-dev \libpqxx-dev \libresample1-dev \libspandsp-dev \libspeex-dev \libspeexdsp-dev \libsqlite3-dev \libssl-dev \libtool \libvorbis-dev \libxml2-dev \libxslt1-dev \make \odbcinst \patch \pkg-config \portaudio19-dev \procps \python3-dev \unixodbc \unixodbc-dev \uuid \uuid-dev \xmlstarlet \libsrtp2-dev \git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install git (required for git-based builds)
RUN --mount=type=cache,target=/var/lib/apt/lists,id=apt-lists-git-$TARGETARCH \
    --mount=type=cache,target=/var/cache/apt,id=apt-cache-git-$TARGETARCH \
    apt-get update \
    && apt-get install -y --no-install-recommends git \
    && apt-get clean

# Clone Asterisk source from git repository
WORKDIR /usr/src/asterisk
RUN git clone --depth 1 https://github.com/asterisk/asterisk.git . \
    && GIT_SHA_FULL=$(git rev-parse HEAD) \
    && GIT_SHA_SHORT=$(git rev-parse --short HEAD) \
    && echo "Git SHA: $GIT_SHA_FULL (short: $GIT_SHA_SHORT)" \
    && echo "$GIT_SHA_SHORT" >/usr/src/asterisk/.git_sha

# Copy and run build script
COPY build.sh /usr/src/asterisk/build.sh
RUN chmod +x /usr/src/asterisk/build.sh

# Build Asterisk with git source
RUN --mount=type=cache,target=/tmp/asterisk_build \
    cd /usr/src/asterisk \
    && ./build.sh \
    && make install \
    && make install-logrotate \
    && make basic-pbx \
    && ldconfig

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
LABEL org.opencontainers.image.title="Asterisk PBX (Git Development)"
LABEL org.opencontainers.image.description="Asterisk git-unknown on Debian forky"
LABEL org.opencontainers.image.version="git-unknown"
LABEL org.opencontainers.image.source="https://github.com/asterisk/asterisk"

# Runtime environment
ARG GIT_SHA=unknown
ARG TARGETARCH
ENV GIT_SHA=${GIT_SHA}

# EOL distribution setup (if needed)
# Install runtime dependencies: non-library essentials (explicit) plus the
# shared-library packages auto-derived from the built binaries (builder stage).
COPY --from=asterisk-builder /runtime-lib-deps.txt /tmp/runtime-lib-deps.txt
RUN --mount=type=cache,target=/var/lib/apt/lists,id=apt-lists-runtime-$TARGETARCH \
    --mount=type=cache,target=/var/cache/apt,id=apt-cache-runtime-$TARGETARCH \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        binutils \
        ca-certificates \
        curl \
        gettext-base \
        odbcinst \
        portaudio19-dev \
        procps \
        python3 \
        unixodbc \
        uuid \
        $(cat /tmp/runtime-lib-deps.txt) \
    && rm -f /tmp/runtime-lib-deps.txt \
    && apt-get clean
# Create asterisk user and required directories
RUN groupadd -g 1000 asterisk \
    && useradd -r -u 1000 -g asterisk -d /var/lib/asterisk -s /bin/bash asterisk \
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

# Copy Asterisk from builder stage
COPY --from=asterisk-builder /usr/sbin/asterisk /usr/sbin/asterisk
COPY --from=asterisk-builder /usr/lib/asterisk/ /usr/lib/asterisk/
COPY --from=asterisk-builder /var/lib/asterisk/ /var/lib/asterisk/
COPY --from=asterisk-builder /etc/asterisk/ /etc/asterisk/
COPY --from=asterisk-builder /var/spool/asterisk/ /var/spool/asterisk/
COPY --from=asterisk-builder /var/log/asterisk/ /var/log/asterisk/
COPY --from=asterisk-builder /usr/src/asterisk/.git_sha /var/lib/asterisk/.git_sha

# Copy Asterisk shared libraries
COPY --from=asterisk-builder /usr/lib/libasterisk*.so* /usr/lib/

# Set proper ownership and permissions
RUN chown -R asterisk:asterisk \
    /etc/asterisk \
    /var/lib/asterisk \
    /var/run/asterisk \
    /var/log/asterisk \
    /var/spool/asterisk \
    /usr/lib/asterisk 2>/dev/null || true \
    && chmod -R 750 /var/spool/asterisk

# Copy healthcheck script
COPY healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh

# Copy entrypoint script (PUID/PGID volume permission handling)
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# Runtime verification
RUN asterisk -V || (echo "Error: Unable to run asterisk -V" && exit 1)

# Configure volumes
VOLUME ["/var/lib/asterisk/sounds"]
VOLUME ["/var/lib/asterisk/keys"]
VOLUME ["/var/lib/asterisk/phoneprov"]
VOLUME ["/var/spool/asterisk"]
VOLUME ["/var/log/asterisk"]
VOLUME ["/etc/asterisk"]

# Expose ports
EXPOSE 5060/udp
EXPOSE 5060/tcp
EXPOSE 10000-20000/udp

# Entrypoint runs as root, adapts asterisk uid/gid to PUID/PGID, then execs CMD.
# Asterisk drops privileges itself via `-U asterisk -p` in the CMD below.
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

# Default command
CMD ["/usr/sbin/asterisk", "-f", "-U", "asterisk", "-p"]
