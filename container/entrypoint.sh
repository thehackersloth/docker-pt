#!/bin/bash
# Entrypoint script for pentest container

set -e

echo "=========================================="
echo "Professional Pentesting Platform"
echo "Container Starting..."
echo "=========================================="

# Generate secrets if not provided
export SECRET_KEY="${SECRET_KEY:-$(openssl rand -hex 32)}"
export ENCRYPTION_KEY="${ENCRYPTION_KEY:-$(openssl rand -hex 32)}"
export JWT_SECRET="${JWT_SECRET:-$(openssl rand -hex 32)}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(openssl rand -hex 12)}"
export NEO4J_PASSWORD="${NEO4J_PASSWORD:-$(openssl rand -hex 12)}"
export POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
export POSTGRES_USER="${POSTGRES_USER:-pentest}"
export POSTGRES_DB="${POSTGRES_DB:-pentest}"
export REDIS_HOST="${REDIS_HOST:-localhost}"
export REDIS_PORT="${REDIS_PORT:-6379}"
export NEO4J_HOST="${NEO4J_HOST:-localhost}"
export NEO4J_PORT="${NEO4J_PORT:-7687}"
export DATABASE_URL="postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@${POSTGRES_HOST}:${POSTGRES_PORT}/${POSTGRES_DB}"

# Write environment to file for other processes
cat > /app/backend/.env << EOF
SECRET_KEY=${SECRET_KEY}
ENCRYPTION_KEY=${ENCRYPTION_KEY}
JWT_SECRET=${JWT_SECRET}
POSTGRES_HOST=${POSTGRES_HOST}
POSTGRES_PORT=${POSTGRES_PORT}
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_DB=${POSTGRES_DB}
DATABASE_URL=${DATABASE_URL}
REDIS_HOST=${REDIS_HOST}
REDIS_PORT=${REDIS_PORT}
NEO4J_HOST=${NEO4J_HOST}
NEO4J_PORT=${NEO4J_PORT}
NEO4J_PASSWORD=${NEO4J_PASSWORD}
AI_ENABLED=true
AI_PRIVACY_MODE=normal
AI_LOCAL_ONLY=false
OPENAI_ENABLED=false
ANTHROPIC_ENABLED=false
OLLAMA_ENABLED=false
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
LLAMA_CPP_ENABLED=false
LLAMA_CPP_MODEL_PATH=/models/llama.gguf
RAYSERVE_ENABLED=false
RAYSERVE_ENDPOINT=http://localhost:8080
WHITERABBIT_NEO_ENABLED=false
WHITERABBIT_NEO_BASE_URL=http://localhost:5000
WHITERABBIT_NEO_MODEL=whiterabbit-neo
GEMINI_ENABLED=false
GITHUB_COPILOT_ENABLED=false
SMTP_ENABLED=false
SMTP_HOST=localhost
SMTP_PORT=587
SMTP_USE_TLS=true
EMAIL_FROM=noreply@localhost
EMAIL_FROM_NAME=Pentest Platform
MAX_CONCURRENT_SCANS=5
MAX_SCAN_DURATION=3600
JWT_EXPIRATION=3600
AUDIT_ENABLED=true
LOG_AI_QUERIES=true
APP_NAME=Professional Pentesting Platform
APP_VERSION=1.0.0
TIMEZONE=UTC
LOG_LEVEL=INFO
DEBUG=false
REPORT_OUTPUT_DIR=/data/reports
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
EOF

# Initialize directories
mkdir -p /data/scans
mkdir -p /data/bloodhound
mkdir -p /data/logs
mkdir -p /data/evidence
mkdir -p /data/reports
mkdir -p /opt/pentest/results
mkdir -p /opt/pentest/logs
mkdir -p /var/log/supervisor

# Set permissions
chmod -R 755 /data
chmod -R 755 /opt/pentest
chmod 600 /app/backend/.env

# Initialize PostgreSQL if data directory is empty
PG_DATA="/var/lib/postgresql/18/main"
if [ ! -f "$PG_DATA/PG_VERSION" ]; then
    echo "Initializing PostgreSQL database..."
    sudo -u postgres /usr/lib/postgresql/18/bin/initdb -D "$PG_DATA"

    # Configure PostgreSQL to allow local connections
    echo "local all all trust" > "$PG_DATA/pg_hba.conf"
    echo "host all all 127.0.0.1/32 md5" >> "$PG_DATA/pg_hba.conf"
    echo "host all all ::1/128 md5" >> "$PG_DATA/pg_hba.conf"
fi

# Start PostgreSQL
echo "Starting PostgreSQL..."
sudo -u postgres /usr/lib/postgresql/18/bin/pg_ctl -D "$PG_DATA" -l /var/log/supervisor/postgresql.log start || true
sleep 2

# Create database and user if they don't exist
sudo -u postgres psql -c "CREATE DATABASE ${POSTGRES_DB};" 2>/dev/null || true
sudo -u postgres psql -c "CREATE USER ${POSTGRES_USER} WITH PASSWORD '${POSTGRES_PASSWORD}';" 2>/dev/null || true
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB} TO ${POSTGRES_USER};" 2>/dev/null || true
sudo -u postgres psql -c "ALTER USER ${POSTGRES_USER} CREATEDB;" 2>/dev/null || true
sudo -u postgres psql -d ${POSTGRES_DB} -c "GRANT ALL ON SCHEMA public TO ${POSTGRES_USER};" 2>/dev/null || true

# Start Redis
echo "Starting Redis..."
redis-server /etc/redis/redis.conf --daemonize yes || redis-server --daemonize yes

# Wait for services
sleep 2

# Display tool versions
echo "=========================================="
echo "Installed Tools:"
echo "=========================================="
echo "Nmap: $(nmap --version | head -n 1)"
echo "Metasploit: $(msfconsole --version 2>/dev/null || echo 'Installed')"
echo "Python: $(python3 --version)"
echo "PostgreSQL: $(/usr/lib/postgresql/18/bin/postgres --version)"
echo "=========================================="
echo ""
echo "Services:"
echo "  - Frontend: http://localhost:80"
echo "  - Backend API: http://localhost:8000"
echo "=========================================="

# Start supervisor for remaining services (backend, nginx, celery)
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
