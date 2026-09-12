from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import frida


def on_message(message: dict, data: bytes | None) -> None:
    if message.get("type") == "send":
        payload = message.get("payload")
        print(json.dumps(payload, ensure_ascii=False))
        sys.stdout.flush()
        return
    print(json.dumps(message, ensure_ascii=False))
    sys.stdout.flush()


def main() -> int:
    parser = argparse.ArgumentParser(description="Attach to eufyMake Studio and log outbound MQTT publishes.")
    parser.add_argument("--pid", type=int, help="Target process id")
    parser.add_argument(
        "--process-name",
        default="eufymake studio-console.exe",
        help="Target process name if --pid is not given",
    )
    parser.add_argument(
        "--script",
        default=str(Path(__file__).with_name("mqtt_publish_hook.js")),
        help="Path to the Frida JavaScript hook file",
    )
    args = parser.parse_args()

    script_path = Path(args.script)
    source = script_path.read_text(encoding="utf-8")

    session = frida.attach(args.pid if args.pid is not None else args.process_name)
    script = session.create_script(source)
    script.on("message", on_message)
    script.load()

    print(json.dumps({
        "type": "attached",
        "target": args.pid if args.pid is not None else args.process_name,
        "script": str(script_path),
    }))
    sys.stdout.flush()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        session.detach()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
