import click
import logging
import copy

log = logging.getLogger("cli.mqtt")


import cli.model
import cli.util

from libflagship.mqtt import MqttMsgType
from libflagship.mqttapi import AnkerMQTTBaseClient

servertable = {
    "eu": "make-mqtt-eu.ankermake.com",
    "us": "make-mqtt.ankermake.com",
}


FILE_LIST_SOURCE_VALUES = {
    "onboard": 1,
    "usb": 0,
}


def mqtt_open(config, printer_index, insecure, mqtt_ca_cert=None):
    mqtt_ca_cert = mqtt_ca_cert or cli.model.default_mqtt_ca_cert()

    with config.open() as cfg:
        if printer_index < 0 or printer_index >= len(cfg.printers):
            raise ValueError(f"Printer number {printer_index} out of range, must be in 0..{len(cfg.printers)-1}")
        printer = cfg.printers[printer_index]
        acct = cfg.account
        server = servertable[acct.region]
        log.info(f"Connecting printer {printer.name} ({printer.p2p_duid}) through {server}")
        client = AnkerMQTTBaseClient.login(
            printer.sn,
            acct.mqtt_username,
            acct.mqtt_password,
            printer.mqtt_key,
            ca_cert=mqtt_ca_cert,
            verify=not insecure,
        )
        client.connect(server)
        return client


def mqtt_gcode_dump(client, gcode, collect_window=3.0):
    """Send a GCode command and collect all response packets.

    Unlike mqtt_command, this waits for multiple MQTT responses and
    concatenates their resData fields to reconstruct the full ring-buffer
    output. Useful for commands that generate long responses (M503, M420 V).
    """
    cmd = {
        "commandType": MqttMsgType.ZZ_MQTT_CMD_GCODE_COMMAND.value,
        "cmdData": gcode,
        "cmdLen": len(gcode),
    }
    client.command(cmd)
    msgs = client.await_responses(MqttMsgType.ZZ_MQTT_CMD_GCODE_COMMAND, collect_window=collect_window)
    return msgs


def mqtt_command(client, msg):
    client.command(msg)

    reply = client.await_response(msg["commandType"])
    if reply:
        click.echo(cli.util.pretty_json(reply))
    else:
        log.error("No response from printer")


def mqtt_collect_command(client, msg, timeout=10, collect_window=3.0):
    client.command(msg)
    return client.await_responses(
        msg["commandType"],
        timeout=timeout,
        collect_window=collect_window,
    )


def infer_storage_source_from_path(path):
    if not isinstance(path, str):
        return None
    if path.startswith("/tmp/udisk/"):
        return "usb"
    if path.startswith("/usr/data/local/model/"):
        return "onboard"
    return None


def mqtt_file_list_source_value(source="onboard", value=None):
    if value is not None:
        return int(value)

    normalized = str(source or "onboard").strip().lower()
    if normalized not in FILE_LIST_SOURCE_VALUES:
        raise ValueError(f"Unsupported file-list source: {source}")
    return FILE_LIST_SOURCE_VALUES[normalized]


def parse_file_list_replies(replies, requested_source=None):
    parsed_replies = cli.util.parse_json(copy.deepcopy(replies or []))
    files = []

    for reply in parsed_replies:
        if not isinstance(reply, dict):
            continue
        file_list = reply.get("fileLists")
        if not isinstance(file_list, list):
            continue
        for entry in file_list:
            if not isinstance(entry, dict):
                continue
            inferred_source = infer_storage_source_from_path(entry.get("path")) or requested_source
            if requested_source and inferred_source and inferred_source != requested_source:
                continue
            timestamp = entry.get("timestamp")
            try:
                timestamp = int(timestamp) if timestamp is not None else None
            except (TypeError, ValueError):
                timestamp = None
            files.append({
                "name": entry.get("name"),
                "path": entry.get("path"),
                "timestamp": timestamp,
                "source": inferred_source,
            })

    return {
        "reply_count": len(parsed_replies),
        "replies": parsed_replies,
        "files": files,
    }


def mqtt_file_list_probe(client, source="onboard", source_value=None, timeout=10, collect_window=3.0):
    source_value = mqtt_file_list_source_value(source=source, value=source_value)
    requested_source = "onboard" if source_value == 1 else "usb"
    cmd = {
        "commandType": MqttMsgType.ZZ_MQTT_CMD_FILE_LIST_REQUEST.value,
        "value": source_value,
    }
    result = parse_file_list_replies(
        mqtt_collect_command(client, cmd, timeout=timeout, collect_window=collect_window),
        requested_source=requested_source,
    )
    result["request"] = cmd
    result["source_value"] = source_value
    return result


def mqtt_query(client, msg):
    client.query(msg)

    reply = client.await_response(msg["commandType"])
    if reply:
        click.echo(cli.util.pretty_json(reply))
    else:
        log.error("No response from printer")
