"""
User Serializers
Django REST Framework Serializers
"""

from rest_framework import serializers
from .models import User

class UserSerializer(serializers.ModelSerializer):
    """사용자 정보 Serializer (읽기)"""

    class Meta:
        model = User
        fields = [
            'id',
            'email',
            'full_name',
            'lawyer_registration_number',
            'specializations',
            'is_active',
            'is_staff',
            'date_joined',
            'last_login'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']

class UserCreateSerializer(serializers.ModelSerializer):
    """사용자 생성 Serializer"""

    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = [
            'email',
            'password',
            'password_confirm',
            'full_name',
            'lawyer_registration_number',
            'specializations'
        ]

    def validate(self, data):
        """비밀번호 확인 검증"""
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError({
                "password_confirm": "비밀번호가 일치하지 않습니다."
            })
        return data

    def create(self, validated_data):
        """사용자 생성"""
        # password_confirm 제거
        validated_data.pop('password_confirm')

        # 사용자 생성 (비밀번호 해시 자동 처리)
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            full_name=validated_data['full_name'],
            lawyer_registration_number=validated_data.get('lawyer_registration_number'),
            specializations=validated_data.get('specializations', [])
        )
        return user

class UserUpdateSerializer(serializers.ModelSerializer):
    """사용자 수정 Serializer"""

    class Meta:
        model = User
        fields = [
            'full_name',
            'lawyer_registration_number',
            'specializations'
        ]

class ChangePasswordSerializer(serializers.Serializer):
    """비밀번호 변경 Serializer"""

    old_password = serializers.CharField(
        required=True,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password = serializers.CharField(
        required=True,
        min_length=8,
        write_only=True,
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(
        required=True,
        min_length=8,
        write_only=True,
        style={'input_type': 'password'}
    )

    def validate(self, data):
        """새 비밀번호 확인 검증"""
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({
                "new_password_confirm": "새 비밀번호가 일치하지 않습니다."
            })
        return data
