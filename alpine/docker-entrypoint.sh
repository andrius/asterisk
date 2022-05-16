#!/bin/sh

set -eo pipefail

# optional Docker environment variables
ASTERISK_UID="${ASTERISK_UID:-}"
ASTERISK_GID="${ASTERISK_GID:-}"

# run as user asterisk by default
ASTERISK_USER="${ASTERISK_USER:-asterisk}"
ASTERISK_GROUP="${ASTERISK_GROUP:-${ASTERISK_USER}}"

if [ "$1" = "" ]; then
  COMMAND="/usr/sbin/asterisk -T -W -U ${ASTERISK_USER} -p -vvvdddf"
else
  COMMAND="$@"
fi

if [[ "${ASTERISK_UID}" != "" && "${ASTERISK_GID}" != "" ]]; then
  # recreate user and group for asterisk
  # if they've sent as env variables (i.e. to macth with host user to fix permissions for mounted folders
  deluser asterisk && \
  addgroup -g "${ASTERISK_GID}" "${ASTERISK_GROUP}" && \
  adduser -D -H -u "${ASTERISK_UID}" -G "${ASTERISK_GROUP}" "${ASTERISK_USER}"
fi

chown -R "${ASTERISK_USER}": /var/log/asterisk \
                           /var/lib/asterisk \
                           /var/run/asterisk \
                           /var/spool/asterisk ; \

exec ${COMMAND}
