from fastapi import APIRouter

from app.api.routes import analytics, auth, chat, conversations, documents, health
from app.core.auth import (
    UserRead,
    UserUpdate,
    auth_backend,
    fastapi_users,
    google_oauth_client,
)
from app.core.config import settings

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])
api_router.include_router(
    conversations.router, prefix="/conversations", tags=["conversations"]
)
api_router.include_router(documents.router, prefix="/documents", tags=["documents"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])


api_router.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

api_router.include_router(
    fastapi_users.get_oauth_router(
        google_oauth_client,
        auth_backend,
        settings.SECRET_KEY,
        redirect_url=f"{settings.FRONTEND_URL}/auth/callback",
    ),
    prefix="/auth/google",
    tags=["auth"],
)

api_router.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

api_router.include_router(auth.router, prefix="/auth")
