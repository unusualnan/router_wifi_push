import hashlib
import logging
import random
import time
import os
import sys

import requests
import yaml
from serverchan_sdk import sc_send

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

MIWIFI_KEY = "a2ffa5c9be07488bbb04a3a47d3c5f6a"

MOCK_SPEED_BPS = 8 * 1024 * 1024  # 8 MB/s


def get_init_info(ip: str) -> dict:
    """获取路由器初始化信息，包含 newEncryptMode 字段。"""
    url = f"http://{ip}/api/xqsystem/init_info"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    return resp.json()


def generate_nonce() -> str:
    """生成 MiWiFi 登录所需的 nonce 字符串。"""
    rand_part = random.randint(0, 9999)
    ts = int(time.time())
    return f"0_{ts}_{rand_part}"


def hash_password(password: str, nonce: str, encrypt_mode: int) -> str:
    """根据加密模式对密码进行哈希。encrypt_mode=1 使用 SHA256，否则 SHA1。"""
    if encrypt_mode == 1:
        inner = hashlib.sha256((password + MIWIFI_KEY).encode()).hexdigest()
        return hashlib.sha256((nonce + inner).encode()).hexdigest()
    else:
        inner = hashlib.sha1((password + MIWIFI_KEY).encode()).hexdigest()
        return hashlib.sha1((nonce + inner).encode()).hexdigest()


def login(ip: str, password: str) -> str:
    """登录路由器，返回 token (stok)。自动检测加密方式。"""
    try:
        init_info = get_init_info(ip)
        encrypt_mode = init_info.get("newEncryptMode", 0)
        log.info("检测到加密模式: %s", "SHA256" if encrypt_mode == 1 else "SHA1")
    except Exception:
        log.warning("无法获取 init_info，默认使用 SHA1")
        encrypt_mode = 0

    nonce = generate_nonce()
    hashed_pwd = hash_password(password, nonce, encrypt_mode)

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
        nonce = generate_nonce()
        hashed_pwd = hash_password(password, nonce, encrypt_mode)
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


def get_device_speed(ip: str, token: str, target_mac: str, mock: bool = False) -> tuple[int, str]:
    """获取目标设备的下行速度 (Bit/s) 和设备名称。

    返回 (downspeed_bps, device_name)。设备不在线返回 (0, target_mac)。
    """
    if mock:
        return MOCK_SPEED_BPS, "MockDevice"

    devices = get_device_list(ip, token)
    mac_upper = target_mac.upper()
    for dev in devices:
        if dev.get("mac", "").upper() == mac_upper:
            speed = int(dev.get("statistics", {}).get("downspeed", 0))
            name = dev.get("name", target_mac)
            return speed, name
    return 0, target_mac


def load_config(path: str = "config.yaml") -> dict:
    """读取配置文件并校验必要字段。"""
    with open(path, "r") as f:
        config = yaml.safe_load(f)

    required = ["router_ip", "router_password", "target_mac", "download_threshold_mbps"]
    for key in required:
        if key not in config:
            raise ValueError(f"配置文件缺少必要字段: {key}")

    return config


def get_sendkey() -> str:
    """从环境变量获取 Server酱 SendKey，缺失则退出。"""
    key = os.environ.get("SERVERCHAN_SENDKEY")
    if not key:
        log.error("环境变量 SERVERCHAN_SENDKEY 未设置")
        log.error("请运行: export SERVERCHAN_SENDKEY='你的SendKey'")
        sys.exit(1)
    return key


def send_alert(sendkey: str, device_name: str, speed_mbps: float, threshold_mbps: float) -> None:
    """通过 Server酱推送网速告警。"""
    title = "设备网速告警"
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


def main() -> None:
    config = load_config()
    sendkey = get_sendkey()

    ip = config["router_ip"]
    password = config["router_password"]
    target_mac = config["target_mac"]
    threshold_mbps = config["download_threshold_mbps"]
    poll_interval = config.get("poll_interval", 5)
    mock_mode = config.get("mock_mode", False)

    threshold_bps = int(threshold_mbps * 1024 * 1024)
    alert_state = "normal"

    if mock_mode:
        log.info("Mock 模式: 路由器 API 将返回假数据")

    log.info("启动监控: 目标MAC=%s, 阈值=%.1f MB/s, 轮询间隔=%ds", target_mac, threshold_mbps, poll_interval)

    token = ""
    if not mock_mode:
        token = login(ip, password)

    while True:
        try:
            speed_bps, device_name = get_device_speed(ip, token, target_mac, mock=mock_mode)
            speed_mbps = speed_bps / 1024 / 1024

            log.info("设备 %s 下行速度: %.2f MB/s", device_name, speed_mbps)

            if speed_bps > threshold_bps:
                if alert_state == "normal":
                    alert_state = "alerting"
                    log.warning("速度超过阈值，触发告警")
                    send_alert(sendkey, device_name, speed_mbps, threshold_mbps)
            else:
                if alert_state == "alerting":
                    log.info("速度回落到阈值以下，恢复正常")
                alert_state = "normal"

        except requests.exceptions.RequestException as e:
            log.error("网络请求失败: %s", e)
            if not mock_mode:
                try:
                    token = login(ip, password)
                except Exception as login_err:
                    log.error("重新登录失败: %s", login_err)
        except Exception as e:
            log.error("轮询异常: %s", e)

        time.sleep(poll_interval)


if __name__ == "__main__":
    main()
