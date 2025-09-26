#!/bin/bash
# Healthcheck for Asterisk 21.10.2
exec asterisk -rx "core show uptime" > /dev/null
