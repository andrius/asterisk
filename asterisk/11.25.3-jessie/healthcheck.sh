#!/bin/bash
# Healthcheck for Asterisk 11.25.3
exec asterisk -rx "core show uptime" > /dev/null
