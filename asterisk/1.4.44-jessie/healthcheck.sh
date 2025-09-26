#!/bin/bash
# Healthcheck for Asterisk 1.4.44
exec asterisk -rx "core show uptime" > /dev/null
