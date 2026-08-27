## Context

家庭网络中需要对特定设备的下行速度进行监控。路由器为 Redmi AX5400（RA74），运行 MiWiFi 固件，提供本地 HTTP API。现有开源方案（pymiwifi、python-xiaomi-miwifi）封装的 API 可能过时，因此选择直接调用原始 API 接口。脚本先部署在电脑上，后续考虑迁移到树莓派或旧安卓手机（Termux）。

## Goals / Non-Goals

**Goals:**
- 直接调用 MiWiFi 本地 HTTP API，仅依赖 `requests` 和 `serverchan-sdk`
- Token 过期自动重登，避免每次轮询重新认证
- 状态机告警逻辑，避免重复推送
- SendKey 通过环境变量读取，不硬编码
- 使用 `uv` 管理依赖和虚拟环境

**Non-Goals:**
- 不做多设备监控（先只监控单个 MAC）
- 不做累计流量统计
- 不做上行速度监控
- 不做 HA 集成
- 不做 Web 界面或 API 服务

## Decisions

### 1. 直接调用 API 而非使用 Python SDK

**选择**: 使用 `requests` 直接调用 3 个路由器 API 端点

**备选方案**:
- `pymiwifi`: API 简单但只支持旧固件 SHA1，无自动检测
- `python-xiaomi-miwifi`: 异步设计，功能全面但引入 `aiohttp` 依赖，对我们场景过重

**理由**: 直接调用代码量少（~30 行），依赖轻量（只需 `requests`），完全可控，不受第三方库更新节奏影响。

### 2. 密码哈希策略

**选择**: 通过 `init_info` 接口自动检测 `newEncryptMode`，决定 SHA256 或 SHA1

**流程**:
```
init_info -> newEncryptMode?
  = 1      -> SHA256(nonce + SHA256(password + key))
  = 0/空   -> SHA1(nonce + SHA1(password + key))
  请求失败  -> 先 SHA1，失败再 SHA256
```

**密钥**: `a2ffa5c9be07488bbb04a3a47d3c5f6a`（MiWiFi 固定公钥）

### 3. Token 过期重登策略

**选择**: 不主动刷新，仅在 API 返回 token 无效时重新登录

**理由**: 主动刷新需要维护 token 有效期计时器，增加复杂度。被动刷新更简单：登录接口调用成本低（一次 POST），且路由器本地请求延迟极低（<50ms）。

### 4. 状态机而非冷却期

**选择**: 两状态状态机（正常/告警中）

**备选方案**: 冷却期（如 5 分钟内不重复推送）

**理由**: 状态机更合理 —— 只要速度持续超过阈值，不应重复告警；只有回落再上升才需要再次通知。冷却期的问题是：如果速度持续高但冷却期内不推送，用户不知道当前状态。

### 5. 配置文件格式

**选择**: YAML 格式的 `config.yaml`

**理由**: 可读性好，Python 标准库不支持 YAML 但 `pyyaml` 是轻量依赖。也可用 JSON 但可读性差。环境变量仅用于 SendKey（安全敏感），其他配置放文件。

### 6. 使用 uv 管理环境

**选择**: 用 `uv` 创建虚拟环境、安装依赖

**理由**: 用户明确要求。`uv` 比 pip 快，且支持 `uv run` 直接运行脚本。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|---------|
| 路由器固件更新导致 API 变化 | 只用 3 个核心接口（init_info/login/device_list），这些是最稳定的 |
| Token 过期检测依赖错误码识别 | 如果路由器返回非标准错误码，重新登录即可 |
| 轮询频率过高导致路由器负载 | 默认 5 秒轮询，远低于路由器管理界面的 2 秒轮询 |
| Server酱免费额度有限（5 条/天） | 状态机逻辑确保不会频繁推送 |
| 旧安卓手机 Termux 兼容性 | 后续迁移时验证，当前不影响 |
