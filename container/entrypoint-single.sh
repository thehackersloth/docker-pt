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
export POSTGRES_PORT="${POSTGRES_PORT:-5433}"
export POSTGRES_USER="${POSTGRES_USER:-pentest}"
export POSTGRES_DB="${POSTGRES_DB:-pentest}"
export REDIS_HOST="${REDIS_HOST:-localhost}"
export REDIS_PORT="${REDIS_PORT:-6379}"
export REDIS_PASSWORD="${REDIS_PASSWORD:-$(openssl rand -hex 12)}"
export NEO4J_HOST="${NEO4J_HOST:-localhost}"
export NEO4J_PORT="${NEO4J_PORT:-7687}"
export BACKEND_PORT="${BACKEND_PORT:-8888}"
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
REDIS_PASSWORD=${REDIS_PASSWORD}
CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@localhost:6379/0
CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@localhost:6379/0
BACKEND_PORT=${BACKEND_PORT}
EOF

# Initialize directories
mkdir -p /data/scans /data/bloodhound /data/logs /data/evidence /data/reports
mkdir -p /opt/pentest/results /opt/pentest/logs /var/log/supervisor

# Set permissions
chmod -R 755 /data /opt/pentest
chmod 600 /app/backend/.env

# Start PostgreSQL on port 5433 to avoid conflict with host postgres
echo "Starting PostgreSQL..."
sed -i "s/^port = 5432/port = ${POSTGRES_PORT}/" /etc/postgresql/18/main/postgresql.conf 2>/dev/null || true
service postgresql start || true
sleep 2

# Verify PostgreSQL is running
if ! pg_isready -p ${POSTGRES_PORT} -q; then
    echo "PostgreSQL not running, starting manually..."
    sudo -u postgres /usr/lib/postgresql/18/bin/pg_ctl -D /var/lib/postgresql/18/main -l /var/log/supervisor/postgresql.log -o "-p ${POSTGRES_PORT}" start || true
    sleep 2
fi

# Create database and user if they don't exist
sudo -u postgres psql -p ${POSTGRES_PORT} -c "CREATE DATABASE ${POSTGRES_DB};" 2>/dev/null || true
sudo -u postgres psql -p ${POSTGRES_PORT} -c "CREATE USER ${POSTGRES_USER} WITH PASSWORD '${POSTGRES_PASSWORD}';" 2>/dev/null || true
sudo -u postgres psql -p ${POSTGRES_PORT} -c "ALTER USER ${POSTGRES_USER} WITH PASSWORD '${POSTGRES_PASSWORD}';" 2>/dev/null || true
sudo -u postgres psql -p ${POSTGRES_PORT} -c "GRANT ALL PRIVILEGES ON DATABASE ${POSTGRES_DB} TO ${POSTGRES_USER};" 2>/dev/null || true
sudo -u postgres psql -p ${POSTGRES_PORT} -c "ALTER USER ${POSTGRES_USER} CREATEDB;" 2>/dev/null || true
sudo -u postgres psql -p ${POSTGRES_PORT} -d ${POSTGRES_DB} -c "GRANT ALL ON SCHEMA public TO ${POSTGRES_USER};" 2>/dev/null || true
sudo -u postgres psql -p ${POSTGRES_PORT} -d ${POSTGRES_DB} -c "ALTER SCHEMA public OWNER TO ${POSTGRES_USER};" 2>/dev/null || true

# Start Redis
echo "Starting Redis..."
service redis-server start || redis-server --daemonize yes

# Wait for services
sleep 2

# Initialize database tables if needed
if [ ! -f /data/.db_initialized ]; then
    echo "Initializing database tables..."
    cd /app/backend
    python3 -c "
from app.core.database import init_db
import asyncio
asyncio.run(init_db())
" 2>/dev/null || true
    touch /data/.db_initialized
fi

# Display info
echo "=========================================="
echo "Installed Tools:"
echo "=========================================="
nmap --version 2>/dev/null | head -n 1 || echo "Nmap: installed"
python3 --version
/usr/lib/postgresql/18/bin/postgres --version 2>/dev/null || echo "PostgreSQL: 18"
echo "=========================================="
echo ""
echo "Services:"
echo "  - Frontend: http://localhost (port 80)"
echo "  - Backend API: http://localhost:8000"
echo "=========================================="

# Start supervisor for remaining services
exec /usr/bin/supervisord -c /etc/supervisor/conf.d/supervisord.conf
