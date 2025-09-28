# Git-based Development Asterisk Docker build
# Asterisk git-ff80666 on Debian trixie
# Generated from YAML configuration - DO NOT EDIT MANUALLY

# ==============================================================================
# STAGE 1: Build Environment
# ==============================================================================
FROM debian:trixie AS asterisk-builder

LABEL maintainer="Andrius Kairiukstis <k@andrius.mobi>"
LABEL org.opencontainers.image.title="Asterisk PBX Builder (Git Development)"
LABEL org.opencontainers.image.description="Build stage for Asterisk git-ff80666"
LABEL org.opencontainers.image.version="git-ff80666"
LABEL org.opencontainers.image.source="https://github.com/asterisk/asterisk"

# Build arguments
ARG GIT_SHA=ff80666
ARG JOBS=8
ARG DEBIAN_FRONTEND=noninteractive

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
# Install build dependencies
RUN --mount=type=cache,target=/var/lib/apt/lists --mount=type=cache,target=/var/cache/apt --mount=type=cache,target=/var/cache/apt \
    apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \autoconf \binutils-dev \ca-certificates \curl \file \git \libcurl4-openssl-dev \libedit-dev \libgsm1-dev \libicu-dev \libjansson-dev \libncurses-dev \libogg-dev \libpopt-dev \libpqxx-dev \libresample1-dev \libspandsp-dev \libspeex-dev \libspeexdsp-dev \libsqlite3-dev \libssl-dev \libsrtp2-dev \libtool \libvorbis-dev \libxml2-dev \libxslt1-dev \make \odbcinst \patch \pkg-config \portaudio19-dev \procps \python3-dev \unixodbc \unixodbc-dev \uuid \uuid-dev \xmlstarlet \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install git (required for git-based builds)
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

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
RUN --mount=type=cache,target=/tmp/asterisk_build cd /usr/src/asterisk \
    && ./build.sh \
    && make install \
    && make install-logrotate \
    && make basic-pbx \
    && ldconfig

# ==============================================================================
# STAGE 2: Runtime Environment
# ==============================================================================
FROM debian:trixie AS asterisk-runtime

LABEL maintainer="Andrius Kairiukstis <k@andrius.mobi>"
LABEL org.opencontainers.image.title="Asterisk PBX (Git Development)"
LABEL org.opencontainers.image.description="Asterisk git-ff80666 on Debian trixie"
LABEL org.opencontainers.image.version="git-ff80666"
LABEL org.opencontainers.image.source="https://github.com/asterisk/asterisk"

# Runtime environment
ARG GIT_SHA=ff80666
ENV GIT_SHA=${GIT_SHA}

# EOL distribution setup (if needed)
# Install runtime dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        binutils \curl \libcurl4 \libedit2 \libgsm1 \libicu76 \libjansson4 \libncurses6 \libogg0 \libpopt0 \libpqxx-7.10 \libresample1 \libspandsp2 \libspeex1 \libspeexdsp1 \libsqlite3-0 \libssl3 \libsrtp2-1 \libvorbis0a \libxml2 \libxslt1.1 \odbcinst \portaudio19-dev \procps \python3 \unixodbc \uuid \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create asterisk user and group
RUN groupadd -g 1001 asterisk \
    && useradd -r -u 1001 -g asterisk -d /var/lib/asterisk -s /bin/bash asterisk

# Copy Asterisk from builder stage
COPY --from=asterisk-builder /usr/sbin/asterisk /usr/sbin/asterisk
COPY --from=asterisk-builder /usr/lib/asterisk/ /usr/lib/asterisk/
COPY --from=asterisk-builder /var/lib/asterisk/ /var/lib/asterisk/
COPY --from=asterisk-builder /etc/asterisk/ /etc/asterisk/
COPY --from=asterisk-builder /var/spool/asterisk/ /var/spool/asterisk/
COPY --from=asterisk-builder /var/log/asterisk/ /var/log/asterisk/
COPY --from=asterisk-builder /usr/src/asterisk/.git_sha /var/lib/asterisk/.git_sha

# Set proper ownership
RUN chown -R asterisk:asterisk \
    /var/lib/asterisk \
    /var/spool/asterisk \
    /var/log/asterisk \
    /etc/asterisk

# Copy healthcheck script
COPY healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh

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

# Switch to asterisk user
USER asterisk

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

# Default command
CMD ["/usr/sbin/asterisk", "-f"]
