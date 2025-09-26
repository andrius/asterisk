#!/bin/bash
# Healthcheck for Asterisk 20.15.2
exec asterisk -rx "core show uptime" > /dev/null
