#!/bin/bash
# Healthcheck for Asterisk 12.8.2
exec asterisk -rx "core show uptime" > /dev/null
