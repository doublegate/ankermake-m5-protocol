import cli.model


def _printer_from_config(cfg, printer_index):
    printers = getattr(cfg, "printers", None) or []
    if printer_index < 0 or printer_index >= len(printers):
        return None
    return printers[printer_index]


def _normalize_bool(value, default=False):
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in ("true", "1", "yes", "on")
    return bool(value)


def _normalize_int(value, default, minimum=None):
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = int(default)
    if minimum is not None:
        result = max(int(minimum), result)
    return result


def _normalize_light(value):
    if value == "snapshot":
        return "snapshot"
    if value in (True, "session", "on"):
        return "session"
    return None


def _normalize_camera_source(value):
    source = str(value or "follow").strip().lower()
    if source in {"home", "current", "selected", "camera"}:
        return "follow"
    if source in {"printer", "external", "follow"}:
        return source
    return "follow"


def normalize_timelapse_settings(data):
    defaults = cli.model.default_timelapse_config()
    merged = cli.model.merge_dict_defaults(data, defaults)
    output_dir = str(merged.get("output_dir") or defaults.get("output_dir") or "").strip()
    if not output_dir:
        output_dir = defaults.get("output_dir")
    return {
        "enabled": _normalize_bool(merged.get("enabled"), defaults.get("enabled", False)),
        "interval": _normalize_int(merged.get("interval"), defaults.get("interval", 30), minimum=1),
        "max_videos": _normalize_int(merged.get("max_videos"), defaults.get("max_videos", 10), minimum=0),
        "save_persistent": _normalize_bool(
            merged.get("save_persistent"),
            defaults.get("save_persistent", True),
        ),
        "output_dir": output_dir,
        "light": _normalize_light(merged.get("light")),
        "camera_source": _normalize_camera_source(merged.get("camera_source")),
    }


def resolve_timelapse_settings(cfg, printer_index=0):
    defaults = cli.model.default_timelapse_config()
    root = getattr(cfg, "timelapse", None)
    if not isinstance(root, dict):
        return defaults

    base = normalize_timelapse_settings(root)
    printer = _printer_from_config(cfg, printer_index)
    if not printer:
        return base

    per_printer = root.get("per_printer")
    if not isinstance(per_printer, dict):
        return base

    raw_entry = per_printer.get(getattr(printer, "sn", None), {})
    if not isinstance(raw_entry, dict):
        return base

    return normalize_timelapse_settings({**base, **raw_entry})


def update_timelapse_settings(cfg, printer_index, payload):
    if not isinstance(payload, dict):
        payload = {}

    printer = _printer_from_config(cfg, printer_index)
    if not printer:
        raise ValueError("No active printer is configured.")

    current = resolve_timelapse_settings(cfg, printer_index)
    new_config = normalize_timelapse_settings({**current, **payload})

    root = getattr(cfg, "timelapse", None)
    if not isinstance(root, dict):
        root = {}
    else:
        root = dict(root)

    per_printer = root.get("per_printer")
    if not isinstance(per_printer, dict):
        per_printer = {}
    else:
        per_printer = dict(per_printer)

    per_printer[printer.sn] = new_config
    root["per_printer"] = per_printer
    cfg.timelapse = root
    return new_config
