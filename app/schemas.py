from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, HttpUrl


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class URLCreate(BaseModel):
    original_url: HttpUrl


class URLRead(BaseModel):
    id: UUID
    short_code: str
    original_url: HttpUrl
    click_count: int
    owner_id: UUID
    created_at: datetime

    model_config = {"from_attributes": True}
