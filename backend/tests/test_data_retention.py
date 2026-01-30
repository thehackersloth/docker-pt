"""
Data retention tests
"""

import pytest
from datetime import datetime, timedelta
from app.services.data_retention import DataRetentionService


def test_delete_old_scans(db):
    """Test deleting old scans"""
    from app.models.scan import Scan, ScanStatus, ScanType
    
    # Create old scan
    old_scan = Scan(
        name="Old Scan",
        scan_type=ScanType.NETWORK,
        status=ScanStatus.COMPLETED,
        targets=["127.0.0.1"],
        created_by="test",
        created_at=datetime.utcnow() - timedelta(days=100)
    )
    db.add(old_scan)
    db.commit()
    
    # Delete old scans
    service = DataRetentionService()
    result = service.delete_old_scans(days=90)
    
    assert result["success"] is True
    assert result["deleted_scans"] >= 1


def test_export_user_data(db, admin_user):
    """Test exporting user data"""
    service = DataRetentionService()
    data = service.export_user_data(str(admin_user.id))
    
    assert "user" in data
    assert data["user"]["id"] == str(admin_user.id)
