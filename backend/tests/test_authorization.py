"""
Authorization tests
"""

import pytest
from fastapi import status


def test_create_authorization(client, admin_user):
    """Test creating authorization"""
    # Login first
    login_response = client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "testpass"}
    )
    token = login_response.json()["access_token"]
    
    # Create authorization
    response = client.post(
        "/api/v1/authorization/create",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "target": "192.168.1.1",
            "disclaimer_accepted": True,
            "terms_accepted": True
        }
    )
    
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["disclaimer_accepted"] is True


def test_get_disclaimer(client):
    """Test getting current disclaimer"""
    response = client.get("/api/v1/authorization/disclaimer/current")
    
    assert response.status_code == status.HTTP_200_OK
    assert "content" in response.json()
