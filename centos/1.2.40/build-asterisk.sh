#!/bin/bash
PROGNAME=$(basename $0)

if test -z ${ASTERISK_VERSION}; then
  echo "${PROGNAME}: ASTERISK_VERSION required" >&2
  exit 1
fi

set -ex

useradd --system asterisk

yum -y install \
  cpp \
  gcc \
  gcc-c++ \
  make \
  ncurses \
  ncurses-devel \
  libxml2 \
  libxml2-devel \
  openssl-devel \
  newt-devel \
  libuuid-devel \
  net-snmp-devel \
  xinetd \
  tar \
  libffi-devel \
  sqlite-devel \
  curl \
  bison

mkdir -p /usr/src/asterisk \
         /usr/src/asterisk/addons

cd /usr/src/asterisk/addons
curl -vsL http://downloads.asterisk.org/pub/telephony/asterisk/old-releases/asterisk-addons-${ASTERISK_ADDONS_VERSION}.tar.gz | tar --strip-components 1 -xz

cd /usr/src/asterisk
curl -vsL http://downloads.asterisk.org/pub/telephony/asterisk/old-releases/asterisk-${ASTERISK_VERSION}.tar.gz | tar --strip-components 1 -xz

# 1.5 jobs per core works out okay
: ${JOBS:=$(( $(nproc) + $(nproc) / 2 ))}

mkdir -p /etc/asterisk/ \
         /var/spool/asterisk/fax

make -j ${JOBS} all
make install

# copy default configs
# cp /usr/src/asterisk/configs/basic-pbx/*.conf /etc/asterisk/
make samples

cd /usr/src/asterisk/addons

make -j ${JOBS} all
make install
# make samples

cd /usr/src/asterisk/addons/asterisk-ooh323c/
./configure
make -j ${JOBS} all
make install
make sample

chown -R asterisk:asterisk /etc/asterisk \
                           /var/*/asterisk \
                           /usr/*/asterisk
chmod -R 750 /var/spool/asterisk

cd /
rm -rf /usr/src/asterisk

yum -y clean all
rm -rf /var/cache/yum/*

exec rm -f /build-asterisk.sh
