#!/bin/bash
# Legacy Asterisk build script with addons support
# For versions 1.2, 1.4, 1.6 that require asterisk-addons
# Based on working andrius-asterisk build approach
# Generated from template for 1.4.44

set -euo pipefail

log() {
    echo -e "\033[0;32m[BUILD]\033[0m $1"
}

warn() {
    echo -e "\033[1;33m[WARN]\033[0m $1"
}

log "Starting legacy Asterisk 1.4.44 build process with addons..."

# Set build parallelization
NPROC=$(nproc)
JOBS=${JOBS:-$(( $NPROC + $NPROC / 2 ))}
log "Using $JOBS parallel jobs for compilation (detected $NPROC CPUs)"

# Create directories for Asterisk and addons
mkdir -p /usr/src/asterisk \
         /usr/src/asterisk/addons \
         /etc/asterisk \
         /var/spool/asterisk/fax

# Download and extract addons first
log "Downloading and extracting asterisk-addons..."
cd /usr/src/asterisk/addons
curl -vsL https://downloads.asterisk.org/pub/telephony/asterisk/releases/asterisk-addons-1.4.9.tar.gz | tar --strip-components 1 -xz

# Return to main Asterisk directory
cd /usr/src/asterisk

# Minimal menuselect configuration (legacy approach - skip for very old versions)
log "Configuring Asterisk modules with minimal approach..."

# Disable sound categories to reduce image size
menuselect/menuselect --disable-category MENUSELECT_CORE_SOUNDS menuselect.makeopts
menuselect/menuselect --disable-category MENUSELECT_MOH menuselect.makeopts
menuselect/menuselect --disable-category MENUSELECT_EXTRA_SOUNDS menuselect.makeopts

log "Module configuration completed (minimal approach - let Asterisk choose defaults)"

# Build main Asterisk first
log "Building Asterisk core (this may take several minutes)..."
make -j $JOBS all
log "Installing Asterisk..."
make install

# Copy default configs and clean up
log "Installing sample configurations..."
make samples
make dist-clean
# Set runuser and rungroup
sed -i -E 's/^;(run)(user|group)/\1\2/' /etc/asterisk/asterisk.conf
sed -i -e 's/# MAXFILES=/MAXFILES=/' /usr/sbin/safe_asterisk

# Build and install addons
log "Building and installing asterisk-addons..."
cd /usr/src/asterisk/addons

# Configure addons with same libdir
./configure --libdir=/usr/lib64
make menuselect/menuselect menuselect-tree menuselect.makeopts
# Build and install addons
make -j $JOBS all
make install
make samples
# Fix permissions (ownership handled by Dockerfile STAGE 3)
chmod -R 755 /var/spool/asterisk

# Clean up source directories
cd /
rm -rf /usr/src/asterisk

# Strip binaries to reduce size
log "Stripping binaries to reduce image size..."
find /usr/sbin /usr/lib64/asterisk -type f -executable \
    -exec strip --strip-unneeded {} + 2>/dev/null || true

log "Legacy Asterisk 1.4.44 with addons build completed successfully!"