#!/bin/bash
# Healthcheck for Asterisk 18.9-cert17
exec asterisk -rx "core show uptime" > /dev/null
