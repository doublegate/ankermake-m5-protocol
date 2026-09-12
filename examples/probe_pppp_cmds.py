#!/usr/bin/env python3
"""Probe PPPP JSON commands on the AnkerMake M5 printer.

Reconnects for each command since the printer drops the connection
after receiving some commands or malformed payloads.
"""

import json
import logging
import sys
import time

sys.path.insert(0, ".")

import cli.config
import cli.pppp
from libflagship.mqtt import MqttMsgType
from libflagship.pppp import P2PCmdType

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

MOVE_ZERO = MqttMsgType.ZZ_MQTT_CMD_MOVE_ZERO.value

PROBE_PAYLOADS = [
    ("APP_CMD_GET_ADMIN_PWD", {"commandType": 0x0462}),
    ("APP_CMD_GET_WIFI_PWD", {"commandType": 0x0463}),
    ("APP_CMD_GET_EXCEPTION_LOG", {"commandType": 0x0464}),
    ("APP_CMD_GET_UPDATE_STATUS", {"commandType": 0x0461}),
    ("APP_CMD_GET_NEWVESION", {"commandType": 0x0465}),
    ("APP_CMD_GET_ASEKEY", {"commandType": 0x044C}),
    ("APP_CMD_SDINFO", {"commandType": 0x044E}),
    ("APP_CMD_CAMERA_INFO", {"commandType": 0x044F}),
    ("APP_CMD_GET_HUB_NAME", {"commandType": 0x0468}),
    ("APP_CMD_GET_DEVS_NAME", {"commandType": 0x0469}),
    ("APP_CMD_GET_P2P_CONN_STATUS", {"commandType": 0x046A}),
    ("MOVE_ZERO bare", {"commandType": MOVE_ZERO}),
    ("MOVE_ZERO axis=z", {"commandType": MOVE_ZERO, "axis": "z"}),
    ("MOVE_ZERO axis=xy", {"commandType": MOVE_ZERO, "axis": "xy"}),
    ("MOVE_ZERO axis=all", {"commandType": MOVE_ZERO, "axis": "all"}),
    ("MOVE_ZERO cmdData axis=z", {"commandType": MOVE_ZERO, "cmdData": {"axis": "z"}}),
    ("MOVE_ZERO cmdData axis=xy", {"commandType": MOVE_ZERO, "cmdData": {"axis": "xy"}}),
    ("MOVE_ZERO cmdData axis=all", {"commandType": MOVE_ZERO, "cmdData": {"axis": "all"}}),
    ("MOVE_ZERO cmdData type=0", {"commandType": MOVE_ZERO, "cmdData": {"type": 0}}),
    ("MOVE_ZERO cmdData type=1", {"commandType": MOVE_ZERO, "cmdData": {"type": 1}}),
    ("MOVE_ZERO cmdData type=2", {"commandType": MOVE_ZERO, "cmdData": {"type": 2}}),
    ("MOVE_ZERO cmdData axis=0", {"commandType": MOVE_ZERO, "cmdData": {"axis": 0}}),
    ("MOVE_ZERO cmdData axis=1", {"commandType": MOVE_ZERO, "cmdData": {"axis": 1}}),
    ("MOVE_ZERO cmdData axis=2", {"commandType": MOVE_ZERO, "cmdData": {"axis": 2}}),
]


def connect():
    config = cli.config.configmgr()
    return cli.pppp.pppp_open(config, 0, timeout=10)


def probe_one(cmd_name, payload):
    """Connect, send one payload, collect responses, disconnect."""
    log.info(f"--- {cmd_name} ---")

    try:
        api = connect()
    except Exception as e:
        log.error(f"  Connect failed: {e}")
        return {"cmd": cmd_name, "status": "connect_fail", "data": str(e)}

    tx = json.dumps(payload).encode()
    log.info(f"  TX: {tx}")

    try:
        api.send_xzyh(tx, cmd=P2PCmdType.P2P_JSON_CMD, chan=0)
    except Exception as e:
        log.error(f"  Send failed: {e}")
        try:
            api.stop()
        except Exception:
            pass
        return {"cmd": cmd_name, "status": "send_fail", "data": str(e)}

    responses = []
    deadline = time.time() + 3.0
    while time.time() < deadline:
        try:
            resp = api.recv_xzyh(chan=0, timeout=0.5)
            if resp:
                raw = resp.data
                try:
                    parsed = json.loads(raw)
                    log.info(f"  RX (JSON): {json.dumps(parsed, indent=2)}")
                    responses.append({"type": "json", "data": parsed})
                except (json.JSONDecodeError, UnicodeDecodeError):
                    log.info(f"  RX (hex): {raw.hex()}")
                    log.info(f"  RX (len): {len(raw)} bytes")
                    log.info(f"  RX (str): {raw.decode('utf-8', errors='replace')}")
                    responses.append({"type": "binary", "hex": raw.hex(), "len": len(raw)})
        except Exception:
            break

    try:
        api.stop()
    except Exception:
        pass

    if not responses:
        log.info("  No response")
        return {"cmd": cmd_name, "status": "no_response", "payload": payload}

    return {"cmd": cmd_name, "status": "ok", "payload": payload, "responses": responses}


def main():
    log.info("PPPP Command Probe - AnkerMake M5\n")

    results = []
    for cmd_name, payload in PROBE_PAYLOADS:
        result = probe_one(cmd_name, payload)
        results.append(result)
        time.sleep(2)

    log.info("\n" + "=" * 60)
    log.info("SUMMARY")
    log.info("=" * 60)
    for result in results:
        if result["status"] == "ok":
            log.info(f"  [RESPONSE] {result['cmd']}: {result['responses']}")
        else:
            log.info(f"  [{result['status'].upper()}] {result['cmd']}")

    log.info("\nFull JSON results:")
    log.info(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
