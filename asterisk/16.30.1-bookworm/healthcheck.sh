#!/bin/bash
# Healthcheck for Asterisk 16.30.1
exec asterisk -rx "core show uptime" > /dev/null
