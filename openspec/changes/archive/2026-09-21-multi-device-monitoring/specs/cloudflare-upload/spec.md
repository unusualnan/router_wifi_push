## MODIFIED Requirements

### Requirement: 采集数据缓存

系统 SHALL 在每次轮询时，为每台在本轮获得速度的设备各追加一条数据到本地内存缓存。

#### Scenario: 正常缓存

- **WHEN** 系统成功获取某台设备的速度
- **THEN** 将该设备的时间戳和下行速度（MB/s）追加到缓存列表，上行速度固定为 0

#### Scenario: 缓存包含设备名称

- **WHEN** 缓存一条记录
- **THEN** 记录包含 ts（ISO 8601 UTC 时间）、device（按目标设备列表顺序自动分配的字母）、download（MB/s）、upload（固定 0）

### Requirement: 上传格式

系统 SHALL 使用 POST 方法上传 JSON 数据到 Cloudflare Worker 的 /api/upload 接口。

#### Scenario: 正常上传

- **WHEN** 触发批量上传
- **THEN** POST 请求的 Body 为 `{"records": [{"ts": "...", "device": "A", "download": 123.4, "upload": 0}]}`