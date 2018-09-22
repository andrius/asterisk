FROM centos:6

MAINTAINER Andrius Kairiukstis <andrius@kairiukstis.com>

RUN yum -y install gcc gcc-c++ cpp ncurses ncurses-devel libxml2 libxml2-devel openssl-devel \
      newt-devel libuuid-devel net-snmp-devel xinetd tar libffi-devel sqlite-devel curl bison supervisor \
  && mkdir /tmp/asterisk \
  && curl -sf -o /tmp/asterisk.tar.gz -L http://downloads.asterisk.org/pub/telephony/certified-asterisk/certified-asterisk-11.6-current.tar.gz \
  && tar -xzf /tmp/asterisk.tar.gz -C /tmp/asterisk --strip-components=1 \
  && cd /tmp/asterisk \
  && ./configure --libdir=/usr/lib64 \
  && make menuselect \
  && menuselect/menuselect \
    --disable-all \
    --disable-category MENUSELECT_ADDONS \
    --disable-category MENUSELECT_APPS \
    --disable-category MENUSELECT_BRIDGES \
    --disable-category MENUSELECT_CDR \
    --disable-category MENUSELECT_CEL \
    --disable-category MENUSELECT_CHANNELS \
    --enable-category MENUSELECT_CODECS \
    --enable-category MENUSELECT_FORMATS \
    --disable-category MENUSELECT_FUNCS \
    --disable-category MENUSELECT_PBX \
    --disable-category MENUSELECT_RES \
    --disable-category MENUSELECT_TESTS \
    --disable-category MENUSELECT_UTILS \
    --disable-category MENUSELECT_AGIS \
    --disable-category MENUSELECT_EMBED \
    --enable-category MENUSELECT_CORE_SOUNDS \
    --enable-category MENUSELECT_MOH \
    --enable-category MENUSELECT_EXTRA_SOUNDS \
    --disable-category MENUSELECT_TESTS \
    --enable-category MENUSELECT_OPTS_app_voicemail \
    --enable func_module \
    --enable LOADABLE_MODULES \
    --enable FILE_STORAGE \
    --disable codec_dahdi \
    --enable app_dial \
    --enable app_exec \
    --enable app_originate \
    --enable app_verbose \
    --enable chan_sip \
    --enable pbx_config \
    --enable res_agi \
    --enable res_convert \
    --enable res_musiconhold \
    --enable res_timing_timerfd \
    --disable BUILD_NATIVE \
  menuselect.makeopts \
  && make config \
  && make \
  && make install \
  && mkdir -p /var/lib/asterisk/phoneprov \
  && make samples \
  && make dist-clean \
  && sed -i -e 's/# MAXFILES=/MAXFILES=/' /usr/sbin/safe_asterisk \
  && cd .. \
  && rm /tmp/asterisk.tar.gz \
  && rm -rf /tmp/asterisk \
  && yum -y clean all \
  && rm -rf /var/cache/yum/*


# RUN  yum -y update \
#   && yum -y install epel-release \
#   && yum -y install kernel-headers gcc gcc-c++ cpp ncurses ncurses-devel libxml2 libxml2-devel sqlite sqlite-devel \
#        mysql-devel openssl-devel newt-devel kernel-devel libuuid-devel net-snmp-devel xinetd tar libffi-devel \
#        curl pcre-devel bison mysql-devel ngrep tmux \
#   && mkdir /tmp/asterisk \
#   && curl -sf -o /tmp/asterisk.tar.gz -L http://downloads.asterisk.org/pub/telephony/certified-asterisk/certified-asterisk-11.6-current.tar.gz \
#   && tar -xzf /tmp/asterisk.tar.gz -C /tmp/asterisk --strip-components=1 \
#   && cd /tmp/asterisk \
#   && ./configure --libdir=/usr/lib64 \
#   && make menuselect \
#   && menuselect/menuselect \
#   --disable-category MENUSELECT_ADDONS \
#   --disable-category MENUSELECT_APPS \
#   --disable-category MENUSELECT_BRIDGES \
#   --disable-category MENUSELECT_CDR \
#   --disable-category MENUSELECT_CEL \
#   --disable-category MENUSELECT_CHANNELS \
#   --enable-category MENUSELECT_CODECS \
#   --enable-category MENUSELECT_FORMATS \
#   --disable-category MENUSELECT_FUNCS \
#   --disable-category MENUSELECT_PBX \
#   --disable-category MENUSELECT_RES \
#   --disable-category MENUSELECT_TESTS \
#   --disable-category MENUSELECT_OPTS_app_voicemail \
#   --disable-category MENUSELECT_UTILS \
#   --disable-category MENUSELECT_AGIS \
#   --disable-category MENUSELECT_EMBED \
#   --disable-category MENUSELECT_CORE_SOUNDS \
#   --disable-category MENUSELECT_MOH \
#   --disable-category MENUSELECT_EXTRA_SOUNDS \
#   --enable app_controlplayback \
#   --enable app_dial \
#   --enable app_exec \
#   --enable app_originate \
#   --enable app_queue \
#   --enable app_record \
#   --enable app_senddtmf \
#   --enable app_stasis \
#   --enable app_verbose \
#   --enable app_waituntil \
#   --enable chan_sip \
#   --enable pbx_config \
#   --enable pbx_realtime \
#   --enable res_agi \
#   --enable res_ari \
#   --enable res_ari_channels \
#   --enable res_ari_events \
#   --enable res_ari_playbacks \
#   --enable res_ari_recordings \
#   --enable res_ari_sounds \
#   --enable res_ari_device_states \
#   --enable res_realtime \
#   --enable res_rtp_asterisk \
#   --enable res_rtp_multicast \
#   --enable res_stasis \
#   --enable res_stasis_answer \
#   --enable res_stasis_device_state \
#   --enable res_stasis_playback \
#   --enable res_stasis_recording \
#   --enable res_stun_monitor \
#   --enable res_timing_timerfd \
#   --enable func_callcompletion \
#   --enable func_callerid \
#   --disable BUILD_NATIVE \
#   menuselect.makeopts \
#   && make config \
#   && make \
#   && make install \
#   && mkdir -p /var/lib/asterisk/phoneprov \
#   && make samples \
#   && make dist-clean \
#   && sed -i -e 's/# MAXFILES=/MAXFILES=/' /usr/sbin/safe_asterisk \
#   && cd .. \
#   && rm /tmp/asterisk.tar.gz \
#   && rm -rf /tmp/asterisk \
#   && yum -y clean all \
#   && rm -rf /var/cache/yum/*
#
# CMD asterisk -fvvvvv

