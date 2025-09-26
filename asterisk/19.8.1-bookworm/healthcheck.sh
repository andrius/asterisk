#!/bin/bash
# Healthcheck for Asterisk 19.8.1
exec asterisk -rx "core show uptime" > /dev/null
