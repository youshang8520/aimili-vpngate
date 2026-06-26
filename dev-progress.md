# dev-progress.md

## 2026-06-27

### 当前任务
- 目标：在 `aimili-vpngate` 中新增 PublicVPNList 作为额外 OpenVPN 节点来源。
- 重要要求：**新增来源，不替换现有 VPNGate 来源**。
- 需要复用 AimiliVPN 现有能力：OpenVPN 连接管理、四种路由/网卡模式、本地 HTTP/SOCKS5 代理 `127.0.0.1:7928`、tun0 出站绑定与现有 Web/CLI 管理能力。

### 用户明确要求
- “现在系统已经安装aimili-vpngate，我希望复用”。
- “这个脚本只配抓取ip，openvpn四个aimili的网卡模式”。
- “把aimili改装为支持抓取PublicVPNList的方式接入，而不单单从vpngate获取”。
- “是增加不是替换已有的”。

### 技术方向
- 保留 `API_URL = https://www.vpngate.net/api/iphone/` 与现有 VPNGate 拉取逻辑。
- 增加 PublicVPNList 页面解析逻辑，默认可从 `https://publicvpnlist.com/country/usa/` 获取节点。
- 解析 PublicVPNList 行字段：`data-id`、`data-country`、`data-country-name`、`data-host`、`data-ip`、`data-speed`、`data-latency`、`data-port`、`data-proto`、`data-checked-at`，以及行内可见 `Technical score`。
- 通过 `/download/{data-id}/` 下载 `.ovpn` 配置并转换为 AimiliVPN 现有 node schema。
- 增加可配置过滤：最低速度、最高延迟、最低 Technical score、协议 tcp/udp/all、最大下载数量。

### 已完成
- 已确认 AimiliVPN 现有节点流：`fetch_candidates()` 拉取 VPNGate、`row_to_node()` 转换节点、`maintain_valid_nodes()` 合并/测速、`connect_node()` 复用 OpenVPN 与 `tun0` 策略路由、本地代理继续由 `proxy_server.py` 绑定 `127.0.0.1:7928`。
- 已在 `vpngate_manager.py` 增加 PublicVPNList 附加来源配置与解析：`PUBLICVPNLIST_ENABLED`、`PUBLICVPNLIST_SOURCES`、`PUBLICVPNLIST_MAX_DOWNLOADS`、`PUBLICVPNLIST_MIN_SPEED`、`PUBLICVPNLIST_MAX_LATENCY`、`PUBLICVPNLIST_MIN_SCORE`、`PUBLICVPNLIST_PROTO`。
- 已实现 PublicVPNList HTML 行解析、Technical score 提取、质量过滤、`.ovpn` 下载与 Aimili node schema 转换。
- 已在 `fetch_candidates()` 中将 PublicVPNList 节点合并到现有 VPNGate 候选列表，保留 VPNGate 来源，不替换原逻辑。
- 已在 `install.sh` 中新增 `/etc/default/aimilivpn` 默认环境配置（仅不存在时创建，不覆盖用户现有配置）。
- 已更新 README 中文/英文文档说明 PublicVPNList 是附加来源及过滤参数。

### 验证记录
- `python -m py_compile vpngate_manager.py vpn_utils.py proxy_server.py`：通过。
- `bash -n install.sh`：通过。
- `git diff --check`：通过。
- PublicVPNList 样例行解析验证：通过，能生成 `https://publicvpnlist.com/download/101398/`。
- PublicVPNList 实际 USA 国家页解析验证：通过，解析到 9 个过滤后条目，示例最高排序条目为 `87042 / 24.243.35.205 / 320.79 Mbps / 30 ms / score 69 / tcp`。
- MCP 抓取 `/download/87042/` 受站点 robots.txt 限制，未通过 MCP 查看实际下载内容；运行时代码会按页面 `/download/{data-id}/` 下载 `.ovpn`。

### 提交记录
- 已创建本地提交：`5a4f0b4 feat: add PublicVPNList OpenVPN source`。
- 推送 `origin main` 失败：GitHub 返回 403，当前账号 `youshang8520` 没有 `baoweise-bot/aimili-vpngate` 的推送权限。

### 推送记录
- 用户已要求“复刻并推送”。
- 已通过 GitHub CLI 创建 fork：`https://github.com/youshang8520/aimili-vpngate`。
- 已添加远程：`fork https://github.com/youshang8520/aimili-vpngate.git`。
- 已将本地 `main` 分支推送到 fork。
