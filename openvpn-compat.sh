#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;36m'
PLAIN='\033[0m'

INSTALL_DIR="${1:-/opt/aimilivpn}"
OUTPUT_DIR="${2:-$(pwd)/openvpn-server-backup}"

if [ "$(id -u)" != "0" ]; then
    echo -e "${RED}错误: 必须以 root 权限运行此脚本。请使用: sudo bash $0${PLAIN}"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"
rm -f "$OUTPUT_DIR"/*

copy_tree() {
    src_path="$1"
    dst_path="$2"
    if [ -e "$src_path" ]; then
        mkdir -p "$(dirname "$dst_path")"
        cp -a "$src_path" "$dst_path"
    fi
}

capture_file() {
    src_file="$1"
    dst_file="$2"
    if [ -f "$src_file" ]; then
        cp -a "$src_file" "$dst_file"
    fi
}

capture_service_file() {
    service_path="$1"
    service_name="$2"
    if [ -f "$service_path" ]; then
        cp -a "$service_path" "$OUTPUT_DIR/$service_name"
    fi
}

make_archive() {
    archive_base="$1"
    if command -v tar >/dev/null 2>&1; then
        archive_file="${archive_base}.tar.gz"
        tar -czf "$archive_file" -C "$OUTPUT_DIR" .
        echo "$archive_file"
        return
    fi
    if command -v zip >/dev/null 2>&1; then
        archive_file="${archive_base}.zip"
        (cd "$OUTPUT_DIR" && zip -qr "$archive_file" .)
        echo "$OUTPUT_DIR/$archive_file"
        return
    fi
    echo ""
}

echo -e "${BLUE}正在备份服务器已安装的相关文件...${PLAIN}"
copy_tree "$INSTALL_DIR" "$OUTPUT_DIR/opt-aimilivpn"
capture_file "/etc/default/aimilivpn" "$OUTPUT_DIR/etc-default-aimilivpn"
capture_file "/etc/sysctl.conf" "$OUTPUT_DIR/sysctl.conf"
copy_tree "/etc/openvpn" "$OUTPUT_DIR/etc-openvpn"
capture_service_file "/lib/systemd/system/aimilivpn.service" "aimilivpn.service"
capture_service_file "/etc/init.d/aimilivpn" "aimilivpn-openrc"

if [ -d "$INSTALL_DIR/vpngate_data" ]; then
    copy_tree "$INSTALL_DIR/vpngate_data" "$OUTPUT_DIR/vpngate_data"
fi

cat > "$OUTPUT_DIR/README.txt" <<'EOF'
AimiliVPN server installation backup

This bundle captures the installed application files and the related OpenVPN
compatibility configuration so code changes can be compared against the live
server state.
EOF

cat > "$OUTPUT_DIR/next-steps.txt" <<'EOF'
1. Review opt-aimilivpn/ for the installed application snapshot.
2. Review vpngate_data/ for live state files.
3. Review etc-openvpn/ and related config files for server-side OpenVPN tuning.
4. Compare the backup against the repository version before changing install logic.
EOF

ARCHIVE_PATH=$(make_archive "$OUTPUT_DIR/aimilivpn-server-backup")
if [ -n "$ARCHIVE_PATH" ]; then
    echo -e "${GREEN}已生成服务器备份目录: ${OUTPUT_DIR}${PLAIN}"
    echo -e "${GREEN}已打包归档: ${ARCHIVE_PATH}${PLAIN}"
    echo -e "${GREEN}包就在: ${ARCHIVE_PATH}${PLAIN}"
else
    echo -e "${YELLOW}已生成服务器备份目录: ${OUTPUT_DIR}${PLAIN}"
    echo -e "${YELLOW}未找到 tar/zip，未自动打包${PLAIN}"
fi
