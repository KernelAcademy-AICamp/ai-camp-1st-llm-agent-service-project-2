"""
Authentication module for LawLaw
JWT-based authentication with FastAPI
"""

from .jwt import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from .dependencies import get_current_user, get_current_active_user, oauth2_scheme

__all__ = [
    "create_access_token",
    "decode_token",
    "hash_password",
    "verify_password",
    "get_current_user",
    "get_current_active_user",
    "oauth2_scheme",
    "SECRET_KEY",
    "ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
]
