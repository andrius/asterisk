#!/bin/bash
# Build script for Asterisk
set -euo pipefail
make menuselect.makeopts
menuselect/menuselect --enable-category MENUSELECT_ADDONS menuselect.makeopts || true
make
make install
make samples
