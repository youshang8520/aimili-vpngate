#!/usr/bin/env bash
set -euo pipefail

REMOTE_URL="${1:-https://raw.githubusercontent.com/youshang8520/aimili-vpngate/main/openvpn-compat.sh}"
shift || true

if command -v curl >/dev/null 2>&1; then
    bash <(curl -fsSL "$REMOTE_URL") "$@"
elif command -v wget >/dev/null 2>&1; then
    bash <(wget -qO- "$REMOTE_URL") "$@"
else
    echo "需要 curl 或 wget 才能在线拉取 openvpn-compat.sh" >&2
    exit 1
fi
