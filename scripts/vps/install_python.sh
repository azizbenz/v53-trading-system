#!/usr/bin/env bash
set -euo pipefail

PY_VERSION="${PY_VERSION:-3.14.0}"

sudo apt-get update
sudo apt-get install -y build-essential libssl-dev libffi-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev libsecret-1-dev curl git

if ! command -v uv >/dev/null 2>&1; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

uv python install "${PY_VERSION}"
echo "Python ${PY_VERSION} installed via uv"
