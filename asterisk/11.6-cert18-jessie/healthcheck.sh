#!/bin/bash
# Healthcheck for Asterisk 11.6-cert18
exec asterisk -rx "core show uptime" > /dev/null
