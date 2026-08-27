## Purpose

定时轮询指定设备的下行速度，超过阈值时通过 Server酱推送微信通知，采用状态机避免重复告警。

## ADDED Requirements

### Requirement: 定时轮询设备速度

系统 SHALL 以可配置的间隔（默认 5 秒）定时调用路由器 API 获取目标设备的瞬时下行速度。

#### Scenario: 正常轮询

- **WHEN** 轮询间隔到达
- **THEN** 系统调用路由器 API 获取目标 MAC 设备的当前下行速度

#### Scenario: 轮询失败

- **WHEN** 路由器 API 请求失败
- **THEN** 系统记录错误日志并在下个轮询周期重试

### Requirement: 可配置阈值

系统 SHALL 支持通过配置文件设置下行速度告警阈值（单位 MB/s）。

#### Scenario: 读取配置

- **WHEN** 系统启动
- **THEN** 从配置文件读取阈值（MB/s）并转换为 Bit/s 用于比较

### Requirement: 状态机告警逻辑

系统 SHALL 采用两状态状态机（正常/告警中），仅在状态变化时触发推送。

#### Scenario: 速度从正常变为超过阈值

- **WHEN** 当前状态为「正常」且下行速度超过阈值
- **THEN** 系统切换状态为「告警中」并发送一次推送

#### Scenario: 告警中速度持续超过阈值

- **WHEN** 当前状态为「告警中」且下行速度仍超过阈值
- **THEN** 系统不发送推送

#### Scenario: 速度从超过阈值回落到正常

- **WHEN** 当前状态为「告警中」且下行速度低于阈值
- **THEN** 系统切换状态为「正常」

#### Scenario: 速度再次超过阈值

- **WHEN** 当前状态为「正常」且下行速度超过阈值（之前已回落过）
- **THEN** 系统切换状态为「告警中」并再次发送推送

### Requirement: Server酱微信推送

系统 SHALL 使用 serverchan-sdk 的 `sc_send` 函数推送通知，SendKey 从环境变量 `SERVERCHAN_SENDKEY` 读取。

#### Scenario: 推送成功

- **WHEN** `sc_send` 返回 `code=0`
- **THEN** 推送完成

#### Scenario: 推送失败

- **WHEN** `sc_send` 返回非零 code 或抛出异常
- **THEN** 系统记录错误日志但不影响后续轮询

#### Scenario: SendKey 未配置

- **WHEN** 环境变量 `SERVERCHAN_SENDKEY` 不存在
- **THEN** 系统启动时打印错误信息并退出

### Requirement: 通知内容格式

推送通知 SHALL 包含设备名称、当前下行速度和阈值信息。

#### Scenario: 正常推送

- **WHEN** 触发告警推送
- **THEN** 标题为「设备网速告警」，正文包含设备名称、当前速度（MB/s）和阈值（MB/s）
