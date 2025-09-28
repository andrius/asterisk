#!/bin/bash
# Healthcheck for Asterisk 13.21-cert6
exec asterisk -rx "core show uptime" > /dev/null
