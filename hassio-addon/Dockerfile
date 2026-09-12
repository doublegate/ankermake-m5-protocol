ARG BUILD_FROM=ghcr.io/django1982/ankermake-m5-protocol:latest
FROM ${BUILD_FROM}

# HA Supervisor passes addon options via /data/options.json.
# run.sh reads them, exports env vars, then launches the app.
COPY run.sh /app/run.sh
RUN chmod +x /app/run.sh

ENTRYPOINT ["/app/run.sh"]
