import hashlib
import logging
import random
import re
import time
import os
import sys

import requests
import yaml
from serverchan_sdk import sc_send

def red(text: str) -> str:
    """终端下用 ANSI 红色包裹文本，重定向到非终端时返回原样。"""
    if sys.stdout.isatty():
        return f"\x1b[31m{text}\x1b[0m"
    return text


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

MOCK_SPEED_BPS = 8 * 1024 * 1024  # 8 MB/s


def get_init_info(ip: str) -> dict:
    """获取路由器初始化信息，包含 newEncryptMode 字段。"""
    url = f"http://{ip}/cgi-bin/luci/api/xqsystem/init_info"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def get_web_info(ip: str) -> tuple[str, str]:
    """从路由器管理页面获取 nonce_key 和设备 MAC 地址。"""
    url = f"http://{ip}/cgi-bin/luci/web"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    html = resp.text

    mac_match = re.search(r"var deviceId = '(.*?)'", html)
    key_match = re.search(r"key: '(.*?)'", html)

    if not mac_match or not key_match:
        raise RuntimeError("无法从路由器页面提取 deviceId 或 nonce_key")

    mac = mac_match.group(1)
    nonce_key = key_match.group(1)
    log.info("获取到设备 MAC: %s, nonce_key: %s", mac, nonce_key[:8] + "...")
    return mac, nonce_key


def generate_nonce(mac: str) -> str:
    """生成 MiWiFi 登录所需的 nonce 字符串。"""
    rand_part = random.randint(1000, 9999)
    ts = int(time.time())
    return f"0_{mac}_{ts}_{rand_part}"


def hash_password(password: str, nonce: str, nonce_key: str, encrypt_mode: int) -> str:
    """根据加密模式对密码进行哈希。encrypt_mode=1 使用 SHA256，否则 SHA1。"""
    if encrypt_mode == 1:
        inner = hashlib.sha256((password + nonce_key).encode()).hexdigest()
        return hashlib.sha256((nonce + inner).encode()).hexdigest()
    else:
        inner = hashlib.sha1((password + nonce_key).encode()).hexdigest()
        return hashlib.sha1((nonce + inner).encode()).hexdigest()


def login(ip: str, password: str) -> str:
    """登录路由器，返回 token (stok)。自动检测加密方式。"""
    mac, nonce_key = get_web_info(ip)

    encrypt_mode = 0
    try:
        init_info = get_init_info(ip)
        encrypt_mode = init_info.get("newEncryptMode", 0)
        log.info("检测到加密模式: %s", "SHA256" if encrypt_mode == 1 else "SHA1")
    except Exception:
        log.warning("无法获取 init_info，默认使用 SHA1")

    nonce = generate_nonce(mac)
    hashed_pwd = hash_password(password, nonce, nonce_key, encrypt_mode)

    url = f"http://{ip}/cgi-bin/luci/api/xqsystem/login"
    data = {
        "username": "admin",
        "password": hashed_pwd,
        "logtype": "2",
        "nonce": nonce,
    }
    resp = requests.post(url, data=data, timeout=10)
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") == 0 and "token" in result:
        log.info("登录成功")
        return result["token"]

    # SHA1 失败，尝试 SHA256
    if encrypt_mode == 0:
        log.warning("SHA1 登录失败，尝试 SHA256")
        encrypt_mode = 1
        nonce = generate_nonce(mac)
        hashed_pwd = hash_password(password, nonce, nonce_key, encrypt_mode)
        data["password"] = hashed_pwd
        data["nonce"] = nonce
        resp = requests.post(url, data=data, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") == 0 and "token" in result:
            log.info("SHA256 登录成功")
            return result["token"]

    raise RuntimeError(f"登录失败: {result}")


def get_device_list(ip: str, token: str) -> list:
    """获取当前连接设备列表。"""
    url = f"http://{ip}/cgi-bin/luci/;stok={token}/api/xqsystem/device_list"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") != 0:
        raise RuntimeError(f"获取设备列表失败: {result}")
    return result.get("list", [])


def build_device_labels(macs: list) -> dict:
    """按列表顺序为每台目标设备生成字母标识 (A, B, ...)。"""
    return {mac: chr(ord("A") + i) for i, mac in enumerate(macs)}


def get_device_speeds(ip: str, token: str, macs: list, mock: bool = False) -> list:
    """一次获取全部目标设备的下行速度。

    返回 [(mac, downspeed_bps, device_name), ...]，仅包含设备列表中在线的目标设备；
    离线设备不出现在结果中。mock 模式下每台返回相同固定速度。
    """
    if mock:
        labels = build_device_labels(macs)
        return [(mac, MOCK_SPEED_BPS, f"MockDevice-{labels[mac]}") for mac in macs]

    devices = get_device_list(ip, token)
    by_mac = {d.get("mac", "").upper(): d for d in devices}
    result = []
    for mac in macs:
        dev = by_mac.get(mac.upper())
        if dev is None:
            continue
        speed = int(dev.get("statistics", {}).get("downspeed", 0))
        result.append((mac, speed, dev.get("name", mac)))
    return result


def load_config(path: str = "config.yaml") -> dict:
    """读取配置文件并校验必要字段。"""
    with open(path, "r") as f:
        config = yaml.safe_load(f)

    required = ["router_ip", "router_password", "target_macs", "download_threshold_mbps"]
    for key in required:
        if key not in config:
            raise ValueError(f"配置文件缺少必要字段: {key}")

    if not isinstance(config["target_macs"], list) or not config["target_macs"]:
        raise ValueError("配置字段 target_macs 必须是非空列表")

    return config


def get_sendkey() -> str:
    """从环境变量获取 Server酱 SendKey，缺失则退出。"""
    key = os.environ.get("SERVERCHAN_SENDKEY")
    if not key:
        log.error("环境变量 SERVERCHAN_SENDKEY 未设置")
        log.error("请运行: export SERVERCHAN_SENDKEY='你的SendKey'")
        sys.exit(1)
    return key


def fetch_api_settings(base_url: str) -> dict | None:
    """从 Cloudflare Worker API 拉取远程设置。成功返回 dict，失败返回 None。"""
    url = f"{base_url}/api/settings"
    try:
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if "download_threshold_mbps" in data and "poll_interval" in data:
            log.info("从 API 获取设置: threshold=%.4f, interval=%ds",
                     data["download_threshold_mbps"], data["poll_interval"])
            return data
        log.warning("API 设置缺少必要字段: %s", data)
        return None
    except Exception as e:
        log.warning("获取 API 设置失败: %s", e)
        return None


def merge_settings(local_config: dict, api_settings: dict) -> dict:
    """用 API 设置覆盖本地配置中的可覆盖字段，返回新 dict。"""
    result = dict(local_config)
    result["download_threshold_mbps"] = api_settings["download_threshold_mbps"]
    result["poll_interval"] = api_settings["poll_interval"]
    return result


def evaluate_alert(alert_states: dict, mac: str, speed_bps: int, threshold_bps: int) -> str | None:
    """按阈值更新某设备的告警状态，返回状态变化: 'alert' | 'recover' | None。"""
    if speed_bps > threshold_bps:
        if alert_states[mac] == "normal":
            alert_states[mac] = "alerting"
            return "alert"
        return None
    if alert_states[mac] == "alerting":
        alert_states[mac] = "normal"
        return "recover"
    return None


def send_alert(sendkey: str, device_name: str, speed_mbps: float, threshold_mbps: float) -> None:
    """通过 Server酱推送网速告警。"""
    title = f"设备网速告警: {device_name}"
    desp = (
        f"**设备**: {device_name}\n\n"
        f"**当前下行速度**: {speed_mbps:.2f} MB/s\n\n"
        f"**告警阈值**: {threshold_mbps:.2f} MB/s"
    )
    try:
        result = sc_send(sendkey, title, desp)
        if result.get("code") == 0:
            log.info("告警推送成功")
        else:
            log.warning("告警推送失败: %s", result.get("message"))
    except Exception as e:
        log.error("告警推送异常: %s", e)


def upload_records(records: list, url: str) -> bool:
    """批量上传采集记录到 Cloudflare Worker。成功返回 True，失败返回 False。"""
    if not records:
        return True
    payload = {"records": records}
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        log.info("上传成功: %d 条记录", len(records))
        return True
    except Exception as e:
        log.error("上传失败: %s，将保留数据下次重试", e)
        return False


def main() -> None:
    from datetime import datetime, timezone

    config = load_config()
    sendkey = get_sendkey()

    ip = config["router_ip"]
    password = config["router_password"]
    target_macs = config["target_macs"]
    device_labels = build_device_labels(target_macs)
    threshold_mbps = config["download_threshold_mbps"]
    poll_interval = config.get("poll_interval", 5)
    mock_mode = config.get("mock_mode", False)

    upload_enabled = config.get("upload_enabled", False)
    worker_url = config.get("cloudflare_worker_url", "")
    upload_interval = config.get("upload_interval", 300)
    batch_size = config.get("batch_size", 60)

    # 从 API 拉取远程设置（仅启动时一次）
    if worker_url:
        api_settings = fetch_api_settings(worker_url)
        if api_settings:
            config = merge_settings(config, api_settings)
            threshold_mbps = config["download_threshold_mbps"]
            poll_interval = config["poll_interval"]
            log.info("使用 API 设置: threshold=%.4f, interval=%d",
                     threshold_mbps, poll_interval)
        else:
            log.warning("API 设置不可用，使用本地配置: threshold=%.4f, interval=%d",
                        threshold_mbps, poll_interval)
    else:
        log.info("未配置 cloudflare_worker_url，跳过 API 设置拉取")

    threshold_bps = int(threshold_mbps * 1024 * 1024)
    alert_states = {mac: "normal" for mac in target_macs}
    records = []
    last_upload_time = time.time()

    if mock_mode:
        log.info("Mock 模式: 路由器 API 将返回假数据")

    if upload_enabled and worker_url:
        log.info("上传已启用: Worker=%s, 间隔=%ds, 批大小=%d", worker_url, upload_interval, batch_size)

    log.info("启动监控: 目标MAC=%s, 阈值=%.4f MB/s, 轮询间隔=%ds", ",".join(target_macs), threshold_mbps, poll_interval)

    token = ""
    if not mock_mode:
        token = login(ip, password)

    while True:
        loop_start = time.time()
        try:
            t0 = time.time()
            speeds = get_device_speeds(ip, token, target_macs, mock=mock_mode)
            api_time = time.time() - t0
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

            for mac, speed_bps, device_name in speeds:
                label = device_labels[mac]
                speed_mbps = speed_bps / 1024 / 1024

                log.info("设备 %s(%s) 下行速度: %s MB/s (API耗时 %.2fs)", device_name, label, red(f"{speed_mbps:.2f}"), api_time)

                # 阈值告警（每设备独立状态机）
                transition = evaluate_alert(alert_states, mac, speed_bps, threshold_bps)
                if transition == "alert":
                    log.warning("设备 %s 速度超过阈值，触发告警", device_name)
                    send_alert(sendkey, device_name, speed_mbps, threshold_mbps)
                elif transition == "recover":
                    log.info("设备 %s 速度回落到阈值以下，恢复正常", device_name)

                # 数据缓存
                if upload_enabled and worker_url:
                    records.append({"ts": ts, "device": label, "download": round(speed_mbps, 2), "upload": 0})

            # 双触发上传（每轮检查一次）
            if upload_enabled and worker_url:
                now = time.time()
                should_upload = len(records) >= batch_size or (now - last_upload_time) >= upload_interval
                if should_upload and records:
                    if upload_records(records, f"{worker_url}/api/upload"):
                        records = []
                    last_upload_time = now

        except requests.exceptions.RequestException as e:
            log.error("网络请求失败: %s", e)
            if not mock_mode:
                try:
                    token = login(ip, password)
                except Exception as login_err:
                    log.error("重新登录失败: %s", login_err)
        except RuntimeError as e:
            log.error("API 错误: %s", e)
            if not mock_mode:
                try:
                    token = login(ip, password)
                except Exception as login_err:
                    log.error("重新登录失败: %s", login_err)
        except Exception as e:
            log.error("轮询异常: %s", e)

        time.sleep(max(0, poll_interval - (time.time() - loop_start)))


if __name__ == "__main__":
    main()
