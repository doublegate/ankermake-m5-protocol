#!/usr/bin/env bash
# Generates the local CA and server certificate for the offline MQTT broker.
# Run once from the repo root: bash offline/setup-certs.sh
# The generated files are gitignored — back them up somewhere safe.
set -euo pipefail

CERT_DIR="$(dirname "$0")/mosquitto/certs"
cd "$CERT_DIR"

if [ -f server-cert.pem ]; then
    echo "Certs already exist in $CERT_DIR — delete them first if you want to regenerate."
    exit 0
fi

echo "Generating local CA..."
openssl req -x509 -newkey rsa:4096 -keyout ca-key.pem -out ca-cert.pem -days 3650 -nodes \
    -subj '/CN=ankerctl Local CA/O=ankerctl-offline'

echo "Generating server cert (*.ankermake.com)..."
openssl req -newkey rsa:2048 -keyout server-key.pem -out server-csr.pem -nodes \
    -subj '/CN=make-mqtt-eu.ankermake.com/O=ankermake'

cat > server-ext.cnf <<EOF
subjectAltName = DNS:*.ankermake.com,DNS:make-mqtt.ankermake.com,DNS:make-mqtt-eu.ankermake.com
extendedKeyUsage = serverAuth
EOF

openssl x509 -req -in server-csr.pem -CA ca-cert.pem -CAkey ca-key.pem -CAcreateserial \
    -out server-cert.pem -days 365 -extfile server-ext.cnf

# Mosquitto runs as UID 1883 — needs to read key
chmod 644 server-cert.pem server-key.pem ca-cert.pem

rm -f server-csr.pem server-ext.cnf

echo ""
echo "Done. Cert expires: $(openssl x509 -in server-cert.pem -noout -enddate)"
echo "SANs:               $(openssl x509 -in server-cert.pem -noout -text | grep DNS:)"
