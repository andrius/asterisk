#!/bin/bash
# Healthcheck for Asterisk 1.2.40
exec asterisk -rx "core show uptime" > /dev/null
