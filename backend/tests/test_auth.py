"""
Authentication tests
"""

import pytest
from fastapi import status


def test_login_success(client, admin_user):
    """Test successful login"""
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "testpass"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()


def test_login_failure(client):
    """Test failed login"""
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "wrongpass"}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_get_current_user(client, admin_user):
    """Test getting current user"""
    # Login first
    login_response = client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "testpass"}
    )
    token = login_response.json()["access_token"]
    
    # Get current user
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["username"] == "admin"
