#!/usr/bin/env bash
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;36m'
PLAIN='\033[0m'

INSTALL_DIR="/opt/aimilivpn"
COMPAT_DIR="${INSTALL_DIR}/openvpn-compat"

if [ "$(id -u)" != "0" ]; then
    echo -e "${RED}错误: 必须以 root 权限运行此脚本。请使用: sudo bash $0${PLAIN}"
    exit 1
fi

mkdir -p "$COMPAT_DIR"

cat > "$COMPAT_DIR/README.txt" <<'EOF'
AimiliVPN OpenVPN compatibility helper

This directory stores server-side compatibility notes and companion files for
systems that need the legacy OpenVPN tuning preserved across updates.
EOF

cat > "$COMPAT_DIR/compat.env" <<'EOF'
# Optional OpenVPN compatibility defaults for AlmaLinux 8.10 and similar systems.
# Keep this file under version control if you want the repository to ship it.
OPENVPN_COMPAT_ENABLED=1
OPENVPN_COMPAT_RP_FILTER=2
OPENVPN_COMPAT_TUN_DEVICE=tun0
EOF

echo -e "${GREEN}OpenVPN compatibility helper written to ${COMPAT_DIR}${PLAIN}"
