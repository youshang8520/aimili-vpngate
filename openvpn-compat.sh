#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;36m'
PLAIN='\033[0m'

REPO_DIR="${1:-$(pwd)}"
COMPAT_SOURCE_DIR="${2:-${REPO_DIR}/openvpn-compat}"
OUTPUT_DIR="${3:-${REPO_DIR}/openvpn-compat-diff}"

if [ "$(id -u)" != "0" ]; then
    echo -e "${RED}错误: 必须以 root 权限运行此脚本。请使用: sudo bash $0${PLAIN}"
    exit 1
fi

if [ ! -d "$REPO_DIR" ]; then
    echo -e "${RED}错误: 仓库目录不存在: $REPO_DIR${PLAIN}"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"
rm -f "$OUTPUT_DIR"/*

collect_file() {
    source_file="$1"
    target_file="$2"
    if [ -f "$source_file" ]; then
        cp -a "$source_file" "$target_file"
    fi
}

capture_sysctl_state() {
    state_file="$1"
    {
        echo "# OpenVPN compatibility sysctl snapshot"
        for key in \
            net.ipv4.conf.all.rp_filter \
            net.ipv4.conf.default.rp_filter \
            net.ipv4.conf.tun0.rp_filter \
            net.ipv4.ip_forward
        do
            value=$(sysctl -n "$key" 2>/dev/null || true)
            if [ -n "$value" ]; then
                printf '%s=%s\n' "$key" "$value"
            fi
        done
    } > "$state_file"
}

capture_service_state() {
    state_file="$1"
    {
        echo "# OpenVPN compatibility service snapshot"
        if command -v systemctl >/dev/null 2>&1; then
            systemctl is-enabled openvpn 2>/dev/null || true
            systemctl is-enabled openvpn-client@ 2>/dev/null || true
            systemctl is-enabled firewalld 2>/dev/null || true
        fi
        if command -v rc-status >/dev/null 2>&1; then
            rc-status 2>/dev/null || true
        fi
    } > "$state_file"
}

capture_path_state() {
    state_file="$1"
    {
        echo "# OpenVPN compatibility path snapshot"
        for path in \
            /etc/openvpn \
            /etc/openvpn/client \
            /etc/openvpn/server \
            /etc/openvpn/legacy \
            /etc/openvpn/compat \
            /etc/default/aimilivpn
        do
            if [ -e "$path" ]; then
                printf '%s\n' "$path"
            fi
        done
    } > "$state_file"
}

compare_dir() {
    source_dir="$1"
    if [ -d "$source_dir" ]; then
        find "$source_dir" -maxdepth 2 -type f | sort > "$OUTPUT_DIR/source-files.txt"
        if [ -d "$REPO_DIR/openvpn-compat" ]; then
            find "$REPO_DIR/openvpn-compat" -maxdepth 2 -type f | sort > "$OUTPUT_DIR/repo-files.txt"
            diff -u "$OUTPUT_DIR/repo-files.txt" "$OUTPUT_DIR/source-files.txt" > "$OUTPUT_DIR/file-list.diff" || true
        else
            echo "# repository openvpn-compat directory missing" > "$OUTPUT_DIR/file-list.diff"
        fi
    else
        echo "# compatibility source directory missing: $source_dir" > "$OUTPUT_DIR/file-list.diff"
    fi
}

make_archive() {
    archive_base="$1"
    archive_file=""
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

echo -e "${BLUE}正在采集 OpenVPN 兼容差异...${PLAIN}"
collect_file "/etc/default/aimilivpn" "$OUTPUT_DIR/etc-default-aimilivpn.backup"
collect_file "/etc/sysctl.conf" "$OUTPUT_DIR/sysctl.conf.backup"
collect_file "/etc/openvpn/client.conf" "$OUTPUT_DIR/openvpn-client.conf.backup"
collect_file "/etc/openvpn/server.conf" "$OUTPUT_DIR/openvpn-server.conf.backup"

capture_sysctl_state "$OUTPUT_DIR/sysctl-state.txt"
capture_service_state "$OUTPUT_DIR/service-state.txt"
capture_path_state "$OUTPUT_DIR/path-state.txt"
compare_dir "$COMPAT_SOURCE_DIR"

cat > "$OUTPUT_DIR/README.txt" <<'EOF'
OpenVPN compatibility diff bundle

This directory contains snapshots that help identify the compatibility delta
that should be preserved for AlmaLinux 8.10 and similar systems.
EOF

cat > "$OUTPUT_DIR/next-steps.txt" <<'EOF'
1. Review sysctl-state.txt for rp_filter and forwarding values.
2. Review path-state.txt for existing OpenVPN compatibility files.
3. Review file-list.diff for repository/source compatibility differences or a missing-source note.
4. Copy any required preserved settings into the repository-side OpenVPN compatibility helper.
EOF

ARCHIVE_PATH=$(make_archive "$OUTPUT_DIR/openvpn-compat-diff")
if [ -n "$ARCHIVE_PATH" ]; then
    echo -e "${GREEN}已生成兼容差异包: ${OUTPUT_DIR}${PLAIN}"
    echo -e "${GREEN}已打包归档: ${ARCHIVE_PATH}${PLAIN}"
    echo -e "${GREEN}包就在: ${ARCHIVE_PATH}${PLAIN}"
else
    echo -e "${YELLOW}已生成兼容差异包: ${OUTPUT_DIR}${PLAIN}"
    echo -e "${YELLOW}未找到 tar/zip，未自动打包${PLAIN}"
fi
