"""
BloodHound API endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from app.core.database import SessionLocal, get_db
from app.services.tool_runners.bloodhound_runner import BloodHoundRunner
from sqlalchemy.orm import Session
from neo4j import GraphDatabase
from app.core.config import settings

router = APIRouter()


class BloodHoundCollectionRequest(BaseModel):
    domain: str
    dc_ip: str
    username: str
    password: str
    collection_methods: Optional[List[str]] = ["DCOnly", "RPC"]


class BloodHoundQueryRequest(BaseModel):
    query: str
    parameters: Optional[Dict[str, Any]] = None


@router.post("/collect")
async def collect_bloodhound_data(
    request: BloodHoundCollectionRequest,
    scan_id: Optional[str] = None
):
    """Start BloodHound data collection"""
    try:
        runner = BloodHoundRunner(scan_id or "manual")
        results = runner.run(
            targets=[request.dc_ip],
            config={
                "domain": request.domain,
                "dc_ip": request.dc_ip,
                "username": request.username,
                "password": request.password,
                "collection_methods": request.collection_methods,
            }
        )
        
        if results.get("success"):
            # Import to Neo4j
            import_result = runner.import_to_neo4j(results["output_file"])
            results["neo4j_import"] = import_result
        
        return results
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query")
async def execute_bloodhound_query(request: BloodHoundQueryRequest):
    """Execute BloodHound Cypher query"""
    try:
        driver = GraphDatabase.driver(
            f"bolt://{settings.NEO4J_HOST}:{settings.NEO4J_PORT}",
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        
        with driver.session() as session:
            result = session.run(request.query, request.parameters or {})
            records = [dict(record) for record in result]
        
        driver.close()
        
        return {
            "success": True,
            "results": records,
            "count": len(records)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/queries/paths-to-da")
async def get_paths_to_domain_admin(target_user: Optional[str] = None):
    """Get shortest paths to Domain Admin"""
    query = """
    MATCH (u:User)
    MATCH (g:Group {name: "DOMAIN ADMINS@*"})
    MATCH path = shortestPath((u)-[*1..]->(g))
    RETURN path
    ORDER BY length(path)
    LIMIT 10
    """
    
    if target_user:
        query = f"""
        MATCH (u:User {{name: "{target_user}@*"}})
        MATCH (g:Group {{name: "DOMAIN ADMINS@*"}})
        MATCH path = shortestPath((u)-[*1..]->(g))
        RETURN path
        ORDER BY length(path)
        LIMIT 10
        """
    
    request = BloodHoundQueryRequest(query=query)
    return await execute_bloodhound_query(request)


@router.get("/queries/kerberoastable")
async def get_kerberoastable_accounts():
    """Find Kerberoastable accounts"""
    query = """
    MATCH (u:User)
    WHERE u.hasspn = true
    RETURN u.name, u.enabled, u.pwdlastset
    ORDER BY u.pwdlastset
    """
    
    request = BloodHoundQueryRequest(query=query)
    return await execute_bloodhound_query(request)


@router.get("/queries/asrep-roastable")
async def get_asrep_roastable_accounts():
    """Find AS-REP roastable accounts"""
    query = """
    MATCH (u:User)
    WHERE u.dontreqpreauth = true
    RETURN u.name, u.enabled
    """
    
    request = BloodHoundQueryRequest(query=query)
    return await execute_bloodhound_query(request)


@router.get("/graph")
async def get_graph_data(limit: int = 100):
    """Get graph data for visualization"""
    query = f"""
    MATCH (n)
    OPTIONAL MATCH (n)-[r]->(m)
    RETURN n, r, m
    LIMIT {limit}
    """
    
    request = BloodHoundQueryRequest(query=query)
    return await execute_bloodhound_query(request)
