from __future__ import annotations

import secrets
import string
from collections.abc import Sequence
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import URL, User

SHORT_CODE_ALPHABET = string.ascii_letters + string.digits
SHORT_CODE_LENGTH = 7
MAX_SHORT_CODE_ATTEMPTS = 5


def generate_short_code(length: int = SHORT_CODE_LENGTH) -> str:
    return "".join(secrets.choice(SHORT_CODE_ALPHABET) for _ in range(length))


async def create_short_url(session: AsyncSession, owner: User, original_url: str) -> URL:
    for attempt in range(MAX_SHORT_CODE_ATTEMPTS):
        url = URL(
            short_code=generate_short_code(),
            original_url=original_url,
            owner_id=owner.id,
        )
        session.add(url)
        try:
            await session.commit()
            await session.refresh(url)
            return url
        except IntegrityError:
            await session.rollback()
            if attempt == MAX_SHORT_CODE_ATTEMPTS - 1:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not generate a unique short code",
                )

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Could not generate a unique short code",
    )


async def list_user_urls(session: AsyncSession, owner: User) -> Sequence[URL]:
    result = await session.execute(
        select(URL)
        .where(URL.owner_id == owner.id)
        .order_by(URL.created_at.desc())
    )
    return result.scalars().all()


async def get_url_by_short_code(session: AsyncSession, short_code: str) -> URL:
    result = await session.execute(select(URL).where(URL.short_code == short_code))
    url = result.scalar_one_or_none()
    if url is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short code not found")
    return url


async def redirect_url(session: AsyncSession, short_code: str) -> URL:
    url = await get_url_by_short_code(session, short_code)
    url.click_count += 1
    await session.commit()
    await session.refresh(url)
    return url


async def delete_url(session: AsyncSession, url_id: UUID, current_user: User) -> None:
    url = await session.get(URL, url_id)
    if url is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")
    if url.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to delete this URL")

    await session.delete(url)
    await session.commit()
