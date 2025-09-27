#!/bin/bash
# Asterisk build script
# Generated from template for 15.7.4
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

log "Starting Asterisk 15.7.4 build process..."

# Set build parallelization (use Docker ARG or default)
NPROC=$(nproc)
JOBS=${JOBS:-8}
log "Using $JOBS parallel jobs for compilation (detected $NPROC CPUs)"

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
menuselect/menuselect --enable app_confbridge menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_confbridge menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_dial menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_dial menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_directory menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_directory menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_echo menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_echo menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_followme menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_followme menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_forkcdr menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_forkcdr menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_gosub menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_gosub menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_goto menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_goto menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_hangup menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_hangup menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_if menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_if menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_meetme menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_meetme menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_mixmonitor menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_mixmonitor menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_monitor menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_monitor menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_noop menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_noop menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_playback menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_playback menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_queue menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_queue menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_record menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_record menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_return menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_return menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_stack menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_stack menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_verbose menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_verbose menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_voicemail menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_voicemail menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_voicemailmain menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_voicemailmain menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_waitexten menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_waitexten menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable app_while menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable app_while menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"

# Enable CDR and CEL modules
menuselect/menuselect --enable cdr_csv menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable cdr_csv menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable cdr_odbc menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable cdr_odbc menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable cdr_pgsql menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable cdr_pgsql menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable cel_odbc menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable cel_odbc menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable cel_pgsql menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable cel_pgsql menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"

# Enable channel drivers
menuselect/menuselect --enable chan_bridge_media menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable chan_bridge_media menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable chan_iax2 menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable chan_iax2 menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable chan_local menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable chan_local menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable chan_pjsip menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable chan_pjsip menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"

# Enable resource modules
menuselect/menuselect --enable res_ari menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_ari menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_ari_applications menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_ari_applications menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_ari_asterisk menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_ari_asterisk menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_ari_bridges menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_ari_bridges menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_ari_channels menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_ari_channels menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_ari_device_states menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_ari_device_states menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_ari_endpoints menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_ari_endpoints menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_ari_events menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_ari_events menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_ari_mailboxes menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_ari_mailboxes menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_ari_model menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_ari_model menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_ari_playbacks menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_ari_playbacks menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_ari_recordings menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_ari_recordings menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_ari_sounds menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_ari_sounds menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_cdr menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_cdr menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_cel menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_cel menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_config_odbc menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_config_odbc menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_config_pgsql menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_config_pgsql menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_crypto menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_crypto menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_format_attr menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_format_attr menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_hep menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_hep menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_hep_pjsip menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_hep_pjsip menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_hep_rtcp menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_hep_rtcp menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_http_websocket menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_http_websocket menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_musiconhold menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_musiconhold menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_odbc menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_odbc menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_pjsip menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_pjsip menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_pjsip_authenticator_digest menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_pjsip_authenticator_digest menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_pjsip_caller_id menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_pjsip_caller_id menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_pjsip_endpoint_identifier_ip menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_pjsip_endpoint_identifier_ip menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_pjsip_endpoint_identifier_user menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_pjsip_endpoint_identifier_user menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_pjsip_outbound_registration menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_pjsip_outbound_registration menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_pjsip_registrar menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_pjsip_registrar menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_pjsip_session menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_pjsip_session menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_pjsip_transport_websocket menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_pjsip_transport_websocket menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_prometheus menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_prometheus menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_rtp_asterisk menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_rtp_asterisk menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_srtp menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_srtp menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_statsd menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_statsd menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_stun_monitor menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_stun_monitor menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_timing_timerfd menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_timing_timerfd menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --enable res_websocket_client menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --enable res_websocket_client menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"

# Disable unwanted modules
menuselect/menuselect --disable app_festival menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --disable app_festival menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --disable app_flash menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --disable app_flash menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --disable chan_dahdi menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --disable chan_dahdi menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --disable chan_misdn menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --disable chan_misdn menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --disable codec_dahdi menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --disable codec_dahdi menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"
menuselect/menuselect --disable res_pjsip_sdp_rtp menuselect.makeopts || warn "Module not found: $(echo 'menuselect/menuselect --disable res_pjsip_sdp_rtp menuselect.makeopts' | grep -o '[a-z_]*' | tail -1)"


log "Module configuration completed"


# Build Asterisk
log "Building Asterisk core (this may take several minutes)..."
TMPDIR=${TMPDIR} make -j $JOBS all
log "Installing Asterisk..."
TMPDIR=${TMPDIR} make install
log "Installing sample configurations..."
TMPDIR=${TMPDIR} make samples

# Configure HEP modules (enable by default)
log "Configuring HEP modules..."
sed -i 's/noload = res_hep/load=res_hep/g' /etc/asterisk/modules.conf

# Strip binaries to reduce size
log "Stripping binaries to reduce image size..."
find /usr/sbin /usr/lib/asterisk -type f -executable \
    -exec strip --strip-unneeded {} + 2>/dev/null || true

log "Asterisk 15.7.4 build completed successfully!"