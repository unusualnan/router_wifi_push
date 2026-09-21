## Why

路由器采集的网速数据目前只用于实时告警，没有持久化存储。需要将数据定期上传到 Cloudflare Worker，用于后续的历史查询、趋势分析和可视化。

## What Changes

- 新增 Cloudflare Worker 上传功能：将采集到的网速数据批量 POST 到 `/api/upload` 接口
- 本地缓存机制：每次轮询将数据追加到内存缓存，达到批量大小或上传间隔时一次性发送
- 失败重试：上传失败时保留数据，下次上传时一并重试
- 新增配置项：upload_enabled、cloudflare_worker_url、upload_interval、batch_size
- 上行速度字段暂时固定填 0，后续可扩展

## Capabilities

### New Capabilities

- `cloudflare-upload`: 数据上传能力 —— 本地数据缓存、批量上传到 Cloudflare Worker、失败重试逻辑

### Modified Capabilities

（无，原有告警逻辑不变）

## Impact

- **修改文件**: `src/wifi_speed_monitor.py`（主循环中增加数据缓存和上传逻辑）、`config.yaml`（新增配置项）
- **新增依赖**: 无（复用 `requests`）
- **外部服务**: Cloudflare Worker（用户自建）
- **API 格式**: POST `/api/upload`，Body: `{"records": [{"ts": "...", "download": 123.4, "upload": 0}]}`
