FROM andrius/asterisk:22.5.2_debian-trixie

USER root

# Install envsubst and curl for template processing and IP detection
RUN apt-get update && \
  apt-get install -y --no-install-recommends gettext-base curl && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy entrypoint and config templates
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY config/ /etc/asterisk/

# Set permissions
RUN chmod +x /usr/local/bin/docker-entrypoint.sh && \
  chown -R asterisk:asterisk /etc/asterisk/ /usr/local/bin/docker-entrypoint.sh

USER asterisk

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["asterisk", "-f"]
