## 1. 项目初始化

- [x] 1.1 使用 `uv init` 创建项目结构，创建 `config.yaml` 配置文件模板（router_ip, router_password, target_mac, download_threshold_mbps, poll_interval, cooldown）
- [x] 1.2 用 `uv add requests serverchan-sdk pyyaml` 安装依赖，验证 `uv run python -c "import requests; import serverchan_sdk; import yaml"` 成功

## 2. 路由器 API 客户端

- [x] 2.1 实现 `get_init_info(ip)` 函数：调用 `/api/xqsystem/init_info`，返回 `newEncryptMode` 字段
- [x] 2.2 实现 `generate_nonce()` 函数：生成 `0_{random}_{timestamp}_{random_int}` 格式的 nonce
- [x] 2.3 实现 `hash_password(password, nonce, encrypt_mode)` 函数：根据 encrypt_mode 使用 SHA256 或 SHA1 哈希
- [x] 2.4 实现 `login(ip, password)` 函数：调用登录接口获取 token，验证 `code=0` 时返回 token
- [x] 2.5 实现 `get_device_list(ip, token)` 函数：调用 `device_list` 接口返回设备列表 JSON
- [x] 2.6 实现 `get_device_speed(ip, token, target_mac)` 函数：在设备列表中查找目标 MAC，返回 downspeed（Bit/s），设备不在线返回 0

## 3. 配置与主流程

- [x] 3.1 实现 `load_config(path)` 函数：读取 `config.yaml`，校验必要字段存在
- [x] 3.2 实现环境变量检查：启动时检查 `SERVERCHAN_SENDKEY`，缺失则打印错误并退出
- [x] 3.3 实现主循环：按 `poll_interval` 间隔轮询，包含 token 过期重登逻辑（捕获异常后重新登录并重试）

## 4. 告警与通知

- [x] 4.1 实现状态机：维护 `alert_state`（normal/alerting），根据阈值比较切换状态
- [x] 4.2 实现 `send_alert(sendkey, device_name, speed_mbps, threshold_mbps)` 函数：调用 `sc_send` 推送微信通知，内容包含设备名、当前速度和阈值
- [x] 4.3 将状态机与推送集成到主循环：状态从 normal 切换到 alerting 时调用 `send_alert`

## 5. 验证

- [x] 5.1 用 `uv run python src/router_wifi_push/wifi_speed_monitor.py` 运行脚本，确认能成功登录路由器并获取设备速度（打印到控制台）
- [ ] 5.2 设置低阈值（如 0.1 MB/s）触发告警推送，确认微信收到通知（需连接真实路由器手动验证）
- [ ] 5.3 确认状态机工作：持续超过阈值时不重复推送，回落后再次超过时重新推送（需连接真实路由器手动验证）
