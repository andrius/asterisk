# vim:set ft=dockerfile:
FROM alpine:3.14

MAINTAINER Andrius Kairiukstis <andrius@kairiukstis.com>

RUN apk add --update --no-cache --quiet \
      asterisk \
      asterisk-sample-config \
    >/dev/null \
&& asterisk -U asterisk &>/dev/null \
&& sleep 5s \
&& [ "$(asterisk -rx "core show channeltypes" | grep PJSIP)" != "" ] && : \
     || rm -rf /usr/lib/asterisk/modules/*pj* \
&& pkill -9 asterisk \
&& pkill -9 astcanary \
&& sleep 1s \
&& rm -rf /var/run/asterisk/* \
&& mkdir -p /var/spool/asterisk/fax \
&& chown -R asterisk: /var/spool/asterisk \
&& truncate -s 0 /var/log/asterisk/messages \
                 /var/log/asterisk/queue_log \
&&  rm -rf /var/cache/apk/* \
           /tmp/* \
           /var/tmp/*

EXPOSE 5060/udp 5060/tcp
VOLUME /var/lib/asterisk/sounds /var/lib/asterisk/keys /var/lib/asterisk/phoneprov /var/spool/asterisk /var/log/asterisk

ADD docker-entrypoint.sh /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
