#!/usr/bin/env bash
set -euo pipefail

systemctl is-active --quiet v53-shadow || exit 1
tail -n 200 /var/log/v53/shadow.log 2>/dev/null | grep -q "ws_heartbeat_ok" || exit 1
exit 0
