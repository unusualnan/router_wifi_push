## Context

`wifi_speed_monitor.py` 当前从本地 `config.yaml` 读取所有配置。Cloudflare Worker 已提供 `GET /api/settings` 接口（返回 `AppSettings`：`download_threshold_mbps` + `poll_interval`）和 `PUT /api/settings` 接口。需要在脚本启动时拉取远程设置覆盖本地默认值。

本地配置中可被 API 覆盖的字段：`download_threshold_mbps`、`poll_interval`。
本地配置中保持不变的字段：`router_ip`、`router_password`、`target_mac`、`upload_enabled`、`cloudflare_worker_url`、`upload_interval`、`batch_size`、`mock_mode`。
`cloudflare_worker_url` 存储基础 URL，脚本中拼接 `/api/upload`（上传）和 `/api/settings`（设置拉取）。

## Goals / Non-Goals

**Goals:**
- 启动时从 API 拉取设置，成功则覆盖本地值，失败则回退本地
- 从 `cloudflare_worker_url` 推导基础 URL（剥离 `/api/upload`）
- API 请求设置合理超时（5 秒），不阻塞启动流程过久

**Non-Goals:**
- 不做周期性重拉（仅启动时一次）
- 不做设置持久化回写（PUT 接口由 Web 端使用）
- 不做多字段合并策略（简单替换：有 API 值就用，没有就用本地）

## Decisions

### 1. 替换策略而非合并

**选择**: API 返回的 `download_threshold_mbps` 和 `poll_interval` 直接替换本地值

**备选方案**: 只在 API 值非 null 时替换

**理由**: API 返回的总是完整 `AppSettings` 对象（含默认值），不存在 null 情况。简单替换逻辑清晰，无需额外判断。

### 2. 超时 5 秒

**选择**: API 请求超时设为 5 秒

**理由**: 脚本部署在同一网络环境（树莓派/电脑），路由器本地请求 <50ms。5 秒足够应对网络波动，同时不会在 API 真正不可达时阻塞过久。

### 3. cloudflare_worker_url 存储基础 URL

**选择**: `cloudflare_worker_url` 只存基础 URL（如 `https://xxx.workers.dev`），脚本中拼接 `/api/upload` 和 `/api/settings`

**备选方案**: 存完整上传地址，脚本中剥离后缀

**理由**: 配置更直观，用户不需要关心 URL 拼接细节。上传和设置两个端点由脚本自行组装。

### 4. 失败时静默回退

**选择**: API 不可达或返回无效数据时，记录 warning 日志并使用本地配置

**备选方案**: 打印错误并退出

**理由**: 设置拉取是锦上添花功能，不应因为 API 暂时不可用而阻止脚本启动。脚本的核心功能（路由器监控）不依赖此 API。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| API 返回异常值导致脚本行为异常 | 仅覆盖两个数值字段，后续主循环的阈值比较本身就会处理异常值 |
| 启动时 API 不可达，用户不知道远程设置未生效 | 记录 warning 日志说明回退到本地配置 |
| cloudflare_worker_url 配置错误（如包含 /api/upload） | 脚本直接拼接，异常 URL 会导致上传和设置拉取同时失败，用户易于排查 |
