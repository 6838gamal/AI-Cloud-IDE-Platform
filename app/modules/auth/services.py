"""Authentication service: session management, Google OAuth."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.security import generate_session_token, hash_token, verify_token
from app.config import settings
from app.modules.auth.models import Session as SessionModel
from app.modules.auth.schemas import GoogleUserInfo
from app.modules.users.services import UserService


GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_session(self, user_id: str, ip: str | None, ua: str | None) -> str:
        token = generate_session_token()
        session = SessionModel(
            token_hash=hash_token(token),
            user_id=user_id,
            ip_address=ip,
            user_agent=ua,
            expires_at=datetime.now(timezone.utc) + timedelta(seconds=settings.session_max_age),
        )
        self.db.add(session)
        await self.db.commit()
        return token

    async def get_session_user_id(self, token: str) -> str | None:
        result = await self.db.execute(
            select(SessionModel).where(SessionModel.token_hash == hash_token(token))
        )
        session = result.scalar_one_or_none()
        if not session:
            return None
        if session.expires_at < datetime.now(timezone.utc):
            await self.db.delete(session)
            await self.db.commit()
            return None
        return session.user_id

    async def delete_session(self, token: str) -> None:
        result = await self.db.execute(
            select(SessionModel).where(SessionModel.token_hash == hash_token(token))
        )
        session = result.scalar_one_or_none()
        if session:
            await self.db.delete(session)
            await self.db.commit()

    async def exchange_google_code(self, code: str) -> GoogleUserInfo | None:
        if not settings.google_configured:
            return None
        async with httpx.AsyncClient() as client:
            token_resp = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if token_resp.status_code != 200:
                return None
            access_token = token_resp.json().get("access_token")
            if not access_token:
                return None
            user_resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if user_resp.status_code != 200:
                return None
            data = user_resp.json()
            return GoogleUserInfo(
                sub=data.get("sub", ""),
                email=data.get("email", ""),
                name=data.get("name", ""),
                picture=data.get("picture"),
            )

    async def login_with_google(self, code: str) -> str | None:
        user_info = await self.exchange_google_code(code)
        if not user_info or not user_info.email:
            return None
        user_service = UserService(self.db)
        user = await user_service.upsert_google_user(
            google_id=user_info.sub,
            email=user_info.email,
            name=user_info.name,
            profile_picture=user_info.picture,
        )
        return user.id

    @staticmethod
    def get_google_auth_url(state: str) -> str:
        if not settings.google_configured:
            return ""
        from urllib.parse import urlencode
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
