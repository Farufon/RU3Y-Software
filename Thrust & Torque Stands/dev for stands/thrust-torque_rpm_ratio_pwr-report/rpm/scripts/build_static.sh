#!/usr/bin/env bash
# Builds rpm_reader_static and list_ftdi next to this script's parent folder (rpm/).
# live.py looks for rpm/rpm_reader_static by default.
set -euo pipefail
cd "$(dirname "$0")/.."
clang -O2 -Wall src/rpm_reader.c -o rpm_reader_static \
  -Ivendor/ftdi vendor/ftdi/libftd2xx.a \
  -framework IOKit -framework CoreFoundation
clang -O2 -Wall src/list_ftdi.c -o list_ftdi \
  -Ivendor/ftdi vendor/ftdi/libftd2xx.a \
  -framework IOKit -framework CoreFoundation
xattr -d com.apple.quarantine rpm_reader_static list_ftdi 2>/dev/null || true
echo "Built ./rpm_reader_static and ./list_ftdi in $(pwd)"
