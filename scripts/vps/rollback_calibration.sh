#!/usr/bin/env bash
set -euo pipefail

DRY_RUN="${DRY_RUN:-1}"
REGISTRY="${REGISTRY:-/var/v53/calibration_registry}"

[[ -f "${REGISTRY}/CURRENT" ]] || { echo "no CURRENT"; exit 2; }
[[ -f "${REGISTRY}/PREVIOUS" ]] || { echo "no PREVIOUS"; exit 2; }

CURRENT="$(cat "${REGISTRY}/CURRENT")"
PREVIOUS="$(cat "${REGISTRY}/PREVIOUS")"
echo "Rolling back from ${CURRENT} to ${PREVIOUS} (DRY_RUN=${DRY_RUN})"

if [[ "${DRY_RUN}" == "0" ]]; then
    echo "${PREVIOUS}" | sudo tee "${REGISTRY}/CURRENT" >/dev/null
    echo "${CURRENT}" | sudo tee "${REGISTRY}/PREVIOUS" >/dev/null
    sudo systemctl restart v53-shadow
fi
