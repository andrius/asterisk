#!/bin/bash
# Asterisk 10 minimal build script
# Based on working andrius-asterisk build approach
# Generated from template for 10.12.4

set -euo pipefail

log() {
    echo -e "\033[0;32m[BUILD]\033[0m $1"
}

warn() {
    echo -e "\033[1;33m[WARN]\033[0m $1"
}

log "Starting Asterisk 10.12.4 build process..."

# Set build parallelization
NPROC=$(nproc)
JOBS=${JOBS:-$(( $NPROC + $NPROC / 2 ))}
log "Using $JOBS parallel jobs for compilation (detected $NPROC CPUs)"

# Minimal menuselect configuration (andrius-asterisk approach)
log "Configuring Asterisk modules with minimal approach..."

# Disable BUILD_NATIVE to avoid platform issues
menuselect/menuselect --disable BUILD_NATIVE menuselect.makeopts

# Enable better backtraces for debugging
menuselect/menuselect --enable BETTER_BACKTRACES menuselect.makeopts

# Disable sound categories to reduce image size
menuselect/menuselect --disable-category MENUSELECT_CORE_SOUNDS menuselect.makeopts
menuselect/menuselect --disable-category MENUSELECT_MOH menuselect.makeopts
menuselect/menuselect --disable-category MENUSELECT_EXTRA_SOUNDS menuselect.makeopts

log "Module configuration completed (minimal approach - let Asterisk choose defaults)"

# Build Asterisk
log "Building Asterisk core (this may take several minutes)..."
make -j $JOBS all || make -j $JOBS all
log "Installing Asterisk..."
make install
log "Installing sample configurations..."
make samples

# Set runuser and rungroup
sed -i -E 's/^;(run)(user|group)/\1\2/' /etc/asterisk/asterisk.conf

# Strip binaries to reduce size
log "Stripping binaries to reduce image size..."
find /usr/sbin /usr/lib/asterisk -type f -executable \
    -exec strip --strip-unneeded {} + 2>/dev/null || true

log "Asterisk 10.12.4 build completed successfully!"