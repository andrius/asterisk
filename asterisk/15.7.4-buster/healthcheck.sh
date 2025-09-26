#!/bin/bash
# Healthcheck for Asterisk 15.7.4
exec asterisk -rx "core show uptime" > /dev/null
