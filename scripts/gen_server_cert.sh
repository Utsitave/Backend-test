#!/usr/bin/env bash
# Generate a self-signed TLS certificate for the FastAPI backend server.
# Run on the backend VM, then copy server.crt to each RPi client.
#
# Usage:
#   ./scripts/gen_server_cert.sh                          # auto-detect IP and hostname
#   ./scripts/gen_server_cert.sh 192.168.1.50             # specify IP
#   ./scripts/gen_server_cert.sh 192.168.1.50 my-host     # specify IP and hostname
#
# Requires: openssl >= 1.1.1  (Ubuntu 20.04+, Debian 11+, Raspberry Pi OS Bullseye+)

set -euo pipefail

SERVER_IP="${1:-$(hostname -I | awk '{print $1}')}"
HOSTNAME="${2:-$(hostname)}"
CERT_DIR="certs"
DAYS=730

if [[ -z "$SERVER_IP" ]]; then
    echo "ERROR: Could not detect server IP. Pass it as the first argument." >&2
    exit 1
fi

mkdir -p "$CERT_DIR"

echo "Generating self-signed certificate for IP=$SERVER_IP  hostname=$HOSTNAME ..."

openssl req -x509 -newkey rsa:4096 \
    -keyout "$CERT_DIR/server.key" \
    -out    "$CERT_DIR/server.crt" \
    -days   "$DAYS" \
    -nodes \
    -subj   "/CN=$HOSTNAME/O=IoT System" \
    -addext "subjectAltName=IP:$SERVER_IP,DNS:$HOSTNAME,DNS:localhost"

chmod 600 "$CERT_DIR/server.key"
chmod 644 "$CERT_DIR/server.crt"

echo ""
echo "Done."
echo ""
echo "Add to .env on this machine:"
echo "  TLS_CERT_PATH=$CERT_DIR/server.crt"
echo "  TLS_KEY_PATH=$CERT_DIR/server.key"
echo ""
echo "Copy the cert to each RPi (the key stays on the server):"
echo "  scp $CERT_DIR/server.crt pi@<rpi-ip>:~/iot_client/server.crt"
echo ""
echo "In rpi_client.py set:"
echo "  VERIFY_TLS = \"/home/pi/iot_client/server.crt\""
