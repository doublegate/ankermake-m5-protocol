#!/bin/sh
set -eu

OPTIONS_FILE="/data/options.json"

# Helper: read a string field from options.json
# Usage: json_get FIELD DEFAULT_QUOTED
# DEFAULT_QUOTED must be a valid Python expression (e.g., '"0.0.0.0"' or '4470')
json_get() {
    python3 -c "
import json, sys
try:
    data = json.load(open('${OPTIONS_FILE}'))
except Exception:
    data = {}
val = data.get('${1}', ${2})
if val is None:
    sys.exit(0)
print(val)
" 2>/dev/null || true
}

# Helper: read a boolean field from options.json, output 'true' or 'false'
json_bool() {
    python3 -c "
import json
try:
    data = json.load(open('${OPTIONS_FILE}'))
except Exception:
    data = {}
val = data.get('${1}', False)
print('true' if val else 'false')
" 2>/dev/null || echo "false"
}

# ------------------------------------------------------------------
# Ensure persistent storage directories exist and are writable
# ------------------------------------------------------------------
mkdir -p /data/.config/ankerctl
mkdir -p /home/ankerctl/.config
rm -rf /home/ankerctl/.config/ankerctl
ln -sfn /data/.config/ankerctl /home/ankerctl/.config/ankerctl
mkdir -p /data/captures
mkdir -p /data/logs
chown -R ankerctl:ankerctl /data

# ------------------------------------------------------------------
# Map HA addon options → ankerctl environment variables
# ------------------------------------------------------------------

# Config path: redirect platformdirs to the Supervisor-managed /data volume
export HOME=/data

# Server
export FLASK_HOST="$(json_get flask_host '"0.0.0.0"')"
export FLASK_PORT="$(json_get flask_port 4470)"

SECRET="$(json_get flask_secret_key '""')"
if [ -n "$SECRET" ]; then
    export FLASK_SECRET_KEY="$SECRET"
fi

# Security
API_KEY="$(json_get ankerctl_api_key '""')"
if [ -n "$API_KEY" ]; then
    export ANKERCTL_API_KEY="$API_KEY"
fi

# Printer
export PRINTER_INDEX="$(json_get printer_index 0)"

# Upload
export UPLOAD_RATE_MBPS="$(json_get upload_rate_mbps 10)"

# Timelapse — captures stored in persistent /data volume
export TIMELAPSE_ENABLED="$(json_bool timelapse_enabled)"
export TIMELAPSE_INTERVAL_SEC="$(json_get timelapse_interval_sec 30)"
export TIMELAPSE_CAPTURES_DIR="/data/captures"

# Logs — persistent and accessible from HA log viewer
export ANKERCTL_LOG_DIR="/data/logs"

# Apprise notifications
export APPRISE_ENABLED="$(json_bool apprise_enabled)"
APPRISE_URL="$(json_get apprise_server_url '""')"
if [ -n "$APPRISE_URL" ]; then
    export APPRISE_SERVER_URL="$APPRISE_URL"
fi
APPRISE_K="$(json_get apprise_key '""')"
if [ -n "$APPRISE_K" ]; then
    export APPRISE_KEY="$APPRISE_K"
fi

# Home Assistant MQTT Discovery
export HA_MQTT_ENABLED="$(json_bool ha_mqtt_enabled)"
export HA_MQTT_HOST="$(json_get ha_mqtt_host '"localhost"')"
export HA_MQTT_PORT="$(json_get ha_mqtt_port 1883)"
MQTT_USER="$(json_get ha_mqtt_user '""')"
if [ -n "$MQTT_USER" ]; then
    export HA_MQTT_USER="$MQTT_USER"
fi
MQTT_PASS="$(json_get ha_mqtt_password '""')"
if [ -n "$MQTT_PASS" ]; then
    export HA_MQTT_PASSWORD="$MQTT_PASS"
fi

# ------------------------------------------------------------------
# Hand off to the existing entrypoint (handles gosu privilege drop)
# ------------------------------------------------------------------
exec /app/entrypoint.sh /app/ankerctl.py webserver run
