#!/usr/bin/env bash
set -euo pipefail

REMOTE_URL="${1:-https://raw.githubusercontent.com/youshang8520/aimili-vpngate/main/openvpn-compat.sh}"
shift || true

if command -v curl >/dev/null 2>&1; then
    tmp_script=$(mktemp /tmp/openvpn-compat.XXXXXX.sh)
    trap 'rm -f "$tmp_script"' EXIT
    curl -fsSL "$REMOTE_URL" -o "$tmp_script"
    bash "$tmp_script" "$@"
elif command -v wget >/dev/null 2>&1; then
    tmp_script=$(mktemp /tmp/openvpn-compat.XXXXXX.sh)
    trap 'rm -f "$tmp_script"' EXIT
    wget -qO "$tmp_script" "$REMOTE_URL"
    bash "$tmp_script" "$@"
else
    echo "需要 curl 或 wget 才能在线拉取 openvpn-compat.sh" >&2
    exit 1
fi
