from datetime import datetime

from cli.model import Account, Config, Printer, merge_dict_defaults


def test_merge_dict_defaults_keeps_existing_values_and_extra_keys():
    defaults = {
        "apprise": {
            "enabled": False,
            "events": {"print_started": True, "print_finished": True},
        }
    }
    data = {
        "apprise": {
            "enabled": True,
            "events": {"print_started": False},
            "custom": "value",
        }
    }

    merged = merge_dict_defaults(data, defaults)

    assert merged["apprise"]["enabled"] is True
    assert merged["apprise"]["events"]["print_started"] is False
    assert merged["apprise"]["events"]["print_finished"] is True
    assert merged["apprise"]["custom"] == "value"


def test_printer_from_dict_normalizes_legacy_fields():
    printer = Printer.from_dict({
        "id": "printer-1",
        "sn": "SN-1",
        "name": "Printer",
        "model": "V8111",
        "create_time": datetime(2024, 1, 1, 12, 0, 0).timestamp(),
        "update_time": datetime(2024, 1, 1, 12, 30, 0).timestamp(),
        "wifi_mac": "aabbccddeeff",
        "ip_addr": "",
        "mqtt_key": "0102",
        "api_hosts": "api.example",
        "p2p_hosts": "",
        "p2p_did": "legacy-duid",
        "p2p_key": "secret",
    })

    assert printer.api_hosts == ["api.example"]
    assert printer.p2p_hosts == []
    assert printer.p2p_duid == "legacy-duid"
    assert printer.p2p_did == "legacy-duid"


def test_config_from_dict_coerces_active_printer_index_and_defaults():
    cfg = Config.from_dict({
        "account": Account(
            auth_token="token",
            region="eu",
            user_id="user-1",
            email="printer@example.com",
        ),
        "printers": [],
        "active_printer_index": "invalid",
        "notifications": {"apprise": {"enabled": True}},
    })

    assert cfg.active_printer_index == 0
    assert cfg.notifications["apprise"]["enabled"] is True
    assert cfg.notifications["apprise"]["events"]["print_started"] is True
    assert "timelapse" in cfg.to_dict()
