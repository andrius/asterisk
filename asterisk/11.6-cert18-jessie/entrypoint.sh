#!/bin/bash
# Asterisk container entrypoint
# Generated from template for 11.6-cert18
#
# Adapts the in-container `asterisk` user (default uid:gid 1000:1000) to the
# uid/gid supplied via PUID / PGID env vars, then chowns runtime directories
# so bind-mounted volumes are writable. Asterisk drops privileges itself via
# its `-U asterisk -p` CMD flags, so no gosu/su-exec is needed.
#
# When the container is launched with `--user N:M` (compose `user:`), this
# script runs as that user instead of root: the adapt/chown branch is skipped
# and "$@" is exec'd as-is, matching pre-entrypoint behaviour.

set -e

PUID="${PUID:-1000}"
PGID="${PGID:-1000}"

if [ "$(id -u)" = "0" ]; then
    current_uid="$(id -u asterisk)"
    current_gid="$(id -g asterisk)"

    if [ "$PGID" != "$current_gid" ]; then
        groupmod -o -g "$PGID" asterisk
    fi
    if [ "$PUID" != "$current_uid" ]; then
        usermod -o -u "$PUID" -g "$PGID" asterisk
    fi

    for path in /etc/asterisk /home/asterisk /var/lib/asterisk \
                /var/log/asterisk /var/spool/asterisk /var/run/asterisk; do
        [ -d "$path" ] || continue
        if [ "$(stat -c '%u:%g' "$path" 2>/dev/null)" != "$PUID:$PGID" ]; then
            chown -R "$PUID:$PGID" "$path" 2>/dev/null || true
        fi
    done
fi

exec "$@"
