# vim:set ft=dockerfile:
FROM gliderlabs/alpine:2.7

MAINTAINER Andrius Kairiukstis <andrius@kairiukstis.com>

RUN apk add --update less curl ngrep \
  asterisk asterisk-curl asterisk-speex asterisk-sample-config \
&&  rm -rf /var/cache/apk/*

ADD docker-entrypoint.sh /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["/usr/sbin/asterisk", "-vvvdddf", "-T", "-W", "-U", "root", "-p"]


