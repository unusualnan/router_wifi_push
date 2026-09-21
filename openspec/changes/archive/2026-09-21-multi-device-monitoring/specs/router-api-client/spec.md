## MODIFIED Requirements

### Requirement: 获取设备列表

系统 SHALL 调用 `device_list` 接口获取当前连接设备列表，每个设备包含 MAC 地址、设备名称和统计数据（含下行速度）。

#### Scenario: 获取成功

- **WHEN** 调用 `device_list` 接口成功
- **THEN** 返回设备列表，每个设备的 `statistics.downspeed` 为当前下行速度（Bit/s）

#### Scenario: 目标设备不在线

- **WHEN** 设备列表中不包含某个目标 MAC 地址
- **THEN** 该设备不出现在匹配结果中，不回退为速度 0