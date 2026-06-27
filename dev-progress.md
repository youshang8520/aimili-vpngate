# dev-progress.md

## 2026-06-27

### 当前任务
- 目标：在 `aimili-vpngate` 中新增 PublicVPNList 作为额外 OpenVPN 节点来源，并补齐 Web UI 的节点来源切换。
- 重要要求：**新增来源，不替换现有 VPNGate 来源**。
- 需要复用 AimiliVPN 现有能力：OpenVPN 连接管理、四种路由/网卡模式、本地 HTTP/SOCKS5 代理 `127.0.0.1:7928`、tun0 出站绑定与现有 Web/CLI 管理能力。

### 用户明确要求
- “现在系统已经安装aimili-vpngate，我希望复用”。
- “这个脚本只配抓取ip，openvpn四个aimili的网卡模式”。
- “把aimili改装为支持抓取PublicVPNList的方式接入，而不单单从vpngate获取”。
- “是增加不是替换已有的”。
- 之后又要求把 Web UI 里的节点来源切换“直接开始改这个 UI 切换”。

### 技术方向
- 保留 `API_URL = https://www.vpngate.net/api/iphone/` 与现有 VPNGate 拉取逻辑。
- 增加 PublicVPNList 页面解析逻辑，默认可从 `https://publicvpnlist.com/country/usa/` 获取节点。
- 解析 PublicVPNList 行字段：`data-id`、`data-country`、`data-country-name`、`data-host`、`data-ip`、`data-speed`、`data-latency`、`data-port`、`data-proto`、`data-checked-at`，以及行内可见 `Technical score`。
- 通过 `/download/{data-id}/` 下载 `.ovpn` 配置并转换为 AimiliVPN 现有 node schema。
- 增加可配置过滤：最低速度、最高延迟、最低 Technical score、协议 tcp/udp/all、最大下载数量。
- 新增 UI 节点来源模式 `both` / `vpngate` / `publicvpnlist`，并把选择写入 `ui_auth.json`。

### 已完成
- 已确认 AimiliVPN 现有节点流：`fetch_candidates()` 拉取 VPNGate、`row_to_node()` 转换节点、`maintain_valid_nodes()` 合并/测速、`connect_node()` 复用 OpenVPN 与 `tun0` 策略路由、本地代理继续由 `proxy_server.py` 绑定 `127.0.0.1:7928`。
- 已在 `vpngate_manager.py` 增加 PublicVPNList 附加来源配置与解析：`PUBLICVPNLIST_ENABLED`、`PUBLICVPNLIST_SOURCES`、`PUBLICVPNLIST_MAX_DOWNLOADS`、`PUBLICVPNLIST_MIN_SPEED`、`PUBLICVPNLIST_MAX_LATENCY`、`PUBLICVPNLIST_MIN_SCORE`、`PUBLICVPNLIST_PROTO`。
- 已实现 PublicVPNList HTML 行解析、Technical score 提取、质量过滤、`.ovpn` 下载与 Aimili node schema 转换。
- 已在 `fetch_candidates()` 中将 PublicVPNList 节点合并到现有 VPNGate 候选列表，保留 VPNGate 来源，不替换原逻辑。
- 已在 `install.sh` 中新增 `/etc/default/aimilivpn` 默认环境配置（仅不存在时创建，不覆盖用户现有配置）。
- 已更新 README 中文/英文文档说明 PublicVPNList 是附加来源及过滤参数。
- 已把 Web UI 的 Network modal 增加为三档节点来源切换，并在前端保存时提交 `node_source_mode`。
- 已把 `node_source_mode` 接到后端 `/api/update_settings` 与 `/api/update_routing`，并在 `fetch_candidates()` 里按 `both` / `vpngate` / `publicvpnlist` 分流拉取。
- 已修正 `selectOptionCard()`，让 `node_source_mode` 选项能像路由模式一样被高亮与回写。
- 已开始把 `install.sh` 改成“下载 GitHub 分支快照 + 本地解压部署”的流程，目标是让生产 Linux 服务器不再执行 `git fetch/reset/clone`。
- 已移除安装依赖中的 `git`，并把源码获取改为 GitHub archive 下载路径；默认仍指向 `youshang8520/aimili-vpngate` 的 `main` 分支。
- 已加入快照部署辅助函数，当前方向是覆盖应用文件、保留 `/etc/openvpn` 及其客户端/服务端兼容目录，同时继续保留 `/etc/default/aimilivpn`。
- 已按最新方向拆分出独立的 OpenVPN 兼容辅助脚本 `openvpn-compat.sh`，让安装器继续专注于仓库对齐与升级流程。
- 已新增 `openvpn-compat-run.sh` 在线拉取入口，可在服务器无需预置脚本文件时直接执行远端版本。
- 需要确认该远端脚本已推送到仓库，否则 `raw.githubusercontent.com` 会 404。

### 验证记录
- `python -m py_compile vpngate_manager.py vpn_utils.py proxy_server.py`：通过。
- `bash -n install.sh`：先前通过；本轮改动后仍需重新核对。
- `git diff --check`：通过。
- PublicVPNList 样例行解析验证：通过，能生成 `https://publicvpnlist.com/download/101398/`。
- PublicVPNList 实际 USA 国家页解析验证：通过，解析到 9 个过滤后条目，示例最高排序条目为 `87042 / 24.243.35.205 / 320.79 Mbps / 30 ms / score 69 / tcp`。
- MCP 抓取 `/download/87042/` 受站点 robots.txt 限制，未通过 MCP 查看实际下载内容；运行时代码会按页面 `/download/{data-id}/` 下载 `.ovpn`。
- 本轮已额外验证 `vpngate_manager.py` 语法编译通过。
- `openvpn-compat.sh` 已补充源目录缺失兜底：即使对比源不存在，也会生成 `file-list.diff` 说明原因，避免只产出状态快照。
- `openvpn-compat-run.sh` 在线入口继续保留临时文件执行方式，确保服务器直接运行稳定。

### 提交记录
- 已创建本地提交：`5a4f0b4 feat: add PublicVPNList OpenVPN source`。
- 推送 `origin main` 失败：GitHub 返回 403，当前账号 `youshang8520` 没有 `baoweise-bot/aimili-vpngate` 的推送权限。
- 最新 `openvpn-compat.sh` 与 `openvpn-compat-run.sh` 需要同步发布到 fork，否则服务器端会继续拉到旧内容。

### 推送记录
- 用户已要求“复刻并推送”。
- 已通过 GitHub CLI 创建 fork：`https://github.com/youshang8520/aimili-vpngate`。
- 已添加远程：`fork https://github.com/youshang8520/aimili-vpngate.git`。
- 已将本地 `main` 分支推送到 fork。

### 文档与安装命令修正
- 用户指出描述和一键安装命令仍指向原仓库。
- 已修正 README 中文/英文项目描述，明确为 PublicVPNList 增强版。
- 已将 README 一键安装命令改为：`bash <(curl -Ls https://raw.githubusercontent.com/youshang8520/aimili-vpngate/main/install.sh)`。
- 已将 `install.sh` 默认仓库改为 `youshang8520/aimili-vpngate`，避免安装脚本拉回原仓库。
- 已将 Web UI GitHub 链接改为优先显示 fork，并保留原版项目链接。
- 已更新 GitHub fork 描述：`AimiliVPN fork with VPNGate + PublicVPNList OpenVPN sources, quality filtering, and local HTTP/SOCKS5 proxy`。
- 验证：`python -m py_compile vpngate_manager.py vpn_utils.py proxy_server.py`、`bash -n install.sh`、`git diff --check` 均通过。
