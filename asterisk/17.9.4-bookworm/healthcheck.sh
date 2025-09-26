#!/bin/bash
# Healthcheck for Asterisk 17.9.4
exec asterisk -rx "core show uptime" > /dev/null
