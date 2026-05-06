from __future__ import annotations

import os
from pathlib import Path
from uuid import UUID

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./authlink_test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("BASE_URL", "http://testserver")

from app.database import AsyncSessionLocal, Base, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models import URL  # noqa: E402

TEST_DB_FILE = Path("authlink_test.db")


@pytest_asyncio.fixture(autouse=True)
async def reset_database() -> None:
    if TEST_DB_FILE.exists():
        TEST_DB_FILE.unlink()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)
        await connection.run_sync(Base.metadata.create_all)

    yield

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)

    if TEST_DB_FILE.exists():
        TEST_DB_FILE.unlink()


@pytest.mark.asyncio
async def test_register_login_create_redirect_and_delete() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        register_response = await client.post(
            "/auth/register",
            json={"email": "user@example.com", "password": "StrongPass123!"},
        )
        assert register_response.status_code == 201
        assert register_response.json()["email"] == "user@example.com"

        login_response = await client.post(
            "/auth/login",
            data={"username": "user@example.com", "password": "StrongPass123!"},
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        create_response = await client.post(
            "/urls",
            headers=headers,
            json={"original_url": "https://example.com/articles/123"},
        )
        assert create_response.status_code == 201
        created_url = create_response.json()
        assert len(created_url["short_code"]) == 7
        url_id = created_url["id"]
        short_code = created_url["short_code"]

        list_response = await client.get("/urls/me", headers=headers)
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1

        redirect_response = await client.get(f"/{short_code}", follow_redirects=False)
        assert redirect_response.status_code == 307
        assert redirect_response.headers["location"] == "https://example.com/articles/123"

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(URL).where(URL.id == UUID(url_id)))
            stored_url = result.scalar_one()
            assert stored_url.click_count == 1

        delete_response = await client.delete(f"/urls/{url_id}", headers=headers)
        assert delete_response.status_code == 204

        missing_response = await client.get(f"/{short_code}", follow_redirects=False)
        assert missing_response.status_code == 404
