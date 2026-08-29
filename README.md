# MiWiFi 路由器设备网速监控

定时轮询指定 MAC 设备的下行速度，超过阈值通过 Server酱 推送微信通知。

## 功能

- 轮询指定设备下行速度
- 超过阈值通过 Server酱 微信推送
- 自动检测路由器加密模式（SHA1/SHA256）
- 支持数据上传到 Cloudflare Worker

## 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/unusualnan/router_wifi_push.git
cd router_wifi_push
```

### 2. 安装依赖

```bash
uv sync --python $(which python)
```

或使用 pip：

```bash
pip install -r requirements.txt
```

### 3. 配置

复制并编辑配置文件：

```bash
cp config.yaml.example config.yaml
```

修改 `config.yaml` 中的路由器信息：

```yaml
router_ip: "192.168.31.1"
router_password: "你的路由器密码"
target_mac: "AA:BB:CC:DD:EE:FF"  # 监控设备的 MAC 地址
download_threshold_mbps: 10       # 告警阈值 (MB/s)
poll_interval: 5                  # 轮询间隔 (秒)
```

### 4. 设置环境变量

```bash
export SERVERCHAN_SENDKEY="你的SendKey"
```

### 5. 运行

```bash
uv run python src/wifi_speed_monitor.py
```

## 部署到安卓手机 (Termux)

### 安装 Termux

从 F-Droid 或 GitHub 下载安装 [Termux](https://github.com/termux/termux-app)。

### 安装依赖

```bash
# 更新包管理器
pkg update && pkg upgrade

# 安装 Python 和 git
pkg install python git

# 安装 uv
pkg install uv

# 克隆仓库
git clone https://github.com/unusualnan/router_wifi_push.git
cd router_wifi_push

# 安装 Python 依赖
uv sync --python $(which python)
```

### 运行脚本

```bash
export SERVERCHAN_SENDKEY="你的SendKey"
uv run python src/wifi_speed_monitor.py
```

### 后台运行

使用 `tmux` 或 `screen` 保持会话：

```bash
# 安装 tmux
pkg install tmux

# 创建新会话
tmux new -s monitor

# 运行脚本
uv run python src/wifi_speed_monitor.py

# 断开会话: Ctrl+B, 然后按 D
# 重新连接: tmux attach -t monitor
```

### 开机自启（可选）

创建启动脚本：

```bash
cat > ~/start_monitor.sh << 'EOF'
#!/data/data/com.termux/files/usr/bin/bash
cd ~/router_wifi_push
export SERVERCHAN_SENDKEY="你的SendKey"
uv run python src/wifi_speed_monitor.py
EOF

chmod +x ~/start_monitor.sh
```

## 配置说明

| 字段 | 说明 | 默认值 |
|------|------|--------|
| `router_ip` | 路由器 IP 地址 | 必填 |
| `router_password` | 路由器密码 | 必填 |
| `target_mac` | 监控设备 MAC 地址 | 必填 |
| `download_threshold_mbps` | 下行速度告警阈值 (MB/s) | 必填 |
| `poll_interval` | 轮询间隔 (秒) | 5 |
| `mock_mode` | 模拟模式（测试用） | false |
| `upload_enabled` | 启用数据上传 | false |
| `cloudflare_worker_url` | Worker URL | - |
| `upload_interval` | 上传间隔 (秒) | 300 |
| `batch_size` | 批量上传条数 | 60 |

## 注意事项

- `SERVERCHAN_SENDKEY` 必须通过环境变量设置，不要写在配置文件中
- 路由器 API 响应较慢（约 3 秒），这是路由器固件的限制
- WiFi 切换（2.4G/5G）可能导致短暂断连，脚本会自动重连
