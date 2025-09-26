FROM andrius/asterisk:22.5.2_debian-trixie

# Get root to install additional packages
USER root

# Install envsubst and curl for template processing and IP detection
RUN apt-get update && \
  apt-get install -y --no-install-recommends gettext-base curl && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

# Copy entrypoint and config templates
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
COPY config/extensions.conf /etc/asterisk/
COPY config/logger.conf /etc/asterisk/
COPY config/modules.conf /etc/asterisk/
COPY config/pjsip.conf.template /etc/asterisk/
COPY config/rtp.conf /etc/asterisk/

# Set permissions
RUN chmod +x /usr/local/bin/docker-entrypoint.sh && \
  chown -R asterisk:asterisk /etc/asterisk/ /usr/local/bin/docker-entrypoint.sh

# Return to asterisk user
USER asterisk

ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["/usr/sbin/asterisk", "-vvvdddf", "-W", "-U", "asterisk", "-p"]
