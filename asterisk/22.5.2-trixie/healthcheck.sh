#!/bin/bash
# Healthcheck for Asterisk 22.5.2
exec asterisk -rx "core show uptime" > /dev/null
