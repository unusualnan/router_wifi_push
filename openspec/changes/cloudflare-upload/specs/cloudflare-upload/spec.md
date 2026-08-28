## Purpose

将路由器采集的网速数据批量上传到 Cloudflare Worker，用于持久化存储和后续分析。

## ADDED Requirements

### Requirement: 采集数据缓存

系统 SHALL 在每次轮询时将当前采集的数据追加到本地内存缓存。

#### Scenario: 正常缓存

- **WHEN** 系统成功获取设备速度
- **THEN** 将当前时间戳和下行速度（MB/s）追加到缓存列表，上行速度固定为 0

#### Scenario: 缓存包含设备名称

- **WHEN** 缓存一条记录
- **THEN** 记录包含 ts（ISO 8601 UTC 时间）、download（MB/s）、upload（固定 0）

### Requirement: 批量上传

系统 SHALL 在缓存记录数达到 batch_size 或距上次上传超过 upload_interval 时，将缓存数据批量上传。

#### Scenario: 达到批量大小触发上传

- **WHEN** 缓存记录数 >= batch_size
- **THEN** 系统将所有缓存记录作为一次 POST 请求上传

#### Scenario: 达到上传间隔触发上传

- **WHEN** 距上次上传超过 upload_interval 秒且缓存非空
- **THEN** 系统将所有缓存记录作为一次 POST 请求上传

#### Scenario: 上传成功后清空缓存

- **WHEN** POST 请求返回成功
- **THEN** 系统清空本地缓存

### Requirement: 上传失败重试

系统 SHALL 在上传失败时保留缓存数据，下次上传时一并重试。

#### Scenario: 上传失败保留数据

- **WHEN** POST 请求失败（网络错误或非 2xx 响应）
- **THEN** 系统记录错误日志，保留缓存数据不丢弃

#### Scenario: 失败后下次重试

- **WHEN** 上次上传失败且再次触发上传
- **THEN** 系统将包含上次失败的记录一起上传

### Requirement: 上传格式

系统 SHALL 使用 POST 方法上传 JSON 数据到 Cloudflare Worker 的 /api/upload 接口。

#### Scenario: 正常上传

- **WHEN** 触发批量上传
- **THEN** POST 请求的 Body 为 `{"records": [{"ts": "...", "download": 123.4, "upload": 0}]}`

### Requirement: 可配置开关

系统 SHALL 支持通过 upload_enabled 配置项控制是否开启上传功能。

#### Scenario: 上传关闭

- **WHEN** upload_enabled 为 false 或未设置
- **THEN** 系统不执行任何上传逻辑，不缓存数据

#### Scenario: 上传开启

- **WHEN** upload_enabled 为 true
- **THEN** 系统按配置执行缓存和上传逻辑
