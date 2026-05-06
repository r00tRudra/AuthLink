from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models import User
from app.schemas import URLCreate, URLRead
from app.urls.service import create_short_url, delete_url, list_user_urls, redirect_url

router = APIRouter(prefix="/urls", tags=["URLs"])
redirect_router = APIRouter(tags=["Redirect"])


@router.post("", response_model=URLRead, status_code=status.HTTP_201_CREATED)
async def create_url(
    payload: URLCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> URLRead:
    return await create_short_url(session, current_user, str(payload.original_url))


@router.get("/me", response_model=list[URLRead])
async def get_my_urls(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> list[URLRead]:
    return list(await list_user_urls(session, current_user))


@router.delete("/{url_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_url(
    url_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> Response:
    await delete_url(session, url_id, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@redirect_router.get("/{short_code}", include_in_schema=False)
async def redirect_to_original_url(
    short_code: str,
    session: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    url = await redirect_url(session, short_code)
    return RedirectResponse(url=url.original_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)
