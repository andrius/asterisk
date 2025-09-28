#!/bin/bash
# Healthcheck for Asterisk 13.38.3
exec asterisk -rx "core show uptime" > /dev/null
