#!/bin/bash
# Asterisk health check script
# Generated from template for 1.4.44

set -euo pipefail

# Configuration
ASTERISK_CLI="/usr/sbin/asterisk -rx"
TIMEOUT=10
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        *)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
    esac
done

# Logging functions
log() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" >&2
    fi
}

error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2
}

# Health check functions
check_asterisk_running() {
    log "Checking if Asterisk is running..."
    if ! pgrep -x asterisk >/dev/null; then
        error "Asterisk process not found"
        return 1
    fi
    log "✓ Asterisk process is running"
    return 0
}

check_asterisk_responsive() {
    log "Checking if Asterisk CLI is responsive..."
    if ! timeout $TIMEOUT $ASTERISK_CLI "core show version" >/dev/null 2>&1; then
        error "Asterisk CLI not responsive"
        return 1
    fi
    log "✓ Asterisk CLI is responsive"
    return 0
}

check_pjsip_status() {
    log "Checking PJSIP status..."
    if ! timeout $TIMEOUT $ASTERISK_CLI "pjsip show version" >/dev/null 2>&1; then
        error "PJSIP not available or not responding"
        return 1
    fi
    log "✓ PJSIP is available"
    return 0
}

check_database_connectivity() {
    log "Checking database connectivity..."
    # Check if ODBC is configured and working
    if ! timeout $TIMEOUT $ASTERISK_CLI "odbc show all" | grep -q "Connected" 2>/dev/null; then
        log "⚠ No ODBC connections found (this may be normal)"
    else
        log "✓ Database connections available"
    fi
    return 0
}

check_essential_modules() {
    log "Checking essential modules..."
    local required_modules=(
        "res_rtp_asterisk"
        "res_timing_timerfd"
        "res_crypto"
        "res_pjsip"
    )

    for module in "${required_modules[@]}"; do
        if ! timeout $TIMEOUT $ASTERISK_CLI "module show like $module" | grep -q "$module" >/dev/null 2>&1; then
            error "Required module $module not loaded"
            return 1
        fi
    done
    log "✓ Essential modules are loaded"
    return 0
}

check_filesystem_access() {
    log "Checking filesystem access..."
    local required_dirs=(
        "/var/log/asterisk"
        "/var/spool/asterisk"
        "/var/lib/asterisk"
        "/etc/asterisk"
    )

    for dir in "${required_dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            error "Required directory $dir not found"
            return 1
        fi
        if [[ ! -r "$dir" ]]; then
            error "Directory $dir not readable"
            return 1
        fi
    done
    log "✓ Filesystem access is working"
    return 0
}

# Main health check
main() {
    log "Starting Asterisk health check..."

    local checks=(
        "check_asterisk_running"
        "check_asterisk_responsive"
        "check_pjsip_status"
        "check_database_connectivity"
        "check_essential_modules"
        "check_filesystem_access"
    )

    local failed=0
    for check in "${checks[@]}"; do
        if ! $check; then
            failed=$((failed + 1))
        fi
    done

    if [[ $failed -eq 0 ]]; then
        log "✓ All health checks passed"
        exit 0
    else
        error "Health check failed: $failed checks failed"
        exit 1
    fi
}

# Handle signals
trap 'error "Health check interrupted"; exit 1' INT TERM

main "$@"