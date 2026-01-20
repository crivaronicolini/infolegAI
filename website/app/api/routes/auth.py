from fastapi import APIRouter, Depends, Response
from fastapi_users import schemas

from app.core.auth import (
    User,
    get_jwt_strategy,
    get_user_manager,
)
from app.core.config import settings
from app.db import SessionDep

router = APIRouter()

if settings.DEBUG:

    class UserCreate(schemas.BaseUserCreate):
        pass

    @router.post("/debug-login", tags=["auth"])
    async def debug_login(
        response: Response,
        session: SessionDep,
        user_manager=Depends(get_user_manager),
    ):
        """Debug-only endpoint to bypass OAuth login. Creates admin superuser."""
        from sqlalchemy import select

        email = "admin@example.com"
        result = await session.execute(select(User).where(User.email == email))
        user = result.unique().scalar_one_or_none()

        if not user:
            user_create = UserCreate(
                email=email, password="adminpassword", is_superuser=True
            )
            user = await user_manager.create(user_create)

        strategy = get_jwt_strategy()
        token = await strategy.write_token(user)
        response.set_cookie(
            key="fastapiusersauth",
            value=token,
            max_age=3600 * 24 * 7,
            httponly=True,
            samesite="lax",
            secure=not settings.DEBUG,
            path="/",
        )
        return {"message": "Admin login successful", "email": user.email}

    @router.get("/debug-status", tags=["auth"])
    async def debug_status():
        """Check if debug mode is enabled."""
        return {"debug": True}
