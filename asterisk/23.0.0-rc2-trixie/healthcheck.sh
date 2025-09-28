#!/bin/bash
# Healthcheck for Asterisk 23.0.0-rc2
exec asterisk -rx "core show uptime" > /dev/null
