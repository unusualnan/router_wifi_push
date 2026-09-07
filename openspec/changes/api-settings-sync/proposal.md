## Why

脚本当前从本地 `config.yaml` 读取所有配置，包括 `download_threshold_mbps` 和 `poll_interval`。但 Cloudflare Worker 已经有 `/api/settings` 接口支持远程读写这两个参数。为了能在 Web 界面上调整阈值和轮询间隔而不用手动改配置文件重启脚本，需要在启动时从 API 拉取配置覆盖本地默认值。

## What Changes

- 启动时从 `{cloudflare_worker_url}/api/settings` 拉取远程配置
- 如果 `cloudflare_worker_url` 未配置或 API 不可达，回退到本地 `config.yaml` 的值
- API 返回的 `download_threshold_mbps` 和 `poll_interval` 覆盖本地同名字段
- 仅在启动时拉取一次，不进行周期性重拉
- `cloudflare_worker_url` 存储基础 URL，脚本中拼接 `/api/upload` 和 `/api/settings`

## Capabilities

### New Capabilities

- `api-settings-sync`: 启动时从 Cloudflare Worker API 拉取配置并覆盖本地默认值的能力

### Modified Capabilities

（无）

## Impact

- **代码**: `wifi_speed_monitor.py` 的启动流程（`main()` 函数前段）
- **配置**: `cloudflare_worker_url` 字段现在同时用于上传和设置拉取
- **网络**: 启动时多一次 HTTP GET 请求（仅当 `cloudflare_worker_url` 配置时）
- **依赖**: 无新增依赖，仍使用 `requests`
