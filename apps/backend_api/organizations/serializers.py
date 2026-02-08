"""
Serializers for Organization, Membership, and Project models
"""

from rest_framework import serializers
from .models import Organization, Membership, Project


class MembershipSerializer(serializers.ModelSerializer):
    """Serializer for Membership model"""

    user_email = serializers.EmailField(source='user.email', read_only=True)
    user_full_name = serializers.CharField(source='user.full_name', read_only=True)
    organization_name = serializers.CharField(source='organization.name', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    is_admin = serializers.BooleanField(read_only=True)
    can_edit = serializers.BooleanField(read_only=True)

    class Meta:
        model = Membership
        fields = [
            'id',
            'organization',
            'organization_name',
            'user',
            'user_email',
            'user_full_name',
            'role',
            'role_display',
            'is_admin',
            'can_edit',
            'joined_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'joined_at', 'updated_at']

    def validate(self, data):
        """
        Validate membership data
        """
        # Check if user is already a member (only for create)
        if self.instance is None:  # Creating new membership
            organization = data.get('organization')
            user = data.get('user')
            if organization and user:
                if Membership.objects.filter(organization=organization, user=user).exists():
                    raise serializers.ValidationError(
                        'User is already a member of this organization'
                    )
        return data


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for Organization model"""

    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    member_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Organization
        fields = [
            'id',
            'name',
            'created_by',
            'created_by_email',
            'created_by_name',
            'settings',
            'member_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def validate_name(self, value):
        """Validate organization name"""
        if not value or not value.strip():
            raise serializers.ValidationError('Organization name cannot be empty')

        # Check minimum length
        if len(value.strip()) < 2:
            raise serializers.ValidationError('Organization name must be at least 2 characters')

        return value.strip()


class OrganizationDetailSerializer(serializers.ModelSerializer):
    """Serializer for Organization detail with members"""

    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    member_count = serializers.IntegerField(read_only=True)
    memberships = MembershipSerializer(many=True, read_only=True)

    class Meta:
        model = Organization
        fields = [
            'id',
            'name',
            'created_by',
            'created_by_email',
            'created_by_name',
            'settings',
            'member_count',
            'memberships',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'memberships', 'created_at', 'updated_at']


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for Project model"""

    organization_name = serializers.CharField(source='organization.name', read_only=True)
    created_by_email = serializers.EmailField(source='created_by.email', read_only=True)
    created_by_name = serializers.CharField(source='created_by.full_name', read_only=True)
    document_count = serializers.IntegerField(read_only=True)
    case_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Project
        fields = [
            'id',
            'organization',
            'organization_name',
            'name',
            'description',
            'created_by',
            'created_by_email',
            'created_by_name',
            'document_count',
            'case_count',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'created_by', 'created_at', 'updated_at']

    def validate_name(self, value):
        """Validate project name"""
        if not value or not value.strip():
            raise serializers.ValidationError('Project name cannot be empty')

        # Check minimum length
        if len(value.strip()) < 2:
            raise serializers.ValidationError('Project name must be at least 2 characters')

        return value.strip()

    def validate(self, data):
        """
        Validate project data
        """
        # Check if user is a member of the organization
        request = self.context.get('request')
        organization = data.get('organization')

        if request and organization:
            # Check if user is a member of this organization
            is_member = Membership.objects.filter(
                organization=organization,
                user=request.user
            ).exists()

            if not is_member:
                raise serializers.ValidationError(
                    'You must be a member of the organization to create a project'
                )

        return data


class AddMemberSerializer(serializers.Serializer):
    """Serializer for adding a member to an organization"""

    user_email = serializers.EmailField(required=True)
    role = serializers.ChoiceField(
        choices=Membership.ROLE_CHOICES,
        default=Membership.ROLE_VIEWER
    )

    def validate_user_email(self, value):
        """Validate that user exists"""
        from users.models import User

        try:
            User.objects.get(email=value)
        except User.DoesNotExist:
            raise serializers.ValidationError(f'User with email {value} does not exist')

        return value


class UpdateMemberRoleSerializer(serializers.Serializer):
    """Serializer for updating a member's role"""

    role = serializers.ChoiceField(
        choices=Membership.ROLE_CHOICES,
        required=True
    )
