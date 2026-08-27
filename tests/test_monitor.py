from unittest.mock import patch, MagicMock
from wifi_speed_monitor import login, get_device_speed, load_config


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


@patch("wifi_speed_monitor.requests.get")
def test_login_success(mock_get):
    mock_get.side_effect = [
        mock_response(MOCK_INIT_INFO),
        mock_response(MOCK_LOGIN_SUCCESS),
    ]
    # login 内部会先 get init_info，再 post login
    with patch("wifi_speed_monitor.requests.post") as mock_post:
        mock_post.return_value = mock_response(MOCK_LOGIN_SUCCESS)
        token = login("192.168.31.1", "test_password")
        assert token == "abc123token"


@patch("wifi_speed_monitor.requests.get")
def test_get_device_speed(mock_get):
    mock_get.return_value = mock_response(MOCK_DEVICE_LIST)
    speed, name = get_device_speed("192.168.31.1", "token123", "AA:BB:CC:DD:EE:FF")
    assert speed == 8388608
    assert name == "TestPhone"


@patch("wifi_speed_monitor.requests.get")
def test_get_device_speed_offline(mock_get):
    mock_get.return_value = mock_response(MOCK_DEVICE_LIST_OFFLINE)
    speed, name = get_device_speed("192.168.31.1", "token123", "AA:BB:CC:DD:EE:FF")
    assert speed == 0
    assert name == "AA:BB:CC:DD:EE:FF"


def test_load_config():
    import tempfile
    import os

    config_content = """
router_ip: "192.168.31.1"
router_password: "test_pass"
target_mac: "AA:BB:CC:DD:EE:FF"
download_threshold_mbps: 5.0
poll_interval: 5
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(config_content)
        f.flush()
        config = load_config(f.name)
        os.unlink(f.name)

    assert config["router_ip"] == "192.168.31.1"
    assert config["download_threshold_mbps"] == 5.0
