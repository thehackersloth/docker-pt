"""
WebSocket endpoints for real-time updates
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import List, Dict
import json
import asyncio
from app.core.database import SessionLocal
from app.models.scan import Scan, ScanStatus
from sqlalchemy.orm import Session

router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.scan_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, scan_id: str = None):
        """Accept a WebSocket connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        if scan_id:
            if scan_id not in self.scan_connections:
                self.scan_connections[scan_id] = []
            self.scan_connections[scan_id].append(websocket)
    
    def disconnect(self, websocket: WebSocket, scan_id: str = None):
        """Remove a WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if scan_id and scan_id in self.scan_connections:
            if websocket in self.scan_connections[scan_id]:
                self.scan_connections[scan_id].remove(websocket)
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to a specific connection"""
        await websocket.send_json(message)
    
    async def broadcast(self, message: dict):
        """Broadcast to all connections"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass
    
    async def broadcast_to_scan(self, scan_id: str, message: dict):
        """Broadcast to connections watching a specific scan"""
        if scan_id in self.scan_connections:
            for connection in self.scan_connections[scan_id]:
                try:
                    await connection.send_json(message)
                except:
                    pass


manager = ConnectionManager()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """General WebSocket endpoint"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo back or process message
            await manager.send_personal_message({"message": data}, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("/ws/scan/{scan_id}")
async def websocket_scan(websocket: WebSocket, scan_id: str):
    """WebSocket endpoint for scan progress updates"""
    await manager.connect(websocket, scan_id)
    try:
        db = SessionLocal()
        # Send initial scan status
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if scan:
            await manager.send_personal_message({
                "type": "scan_status",
                "scan_id": scan_id,
                "status": scan.status.value,
                "progress": scan.progress_percent,
                "findings_count": scan.findings_count,
            }, websocket)
        
        # Poll for updates
        while True:
            await asyncio.sleep(2)  # Poll every 2 seconds
            
            scan = db.query(Scan).filter(Scan.id == scan_id).first()
            if scan:
                await manager.send_personal_message({
                    "type": "scan_update",
                    "scan_id": scan_id,
                    "status": scan.status.value,
                    "progress": scan.progress_percent,
                    "findings_count": scan.findings_count,
                    "critical_count": scan.critical_count,
                    "high_count": scan.high_count,
                    "medium_count": scan.medium_count,
                    "low_count": scan.low_count,
                }, websocket)
            
            # Check for disconnect
            try:
                await websocket.receive_text()
            except:
                break
                
    except WebSocketDisconnect:
        manager.disconnect(websocket, scan_id)
    finally:
        db.close()


@router.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    """WebSocket endpoint for dashboard updates"""
    await manager.connect(websocket)
    try:
        while True:
            db = SessionLocal()
            # Get dashboard stats
            total_scans = db.query(Scan).count()
            running_scans = db.query(Scan).filter(Scan.status == ScanStatus.RUNNING).count()
            completed_scans = db.query(Scan).filter(Scan.status == ScanStatus.COMPLETED).count()
            
            await manager.send_personal_message({
                "type": "dashboard_update",
                "total_scans": total_scans,
                "running_scans": running_scans,
                "completed_scans": completed_scans,
            }, websocket)
            
            db.close()
            await asyncio.sleep(5)  # Update every 5 seconds
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
