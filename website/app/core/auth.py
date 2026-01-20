import uuid
from typing import Annotated

import structlog
from fastapi import Depends, Request
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin, schemas
from fastapi_users.authentication import (
    AuthenticationBackend,
    CookieTransport,
    JWTStrategy,
)
from httpx_oauth.clients.google import GoogleOAuth2
from structlog.contextvars import bind_contextvars

from app.core.config import settings
from app.db import get_user_db
from app.models import User

logger = structlog.stdlib.get_logger(__name__)


class UserRead(schemas.BaseUser[uuid.UUID]):
    pass


class UserUpdate(schemas.BaseUserUpdate):
    pass


google_oauth_client = GoogleOAuth2(
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET.get_secret_value(),
)


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    reset_password_token_secret = settings.SECRET_KEY
    verification_token_secret = settings.SECRET_KEY

    async def get(self, id: uuid.UUID) -> User | None:
        user = await super().get(id)
        if user is None:
            logger.debug("user not found by id", user_id=str(id))
        else:
            logger.debug("user found by id", user_id=str(id), is_active=user.is_active)
        return user

    async def on_after_register(self, user: User, request: Request | None = None):
        logger.debug("user registered", user_id=str(user.id), email=user.email)
        bind_contextvars(user_id=str(user.id), auth_event="register")

    async def on_after_login(
        self,
        user: User,
        request: Request | None = None,
        response=None,
    ):
        logger.debug("user logged in", user_id=str(user.id), email=user.email)
        bind_contextvars(user_id=str(user.id), auth_event="login")


async def get_user_manager(user_db=Depends(get_user_db)):
    yield UserManager(user_db)


cookie_transport = CookieTransport(
    cookie_max_age=3600 * 24 * 7,  # 7 days
    cookie_secure=not settings.DEBUG,  # Only require HTTPS in production
)


def get_jwt_strategy() -> JWTStrategy:
    return JWTStrategy(secret=settings.SECRET_KEY, lifetime_seconds=3600 * 24 * 7)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=cookie_transport,
    get_strategy=get_jwt_strategy,
)

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

current_active_user = fastapi_users.current_user(active=True)
current_superuser = fastapi_users.current_user(active=True, superuser=True)

CurrentUser = Annotated[User, Depends(current_active_user)]
CurrentSuperuser = Annotated[User, Depends(current_superuser)]
