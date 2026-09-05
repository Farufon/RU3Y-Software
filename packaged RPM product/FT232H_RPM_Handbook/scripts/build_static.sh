#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
clang -O2 -Wall src/rpm_reader.c -o rpm_reader_static   -Ivendor/ftdi vendor/ftdi/libftd2xx.a   -framework IOKit -framework CoreFoundation
echo "Built ./rpm_reader_static"
