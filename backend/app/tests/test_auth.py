import pytest
from httpx import AsyncClient
from app.tests.conftest import get_token


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, admin_user):
    resp = await client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "Admin@123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "admin"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, admin_user):
    resp = await client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient):
    resp = await client.post(
        "/api/auth/login",
        data={"username": "nobody", "password": "anything"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, admin_user):
    token = await get_token(client, "admin", "Admin@123")
    resp = await client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["username"] == "admin"


@pytest.mark.asyncio
async def test_get_me_no_token(client: AsyncClient):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_inactive_user_cannot_login(client: AsyncClient, db_session, admin_user):
    admin_user.is_active = False
    await db_session.flush()
    resp = await client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "Admin@123"},
    )
    assert resp.status_code == 403
