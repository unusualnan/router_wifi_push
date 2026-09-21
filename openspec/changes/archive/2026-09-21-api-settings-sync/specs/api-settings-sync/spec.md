## Purpose

在脚本启动时从 Cloudflare Worker API 拉取运行时配置（阈值、轮询间隔），覆盖本地默认值，使用户可通过 Web 界面调整参数而无需手动编辑配置文件。

## ADDED Requirements

### Requirement: 启动时从 API 拉取设置

脚本 SHALL 在启动时，当 `cloudflare_worker_url` 已配置时，尝试从 `{cloudflare_worker_url}/api/settings` 获取远程设置。

#### Scenario: API 可达，返回有效设置

- **WHEN** `cloudflare_worker_url` 已配置且 API 返回 HTTP 200 且响应体包含 `download_threshold_mbps` 和 `poll_interval` 字段
- **THEN** 使用 API 返回的值覆盖本地配置中的 `download_threshold_mbps` 和 `poll_interval`

#### Scenario: API 不可达（网络错误或超时）

- **WHEN** `cloudflare_worker_url` 已配置但请求失败（连接超时、DNS 解析失败、HTTP 非 200）
- **THEN** 使用本地 `config.yaml` 中的值，并记录一条警告日志

#### Scenario: API 返回无效数据

- **WHEN** `cloudflare_worker_url` 已配置但响应体缺少必要字段或字段类型不正确
- **THEN** 使用本地 `config.yaml` 中的值，并记录一条警告日志

### Requirement: 未配置时跳过 API 拉取

脚本 SHALL 在 `cloudflare_worker_url` 未配置或为空时，直接使用本地配置，不发起任何 API 请求。

#### Scenario: cloudflare_worker_url 未设置

- **WHEN** `config.yaml` 中 `cloudflare_worker_url` 字段不存在或为空字符串
- **THEN** 脚本使用本地配置启动，不尝试访问 API

### Requirement: 仅启动时拉取

脚本 SHALL 仅在启动阶段执行一次 API 设置拉取，主循环运行期间不再周期性拉取。

#### Scenario: 主循环期间不重新拉取

- **WHEN** 脚本已完成启动并进入主轮询循环
- **THEN** 不再向 `/api/settings` 发送请求

### Requirement: URL 拼接

脚本 SHALL 使用 `cloudflare_worker_url` 作为基础 URL，拼接 `/api/settings` 获取设置、拼接 `/api/upload` 上传数据。

#### Scenario: URL 拼接正确

- **WHEN** `cloudflare_worker_url` 为 `https://example.workers.dev`
- **THEN** 设置 API 地址为 `https://example.workers.dev/api/settings`，上传地址为 `https://example.workers.dev/api/upload`
