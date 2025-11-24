"""
Authentication API
JWT 기반 인증 API
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

from users.models import User
from users.serializers import (
    UserSerializer,
    UserCreateSerializer,
    ChangePasswordSerializer
)

@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    """
    회원가입

    POST /api/v1/auth/signup
    {
        "email": "user@example.com",
        "password": "password123",
        "password_confirm": "password123",
        "full_name": "홍길동",
        "specializations": ["민사법"]
    }
    """
    serializer = UserCreateSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()

    return Response(
        {
            "message": "회원가입이 완료되었습니다.",
            "user": UserSerializer(user).data
        },
        status=status.HTTP_201_CREATED
    )

@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    로그인 (JWT 토큰 발급)

    POST /api/v1/auth/login
    {
        "email": "user@example.com",
        "password": "password123"
    }

    Response:
    {
        "access": "...",
        "refresh": "...",
        "user": {...}
    }
    """
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response(
            {"error": "이메일과 비밀번호를 입력해주세요."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 사용자 인증
    user = authenticate(request, username=email, password=password)

    if user is None:
        return Response(
            {"error": "이메일 또는 비밀번호가 올바르지 않습니다."},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {"error": "비활성화된 계정입니다."},
            status=status.HTTP_403_FORBIDDEN
        )

    # JWT 토큰 생성
    refresh = RefreshToken.for_user(user)

    return Response({
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "user": UserSerializer(user).data
    })

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    로그아웃 (Refresh 토큰 블랙리스트)

    POST /api/v1/auth/logout
    {
        "refresh": "..."
    }
    """
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response(
            {"message": "로그아웃 되었습니다."},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"error": str(e)},
            status=status.HTTP_400_BAD_REQUEST
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me(request):
    """
    현재 사용자 정보

    GET /api/v1/auth/me
    """
    return Response(UserSerializer(request.user).data)

@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    프로필 수정

    PUT/PATCH /api/v1/auth/profile
    """
    from users.serializers import UserUpdateSerializer

    serializer = UserUpdateSerializer(
        request.user,
        data=request.data,
        partial=request.method == 'PATCH'
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()

    return Response(UserSerializer(request.user).data)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def change_password(request):
    """
    비밀번호 변경

    POST /api/v1/auth/change-password
    """
    serializer = ChangePasswordSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    user = request.user

    # 기존 비밀번호 확인
    if not user.check_password(serializer.validated_data['old_password']):
        return Response(
            {"error": "기존 비밀번호가 올바르지 않습니다."},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 새 비밀번호 설정
    user.set_password(serializer.validated_data['new_password'])
    user.save()

    return Response({"message": "비밀번호가 변경되었습니다."})
