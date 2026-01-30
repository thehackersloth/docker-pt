# Single Container - All-in-One Pentesting Platform
FROM docker.io/kalilinux/kali-rolling:latest

# Set environment
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV LANG=C.UTF-8

# Install system dependencies (split into steps for better error handling)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget git vim nano \
    python3 python3-pip python3-venv python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y --no-install-recommends nodejs && \
    rm -rf /var/lib/apt/lists/*

# Install database and services
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql postgresql-contrib \
    redis-server \
    default-jdk \
    nginx supervisor \
    net-tools iputils-ping \
    && rm -rf /var/lib/apt/lists/*

# Install Kali tools (split into smaller groups for better error handling)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nmap masscan nikto sqlmap wpscan \
    hydra john hashcat medusa \
    metasploit-framework \
    crackmapexec impacket-scripts responder \
    sslscan testssl.sh sslyze \
    wfuzz ffuf gobuster \
    theharvester recon-ng amass subfinder \
    aircrack-ng wifite \
    && rm -rf /var/lib/apt/lists/* || true

# Install additional tools that might not be in repos
RUN apt-get update && apt-get install -y --no-install-recommends \
    bloodhound \
    kerbrute \
    || echo "Some optional tools not available" && \
    rm -rf /var/lib/apt/lists/* || true

# Install Python packages (use --break-system-packages for container)
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages --ignore-installed -r /tmp/requirements.txt && \
    pip3 install --no-cache-dir --break-system-packages --ignore-installed supervisor gunicorn

# Install Neo4j
RUN wget -O - https://debian.neo4j.com/neotechnology.gpg.key | apt-key add - && \
    echo 'deb https://debian.neo4j.com stable 5' | tee -a /etc/apt/sources.list.d/neo4j.list && \
    apt-get update && apt-get install -y neo4j || \
    (wget -O /tmp/neo4j.deb https://dist.neo4j.org/neo4j-community-5.15.0.deb && \
     dpkg -i /tmp/neo4j.deb || apt-get install -f -y && \
     rm /tmp/neo4j.deb) && \
    rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy backend
COPY backend /app/backend

# Build frontend
COPY frontend /app/frontend
WORKDIR /app/frontend
RUN npm install && npm run build
WORKDIR /app

# Create data directories
RUN mkdir -p /data/{scans,logs,evidence,bloodhound,backups} && \
    chmod -R 777 /data

# Configure PostgreSQL
RUN service postgresql start && \
    sudo -u postgres psql -c "CREATE DATABASE pentest;" && \
    sudo -u postgres psql -c "CREATE USER pentest WITH PASSWORD 'placeholder';" && \
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE pentest TO pentest;" && \
    sudo -u postgres psql -c "ALTER USER pentest CREATEDB;" || true

# Configure Neo4j
RUN mkdir -p /var/lib/neo4j/data /var/lib/neo4j/logs && \
    chown -R neo4j:neo4j /var/lib/neo4j || true

# Configure Redis
RUN sed -i 's/^bind 127.0.0.1/bind 0.0.0.0/' /etc/redis/redis.conf && \
    sed -i 's/^# requirepass foobared/requirepass placeholder/' /etc/redis/redis.conf || true

# Configure Nginx
COPY container/nginx.conf /etc/nginx/sites-available/default
RUN ln -sf /etc/nginx/sites-available/default /etc/nginx/sites-enabled/default

# Configure Supervisor
COPY container/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose ports
EXPOSE 80 8000 5432 6379 7474 7687 11434

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Copy entrypoint
COPY container/entrypoint-single.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Start all services
ENTRYPOINT ["/app/entrypoint.sh"]
