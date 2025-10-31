"""
Security Module
인증, 암호화, 보안 관련 유틸리티
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from cryptography.fernet import Fernet
import hashlib
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# 비밀번호 해싱
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 파일 암호화 (Fernet)
cipher = Fernet(settings.ENCRYPTION_KEY.encode() if isinstance(settings.ENCRYPTION_KEY, str) else settings.ENCRYPTION_KEY)


# ============================================================================
# Password Hashing
# ============================================================================

def hash_password(password: str) -> str:
    """
    비밀번호 해싱

    Args:
        password: 평문 비밀번호

    Returns:
        str: 해싱된 비밀번호
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    비밀번호 검증

    Args:
        plain_password: 평문 비밀번호
        hashed_password: 해싱된 비밀번호

    Returns:
        bool: 일치 여부
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================================
# JWT Token
# ============================================================================

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    JWT 액세스 토큰 생성

    Args:
        data: 토큰에 포함할 데이터
        expires_delta: 만료 시간 (기본값: 설정에서 가져옴)

    Returns:
        str: JWT 토큰
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS)

    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow()
    })

    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """
    JWT 토큰 디코딩

    Args:
        token: JWT 토큰

    Returns:
        Optional[Dict]: 디코딩된 페이로드 또는 None
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


# ============================================================================
# File Encryption (AES-256 via Fernet)
# ============================================================================

def encrypt_file(file_content: bytes) -> bytes:
    """
    파일 내용 암호화 (AES-256-GCM)

    Args:
        file_content: 원본 파일 내용

    Returns:
        bytes: 암호화된 파일 내용
    """
    try:
        return cipher.encrypt(file_content)
    except Exception as e:
        logger.error(f"File encryption error: {e}")
        raise


def decrypt_file(encrypted_content: bytes) -> bytes:
    """
    파일 내용 복호화

    Args:
        encrypted_content: 암호화된 파일 내용

    Returns:
        bytes: 복호화된 파일 내용
    """
    try:
        return cipher.decrypt(encrypted_content)
    except Exception as e:
        logger.error(f"File decryption error: {e}")
        raise


def encrypt_text(text: str) -> str:
    """
    텍스트 필드 암호화

    Args:
        text: 평문 텍스트

    Returns:
        str: 암호화된 텍스트 (base64 인코딩)
    """
    try:
        encrypted = cipher.encrypt(text.encode('utf-8'))
        return encrypted.decode('utf-8')
    except Exception as e:
        logger.error(f"Text encryption error: {e}")
        raise


def decrypt_text(encrypted_text: str) -> str:
    """
    텍스트 필드 복호화

    Args:
        encrypted_text: 암호화된 텍스트

    Returns:
        str: 복호화된 텍스트
    """
    try:
        decrypted = cipher.decrypt(encrypted_text.encode('utf-8'))
        return decrypted.decode('utf-8')
    except Exception as e:
        logger.error(f"Text decryption error: {e}")
        raise


# ============================================================================
# File Hashing
# ============================================================================

def hash_file(file_content: bytes) -> str:
    """
    파일 해시값 생성 (SHA-256)
    중복 파일 체크에 사용

    Args:
        file_content: 파일 내용

    Returns:
        str: SHA-256 해시값 (hex)
    """
    return hashlib.sha256(file_content).hexdigest()


def generate_encryption_key() -> str:
    """
    Fernet 암호화 키 생성 (유틸리티)

    Returns:
        str: Base64 인코딩된 Fernet 키
    """
    return Fernet.generate_key().decode()
