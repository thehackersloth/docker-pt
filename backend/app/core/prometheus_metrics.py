"""
Prometheus metrics
"""

from prometheus_client import Counter, Histogram, Gauge
import time

# Request metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# Scan metrics
scans_total = Counter(
    'scans_total',
    'Total scans',
    ['scan_type', 'status']
)

scan_duration = Histogram(
    'scan_duration_seconds',
    'Scan duration',
    ['scan_type']
)

# AI metrics
ai_requests_total = Counter(
    'ai_requests_total',
    'Total AI requests',
    ['provider', 'feature']
)

ai_request_duration = Histogram(
    'ai_request_duration_seconds',
    'AI request duration',
    ['provider']
)

# System metrics
active_scans = Gauge(
    'active_scans',
    'Number of active scans'
)

active_users = Gauge(
    'active_users',
    'Number of active users'
)

database_connections = Gauge(
    'database_connections',
    'Number of database connections'
)
