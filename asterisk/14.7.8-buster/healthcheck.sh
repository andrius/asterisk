#!/bin/bash
# Healthcheck for Asterisk 14.7.8
exec asterisk -rx "core show uptime" > /dev/null
