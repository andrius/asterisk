#!/bin/bash
# Healthcheck for Asterisk git
exec asterisk -rx "core show uptime" > /dev/null
