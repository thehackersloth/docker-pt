"""
API v1 Router - Automated Penetration Testing Platform
"""

from fastapi import APIRouter

# Core routers
from app.api.v1 import (
    health,
    auth,
    scans,
    config,
    findings,
    reports,
    dashboard,
    schedules,
)

# AI & Automation
from app.api.v1 import (
    ai,
    ai_cost,
    automation,
    natural_language,
    methodology,
    learning,
)

# Security Tools
from app.api.v1 import (
    bloodhound,
    metasploit,
    empire,
)

# Scan Management
from app.api.v1 import (
    scan_profiles,
    scan_approval,
)

# User & Access Management
from app.api.v1 import (
    authorization,
    sessions,
    mfa,
    oauth,
    ldap,
    password_reset,
    invitations,
)

# Data & Evidence
from app.api.v1 import (
    evidence,
    data_management,
    backup,
    pdf_upload,
    assets,
)

# Monitoring & Analytics
from app.api.v1 import (
    monitoring,
    metrics,
    analytics,
    advanced_analytics,
)

# Integrations & Communication
from app.api.v1 import (
    integrations,
    notifications,
    email_advanced,
    websocket,
)

# Project & Compliance
from app.api.v1 import (
    projects,
    compliance,
    webhooks,
    vulndb,
)

# Other
from app.api.v1 import (
    competitive,
    rayserve,
)

api_router = APIRouter()

# Core endpoints
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(scans.router, prefix="/scans", tags=["scans"])
api_router.include_router(config.router, prefix="/config", tags=["configuration"])
api_router.include_router(findings.router, prefix="/findings", tags=["findings"])
api_router.include_router(reports.router, prefix="/reports", tags=["reports"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])

# AI & Automation endpoints
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(ai_cost.router, prefix="/ai-cost", tags=["ai-cost"])
api_router.include_router(automation.router, prefix="/automation", tags=["automation"])
api_router.include_router(natural_language.router, prefix="/nl", tags=["natural-language"])
api_router.include_router(methodology.router, prefix="/methodology", tags=["methodology"])
api_router.include_router(learning.router, prefix="/learning", tags=["learning"])

# Security Tool endpoints
api_router.include_router(bloodhound.router, prefix="/bloodhound", tags=["bloodhound"])
api_router.include_router(metasploit.router, prefix="/metasploit", tags=["metasploit"])
api_router.include_router(empire.router, prefix="/empire", tags=["empire"])

# Scan Management endpoints
api_router.include_router(scan_profiles.router, prefix="/scan-profiles", tags=["scan-profiles"])
api_router.include_router(scan_approval.router, prefix="/scan-approval", tags=["scan-approval"])

# User & Access Management endpoints
api_router.include_router(authorization.router, prefix="/authorization", tags=["authorization"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["sessions"])
api_router.include_router(mfa.router, prefix="/mfa", tags=["mfa"])
api_router.include_router(oauth.router, prefix="/oauth", tags=["oauth"])
api_router.include_router(ldap.router, prefix="/ldap", tags=["ldap"])
api_router.include_router(password_reset.router, prefix="/password-reset", tags=["password-reset"])
api_router.include_router(invitations.router, prefix="/invitations", tags=["invitations"])

# Data & Evidence endpoints
api_router.include_router(evidence.router, prefix="/evidence", tags=["evidence"])
api_router.include_router(data_management.router, prefix="/data", tags=["data-management"])
api_router.include_router(backup.router, prefix="/backup", tags=["backup"])
api_router.include_router(pdf_upload.router, prefix="/pdf-upload", tags=["pdf-upload"])
api_router.include_router(assets.router, prefix="/assets", tags=["assets"])

# Monitoring & Analytics endpoints
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["monitoring"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(advanced_analytics.router, prefix="/advanced-analytics", tags=["advanced-analytics"])

# Integration & Communication endpoints
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(email_advanced.router, prefix="/email", tags=["email"])
api_router.include_router(websocket.router, prefix="/ws", tags=["websocket"])

# Project & Compliance endpoints
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(compliance.router, prefix="/compliance", tags=["compliance"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(vulndb.router, prefix="/vulndb", tags=["vulnerability-database"])

# Other endpoints
api_router.include_router(competitive.router, prefix="/competitive", tags=["competitive"])
api_router.include_router(rayserve.router, prefix="/rayserve", tags=["rayserve"])
