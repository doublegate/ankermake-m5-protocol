import threading
from types import SimpleNamespace

from libflagship.amtypes import IPv4, String, u16le
from libflagship.mqtt import MqttMsgType
from web.service.mqtt import MqttQueue


def test_amtypes_round_trip():
    packed_ip = IPv4("192.168.10.5").pack()
    parsed_ip, rest = IPv4.parse(packed_ip)
    packed_string = String.pack("hello", 8)
    parsed_string, string_rest = String.parse(packed_string, 8)
    parsed_int, int_rest = u16le.parse(u16le(32108).pack())

    assert rest == b""
    assert string_rest == b""
    assert int_rest == b""
    assert parsed_ip == "192.168.10.5"
    assert parsed_string.rstrip("\x00") == "hello"
    assert parsed_int == 32108


def test_mqtt_queue_progress_and_extractors():
    queue = object.__new__(MqttQueue)
    queue._notifier = SimpleNamespace(progress_max=lambda: 200)

    assert MqttQueue._safe_int("12.9") == 12
    assert MqttQueue._normalize_temp(21500) == 215
    assert MqttQueue._normalize_temp(215) == 215
    assert MqttQueue._normalize_progress("0.5") == 50
    assert MqttQueue._normalize_progress(150, max_value=200) == 75
    assert queue._extract_progress({"nested": {"progress": 80}}) == 40
    assert MqttQueue._extract_filename({"fileName": " cube.gcode "}) == "cube.gcode"
    assert MqttQueue._extract_preview_url({"previewUrl": "https://example.test/preview.jpg"}) == "https://example.test/preview.jpg"
    assert MqttQueue._extract_failure_reason({"status": "Print Failed"}) == "Print Failed"
    assert MqttQueue._extract_task_id({"taskId": " task-1 "}) == "task-1"
    assert MqttQueue._extract_status_text({"printStatus": " FINISHED "}) == "finished"


def test_mqtt_queue_z_offset_update_and_state():
    queue = object.__new__(MqttQueue)
    queue._z_offset_steps = None
    queue._z_offset_updated_at = 0.0
    queue._z_offset_seq = 0
    queue._z_offset_cond = threading.Condition()

    queue._handle_z_offset_update({
        "commandType": MqttMsgType.ZZ_MQTT_CMD_Z_AXIS_RECOUP.value,
        "value": 37,
    })
    state = queue.get_z_offset_state()

    assert state["available"] is True
    assert state["steps"] == 37
    assert state["mm"] == 0.37
    assert state["source"] == "cached"
