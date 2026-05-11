from __future__ import annotations

import os
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from fastapi import HTTPException, status
from httpx import ASGITransport, AsyncClient
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./authlink_test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("BASE_URL", "http://testserver")

from app.auth.service import (
    authenticate_user,
    create_access_token,
    get_user_by_email,
    get_user_by_id,
    hash_password,
    login_user,
    register_user,
    verify_password,
)
from app.config import get_settings
from app.database import AsyncSessionLocal
from app.main import app
from app.models import User

settings = get_settings()


@pytest_asyncio.fixture
async def session(reset_database) -> AsyncSession:
    """Create an async session for database tests."""
    async with AsyncSessionLocal() as async_session:
        yield async_session


@pytest_asyncio.fixture
async def test_user(session: AsyncSession) -> User:
    """Create a test user in the database."""
    user = User(
        email="testuser@example.com",
        hashed_password=hash_password("TestPassword123!"),
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# ============================================================================
# Unit Tests for Service Functions
# ============================================================================


class TestPasswordHashing:
    """Tests for password hashing and verification."""

    def test_hash_password(self) -> None:
        """Test that hash_password returns a hashed string."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        assert hashed != password
        assert len(hashed) > len(password)

    def test_verify_password_success(self) -> None:
        """Test that verify_password returns True for correct password."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_password_failure(self) -> None:
        """Test that verify_password returns False for incorrect password."""
        password = "TestPassword123!"
        hashed = hash_password(password)
        assert verify_password("WrongPassword123!", hashed) is False

    def test_different_passwords_produce_different_hashes(self) -> None:
        """Test that the same password creates different hashes (due to salt)."""
        password = "TestPassword123!"
        hashed1 = hash_password(password)
        hashed2 = hash_password(password)
        # Hashes should be different due to random salt
        assert hashed1 != hashed2


class TestTokenCreation:
    """Tests for JWT token creation and validation."""

    def test_create_access_token(self) -> None:
        """Test that create_access_token returns a valid JWT."""
        user_id = str(uuid4())
        token = create_access_token(user_id)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_access_token_contains_user_id(self) -> None:
        """Test that the token contains the correct user ID."""
        user_id = str(uuid4())
        token = create_access_token(user_id)
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["sub"] == user_id

    def test_create_access_token_has_expiration(self) -> None:
        """Test that the token has an expiration time."""
        user_id = str(uuid4())
        token = create_access_token(user_id)
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert "exp" in payload


class TestUserQueries:
    """Tests for user query functions."""

    @pytest.mark.asyncio
    async def test_get_user_by_email_found(self, session: AsyncSession, test_user: User) -> None:
        """Test getting a user by email when they exist."""
        user = await get_user_by_email(session, "testuser@example.com")
        assert user is not None
        assert user.email == "testuser@example.com"
        assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_get_user_by_email_not_found(self, session: AsyncSession) -> None:
        """Test getting a user by email when they don't exist."""
        user = await get_user_by_email(session, "nonexistent@example.com")
        assert user is None

    @pytest.mark.asyncio
    async def test_get_user_by_id_found(self, session: AsyncSession, test_user: User) -> None:
        """Test getting a user by ID when they exist."""
        user = await get_user_by_id(session, test_user.id)
        assert user is not None
        assert user.id == test_user.id
        assert user.email == "testuser@example.com"

    @pytest.mark.asyncio
    async def test_get_user_by_id_not_found(self, session: AsyncSession) -> None:
        """Test getting a user by ID when they don't exist."""
        user = await get_user_by_id(session, uuid4())
        assert user is None


class TestUserRegistration:
    """Tests for user registration."""

    @pytest.mark.asyncio
    async def test_register_user_success(self, session: AsyncSession) -> None:
        """Test successful user registration."""
        user = await register_user(session, "newuser@example.com", "Password123!")
        assert user.email == "newuser@example.com"
        assert user.id is not None
        assert verify_password("Password123!", user.hashed_password)

    @pytest.mark.asyncio
    async def test_register_user_duplicate_email(
        self, session: AsyncSession, test_user: User
    ) -> None:
        """Test that registering with duplicate email raises an error."""
        with pytest.raises(HTTPException) as exc_info:
            await register_user(session, "testuser@example.com", "Password123!")
        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "already registered" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_register_user_creates_unique_passwords_for_same_email_attempt(
        self, session: AsyncSession
    ) -> None:
        """Test that attempted duplicate registrations don't succeed."""
        await register_user(session, "user@example.com", "Password123!")
        with pytest.raises(HTTPException):
            await register_user(session, "user@example.com", "Different123!")


class TestUserAuthentication:
    """Tests for user authentication."""

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, session: AsyncSession, test_user: User) -> None:
        """Test successful user authentication."""
        user = await authenticate_user(session, "testuser@example.com", "TestPassword123!")
        assert user is not None
        assert user.email == "testuser@example.com"
        assert user.id == test_user.id

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(
        self, session: AsyncSession, test_user: User
    ) -> None:
        """Test authentication fails with wrong password."""
        user = await authenticate_user(session, "testuser@example.com", "WrongPassword123!")
        assert user is None

    @pytest.mark.asyncio
    async def test_authenticate_user_nonexistent_email(self, session: AsyncSession) -> None:
        """Test authentication fails for nonexistent email."""
        user = await authenticate_user(session, "nonexistent@example.com", "Password123!")
        assert user is None


class TestUserLogin:
    """Tests for user login."""

    @pytest.mark.asyncio
    async def test_login_user_success(self, session: AsyncSession, test_user: User) -> None:
        """Test successful user login."""
        token = await login_user(session, "testuser@example.com", "TestPassword123!")
        assert isinstance(token, str)
        assert len(token) > 0
        # Verify the token contains the user ID
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        assert payload["sub"] == str(test_user.id)

    @pytest.mark.asyncio
    async def test_login_user_wrong_password(self, session: AsyncSession, test_user: User) -> None:
        """Test login fails with wrong password."""
        with pytest.raises(HTTPException) as exc_info:
            await login_user(session, "testuser@example.com", "WrongPassword123!")
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect email or password" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_login_user_nonexistent_email(self, session: AsyncSession) -> None:
        """Test login fails for nonexistent email."""
        with pytest.raises(HTTPException) as exc_info:
            await login_user(session, "nonexistent@example.com", "Password123!")
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Incorrect email or password" in exc_info.value.detail


# ============================================================================
# Integration Tests for API Endpoints
# ============================================================================


class TestAuthEndpoints:
    """Tests for authentication API endpoints."""

    @pytest.mark.asyncio
    async def test_register_endpoint_success(self) -> None:
        """Test successful registration via API."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/auth/register",
                json={"email": "newuser@example.com", "password": "ValidPass123!"},
            )
            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert data["email"] == "newuser@example.com"
            assert "id" in data
            assert "created_at" in data

    @pytest.mark.asyncio
    async def test_register_endpoint_invalid_email(self) -> None:
        """Test registration with invalid email format."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/auth/register",
                json={"email": "not-an-email", "password": "ValidPass123!"},
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_register_endpoint_short_password(self) -> None:
        """Test registration with password that's too short."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/auth/register",
                json={"email": "user@example.com", "password": "short"},
            )
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_register_endpoint_duplicate_email(self) -> None:
        """Test registration with duplicate email."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # Register first user
            response1 = await client.post(
                "/auth/register",
                json={"email": "user@example.com", "password": "ValidPass123!"},
            )
            assert response1.status_code == status.HTTP_201_CREATED

            # Try to register with same email
            response2 = await client.post(
                "/auth/register",
                json={"email": "user@example.com", "password": "DifferentPass123!"},
            )
            assert response2.status_code == status.HTTP_400_BAD_REQUEST
            assert "already registered" in response2.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_endpoint_success(self) -> None:
        """Test successful login via API."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # Register first
            await client.post(
                "/auth/register",
                json={"email": "user@example.com", "password": "ValidPass123!"},
            )

            # Login
            response = await client.post(
                "/auth/login",
                data={"username": "user@example.com", "password": "ValidPass123!"},
            )
            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_endpoint_wrong_password(self) -> None:
        """Test login with wrong password."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # Register first
            await client.post(
                "/auth/register",
                json={"email": "user@example.com", "password": "ValidPass123!"},
            )

            # Try to login with wrong password
            response = await client.post(
                "/auth/login",
                data={"username": "user@example.com", "password": "WrongPass123!"},
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
            assert "Incorrect email or password" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_endpoint_nonexistent_user(self) -> None:
        """Test login for nonexistent user."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/auth/login",
                data={"username": "nonexistent@example.com", "password": "Password123!"},
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_token_is_valid_for_protected_endpoint(self) -> None:
        """Test that registered user can access protected endpoints with token."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            # Register
            await client.post(
                "/auth/register",
                json={"email": "user@example.com", "password": "ValidPass123!"},
            )

            # Login
            login_response = await client.post(
                "/auth/login",
                data={"username": "user@example.com", "password": "ValidPass123!"},
            )
            token = login_response.json()["access_token"]

            # Use token to create a URL (protected endpoint)
            response = await client.post(
                "/urls",
                headers={"Authorization": f"Bearer {token}"},
                json={"original_url": "https://example.com"},
            )
            assert response.status_code == status.HTTP_201_CREATED

    @pytest.mark.asyncio
    async def test_invalid_token_rejected(self) -> None:
        """Test that invalid token is rejected for protected endpoints."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/urls",
                headers={"Authorization": "Bearer invalid-token"},
                json={"original_url": "https://example.com"},
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_missing_token_rejected(self) -> None:
        """Test that missing token is rejected for protected endpoints."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            response = await client.post(
                "/urls",
                json={"original_url": "https://example.com"},
            )
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
