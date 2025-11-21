"""
User Model
Django ORM 기반 사용자 모델 (FastAPI User 모델 대체)
"""

from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
import uuid

class UserManager(BaseUserManager):
    """
    커스텀 User Manager
    email을 username으로 사용
    """

    def create_user(self, email, password=None, **extra_fields):
        """일반 사용자 생성"""
        if not email:
            raise ValueError('이메일은 필수입니다')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """슈퍼유저 생성"""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('슈퍼유저는 is_staff=True여야 합니다')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('슈퍼유저는 is_superuser=True여야 합니다')

        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    """
    커스텀 사용자 모델

    기존 apps.backend.models.user.User (SQLAlchemy)를
    Django ORM으로 마이그레이션

    주요 변경사항:
    - SQLAlchemy → Django ORM
    - UUID primary key 유지
    - email 기반 인증 (username 비활성화)
    """

    # Primary Key (UUID)
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    # Email (unique, 로그인에 사용)
    email = models.EmailField(
        unique=True,
        db_index=True,
        verbose_name='이메일'
    )

    # Profile
    full_name = models.CharField(
        max_length=255,
        verbose_name='이름'
    )

    lawyer_registration_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='변호사 등록번호'
    )

    specializations = models.JSONField(
        default=list,
        blank=True,
        verbose_name='전문 분야'
    )

    # AbstractUser 필드 재정의
    username = None  # email 사용하므로 username 비활성화
    first_name = None  # full_name 사용
    last_name = None  # full_name 사용

    # 커스텀 Manager 사용
    objects = UserManager()

    # 로그인에 사용할 필드
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']  # createsuperuser 시 요구되는 필드

    class Meta:
        db_table = 'users'
        verbose_name = '사용자'
        verbose_name_plural = '사용자'
        ordering = ['-date_joined']

    def __str__(self):
        return f"{self.full_name} ({self.email})"
