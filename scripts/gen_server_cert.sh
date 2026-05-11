#!/usr/bin/env bash
# Generate a two-tier PKI for the FastAPI backend:
#   ca.crt / ca.key      — CA (copy ca.crt to each RPi client)
#   server.crt / server.key — TLS server cert signed by the CA
#
# Using a CA-signed server cert avoids OpenSSL 3.x behaviour where a
# self-signed cert used as both server cert and trusted root is rejected
# with X509_V_ERR_DEPTH_ZERO_SELF_SIGNED_CERT on Raspberry Pi OS Bookworm+.
#
# Usage:
#   ./scripts/gen_server_cert.sh                          # auto-detect IP and hostname
#   ./scripts/gen_server_cert.sh 192.168.1.50             # specify IP
#   ./scripts/gen_server_cert.sh 192.168.1.50 my-host     # specify IP and hostname
#
# Requires: openssl >= 1.1.1

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

# ── 1. CA ──────────────────────────────────────────────────────────────────────
if [[ -f "$CERT_DIR/ca.key" && -f "$CERT_DIR/ca.crt" ]]; then
    echo "Existing CA found — reusing $CERT_DIR/ca.crt"
else
    echo "Generating CA key and certificate ..."
    openssl genrsa -out "$CERT_DIR/ca.key" 4096
    openssl req -x509 -new -nodes \
        -key  "$CERT_DIR/ca.key" \
        -out  "$CERT_DIR/ca.crt" \
        -days "$DAYS" \
        -subj "/CN=IoT System CA/O=IoT System" \
        -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
        -addext "keyUsage=critical,keyCertSign,cRLSign"
    chmod 600 "$CERT_DIR/ca.key"
    chmod 644 "$CERT_DIR/ca.crt"
    echo "CA certificate written to $CERT_DIR/ca.crt"
fi

# ── 2. Server key + CSR ────────────────────────────────────────────────────────
echo "Generating server key and CSR for IP=$SERVER_IP  hostname=$HOSTNAME ..."

openssl genrsa -out "$CERT_DIR/server.key" 4096
chmod 600 "$CERT_DIR/server.key"

openssl req -new -nodes \
    -key  "$CERT_DIR/server.key" \
    -out  "$CERT_DIR/server.csr" \
    -subj "/CN=$HOSTNAME/O=IoT System"

# ── 3. Sign server cert with CA ────────────────────────────────────────────────
cat > "$CERT_DIR/server_ext.cnf" <<EOF
[req]
distinguished_name = req_distinguished_name
[req_distinguished_name]
[v3_server]
basicConstraints = CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = IP:$SERVER_IP,DNS:$HOSTNAME,DNS:localhost
EOF

openssl x509 -req \
    -in     "$CERT_DIR/server.csr" \
    -CA     "$CERT_DIR/ca.crt" \
    -CAkey  "$CERT_DIR/ca.key" \
    -CAcreateserial \
    -out    "$CERT_DIR/server.crt" \
    -days   "$DAYS" \
    -extfile "$CERT_DIR/server_ext.cnf" \
    -extensions v3_server
chmod 644 "$CERT_DIR/server.crt"

rm -f "$CERT_DIR/server.csr" "$CERT_DIR/server_ext.cnf"

echo ""
echo "Done."
echo ""
echo "Add to .env on this machine:"
echo "  TLS_CERT_PATH=$CERT_DIR/server.crt"
echo "  TLS_KEY_PATH=$CERT_DIR/server.key"
echo ""
echo "Copy the CA cert to each RPi — NOT server.crt:"
echo "  scp $CERT_DIR/ca.crt pi@<rpi-ip>:~/iot_client/ca.crt"
echo ""
echo "In rpi_client.py set:"
echo "  VERIFY_TLS = \"/home/pi/iot_client/ca.crt\""
