FROM andrius/asterisk:22.10.1_debian-trixie

# Get root to install additional packages
USER root

# envsubst (gettext-base) and curl already ship in the base image - no extra
# install needed. Add any project-specific packages here if you have them.

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
