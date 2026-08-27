## Why

家庭网络中需要监控特定设备的 WiFi 下行速度，当速度超过阈值时通过微信推送告警。用于发现异常流量（如后台下载、设备被入侵等场景）。现有方案要么依赖 HA 生态过于重量级，要么 Python 库封装的 API 可能过时，因此选择直接调用 MiWiFi 本地 API 实现轻量监控。

## What Changes

- 新增一个独立 Python 脚本 `wifi_speed_monitor.py`，定时轮询路由器获取指定 MAC 设备的瞬时下行速度
- 直接调用 MiWiFi 路由器本地 HTTP API（`init_info`、`login`、`device_list`），不依赖第三方 miwifi SDK
- 密码哈希自动检测：通过 `init_info` 接口的 `newEncryptMode` 字段判断使用 SHA256（新固件）或 SHA1（老固件）
- Token 过期自动重新登录，避免每次轮询都重新认证
- 下行速度超过可配置阈值时，通过 Server酱（serverchan-sdk）推送微信通知
- 采用状态机逻辑：仅在速度从「正常」变为「超过阈值」时推送，避免重复告警；速度回落后恢复「正常」状态
- SendKey 通过环境变量 `SERVERCHAN_SENDKEY` 读取，不硬编码
- 使用 `uv` 管理 Python 依赖和虚拟环境

## Capabilities

### New Capabilities

- `router-api-client`: MiWiFi 路由器 API 客户端 —— 封装登录、认证、设备列表获取等路由器交互逻辑
- `speed-alert-monitor`: 网速告警监控 —— 定时轮询、阈值比较、状态机判断、Server酱通知推送

### Modified Capabilities

（无，这是新项目）

## Impact

- **新增文件**: `wifi_speed_monitor.py`（主脚本）、`config.yaml`（配置）、`requirements.txt`（依赖）
- **依赖**: `requests`（HTTP 请求）、`serverchan-sdk`（微信推送）、`hashlib`/`secrets`/`time`（标准库）
- **运行环境**: Python 3.8+，uv 管理虚拟环境
- **网络**: 脚本需与路由器在同一局域网（LAN），可访问 `192.168.31.1`
- **外部服务**: Server酱（sct.ftqq.com）微信推送，免费额度 5 条/天
- **兼容性**: 支持 Redmi AX5400（RA74）及其他 MiWiFi 固件路由器
