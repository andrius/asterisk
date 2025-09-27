#!/bin/bash
# Legacy Asterisk build script with addons support
# For versions 1.2, 1.4, 1.6 that require asterisk-addons
# Based on working andrius-asterisk build approach
# Generated from template for 1.2.40

set -euo pipefail

log() {
    echo -e "\033[0;32m[BUILD]\033[0m $1"
}

warn() {
    echo -e "\033[1;33m[WARN]\033[0m $1"
}

log "Starting legacy Asterisk 1.2.40 build process with addons..."

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
curl -vsL https://downloads.asterisk.org/pub/telephony/asterisk/releases/asterisk-addons-1.2.9.tar.gz | tar --strip-components 1 -xz

# Return to main Asterisk directory
cd /usr/src/asterisk

# Minimal menuselect configuration (legacy approach - skip for very old versions)
log "Skipping menuselect configuration for very old Asterisk version (1.2.40)"

# Build main Asterisk first
log "Building Asterisk core (this may take several minutes)..."
# For very old versions, try compatibility fixes for compilation issues
log "Applying compatibility fixes for very old Asterisk version"
# Remove problematic channel source files that conflict with modern headers
if [ -f "channels/chan_alsa.c" ]; then
    log "Removing chan_alsa.c to avoid pollfd conflicts"
    mv channels/chan_alsa.c channels/chan_alsa.c.disabled
    # Also remove from Makefile
    sed -i 's/chan_alsa\.c//g' channels/Makefile
    sed -i 's/chan_alsa\.so//g' channels/Makefile
fi
# Remove problematic IAX2 modules that have inline function conflicts
if [ -f "channels/iax2-provision.c" ]; then
    log "Removing iax2-provision.c to avoid multiple definition conflicts"
    mv channels/iax2-provision.c channels/iax2-provision.c.disabled
    sed -i 's/iax2-provision\.c//g' channels/Makefile
    sed -i 's/iax2-provision\.o//g' channels/Makefile
fi
# Set compatibility compiler flags for old GCC inline function handling
export CFLAGS="${CFLAGS:-} -DPOLLCOMPAT_FORCE -fgnu89-inline -std=gnu89"
make -j $JOBS all
log "Installing Asterisk..."
make install

# Copy default configs and clean up
log "Installing sample configurations..."
make samples
# Very old versions don't have dist-clean target, use clean instead
make clean || true
# Set runuser and rungroup
sed -i -E 's/^;(run)(user|group)/\1\2/' /etc/asterisk/asterisk.conf
sed -i -e 's/# MAXFILES=/MAXFILES=/' /usr/sbin/safe_asterisk

# Build and install addons
log "Building and installing asterisk-addons..."
cd /usr/src/asterisk/addons

# Very old addons versions don't have configure script
log "Skipping configure for very old asterisk-addons version"
# Build and install addons
make -j $JOBS all
make install
# Very old addons versions don't have samples target
log "Skipping samples for very old asterisk-addons version"
# Fix permissions (ownership handled by Dockerfile STAGE 3)
chmod -R 755 /var/spool/asterisk

# Clean up source directories
cd /
rm -rf /usr/src/asterisk

# Strip binaries to reduce size
log "Stripping binaries to reduce image size..."
find /usr/sbin /usr/lib64/asterisk -type f -executable \
    -exec strip --strip-unneeded {} + 2>/dev/null || true

log "Legacy Asterisk 1.2.40 with addons build completed successfully!"