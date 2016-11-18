# vim:set ft=dockerfile:
FROM gliderlabs/alpine:edge

MAINTAINER Andrius Kairiukstis <andrius@kairiukstis.com>

RUN apk add --update less curl sngrep ngrep \
      asterisk asterisk-curl asterisk-speex asterisk-sample-config \
&&  rm -rf /var/cache/apk/* /tmp/* /var/tmp/*

# start asterisk so it creates missing folders and initializes astdb
RUN asterisk && sleep 5

ADD docker-entrypoint.sh /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["/usr/sbin/asterisk", "-vvvdddf", "-T", "-W", "-U", "root", "-p"]


