"""
Authentication Router
회원가입, 로그인, 프로필 관리 API
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr, validator
from typing import List, Optional
import logging

from backend.database import get_db
from backend.models.user import User
from backend.core.auth.jwt import create_access_token, hash_password, verify_password
from backend.core.auth.dependencies import get_current_user, get_current_active_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ============================================
# Request/Response Models
# ============================================


class SignupRequest(BaseModel):
    """회원가입 요청"""

    email: EmailStr
    password: str
    full_name: str
    specializations: List[str]
    lawyer_registration_number: Optional[str] = None

    @validator("password")
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v

    @validator("full_name")
    def name_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @validator("specializations")
    def specializations_not_empty(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one specialization must be selected")
        return v


class UserResponse(BaseModel):
    """사용자 정보 응답"""

    id: str
    email: str
    full_name: str
    specializations: List[str]
    lawyer_registration_number: Optional[str] = None
    is_active: bool


class TokenResponse(BaseModel):
    """토큰 응답"""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ProfileUpdateRequest(BaseModel):
    """프로필 수정 요청"""

    full_name: Optional[str] = None
    specializations: Optional[List[str]] = None
    lawyer_registration_number: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    """비밀번호 변경 요청"""

    current_password: str
    new_password: str

    @validator("new_password")
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters")
        return v


class ForgotPasswordRequest(BaseModel):
    """비밀번호 재설정 요청"""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """비밀번호 재설정 확인"""

    token: str
    new_password: str

    @validator("new_password")
    def password_strength(cls, v):
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters")
        return v


# ============================================
# Authentication Endpoints
# ============================================


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignupRequest, db: AsyncSession = Depends(get_db)):
    """
    회원가입

    - 이메일 중복 확인
    - 비밀번호 해싱
    - 전문 분야 저장
    - JWT 토큰 발급
    """
    logger.info(f"Signup attempt for email: {request.email}")

    # 이메일 중복 확인
    result = await db.execute(select(User).where(User.email == request.email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        logger.warning(f"Signup failed: email already registered - {request.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # 사용자 생성
    new_user = User(
        email=request.email,
        hashed_password=hash_password(request.password),
        full_name=request.full_name,
        specializations=request.specializations,
        lawyer_registration_number=request.lawyer_registration_number,
        is_active=True,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    logger.info(f"User created successfully: {new_user.id} ({new_user.email})")

    # JWT 토큰 발급
    access_token = create_access_token(data={"sub": str(new_user.id)})

    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=str(new_user.id),
            email=new_user.email,
            full_name=new_user.full_name,
            specializations=new_user.specializations,
            lawyer_registration_number=new_user.lawyer_registration_number,
            is_active=new_user.is_active,
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):
    """
    로그인

    - 이메일/비밀번호 확인
    - JWT 토큰 발급

    Note: OAuth2PasswordRequestForm uses 'username' field for email
    """
    logger.info(f"Login attempt for email: {form_data.username}")

    # 사용자 조회
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    # 사용자 없음 또는 비밀번호 불일치
    if not user or not verify_password(form_data.password, user.hashed_password):
        logger.warning(f"Login failed: invalid credentials - {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 비활성 계정 체크
    if not user.is_active:
        logger.warning(f"Login failed: inactive user - {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive"
        )

    logger.info(f"Login successful: {user.id} ({user.email})")

    # JWT 토큰 발급
    access_token = create_access_token(data={"sub": str(user.id)})

    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=str(user.id),
            email=user.email,
            full_name=user.full_name,
            specializations=user.specializations,
            lawyer_registration_number=user.lawyer_registration_number,
            is_active=user.is_active,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    현재 로그인한 사용자 정보 조회

    Requires: Authorization Bearer token
    """
    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        specializations=current_user.specializations,
        lawyer_registration_number=current_user.lawyer_registration_number,
        is_active=current_user.is_active,
    )


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    update_data: ProfileUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    프로필 수정

    - 이름, 전문 분야, 변호사 등록번호 수정 가능
    - 이메일, 비밀번호는 별도 엔드포인트 사용
    """
    logger.info(f"Profile update request for user: {current_user.id}")

    # 수정할 필드만 업데이트
    if update_data.full_name is not None:
        current_user.full_name = update_data.full_name.strip()

    if update_data.specializations is not None:
        if len(update_data.specializations) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one specialization must be selected",
            )
        current_user.specializations = update_data.specializations

    if update_data.lawyer_registration_number is not None:
        current_user.lawyer_registration_number = update_data.lawyer_registration_number

    await db.commit()
    await db.refresh(current_user)

    logger.info(f"Profile updated successfully for user: {current_user.id}")

    return UserResponse(
        id=str(current_user.id),
        email=current_user.email,
        full_name=current_user.full_name,
        specializations=current_user.specializations,
        lawyer_registration_number=current_user.lawyer_registration_number,
        is_active=current_user.is_active,
    )


@router.post("/logout")
async def logout(current_user: User = Depends(get_current_active_user)):
    """
    로그아웃

    - JWT는 stateless이므로 클라이언트에서 토큰 삭제 필요
    - 서버는 로그아웃 기록만 남김
    - 향후 토큰 블랙리스트 기능 추가 가능

    Returns:
        성공 메시지
    """
    logger.info(f"User logged out: {current_user.id} ({current_user.email})")

    return {"message": "Successfully logged out", "detail": "Please delete the token on client side"}


@router.put("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    비밀번호 변경

    - 현재 비밀번호 확인 필수
    - 새 비밀번호는 8자 이상

    Returns:
        성공 메시지
    """
    logger.info(f"Password change request for user: {current_user.id}")

    # 현재 비밀번호 확인
    if not verify_password(request.current_password, current_user.hashed_password):
        logger.warning(f"Password change failed: incorrect current password - {current_user.id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # 새 비밀번호와 현재 비밀번호 동일 체크
    if verify_password(request.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    # 비밀번호 변경
    current_user.hashed_password = hash_password(request.new_password)
    await db.commit()

    logger.info(f"Password changed successfully for user: {current_user.id}")

    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """
    비밀번호 재설정 요청

    - 이메일로 사용자 조회
    - 재설정 토큰 생성 (1시간 만료)
    - 실제 프로덕션에서는 이메일 발송 필요

    Returns:
        재설정 토큰 (개발용, 프로덕션에서는 이메일로만 전달)
    """
    logger.info(f"Password reset request for email: {request.email}")

    # 사용자 조회
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    # 보안상 사용자 존재 여부를 명시하지 않음
    if not user:
        logger.warning(f"Password reset request for non-existent email: {request.email}")
        # 동일한 응답 반환 (타이밍 공격 방지)
        return {
            "message": "If the email exists, a password reset link has been sent",
            "detail": "Check your email for instructions",
        }

    # 재설정 토큰 생성 (1시간 만료)
    from datetime import timedelta

    reset_token = create_access_token(
        data={"sub": str(user.id), "type": "password_reset"}, expires_delta=timedelta(hours=1)
    )

    logger.info(f"Password reset token generated for user: {user.id}")

    # TODO: 실제 프로덕션에서는 이메일로 토큰 발송
    # send_email(user.email, f"Reset link: /reset-password?token={reset_token}")

    return {
        "message": "If the email exists, a password reset link has been sent",
        "detail": "Check your email for instructions",
        # 개발용으로만 토큰 반환 (프로덕션에서는 제거 필요)
        "reset_token": reset_token,
    }


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """
    비밀번호 재설정 확인

    - 재설정 토큰 검증
    - 새 비밀번호 설정

    Returns:
        성공 메시지
    """
    logger.info("Password reset confirmation attempt")

    # 토큰 검증
    from backend.core.auth.jwt import decode_token

    payload = decode_token(request.token)
    if payload is None or payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token"
        )

    # 사용자 조회
    import uuid

    user_uuid = uuid.UUID(user_id)
    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid reset token"
        )

    # 비밀번호 변경
    user.hashed_password = hash_password(request.new_password)
    await db.commit()

    logger.info(f"Password reset successfully for user: {user.id}")

    return {"message": "Password has been reset successfully"}


@router.delete("/account")
async def deactivate_account(
    current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db)
):
    """
    계정 비활성화

    - 실제 삭제 대신 is_active를 False로 설정
    - 복구 가능하도록 데이터는 유지
    - 관리자가 수동으로 재활성화 가능

    Returns:
        성공 메시지
    """
    logger.info(f"Account deactivation request for user: {current_user.id}")

    # 계정 비활성화
    current_user.is_active = False
    await db.commit()

    logger.info(f"Account deactivated for user: {current_user.id} ({current_user.email})")

    return {
        "message": "Account has been deactivated",
        "detail": "Contact support to reactivate your account",
    }


def setup_auth_routes() -> APIRouter:
    """Setup and return auth router"""
    return router
