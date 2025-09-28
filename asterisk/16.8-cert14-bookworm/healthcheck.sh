#!/bin/bash
# Healthcheck for Asterisk 16.8-cert14
exec asterisk -rx "core show uptime" > /dev/null
