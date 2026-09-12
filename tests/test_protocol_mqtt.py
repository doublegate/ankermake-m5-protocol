import pytest

from libflagship.mqtt import MqttMsg, MqttPktType


KEY = b"0123456789abcdef"


def _build_message(*, m5=2, data=b'{"ok":true}', packet_num=1):
    padding = b"\x11" * 12 if m5 == 1 else b"\x22" * 11
    return MqttMsg(
        size=0,
        m3=5,
        m4=1,
        m5=m5,
        m6=5,
        m7=ord("F"),
        packet_type=MqttPktType.Single,
        packet_num=packet_num,
        time=1712345678,
        device_guid="device-guid-123",
        padding=padding,
        data=data,
    )


def test_mqtt_msg_round_trip_m5():
    msg = _build_message(m5=2)

    packed = msg.pack(KEY)
    parsed, rest = MqttMsg.parse(packed, KEY)

    assert rest == b""
    assert parsed.m5 == 2
    assert parsed.packet_type == MqttPktType.Single
    assert parsed.packet_num == 1
    assert parsed.time == 1712345678
    assert parsed.device_guid.rstrip("\x00") == "device-guid-123"
    assert parsed.padding == b"\x22" * 11
    assert parsed.getjson() == {"ok": True}


def test_mqtt_msg_round_trip_m5c():
    msg = _build_message(m5=1, data=b'{"mode":"compact"}', packet_num=7)

    packed = msg.pack(KEY)
    parsed, rest = MqttMsg.parse(packed, KEY)

    assert rest == b""
    assert parsed.m5 == 1
    assert parsed.packet_num == 7
    assert parsed.time == 0
    assert parsed.device_guid == ""
    assert parsed.padding == b"\x11" * 12
    assert parsed.getjson() == {"mode": "compact"}


def test_mqtt_parse_rejects_invalid_checksum():
    msg = _build_message()
    packed = bytearray(msg.pack(KEY))
    packed[-1] ^= 0x01

    with pytest.raises(ValueError, match="checksum mismatch"):
        MqttMsg.parse(bytes(packed), KEY)


def test_mqtt_pack_rejects_unsupported_format():
    msg = _build_message(m5=2)
    msg.m5 = 9

    with pytest.raises(ValueError, match="unsupported mqtt message format"):
        msg.pack(KEY)
