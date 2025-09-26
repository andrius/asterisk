#!/bin/bash
# Healthcheck for Asterisk 1.6.2.24
exec asterisk -rx "core show uptime" > /dev/null
