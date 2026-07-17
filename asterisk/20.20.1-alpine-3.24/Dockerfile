# Alpine Asterisk image - installs prebuilt, signed apks from the sibling
# project's Cloudsmith repository (andrius/asterisk-alpine). There is no build
# stage: the .apk already contains the compiled, module-selected Asterisk.
# Generated from YAML configuration - DO NOT EDIT MANUALLY
FROM alpine:3.24

LABEL maintainer="Andrius Kairiukstis <k@andrius.mobi>"
LABEL org.opencontainers.image.title="Asterisk PBX"
LABEL org.opencontainers.image.description="Asterisk PBX 20.20.1 on Alpine (apk)"
LABEL org.opencontainers.image.version="20.20.1"
LABEL org.opencontainers.image.source="https://github.com/andrius/asterisk"
LABEL org.opencontainers.image.vendor="Andrius Kairiukstis <k@andrius.mobi>"

# Trust the Cloudsmith repository signing key (vendored; copied into the build
# context alongside this Dockerfile).
COPY cloudsmith-asterisk-alpine.rsa.pub /etc/apk/keys/alpine@asterisk-25B0C9A992BE0CEF.rsa.pub

# Add the pinned apk repository and install Asterisk + the selected subpackages
# at an exact version, plus the runtime tools the entrypoint/healthcheck need.
# The @andrius-asterisk tag keeps these from clashing with Alpine's own
# asterisk in the main repo; the exact "=version-rN" pin makes rebuilds
# reproducible (or fail loudly if the apk was pruned).
RUN echo "@andrius-asterisk https://dl.cloudsmith.io/public/asterisk/alpine/alpine/v3.24/main" >>/etc/apk/repositories \
    && apk add --no-cache \
        "asterisk@andrius-asterisk=20.20.1-r0" \
        "asterisk-sample-config@andrius-asterisk=20.20.1-r0" \
        "asterisk-opus@andrius-asterisk=20.20.1-r0" \
        "asterisk-srtp@andrius-asterisk=20.20.1-r0" \
        "asterisk-curl@andrius-asterisk=20.20.1-r0" \
        "asterisk-speex@andrius-asterisk=20.20.1-r0" \
        "asterisk-fax@andrius-asterisk=20.20.1-r0" \
        "asterisk-odbc@andrius-asterisk=20.20.1-r0" \
        "asterisk-ldap@andrius-asterisk=20.20.1-r0" \
        "asterisk-pgsql@andrius-asterisk=20.20.1-r0" \
        "asterisk-prometheus@andrius-asterisk=20.20.1-r0" \
        "asterisk-mobile@andrius-asterisk=20.20.1-r0" \
        "asterisk-tds@andrius-asterisk=20.20.1-r0" \
        bash \
        shadow \
        gettext \
        procps \
        ca-certificates \
        curl \
        tzdata \
    && asterisk -V

# The asterisk apk creates the asterisk user (uid 100, home /var/lib/asterisk).
# Normalize it to the Debian image's identity (uid/gid 1000, home
# /home/asterisk, bash shell) so both image families behave identically and
# cloud/orchestration setups see a consistent uid. The entrypoint's PUID/PGID
# remap then no-ops on the default, exactly as on Debian.
RUN groupmod -g 1000 asterisk \
    && usermod -u 1000 -g 1000 -d /home/asterisk -s /bin/bash asterisk \
    && mkdir -p \
        /home/asterisk \
        /var/run/asterisk \
        /var/log/asterisk \
        /var/spool/asterisk/monitor \
        /var/spool/asterisk/outgoing \
        /var/spool/asterisk/tmp \
        /var/spool/asterisk/voicemail \
        /var/spool/asterisk/fax \
        /var/lib/asterisk/keys \
        /var/lib/asterisk/phoneprov \
        /var/lib/asterisk/sounds \
        /var/lib/asterisk/docs

# Healthcheck + entrypoint (the shared bash partials; bash + shadow are
# installed above so usermod/groupmod PUID/PGID remap works unchanged).
COPY healthcheck.sh /usr/local/bin/healthcheck.sh
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/healthcheck.sh /usr/local/bin/entrypoint.sh \
    && chown -R asterisk:asterisk \
        /etc/asterisk \
        /home/asterisk \
        /var/lib/asterisk \
        /var/log/asterisk \
        /var/spool/asterisk \
        /var/run/asterisk \
    && chmod -R 750 /var/spool/asterisk

# Networking (documented; publish explicitly at run time).
# EXPOSE 5060/udp
# EXPOSE 5060/tcp
# EXPOSE 10000-20000/udp
VOLUME ["/var/lib/asterisk/sounds", "/var/lib/asterisk/keys", "/var/lib/asterisk/phoneprov", "/var/spool/asterisk", "/var/log/asterisk", "/etc/asterisk"]
# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

# Entrypoint runs as root, remaps the asterisk uid/gid to PUID/PGID, then execs
# CMD. Asterisk drops privileges itself via the -U/-p flags below.
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
WORKDIR /home/asterisk
CMD ["/usr/sbin/asterisk", "-vvvdddf", "-T", "-W", "-U", "asterisk", "-p"]
