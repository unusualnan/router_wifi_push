# Proposal

## Why

当前脚本只监控单个目标设备（`target_mac`），无法同时跟踪家中多台设备的网速。设备数量增加后，希望一次轮询就能获得多台设备的实时速度、分别按阈值告警，并把数据按设备区分上传，便于在 Web 端分别查看。

## What Changes

- 配置项 `target_mac`（单个字符串）改为 `target_macs`（MAC 列表），**BREAKING**
- 每个轮询周期只拉取一次 `device_list`，按 `target_macs` 过滤出全部在线设备
- 每台在线设备独立维护告警状态机（normal/alerting），共享同一个 `download_threshold_mbps`
- 设备不在线时直接跳过：不记录、不告警、不改变其告警状态
- 上传记录新增 `device` 字段，值为按 `target_macs` 列表顺序自动分配的字母（A、B、...）
- 告警通知标题与正文包含具体设备名（取自路由器 `device_list` 返回的 name）
- mock 模式下每台目标设备返回相同速度，用于本地验证多设备逻辑

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `speed-alert-monitor`: 轮询对象由单设备改为多设备；配置项由 `target_mac` 改为 `target_macs` 列表；告警状态机由单一状态改为每设备独立；通知标题区分设备
- `router-api-client`: 目标设备不在线时的行为由「返回速度 0」改为「跳过、不出现在结果中」
- `cloudflare-upload`: 采集记录与上传 Body 新增 `device` 字段以区分设备

## Impact

- **代码**: `wifi_speed_monitor.py` 的配置加载、设备速度获取、主循环告警/上传逻辑
- **配置**: `config.yaml` 需从 `target_mac` 迁移为 `target_macs`（本地手改）
- **数据模型**: Cloudflare Worker 与 D1 需支持 `device` 字段（由用户在 Worker 侧同步修改）
- **依赖**: 无新增依赖
