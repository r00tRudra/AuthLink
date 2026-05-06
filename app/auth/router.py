from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.auth.service import login_user, register_user
from app.database import get_db
from app.schemas import TokenResponse, UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserCreate,
    session: AsyncSession = Depends(get_db),
) -> UserRead:
    user = await register_user(session, payload.email, payload.password)
    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    token = await login_user(session, payload.username, payload.password)
    return TokenResponse(access_token=token)
