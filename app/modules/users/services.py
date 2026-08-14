"""User service layer."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User
from app.modules.users.schemas import UserCreate, UserUpdate


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str) -> User | None:
        return await self.db.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_google_id(self, google_id: str) -> User | None:
        result = await self.db.execute(select(User).where(User.google_id == google_id))
        return result.scalar_one_or_none()

    async def create(self, data: UserCreate) -> User:
        user = User(
            email=data.email,
            name=data.name,
            google_id=data.google_id,
            profile_picture=data.profile_picture,
            language=data.language,
            theme=data.theme,
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update(self, user_id: str, data: UserUpdate) -> User | None:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(user, key, value)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def upsert_google_user(
        self, google_id: str, email: str, name: str, profile_picture: str | None
    ) -> User:
        user = await self.get_by_google_id(google_id)
        if user:
            user.name = name
            user.profile_picture = profile_picture
            await self.db.commit()
            await self.db.refresh(user)
            return user
        user = await self.get_by_email(email)
        if user:
            user.google_id = google_id
            user.name = name
            user.profile_picture = profile_picture
            await self.db.commit()
            await self.db.refresh(user)
            return user
        return await self.create(
            UserCreate(
                email=email,
                name=name,
                google_id=google_id,
                profile_picture=profile_picture,
            )
        )
