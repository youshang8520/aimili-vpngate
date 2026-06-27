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
- 之后又要求把 PublicVPNList 的真实交互点击下载链路整合进脚本，并测试能否成功下载 `.ovpn`。

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
- 已新增本地 Playwright 捕获脚本 `publicvpnlist_capture.py`，用于记录 PublicVPNList 下载页的初始状态、`Run current check` / `Generate .ovpn link` 的状态变化以及最终 `#dlReadyLink` 情况。
- 已按真实交互链路更新 `publicvpnlist_capture.py`，将下载流程收敛为按按钮点击生成临时链接，再读取 `#dlReadyLink`。
- 已把 `fetch_publicvpnlist_ovpn_config()` 改成先尝试直接解析链接，再回退到交互后页面的 `#dlReadyLink`。

### 验证记录
- `python -m py_compile vpngate_manager.py vpn_utils.py proxy_server.py`：通过。
- `bash -n install.sh`：先前通过；本轮安装器对照分析后仍需重新核对。
- `git diff --check`：通过。
- PublicVPNList 样例行解析验证：通过，能生成 `https://publicvpnlist.com/download/101398/`。
- PublicVPNList 实际 USA 国家页解析验证：通过，解析到 9 个过滤后条目，示例最高排序条目为 `87042 / 24.243.35.205 / 320.79 Mbps / 30 ms / score 69 / tcp`。
- MCP 抓取 `/download/87042/` 受站点 robots.txt 限制，未通过 MCP 查看实际下载内容；运行时代码会按页面 `/download/{data-id}/` 下载 `.ovpn`。
- 本轮已额外验证 `vpngate_manager.py` 语法编译通过。
- 已将 `openvpn-compat.sh` 方向切换为“服务器已安装相关文件备份版”，可一次导出 `/opt/aimilivpn`、`/etc/default/aimilivpn`、`/etc/sysctl.conf`、`/etc/openvpn/`、服务文件及 `vpngate_data`。
- 已完成备份态对照，当前服务器关键缺口在于 `OPENVPN_CMD` 仍需要指向兼容命令 `/usr/local/sbin/openvpn24-compat`，而仓库主线安装器要确保在新机/旧机上都能一次性落到该兼容路径或等价可用的兼容配置。
- 已补齐主线安装器与文档的默认兼容命令写入，避免新装后仍回落到普通 `openvpn`。
- 已开始把 `publicvpnlist_click_watch.json` 里的真实交互可用链路回写到脚本设计中。

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

### 本轮新增进展
- 已收束 `fetch_publicvpnlist_ovpn_config()`：静态解析失败后统一走详情页再到 Playwright 真实点击 `Run current check` / `Generate .ovpn link`，最后读取 `#dlReadyLink` 并尝试下载落盘。
- 已确认 `publicvpnlist_capture.py` 的交互顺序与主逻辑一致，可作为真实下载链路参考。
- 已新增 `publicvpnlist_batch_download.py` 专门执行国家页批量真实下载验证：国家页解析 → 条目详情页 → 只点击当前详情页 `#downloadCurrentCheckBtn` / `#dlStart` → `#dlReadyLink` → Playwright `expect_download()` → `save_as()`。
- 已修正批量验证中的误点问题：不能点击页面下方 Similar checked servers 里的 `Check & download`，否则会跳到相似服务器并下载错误配置；现在必须校验 `.ovpn` 内 `remote host port` 与当前条目 IP/端口匹配，否则不计入成功。
- 已执行 USA 国家页全量真实下载验证：`https://publicvpnlist.com/country/usa/` 解析 16 个条目，真实下载并校验成功 7 个，失败 9 个均为实时检查后不可达；成功文件落盘到 `publicvpnlist_downloads_usa_verified/`，清单写入 `publicvpnlist_usa_downloads.json` 和 `publicvpnlist_usa_downloads.csv`。
- 已通过 `python -m py_compile vpngate_manager.py publicvpnlist_capture.py publicvpnlist_batch_download.py` 语法检查。
- 已将成功链路正式接入生产逻辑：新增 `PUBLICVPNLIST_REQUIRE_REAL_DOWNLOAD=1` 默认开关；PublicVPNList 候选必须真实下载到 OpenVPN 配置，且 `.ovpn` 内 `remote host port` 必须与当前条目 IP/端口匹配，否则跳过，不再默认使用手工拼接配置兜底。
- 已修正 `publicvpnlist_capture.py`，参考脚本也只点击当前详情页 `#downloadCurrentCheckBtn` / `#dlStart`，避免误点 Similar checked servers 的 `Check & download`。
- 已新增 `requirements.txt` 并更新 `install.sh`：安装时创建 `/opt/aimilivpn/.venv`，安装 Python Playwright 与 Chromium；systemd/OpenRC 服务均改用 venv Python 启动，确保 Linux 服务器正式运行时能执行 PublicVPNList 真实交互下载链路。
- 已更新 README 中英文文档，说明真实点击下载链路、`PUBLICVPNLIST_REQUIRE_REAL_DOWNLOAD=1` 与 Playwright/Chromium 安装行为。
- 发布前校验：`python -m py_compile vpngate_manager.py publicvpnlist_capture.py publicvpnlist_batch_download.py` 通过；`bash -n install.sh` 通过；发布版批量脚本按 USA 前 8 个条目验证，真实下载并 remote 匹配成功 3 个，其余为站点实时检查不可达。
- 已确认下载下来的 `.ovpn` 可直接作为 OpenVPN 配置使用：生产连接流程会把节点 `config_text` 写入 `.ovpn` 文件，并通过 `OPENVPN_CMD --config <file>` 启动 OpenVPN。
- 已确认 PublicVPNList 来源不是固定 USA：`PUBLICVPNLIST_SOURCES` 留空且 `PUBLICVPNLIST_AUTO_COUNTRIES=1` 时会从 `PUBLICVPNLIST_COUNTRY_INDEX_URL` 自动发现所有 `/country/.../` 国家页；手动配置 `PUBLICVPNLIST_SOURCES` 时可指定一个或多个国家页。
- 已把默认 PublicVPNList 拉取策略改为全国家：`PUBLICVPNLIST_MAX_DOWNLOADS=0` 表示不限制总下载数，新增 `PUBLICVPNLIST_PER_COUNTRY_LIMIT=20`，每个国家页按 Speed Mbps 降序、Latency ms 升序、Technical score 降序排序后最多取 20 个，不足 20 个全部使用。
- 已把默认调度改为号池健康时每日刷新：`FETCH_INTERVAL_SECONDS=86400`、`CHECK_INTERVAL_SECONDS=86400`；若当前路由/国家范围内可用节点低于 `TARGET_VALID_NODES=3`，按 `LOW_POOL_RETRY_SECONDS=300` 重新拉取补池。
- 已按用户要求修正刷新/补池合并规则：重新拉取和每天定时刷新都不会删除已经验证可用的 IP；只有某个 IP 后续被检测为不可用，才会在后续合并中被淘汰；同时号池合并按 IP 去重，避免重复 IP。
