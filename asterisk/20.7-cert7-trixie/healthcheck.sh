#!/bin/bash
# Healthcheck for Asterisk 20.7-cert7
exec asterisk -rx "core show uptime" > /dev/null
