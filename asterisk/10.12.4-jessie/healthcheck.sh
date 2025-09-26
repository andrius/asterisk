#!/bin/bash
# Healthcheck for Asterisk 10.12.4
exec asterisk -rx "core show uptime" > /dev/null
