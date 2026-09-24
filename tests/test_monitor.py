import os
import tempfile
from unittest.mock import patch, MagicMock

import pytest

from wifi_speed_monitor import (
    login,
    get_device_speeds,
    build_device_labels,
    evaluate_alert,
    send_alert,
    load_config,
    merge_settings,
    MOCK_SPEED_BPS,
)


MOCK_WEB_HTML = "var deviceId = 'AA:BB:CC:DD:EE:FF';\nkey: 'noncekey123';"

MOCK_INIT_INFO = {
    "code": 0,
    "newEncryptMode": 1,
    "hardware": "RA74",
    "romversion": "1.0.88",
}

MOCK_LOGIN_SUCCESS = {
    "code": 0,
    "token": "abc123token",
    "url": "/cgi-bin/luci/;stok=abc123token/web/home#router",
}

MOCK_DEVICE_LIST = {
    "code": 0,
    "mac": "AA:BB:CC:DD:EE:FF",
    "list": [
        {
            "mac": "AA:BB:CC:DD:EE:FF",
            "name": "TestPhone",
            "ip": "192.168.31.100",
            "online": 1,
            "statistics": {
                "downspeed": "8388608",
                "upspeed": "1048576",
                "download": "123456789",
                "upload": "987654321",
            },
        },
        {
            "mac": "11:22:33:44:55:66",
            "name": "OtherDevice",
            "ip": "192.168.31.101",
            "online": 1,
            "statistics": {
                "downspeed": "0",
                "upspeed": "0",
                "download": "0",
                "upload": "0",
            },
        },
    ],
}

MOCK_DEVICE_LIST_OFFLINE = {
    "code": 0,
    "mac": "AA:BB:CC:DD:EE:FF",
    "list": [
        {
            "mac": "11:22:33:44:55:66",
            "name": "OtherDevice",
            "ip": "192.168.31.101",
            "online": 1,
            "statistics": {
                "downspeed": "0",
                "upspeed": "0",
                "download": "0",
                "upload": "0",
            },
        },
    ],
}


def mock_response(json_data, status_code=200):
    mock = MagicMock()
    mock.json.return_value = json_data
    mock.status_code = status_code
    mock.raise_for_status.return_value = None
    return mock


def mock_text_response(html, status_code=200):
    mock = MagicMock()
    mock.text = html
    mock.status_code = status_code
    mock.raise_for_status.return_value = None
    return mock


def write_config(content):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(content)
        f.flush()
        path = f.name
    return path


@patch("wifi_speed_monitor.requests.get")
def test_login_success(mock_get):
    mock_get.side_effect = [
        mock_text_response(MOCK_WEB_HTML),
        mock_response(MOCK_INIT_INFO),
    ]
    # login 内部会先 get 网页 nonce，再 get init_info，最后 post login
    with patch("wifi_speed_monitor.requests.post") as mock_post:
        mock_post.return_value = mock_response(MOCK_LOGIN_SUCCESS)
        token = login("192.168.31.1", "test_password")
        assert token == "abc123token"


@patch("wifi_speed_monitor.requests.get")
def test_get_device_speeds_returns_all_online(mock_get):
    mock_get.return_value = mock_response(MOCK_DEVICE_LIST)
    speeds = get_device_speeds(
        "192.168.31.1", "token123", ["AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66"]
    )
    assert speeds == [
        ("AA:BB:CC:DD:EE:FF", 8388608, "TestPhone"),
        ("11:22:33:44:55:66", 0, "OtherDevice"),
    ]


@patch("wifi_speed_monitor.requests.get")
def test_get_device_speeds_skips_offline(mock_get):
    mock_get.return_value = mock_response(MOCK_DEVICE_LIST_OFFLINE)
    speeds = get_device_speeds(
        "192.168.31.1", "token123", ["AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66"]
    )
    assert [mac for mac, _speed, _name in speeds] == ["11:22:33:44:55:66"]


def test_get_device_speeds_mock_matches_targets():
    macs = ["AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66"]
    speeds = get_device_speeds("192.168.31.1", "token", macs, mock=True)
    assert len(speeds) == len(macs)
    assert all(speed == MOCK_SPEED_BPS for _mac, speed, _name in speeds)
    assert [mac for mac, _speed, _name in speeds] == macs


def test_build_device_labels():
    assert build_device_labels(["m1", "m2"]) == {"m1": "A", "m2": "B"}


def test_evaluate_alert_independent_states():
    threshold = 100
    states = {"A": "normal", "B": "normal"}

    assert evaluate_alert(states, "A", 200, threshold) == "alert"
    assert states == {"A": "alerting", "B": "normal"}

    # A 持续超阈值不重复告警；B 正常不受影响
    assert evaluate_alert(states, "A", 200, threshold) is None
    assert evaluate_alert(states, "B", 50, threshold) is None
    assert states == {"A": "alerting", "B": "normal"}

    # A 回落后再次超阈值会重新告警
    assert evaluate_alert(states, "A", 50, threshold) == "recover"
    assert evaluate_alert(states, "A", 200, threshold) == "alert"


@patch("wifi_speed_monitor.sc_send")
def test_send_alert_title_includes_device_name(mock_sc_send):
    mock_sc_send.return_value = {"code": 0}
    send_alert("dummy-key", "TestPhone", 12.5, 5.0)
    title = mock_sc_send.call_args.args[1]
    desp = mock_sc_send.call_args.args[2]
    assert "TestPhone" in title
    assert "TestPhone" in desp


def test_load_config():
    path = write_config(
        """
router_ip: "192.168.31.1"
router_password: "test_pass"
target_macs:
  - "AA:BB:CC:DD:EE:FF"
download_threshold_mbps: 5.0
poll_interval: 5
push_serverchan: false
"""
    )
    try:
        config = load_config(path)
    finally:
        os.unlink(path)

    assert config["router_ip"] == "192.168.31.1"
    assert config["target_macs"] == ["AA:BB:CC:DD:EE:FF"]
    assert config["download_threshold_mbps"] == 5.0
    assert config["push_serverchan"] is False


def test_load_config_missing_target_macs():
    path = write_config(
        """
router_ip: "192.168.31.1"
router_password: "test_pass"
download_threshold_mbps: 5.0
"""
    )
    try:
        with pytest.raises(ValueError):
            load_config(path)
    finally:
        os.unlink(path)


def test_merge_settings_includes_push_serverchan():
    local = {
        "download_threshold_mbps": 5.0,
        "poll_interval": 5,
        "push_serverchan": False,
    }
    api = {
        "download_threshold_mbps": 8.0,
        "poll_interval": 10,
        "push_serverchan": True,
    }
    merged = merge_settings(local, api)
    assert merged["push_serverchan"] is True
    assert merged["download_threshold_mbps"] == 8.0
    assert merged["poll_interval"] == 10


def test_load_config_empty_target_macs():
    path = write_config(
        """
router_ip: "192.168.31.1"
router_password: "test_pass"
target_macs: []
download_threshold_mbps: 5.0
"""
    )
    try:
        with pytest.raises(ValueError):
            load_config(path)
    finally:
        os.unlink(path)
