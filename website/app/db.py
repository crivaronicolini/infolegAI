from typing import Annotated, AsyncGenerator

from fastapi import Depends
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.models import Base, OAuthAccount, User

engine = create_async_engine(
    settings.DATABASE_URL, connect_args={"check_same_thread": False}
)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def create_db_and_tables():
    async with engine.begin() as conn:
        # Base.metadata is shared with SQLModel.metadata in models.py
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_db)]


async def get_user_db(session: SessionDep):
    yield SQLAlchemyUserDatabase(session, User, OAuthAccount)
