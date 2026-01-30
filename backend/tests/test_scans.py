"""
Scan tests
"""

import pytest
from fastapi import status


def test_create_scan(client, admin_user):
    """Test creating a scan"""
    # Login first
    login_response = client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "testpass"}
    )
    token = login_response.json()["access_token"]
    
    # Create scan
    response = client.post(
        "/api/v1/scans",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Test Scan",
            "scan_type": "network",
            "targets": ["127.0.0.1"]
        }
    )
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_201_CREATED]
    assert "id" in response.json()


def test_list_scans(client, admin_user):
    """Test listing scans"""
    # Login first
    login_response = client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "testpass"}
    )
    token = login_response.json()["access_token"]
    
    # List scans
    response = client.get(
        "/api/v1/scans",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), list)
