# vim:set ft=dockerfile:
FROM debian:buster-slim
# FROM debian:bullseye-slim

LABEL maintainer="Andrius Kairiukstis <k@andrius.mobi>"

ENV ASTERISK_VERSION asterisk-certified-13.21-cert6
ENV OPUS_CODEC       asterisk-13.0/x86-64/codec_opus-13.0_current-x86_64

COPY build-asterisk.sh /
RUN /build-asterisk.sh

EXPOSE 5060/udp 5060/tcp
VOLUME /var/lib/asterisk/sounds /var/lib/asterisk/keys /var/lib/asterisk/phoneprov /var/spool/asterisk /var/log/asterisk

COPY docker-entrypoint.sh /
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["/usr/sbin/asterisk", "-vvvdddf", "-T", "-W", "-U", "asterisk", "-p"]
