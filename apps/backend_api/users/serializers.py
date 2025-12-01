"""
User Serializers
Django REST Framework Serializers
"""

from rest_framework import serializers
from .models import User, SearchHistory


class OrganizationInfoSerializer(serializers.Serializer):
    """조직 정보 Serializer (User 응답에 포함)"""
    id = serializers.UUIDField()
    name = serializers.CharField()


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


class UserWithRoleSerializer(serializers.ModelSerializer):
    """사용자 정보 + 조직/역할 Serializer (Agent Hub용)"""

    organization = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    permissions = serializers.SerializerMethodField()

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
            'last_login',
            'organization',
            'role',
            'permissions'
        ]
        read_only_fields = ['id', 'date_joined', 'last_login']

    def get_organization(self, obj):
        """사용자의 첫 번째 조직 정보 반환"""
        membership = obj.memberships.select_related('organization').first()
        if membership and membership.organization:
            return {
                'id': str(membership.organization.id),
                'name': membership.organization.name
            }
        return None

    def get_role(self, obj):
        """사용자의 역할 반환 (첫 번째 조직 기준)"""
        membership = obj.memberships.first()
        if membership:
            return membership.role
        return 'VIEWER'  # 기본 역할

    def get_permissions(self, obj):
        """사용자의 권한 반환"""
        membership = obj.memberships.first()
        if membership:
            return {
                'can_edit': membership.role in ['ADMIN', 'EDITOR'],
                'can_admin': membership.role == 'ADMIN'
            }
        return {
            'can_edit': False,
            'can_admin': False
        }

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


class SearchHistorySerializer(serializers.ModelSerializer):
    """검색 기록 Serializer"""

    class Meta:
        model = SearchHistory
        fields = [
            'id',
            'query',
            'top_k',
            'response_mode',
            'filters',
            'source_count',
            'answer',
            'sources',
            'model',
            'revised',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def create(self, validated_data):
        """검색 기록 생성 - 현재 사용자 자동 할당"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        return super().create(validated_data)


class SearchHistoryCreateSerializer(serializers.ModelSerializer):
    """검색 기록 생성 Serializer"""

    class Meta:
        model = SearchHistory
        fields = [
            'query',
            'top_k',
            'response_mode',
            'filters',
            'source_count',
            'answer',
            'sources',
            'model',
            'revised',
        ]

    def create(self, validated_data):
        """검색 기록 생성 - 현재 사용자 자동 할당, 중복 쿼리 업데이트"""
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            user = request.user
            query = validated_data.get('query', '').strip().lower()

            # 동일한 쿼리가 있으면 삭제 (최신으로 업데이트하기 위해)
            SearchHistory.objects.filter(
                user=user,
                query__iexact=query
            ).delete()

            validated_data['user'] = user

        return super().create(validated_data)
