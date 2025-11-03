"""
FastAPI dependencies for authentication
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.backend.database import get_db
from app.backend.models.user import User
from app.backend.core.auth.jwt import decode_token

# OAuth2 scheme for token authentication
# tokenUrl is the endpoint where users can get tokens
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency to get the currently authenticated user.

    Usage:
        @app.get("/profile")
        async def get_profile(current_user: User = Depends(get_current_user)):
            return current_user.to_dict()

    Args:
        token: JWT token from Authorization header
        db: Database session

    Returns:
        User: Authenticated user object

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Decode token
    payload = decode_token(token)
    if payload is None:
        raise credentials_exception

    # Extract user ID from token
    user_id: Optional[str] = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    # Query user from database
    try:
        import uuid
        # Convert string UUID to UUID object
        user_uuid = uuid.UUID(user_id)
        result = await db.execute(select(User).where(User.id == user_uuid))
        user = result.scalar_one_or_none()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )

    if user is None:
        raise credentials_exception

    return user


async def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency to get the currently authenticated active user.

    Usage:
        @app.get("/protected")
        async def protected_route(user: User = Depends(get_current_active_user)):
            return {"message": f"Hello, {user.full_name}!"}

    Args:
        current_user: User from get_current_user dependency

    Returns:
        User: Authenticated active user

    Raises:
        HTTPException: 400 if user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    return current_user


async def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    """
    Dependency to get the current user if authenticated, None otherwise.
    Useful for endpoints that work with or without authentication.

    Usage:
        @app.get("/public")
        async def public_route(user: Optional[User] = Depends(get_optional_current_user)):
            if user:
                return {"message": f"Hello, {user.full_name}!"}
            return {"message": "Hello, guest!"}

    Args:
        token: Optional JWT token
        db: Database session

    Returns:
        Optional[User]: User if authenticated, None otherwise
    """
    if not token:
        return None

    try:
        return await get_current_user(token, db)
    except HTTPException:
        return None
