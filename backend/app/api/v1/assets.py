"""
Asset management endpoints - manage hosts, networks, domains, and other targets
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from typing import List, Optional
from app.core.database import get_db
from app.models.asset import Asset, AssetType, AssetCriticality
from sqlalchemy.orm import Session
from datetime import datetime
import ipaddress

router = APIRouter()


class AssetCreate(BaseModel):
    name: str
    asset_type: str  # host, domain, ip_range, web_application, api, cloud_resource
    identifier: str  # IP, domain, CIDR, URL
    description: Optional[str] = None
    criticality: Optional[str] = "unknown"
    tags: Optional[List[str]] = None
    owner: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    properties: Optional[dict] = None


class AssetUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    criticality: Optional[str] = None
    tags: Optional[List[str]] = None
    owner: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None
    properties: Optional[dict] = None


class AssetResponse(BaseModel):
    id: str
    name: str
    asset_type: str
    identifier: str
    description: Optional[str] = None
    criticality: str
    tags: Optional[List[str]] = None
    owner: Optional[str] = None
    department: Optional[str] = None
    location: Optional[str] = None
    discovered_at: str
    last_seen: str
    vulnerabilities_count: int
    findings_count: int
    notes: Optional[str] = None
    properties: Optional[dict] = None

    class Config:
        from_attributes = True


class AssetListResponse(BaseModel):
    items: List[AssetResponse]
    total: int
    page: int
    page_size: int


class BulkAssetCreate(BaseModel):
    """Create multiple assets at once - supports CIDR expansion"""
    assets: Optional[List[AssetCreate]] = None
    cidr_ranges: Optional[List[str]] = None  # Auto-create hosts from CIDR
    domains: Optional[List[str]] = None  # Auto-create domain assets
    default_criticality: Optional[str] = "unknown"
    default_tags: Optional[List[str]] = None


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(asset: AssetCreate, db: Session = Depends(get_db)):
    """Create a new asset (host, network, domain, etc.)"""
    # Check for duplicate identifier
    existing = db.query(Asset).filter(Asset.identifier == asset.identifier).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Asset with identifier '{asset.identifier}' already exists"
        )

    # Validate asset type
    try:
        asset_type = AssetType(asset.asset_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid asset type: {asset.asset_type}")

    # Validate criticality
    try:
        criticality = AssetCriticality(asset.criticality) if asset.criticality else AssetCriticality.UNKNOWN
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid criticality: {asset.criticality}")

    db_asset = Asset(
        name=asset.name,
        asset_type=asset_type,
        identifier=asset.identifier,
        description=asset.description,
        criticality=criticality,
        tags=asset.tags,
        owner=asset.owner,
        department=asset.department,
        location=asset.location,
        notes=asset.notes,
        properties=asset.properties,
        discovered_by="manual"
    )

    db.add(db_asset)
    db.commit()
    db.refresh(db_asset)

    return _asset_to_response(db_asset)


@router.post("/bulk", status_code=status.HTTP_201_CREATED)
async def bulk_create_assets(bulk: BulkAssetCreate, db: Session = Depends(get_db)):
    """Bulk create assets - supports CIDR expansion and domain lists"""
    created = []
    errors = []

    # Process individual assets
    if bulk.assets:
        for asset in bulk.assets:
            try:
                existing = db.query(Asset).filter(Asset.identifier == asset.identifier).first()
                if existing:
                    errors.append({"identifier": asset.identifier, "error": "Already exists"})
                    continue

                db_asset = Asset(
                    name=asset.name,
                    asset_type=AssetType(asset.asset_type),
                    identifier=asset.identifier,
                    description=asset.description,
                    criticality=AssetCriticality(asset.criticality or bulk.default_criticality or "unknown"),
                    tags=asset.tags or bulk.default_tags,
                    owner=asset.owner,
                    department=asset.department,
                    location=asset.location,
                    notes=asset.notes,
                    properties=asset.properties,
                    discovered_by="bulk_import"
                )
                db.add(db_asset)
                created.append(asset.identifier)
            except Exception as e:
                errors.append({"identifier": asset.identifier, "error": str(e)})

    # Expand CIDR ranges into individual hosts
    if bulk.cidr_ranges:
        for cidr in bulk.cidr_ranges:
            try:
                network = ipaddress.ip_network(cidr, strict=False)
                # Limit expansion to /24 or smaller to prevent huge lists
                if network.num_addresses > 256:
                    errors.append({"identifier": cidr, "error": "CIDR too large (max /24)"})
                    continue

                for ip in network.hosts():
                    ip_str = str(ip)
                    existing = db.query(Asset).filter(Asset.identifier == ip_str).first()
                    if existing:
                        continue

                    db_asset = Asset(
                        name=f"Host-{ip_str}",
                        asset_type=AssetType.HOST,
                        identifier=ip_str,
                        description=f"Auto-created from CIDR {cidr}",
                        criticality=AssetCriticality(bulk.default_criticality or "unknown"),
                        tags=bulk.default_tags,
                        discovered_by="cidr_expansion"
                    )
                    db.add(db_asset)
                    created.append(ip_str)
            except ValueError as e:
                errors.append({"identifier": cidr, "error": f"Invalid CIDR: {str(e)}"})

    # Add domains
    if bulk.domains:
        for domain in bulk.domains:
            existing = db.query(Asset).filter(Asset.identifier == domain).first()
            if existing:
                errors.append({"identifier": domain, "error": "Already exists"})
                continue

            db_asset = Asset(
                name=domain,
                asset_type=AssetType.DOMAIN,
                identifier=domain,
                criticality=AssetCriticality(bulk.default_criticality or "unknown"),
                tags=bulk.default_tags,
                discovered_by="bulk_import"
            )
            db.add(db_asset)
            created.append(domain)

    db.commit()

    return {
        "created_count": len(created),
        "error_count": len(errors),
        "created": created[:50],  # Limit response size
        "errors": errors[:20]
    }


@router.get("", response_model=AssetListResponse)
async def list_assets(
    asset_type: Optional[str] = None,
    criticality: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """List assets with filtering and pagination"""
    query = db.query(Asset)

    if asset_type:
        try:
            query = query.filter(Asset.asset_type == AssetType(asset_type))
        except ValueError:
            pass

    if criticality:
        try:
            query = query.filter(Asset.criticality == AssetCriticality(criticality))
        except ValueError:
            pass

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Asset.name.ilike(search_term)) |
            (Asset.identifier.ilike(search_term)) |
            (Asset.description.ilike(search_term))
        )

    # Tag filtering (JSON contains)
    if tag:
        query = query.filter(Asset.tags.contains([tag]))

    total = query.count()

    assets = query.order_by(Asset.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return AssetListResponse(
        items=[_asset_to_response(a) for a in assets],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/stats")
async def get_asset_stats(db: Session = Depends(get_db)):
    """Get asset statistics"""
    from sqlalchemy import func

    total = db.query(Asset).count()

    by_type = db.query(Asset.asset_type, func.count(Asset.id)).group_by(Asset.asset_type).all()
    by_criticality = db.query(Asset.criticality, func.count(Asset.id)).group_by(Asset.criticality).all()

    with_vulns = db.query(Asset).filter(Asset.vulnerabilities_count > 0).count()

    return {
        "total": total,
        "by_type": {str(t[0].value) if t[0] else "unknown": t[1] for t in by_type},
        "by_criticality": {str(c[0].value) if c[0] else "unknown": c[1] for c in by_criticality},
        "with_vulnerabilities": with_vulns
    }


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(asset_id: str, db: Session = Depends(get_db)):
    """Get a specific asset by ID"""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    return _asset_to_response(asset)


@router.put("/{asset_id}", response_model=AssetResponse)
async def update_asset(asset_id: str, update: AssetUpdate, db: Session = Depends(get_db)):
    """Update an asset"""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    if update.name is not None:
        asset.name = update.name
    if update.description is not None:
        asset.description = update.description
    if update.criticality is not None:
        try:
            asset.criticality = AssetCriticality(update.criticality)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid criticality: {update.criticality}")
    if update.tags is not None:
        asset.tags = update.tags
    if update.owner is not None:
        asset.owner = update.owner
    if update.department is not None:
        asset.department = update.department
    if update.location is not None:
        asset.location = update.location
    if update.notes is not None:
        asset.notes = update.notes
    if update.properties is not None:
        asset.properties = update.properties

    asset.last_seen = datetime.utcnow()

    db.commit()
    db.refresh(asset)

    return _asset_to_response(asset)


@router.delete("/{asset_id}")
async def delete_asset(asset_id: str, db: Session = Depends(get_db)):
    """Delete an asset"""
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    db.delete(asset)
    db.commit()

    return {"message": "Asset deleted successfully"}


@router.delete("")
async def bulk_delete_assets(asset_ids: List[str], db: Session = Depends(get_db)):
    """Delete multiple assets"""
    deleted = 0
    for asset_id in asset_ids:
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if asset:
            db.delete(asset)
            deleted += 1

    db.commit()
    return {"deleted": deleted}


@router.post("/import/nmap")
async def import_from_nmap(nmap_xml: str, db: Session = Depends(get_db)):
    """Import assets from Nmap XML output"""
    import xml.etree.ElementTree as ET

    created = []
    updated = []

    try:
        root = ET.fromstring(nmap_xml)

        for host in root.findall('.//host'):
            # Get IP address
            addr_elem = host.find('.//address[@addrtype="ipv4"]')
            if addr_elem is None:
                addr_elem = host.find('.//address[@addrtype="ipv6"]')
            if addr_elem is None:
                continue

            ip = addr_elem.get('addr')

            # Get hostname if available
            hostname = None
            hostname_elem = host.find('.//hostname')
            if hostname_elem is not None:
                hostname = hostname_elem.get('name')

            # Get OS info
            os_info = None
            os_match = host.find('.//osmatch')
            if os_match is not None:
                os_info = os_match.get('name')

            # Get open ports
            ports = []
            for port in host.findall('.//port'):
                state = port.find('state')
                if state is not None and state.get('state') == 'open':
                    service = port.find('service')
                    port_info = {
                        'port': port.get('portid'),
                        'protocol': port.get('protocol'),
                        'service': service.get('name') if service is not None else None
                    }
                    ports.append(port_info)

            # Check if exists
            existing = db.query(Asset).filter(Asset.identifier == ip).first()

            properties = {
                'os': os_info,
                'ports': ports,
                'imported_from': 'nmap'
            }

            if existing:
                existing.properties = properties
                existing.last_seen = datetime.utcnow()
                if hostname and not existing.name.startswith('Host-'):
                    existing.name = hostname
                updated.append(ip)
            else:
                asset = Asset(
                    name=hostname or f"Host-{ip}",
                    asset_type=AssetType.HOST,
                    identifier=ip,
                    properties=properties,
                    discovered_by="nmap_import"
                )
                db.add(asset)
                created.append(ip)

        db.commit()

        return {
            "created": len(created),
            "updated": len(updated),
            "created_hosts": created[:20],
            "updated_hosts": updated[:20]
        }
    except ET.ParseError as e:
        raise HTTPException(status_code=400, detail=f"Invalid XML: {str(e)}")


def _asset_to_response(asset: Asset) -> AssetResponse:
    """Convert Asset model to response"""
    return AssetResponse(
        id=str(asset.id),
        name=asset.name,
        asset_type=asset.asset_type.value if asset.asset_type else "unknown",
        identifier=asset.identifier,
        description=asset.description,
        criticality=asset.criticality.value if asset.criticality else "unknown",
        tags=asset.tags,
        owner=asset.owner,
        department=asset.department,
        location=asset.location,
        discovered_at=asset.discovered_at.isoformat() if asset.discovered_at else None,
        last_seen=asset.last_seen.isoformat() if asset.last_seen else None,
        vulnerabilities_count=asset.vulnerabilities_count or 0,
        findings_count=asset.findings_count or 0,
        notes=asset.notes,
        properties=asset.properties
    )
