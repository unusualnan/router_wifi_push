# AGENTS.md

## Project

MiWiFi 路由器设备网速监控脚本。定时轮询指定 MAC 设备的下行速度，超过阈值通过 Server酱推送微信通知。

## Run

```bash
export SERVERCHAN_SENDKEY="你的SendKey"
uv run python src/wifi_speed_monitor.py
```

## Dependencies

管理工具: `uv`（不用 pip）。安装/添加依赖: `uv add <pkg>`。

核心依赖: `requests`, `serverchan-sdk`, `pyyaml`

## Config

`config.yaml` 包含路由器 IP、密码、目标 MAC、阈值等。`SERVERCHAN_SENDKEY` 必须通过环境变量设置，不写在配置文件里。

## Architecture

单文件脚本 `wifi_speed_monitor.py` (~200行)，包含:
- 路由器 API 客户端（login, device_list, 自动检测 SHA1/SHA256）
- 状态机告警逻辑（normal/alerting，状态变化时推送一次）
- Server酱微信推送

路由器 API: 直接调用 MiWiFi 本地 HTTP API，不依赖第三方 miwifi SDK。只用 3 个接口: `init_info`, `login`, `device_list`。
