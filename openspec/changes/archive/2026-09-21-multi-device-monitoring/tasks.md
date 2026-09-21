# Tasks

## 1. 配置改造

- [x] 1.1 `load_config` 的必要字段由 `target_mac` 改为 `target_macs`，并校验其为非空列表。验证：缺失或空列表时抛 `ValueError`，合法列表通过
- [x] 1.2 新增 `mac -> 字母标识` 映射（按 `target_macs` 顺序生成 A、B、...）。验证：单测断言 `["m1","m2"]` 映射为 `{"m1":"A","m2":"B"}`

## 2. 多设备速度获取

- [x] 2.1 将 `get_device_speed` 重构为面向多设备（如 `get_device_speeds(ip, token, macs)`）：一次拉取 `device_list`，返回全部在线目标设备的 `(mac, speed_bps, name)` 列表。验证：mock requests 测试多目标混合在线/离线，断言离线设备不出现在结果中
- [x] 2.2 mock 模式下为每个目标设备返回相同固定速度与占位设备名。验证：mock 调用返回与 `target_macs` 等长的结果

## 3. 主循环集成

- [x] 3.1 告警状态由单个 `alert_state` 改为每设备字典 `alert_states`（按 mac 键）。验证：单测覆盖 A 告警、B 正常互不影响
- [x] 3.2 每次轮询为每台在线设备追加带 `device` 字母字段的记录。验证：mock 运行一轮后记录数与在线设备数一致，且 `device` 为对应字母
- [x] 3.3 告警标题与正文包含设备名。验证：mock 触发告警，断言 `sc_send` 入参标题含设备名

## 4. 验证

- [x] 4.1 空 `target_macs` 配置启动报错退出。验证：临时配置运行脚本，确认抛出 `ValueError` 并退出
- [x] 4.2 mock 多设备端到端验证：一台设备超阈值告警、另一台正常；离线设备被跳过且状态保留。验证：mock 运行并检查日志与状态输出
- [ ] 4.3 真实路由器手动验证多设备轮询与上传记录含 `device` 字段（需 Worker 侧已支持该字段）
