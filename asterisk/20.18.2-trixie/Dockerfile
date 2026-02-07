# Multi-stage optimized Asterisk Docker build
# Asterisk 20.18.2 on Debian trixie
# Generated from YAML configuration - DO NOT EDIT MANUALLY

# ==============================================================================
# STAGE 1: Build Environment
# ==============================================================================
FROM debian:trixie AS asterisk-builder

LABEL maintainer="Andrius Kairiukstis <k@andrius.mobi>"
LABEL org.opencontainers.image.title="Asterisk PBX Builder"
LABEL org.opencontainers.image.description="Build stage for Asterisk 20.18.2"
LABEL org.opencontainers.image.version="20.18.2"
LABEL org.opencontainers.image.source="https://github.com/andrius/asterisk"

# Build arguments
ARG ASTERISK_VERSION=20.18.2
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
RUN curl -fsSL https://downloads.asterisk.org/pub/telephony/asterisk/releases/asterisk-20.18.2.tar.gz \
    | tar --strip-components=1 -xz


# Configure Asterisk build (skip for very old versions that don't have configure script)
RUN ./configure

# Generate menuselect configuration
RUN make menuselect/menuselect menuselect-tree menuselect.makeopts

# Optimize build configuration for smaller image
RUN sed -i 's/HAVE_XML2 = yes/HAVE_XML2 = no/' makeopts \
    && sed -i 's/HAVE_XMLSTARLET = yes/HAVE_XMLSTARLET = no/' makeopts

# Copy and execute build script
COPY build.sh /usr/src/asterisk/build.sh
RUN chmod +x build.sh && ./build.sh

# ==============================================================================
# STAGE 2: Runtime Environment
# ==============================================================================
FROM debian:trixie AS asterisk-runtime

LABEL maintainer="Andrius Kairiukstis <k@andrius.mobi>"
LABEL org.opencontainers.image.title="Asterisk PBX Runtime"
LABEL org.opencontainers.image.description="Runtime environment for Asterisk 20.18.2"

ARG DEBIAN_FRONTEND=noninteractive
ARG TARGETARCH
ENV DEBIAN_FRONTEND=${DEBIAN_FRONTEND}

# Install only runtime dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        binutils curl libedit2 libgsm1 libjansson4 libogg0 libpopt0 libresample1 \
        libspandsp2 libspeex1 libspeexdsp1 libsqlite3-0 libvorbis0a libxml2 \
        libxslt1.1 odbcinst portaudio19-dev procps python3 unixodbc uuid libcurl4t64 \
        libssl3t64 libsrtp2-1 libncurses6 libpqxx-7.10 libicu76 \
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
LABEL org.opencontainers.image.description="Production Asterisk PBX 20.18.2"
LABEL org.opencontainers.image.version="20.18.2"
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

# Switch to non-root user
USER asterisk

# Set working directory
WORKDIR /home/asterisk

# Default command with production settings
CMD ["/usr/sbin/asterisk", "-vvvdddf", "-T", "-W", "-U", "asterisk", "-p"]
