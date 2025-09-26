#!/bin/bash
# Healthcheck for Asterisk 1.8.32.3
exec asterisk -rx "core show uptime" > /dev/null
