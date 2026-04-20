#!/usr/bin/env bash
set -euo pipefail

LOG_DIR="${LOG_DIR:-/var/log/v53}"

find "${LOG_DIR}" -name "*.log" -mtime +7 -exec gzip {} \;
find "${LOG_DIR}" -name "*.log.gz" -mtime +30 -delete
