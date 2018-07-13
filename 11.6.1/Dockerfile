# vim:set ft=dockerfile:
FROM alpine:2.6

MAINTAINER Andrius Kairiukstis <andrius@kairiukstis.com>

RUN apk add --update \
      asterisk \
      asterisk-sample-config \
&& asterisk -U asterisk \
&& sleep 5 \
&& pkill -9 asterisk \
&& sleep 2 \
&& rm -rf /var/run/asterisk/* \
&& mkdir -p /var/spool/asterisk/fax \
&& chown -R asterisk: /var/spool/asterisk/fax \
&&  rm -rf /var/cache/apk/* \
           /tmp/* \
           /var/tmp/*

EXPOSE 5060/udp 5060/tcp
VOLUME /var/lib/asterisk/sounds /var/lib/asterisk/keys /var/lib/asterisk/phoneprov /var/spool/asterisk /var/log/asterisk

ADD docker-entrypoint.sh /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
