# ankerctl Home Assistant Addon

ankerctl is a web UI and CLI for monitoring and controlling AnkerMake M5 3D printers over your local network — without relying on the proprietary AnkerMake cloud app. This addon runs the ankerctl web interface as a Home Assistant Supervisor addon, giving you print control, live camera, timelapse, print history, and optional Home Assistant MQTT Discovery integration, all from your HA dashboard.

## Prerequisites

- An AnkerMake M5 printer on the same LAN as your Home Assistant host.
- Either a `login.json` exported from the AnkerMake slicer, or your AnkerMake account email and password (used once to generate a local config — no ongoing cloud dependency).
- Home Assistant OS or Supervised installation (Supervisor required).

## Installation

1. In Home Assistant, go to **Settings → Add-ons → Add-on Store**.
2. Click the three-dot menu (top right) and select **Repositories**.
3. Add the repository URL: `https://github.com/doublegate/ankermake-m5-protocol`
4. Click **Add**, then close the dialog. The **ankerctl** addon will appear in the store.
5. Click **ankerctl**, then **Install**.
6. Configure the addon options (see table below). At minimum, leave defaults — you can configure credentials after first start via the web UI.
7. Click **Start**.
8. Open the web UI on port **4470** (click **OPEN WEB UI** in the addon panel).
9. On first run, upload your `login.json` or log in with email/password via the Setup tab.

## Configuration Options

| Option | Description | Default |
|---|---|---|
| `flask_host` | IP address the web server binds to | `0.0.0.0` |
| `flask_port` | TCP port for the web UI | `4470` |
| `flask_secret_key` | Session cookie secret. Set a fixed value if you want sessions to survive restarts. Auto-generated if blank. | _(blank)_ |
| `ankerctl_api_key` | API key required for all write operations (GCode, print control, uploads). Leave blank to disable auth. | _(blank)_ |
| `printer_index` | Zero-based index of the printer to control when multiple are configured. | `0` |
| `upload_rate_mbps` | GCode upload speed to the printer in Mbit/s. Choices: 5, 10, 25, 50, 100. | `10` |
| `timelapse_enabled` | Enable automatic timelapse capture during prints (requires ffmpeg, included in image). | `false` |
| `timelapse_interval_sec` | Seconds between timelapse snapshots. | `30` |
| `apprise_enabled` | Enable Apprise push notifications (print started/finished/failed, progress). | `false` |
| `apprise_server_url` | URL of your Apprise API server (e.g. `http://192.168.1.10:8000`). | _(blank)_ |
| `apprise_key` | Apprise notification key. | _(blank)_ |
| `ha_mqtt_enabled` | Enable Home Assistant MQTT Discovery — publishes printer sensors, binary sensors, and light control to your HA MQTT broker. | `false` |
| `ha_mqtt_host` | Hostname or IP of your HA MQTT broker. | `localhost` |
| `ha_mqtt_port` | Port of your HA MQTT broker. | `1883` |
| `ha_mqtt_user` | MQTT broker username (optional). | _(blank)_ |
| `ha_mqtt_password` | MQTT broker password (optional, stored as HA secret). | _(blank)_ |

All persistent data (printer config, print history, timelapse videos, logs) is stored in the addon's `/data` volume and survives addon restarts and updates.

## Network Note

This addon runs with `host_network: true`. This is not optional — the PPPP protocol used for LAN communication with the printer uses asymmetric UDP (the printer replies to a different port than the one it receives on). Docker bridge networking breaks this handshake. Host networking is the only reliable solution, and is the same requirement as the standalone Docker deployment.

## HA Sidebar Access

To add ankerctl to your Home Assistant sidebar, go to **Settings → Dashboard** and add an **iframe_panel** card pointing to `http://<your-ha-ip>:4470`. Alternatively, use the **Webpage** dashboard card type.

## Ingress

Ingress (the built-in HA reverse proxy that serves addons under the `/api/hassio_ingress/` path) is not currently supported. Use direct port access on `4470` instead.
