#!/bin/bash
# ============================================
# ResearchFlow - Generate Development SSL Certificates
# ============================================
# This script generates self-signed SSL certificates for local development.
# For production, use Let's Encrypt or a proper CA-signed certificate.
#
# Usage: ./scripts/generate-dev-certs.sh
# ============================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Certificate directories
NGINX_CERT_DIR="$PROJECT_ROOT/certs"
REDIS_CERT_DIR="$PROJECT_ROOT/certs/redis"
POSTGRES_CERT_DIR="$PROJECT_ROOT/certs/postgres"

# Certificate validity (in days)
VALIDITY_DAYS=365

# Common name for certificates
COMMON_NAME="${COMMON_NAME:-localhost}"
ORGANIZATION="${ORGANIZATION:-ResearchFlow Development}"

echo "🔐 Generating development SSL certificates..."
echo "   Common Name: $COMMON_NAME"
echo "   Organization: $ORGANIZATION"
echo "   Validity: $VALIDITY_DAYS days"
echo ""

# Create certificate directories
mkdir -p "$NGINX_CERT_DIR"
mkdir -p "$REDIS_CERT_DIR"
mkdir -p "$POSTGRES_CERT_DIR"

# ===================
# 1. Generate CA certificate (for signing other certificates)
# ===================
echo "📜 Generating CA certificate..."
openssl genrsa -out "$NGINX_CERT_DIR/ca.key" 4096

openssl req -new -x509 \
    -days $VALIDITY_DAYS \
    -key "$NGINX_CERT_DIR/ca.key" \
    -out "$NGINX_CERT_DIR/ca.crt" \
    -subj "/C=US/ST=Development/L=Local/O=$ORGANIZATION/CN=ResearchFlow CA"

echo "   ✓ CA certificate created: $NGINX_CERT_DIR/ca.crt"

# ===================
# 2. Generate Nginx/Web certificate
# ===================
echo ""
echo "🌐 Generating Nginx SSL certificate..."

# Generate private key
openssl genrsa -out "$NGINX_CERT_DIR/privkey.pem" 2048

# Generate CSR with SAN (Subject Alternative Names)
cat > "$NGINX_CERT_DIR/san.cnf" << EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn
req_extensions = req_ext

[dn]
C=US
ST=Development
L=Local
O=$ORGANIZATION
CN=$COMMON_NAME

[req_ext]
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
DNS.2 = $COMMON_NAME
DNS.3 = web
DNS.4 = *.researchflow.local
IP.1 = 127.0.0.1
IP.2 = ::1
EOF

openssl req -new \
    -key "$NGINX_CERT_DIR/privkey.pem" \
    -out "$NGINX_CERT_DIR/server.csr" \
    -config "$NGINX_CERT_DIR/san.cnf"

# Sign with CA
openssl x509 -req \
    -days $VALIDITY_DAYS \
    -in "$NGINX_CERT_DIR/server.csr" \
    -CA "$NGINX_CERT_DIR/ca.crt" \
    -CAkey "$NGINX_CERT_DIR/ca.key" \
    -CAcreateserial \
    -out "$NGINX_CERT_DIR/fullchain.pem" \
    -extfile "$NGINX_CERT_DIR/san.cnf" \
    -extensions req_ext

echo "   ✓ Nginx certificate created: $NGINX_CERT_DIR/fullchain.pem"

# ===================
# 3. Generate Redis TLS certificate
# ===================
echo ""
echo "🔴 Generating Redis TLS certificate..."

openssl genrsa -out "$REDIS_CERT_DIR/redis.key" 2048

cat > "$REDIS_CERT_DIR/redis.cnf" << EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn

[dn]
C=US
ST=Development
L=Local
O=$ORGANIZATION
CN=redis
EOF

openssl req -new \
    -key "$REDIS_CERT_DIR/redis.key" \
    -out "$REDIS_CERT_DIR/redis.csr" \
    -config "$REDIS_CERT_DIR/redis.cnf"

openssl x509 -req \
    -days $VALIDITY_DAYS \
    -in "$REDIS_CERT_DIR/redis.csr" \
    -CA "$NGINX_CERT_DIR/ca.crt" \
    -CAkey "$NGINX_CERT_DIR/ca.key" \
    -CAcreateserial \
    -out "$REDIS_CERT_DIR/redis.crt"

# Copy CA cert for Redis client verification
cp "$NGINX_CERT_DIR/ca.crt" "$REDIS_CERT_DIR/ca.crt"

echo "   ✓ Redis certificate created: $REDIS_CERT_DIR/redis.crt"

# ===================
# 4. Generate PostgreSQL SSL certificate
# ===================
echo ""
echo "🐘 Generating PostgreSQL SSL certificate..."

openssl genrsa -out "$POSTGRES_CERT_DIR/server.key" 2048
chmod 600 "$POSTGRES_CERT_DIR/server.key"

cat > "$POSTGRES_CERT_DIR/postgres.cnf" << EOF
[req]
default_bits = 2048
prompt = no
default_md = sha256
distinguished_name = dn

[dn]
C=US
ST=Development
L=Local
O=$ORGANIZATION
CN=postgres
EOF

openssl req -new \
    -key "$POSTGRES_CERT_DIR/server.key" \
    -out "$POSTGRES_CERT_DIR/server.csr" \
    -config "$POSTGRES_CERT_DIR/postgres.cnf"

openssl x509 -req \
    -days $VALIDITY_DAYS \
    -in "$POSTGRES_CERT_DIR/server.csr" \
    -CA "$NGINX_CERT_DIR/ca.crt" \
    -CAkey "$NGINX_CERT_DIR/ca.key" \
    -CAcreateserial \
    -out "$POSTGRES_CERT_DIR/server.crt"

echo "   ✓ PostgreSQL certificate created: $POSTGRES_CERT_DIR/server.crt"

# ===================
# 5. Clean up temporary files
# ===================
echo ""
echo "🧹 Cleaning up temporary files..."
rm -f "$NGINX_CERT_DIR"/*.csr "$NGINX_CERT_DIR"/*.srl "$NGINX_CERT_DIR"/*.cnf
rm -f "$REDIS_CERT_DIR"/*.csr "$REDIS_CERT_DIR"/*.cnf
rm -f "$POSTGRES_CERT_DIR"/*.csr "$POSTGRES_CERT_DIR"/*.cnf

# ===================
# 6. Set appropriate permissions
# ===================
echo "🔒 Setting file permissions..."
chmod 600 "$NGINX_CERT_DIR/privkey.pem" "$NGINX_CERT_DIR/ca.key"
chmod 644 "$NGINX_CERT_DIR/fullchain.pem" "$NGINX_CERT_DIR/ca.crt"
chmod 600 "$REDIS_CERT_DIR/redis.key"
chmod 644 "$REDIS_CERT_DIR/redis.crt" "$REDIS_CERT_DIR/ca.crt"
chmod 600 "$POSTGRES_CERT_DIR/server.key"
chmod 644 "$POSTGRES_CERT_DIR/server.crt"

# ===================
# Summary
# ===================
echo ""
echo "✅ Development SSL certificates generated successfully!"
echo ""
echo "📁 Certificate locations:"
echo "   Nginx/Web:"
echo "      - Certificate: $NGINX_CERT_DIR/fullchain.pem"
echo "      - Private Key: $NGINX_CERT_DIR/privkey.pem"
echo "      - CA:          $NGINX_CERT_DIR/ca.crt"
echo ""
echo "   Redis:"
echo "      - Certificate: $REDIS_CERT_DIR/redis.crt"
echo "      - Private Key: $REDIS_CERT_DIR/redis.key"
echo "      - CA:          $REDIS_CERT_DIR/ca.crt"
echo ""
echo "   PostgreSQL:"
echo "      - Certificate: $POSTGRES_CERT_DIR/server.crt"
echo "      - Private Key: $POSTGRES_CERT_DIR/server.key"
echo ""
echo "⚠️  These are DEVELOPMENT certificates only!"
echo "   For production, use Let's Encrypt or a proper CA-signed certificate."
echo ""
echo "🔧 To trust the CA on your system (optional):"
echo "   macOS:  sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain $NGINX_CERT_DIR/ca.crt"
echo "   Ubuntu: sudo cp $NGINX_CERT_DIR/ca.crt /usr/local/share/ca-certificates/researchflow-dev.crt && sudo update-ca-certificates"
