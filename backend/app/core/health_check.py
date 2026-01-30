"""
Health check system
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Dict, Any
from app.core.database import SessionLocal, get_db
from app.core.config import settings
from sqlalchemy.orm import Session
from sqlalchemy import text
import redis
from neo4j import GraphDatabase

router = APIRouter()


class HealthStatus(BaseModel):
    status: str
    version: str
    services: Dict[str, Any]


@router.get("/health", response_model=HealthStatus)
async def health_check(db: Session = Depends(get_db)):
    """Comprehensive health check"""
    services = {
        "api": {"status": "healthy"},
        "database": check_database(db),
        "redis": check_redis(),
        "neo4j": check_neo4j(),
    }
    
    # Overall status
    all_healthy = all(
        service.get("status") == "healthy"
        for service in services.values()
        if isinstance(service, dict)
    )
    
    return HealthStatus(
        status="healthy" if all_healthy else "degraded",
        version=settings.APP_VERSION,
        services=services
    )


def check_database(db: Session) -> Dict[str, Any]:
    """Check PostgreSQL database"""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "type": "postgresql"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_redis() -> Dict[str, Any]:
    """Check Redis connection"""
    try:
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD,
            socket_connect_timeout=2
        )
        r.ping()
        return {"status": "healthy", "type": "redis"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


def check_neo4j() -> Dict[str, Any]:
    """Check Neo4j connection"""
    try:
        driver = GraphDatabase.driver(
            f"bolt://{settings.NEO4J_HOST}:{settings.NEO4J_PORT}",
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        with driver.session() as session:
            session.run("RETURN 1")
        driver.close()
        return {"status": "healthy", "type": "neo4j"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@router.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe"""
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    """Kubernetes readiness probe"""
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ready"}
    except:
        return {"status": "not_ready"}
