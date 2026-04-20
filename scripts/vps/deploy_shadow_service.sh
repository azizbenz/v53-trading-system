#!/usr/bin/env bash
set -euo pipefail

if ! id -u v53 >/dev/null 2>&1; then
    sudo adduser --system --group --home /opt/v53 v53
fi

sudo mkdir -p /var/log/v53 /etc/v53
sudo chown v53:v53 /var/log/v53 /etc/v53

sudo cp config/systemd/v53-shadow.service /etc/systemd/system/v53-shadow.service
sudo systemctl daemon-reload
sudo systemctl enable v53-shadow
sudo systemctl restart v53-shadow
sudo systemctl status v53-shadow --no-pager
