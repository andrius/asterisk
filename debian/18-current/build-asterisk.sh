#!/bin/bash
PROGNAME=$(basename $0)

if test -z ${ASTERISK_VERSION}; then
  echo "${PROGNAME}: ASTERISK_VERSION required" >&2
  exit 1
fi

set -ueo pipefail

useradd --system asterisk

DEBIAN_FRONTEND=noninteractive \
apt-get update -qq

DEBIAN_FRONTEND=noninteractive \
apt-get install --yes -qq --no-install-recommends --no-install-suggests \
  autoconf \
  binutils-dev \
  build-essential \
  ca-certificates \
  curl \
  file \
  libcurl4-openssl-dev \
  libedit-dev \
  libgsm1-dev \
  libogg-dev \
  libpopt-dev \
  libresample1-dev \
  libspandsp-dev \
  libspeex-dev \
  libspeexdsp-dev \
  libsqlite3-dev \
  libsrtp2-dev \
  libssl-dev \
  libvorbis-dev \
  libxml2-dev \
  libxslt1-dev \
  odbcinst \
  portaudio19-dev \
  procps \
  unixodbc \
  unixodbc-dev \
  uuid \
  uuid-dev \
  xmlstarlet \
> /dev/null

DEBIAN_FRONTEND=noninteractive \
apt-get purge --yes -qq --auto-remove > /dev/null
rm -rf /var/lib/apt/lists/*

mkdir -p /usr/src/asterisk
cd /usr/src/asterisk

( \
  curl -sL http://downloads.asterisk.org/pub/telephony/asterisk/releases/asterisk-${ASTERISK_VERSION}.tar.gz | tar --strip-components 1 -xz || \
  curl -sL http://downloads.asterisk.org/pub/telephony/asterisk/asterisk-${ASTERISK_VERSION}.tar.gz | tar --strip-components 1 -xz || \
  curl -sL http://downloads.asterisk.org/pub/telephony/asterisk/old-releases/asterisk-${ASTERISK_VERSION}.tar.gz | tar --strip-components 1 -xz \
) &>/dev/null

# 1.5 jobs per core works out okay
: ${JOBS:=$(( $(nproc) + $(nproc) / 2 ))}

./configure --with-resample \
            --with-pjproject-bundled \
            --with-jansson-bundled > /dev/null
make menuselect/menuselect menuselect-tree menuselect.makeopts

# disable BUILD_NATIVE to avoid platform issues
menuselect/menuselect --disable BUILD_NATIVE menuselect.makeopts

# enable good things
menuselect/menuselect --enable BETTER_BACKTRACES menuselect.makeopts

# enable ooh323
menuselect/menuselect --enable chan_ooh323 menuselect.makeopts

# codecs
# menuselect/menuselect --enable codec_opus menuselect.makeopts
# menuselect/menuselect --enable codec_silk menuselect.makeopts

# # download more sounds
# for i in CORE-SOUNDS-EN MOH-OPSOUND EXTRA-SOUNDS-EN; do
#   for j in ULAW ALAW G722 GSM SLN16; do
#     menuselect/menuselect --enable $i-$j menuselect.makeopts
#   done
# done

# we don't need any sounds in docker, they will be mounted as volume
menuselect/menuselect --disable-category MENUSELECT_CORE_SOUNDS menuselect.makeopts
menuselect/menuselect --disable-category MENUSELECT_MOH menuselect.makeopts
menuselect/menuselect --disable-category MENUSELECT_EXTRA_SOUNDS menuselect.makeopts

make -j ${JOBS} all > /dev/null || make -j ${JOBS} all
make install > /dev/null

# copy default configs
# cp /usr/src/asterisk/configs/basic-pbx/*.conf /etc/asterisk/
make samples > /dev/null

# set runuser and rungroup
sed -i -E 's/^;(run)(user|group)/\1\2/' /etc/asterisk/asterisk.conf

# Install opus, for some reason menuselect option above does not working
mkdir -p /usr/src/codecs/opus
cd /usr/src/codecs/opus
curl -sL http://downloads.digium.com/pub/telephony/codec_opus/${OPUS_CODEC}.tar.gz | tar --strip-components 1 -xz
cp *.so /usr/lib/asterisk/modules/
cp codec_opus_config-en_US.xml /var/lib/asterisk/documentation/

mkdir -p /etc/asterisk/ \
         /var/spool/asterisk/fax

chown -R asterisk:asterisk /etc/asterisk \
                           /var/*/asterisk \
                           /usr/*/asterisk
chmod -R 750 /var/spool/asterisk

cd /
rm -rf /usr/src/asterisk \
       /usr/src/codecs

DEVPKGS="$(dpkg -l | grep '\-dev' | awk '{print $2}' | xargs)"
DEBIAN_FRONTEND=noninteractive apt-get --yes -qq purge \
  autoconf \
  build-essential \
  bzip2 \
  cpp \
  m4 \
  make \
  patch \
  perl \
  perl-modules \
  pkg-config \
  xz-utils \
  ${DEVPKGS} \
> /dev/null

rm -rf /var/lib/apt/lists/*

exec rm -f /build-asterisk.sh
