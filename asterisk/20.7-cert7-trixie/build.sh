#!/bin/bash
# Asterisk build script
# Generated from template for 20.7-cert7
# Contains menuselect configuration and build commands

set -euo pipefail

# Color output for better readability
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[BUILD]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log "Starting Asterisk 20.7-cert7 build process..."

# Set build parallelization (use Docker ARG or default)
NPROC=$(nproc)
JOBS=${JOBS:-8}
log "Using $JOBS parallel jobs for compilation (detected $NPROC CPUs)"

# Configure Asterisk
log "Configuring Asterisk with options..."
./configure --with-pjproject-bundled --with-ssl=ssl --with-crypto

# Build menuselect tool
log "Building menuselect tool..."
make menuselect

# Configure Asterisk modules using menuselect
log "Configuring Asterisk modules..."

# Disable BUILD_NATIVE optimization for container builds
menuselect/menuselect --disable BUILD_NATIVE menuselect.makeopts

# Enable better backtraces for debugging
menuselect/menuselect --enable BETTER_BACKTRACES menuselect.makeopts

# Disable sound packages to reduce image size
menuselect/menuselect --disable-category MENUSELECT_CORE_SOUNDS menuselect.makeopts
menuselect/menuselect --disable-category MENUSELECT_MOH menuselect.makeopts
menuselect/menuselect --disable-category MENUSELECT_EXTRA_SOUNDS menuselect.makeopts

# Enable core applications
menuselect/menuselect --enable app_voicemail menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_voicemail menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_queue menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_queue menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_confbridge menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_confbridge menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_directory menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_directory menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_dial menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_dial menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_playback menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_playback menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_record menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_record menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_echo menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_echo menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_mixmonitor menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_mixmonitor menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"

# Enable CDR and CEL modules

# Enable channel drivers
menuselect/menuselect --enable chan_pjsip menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable chan_pjsip menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable chan_iax2 menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable chan_iax2 menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable chan_local menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable chan_local menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable chan_bridge_media menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable chan_bridge_media menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"

# Enable resource modules
menuselect/menuselect --enable res_musiconhold menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_musiconhold menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_pjsip menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_pjsip menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_pjsip_session menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_pjsip_session menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_pjsip_outbound_registration menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_pjsip_outbound_registration menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_pjsip_registrar menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_pjsip_registrar menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_rtp_asterisk menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_rtp_asterisk menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_timing_timerfd menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_timing_timerfd menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_crypto menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_crypto menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"

# Disable unwanted modules
menuselect/menuselect --disable chan_dahdi menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --disable chan_dahdi menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --disable chan_misdn menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --disable chan_misdn menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --disable app_festival menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --disable app_festival menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"


log "Module configuration completed"


# Build Asterisk
log "Building Asterisk core (this may take several minutes)..."
TMPDIR=${TMPDIR} make -j $JOBS all
log "Installing Asterisk..."
TMPDIR=${TMPDIR} make install
log "Installing sample configurations..."
TMPDIR=${TMPDIR} make samples


# Strip binaries to reduce size
log "Stripping binaries to reduce image size..."
find /usr/sbin /usr/lib/asterisk -type f -executable \
    -exec strip --strip-unneeded {} + 2>/dev/null || true

log "Asterisk 20.7-cert7 build completed successfully!"