#!/bin/bash
# Healthcheck for Asterisk 18.26.4
exec asterisk -rx "core show uptime" > /dev/null
