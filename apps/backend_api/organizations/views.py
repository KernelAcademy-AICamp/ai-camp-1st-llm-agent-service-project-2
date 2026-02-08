"""
ViewSets for Organization, Membership, and Project CRUD operations
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.db import transaction
import logging

from .models import Organization, Membership, Project
from .serializers import (
    OrganizationSerializer,
    OrganizationDetailSerializer,
    MembershipSerializer,
    ProjectSerializer,
    AddMemberSerializer,
    UpdateMemberRoleSerializer,
)
from .permissions import (
    IsOrganizationAdmin,
    IsOrganizationMember,
    IsProjectEditor,
    IsOrganizationOwnerOrAdmin,
)
from users.models import User

logger = logging.getLogger(__name__)


class OrganizationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Organization CRUD operations

    Endpoints:
    - GET /api/v1/organizations/ - List user's organizations
    - POST /api/v1/organizations/ - Create a new organization
    - GET /api/v1/organizations/{id}/ - Retrieve organization detail
    - PUT /api/v1/organizations/{id}/ - Update organization
    - DELETE /api/v1/organizations/{id}/ - Delete organization (owner only)
    - GET /api/v1/organizations/{id}/members/ - List organization members
    - POST /api/v1/organizations/{id}/add_member/ - Add a member
    - DELETE /api/v1/organizations/{id}/remove_member/{user_id}/ - Remove a member
    - PUT /api/v1/organizations/{id}/update_member_role/{user_id}/ - Update member role
    """

    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Return organizations where user is a member
        """
        user = self.request.user
        return Organization.objects.filter(
            memberships__user=user
        ).distinct().select_related('created_by')

    def get_serializer_class(self):
        """
        Return appropriate serializer based on action
        """
        if self.action == 'retrieve':
            return OrganizationDetailSerializer
        return OrganizationSerializer

    def get_permissions(self):
        """
        Return appropriate permissions based on action
        """
        if self.action in ['update', 'partial_update']:
            return [IsAuthenticated(), IsOrganizationOwnerOrAdmin()]
        elif self.action == 'destroy':
            return [IsAuthenticated(), IsOrganizationOwnerOrAdmin()]
        elif self.action in ['add_member', 'remove_member', 'update_member_role']:
            return [IsAuthenticated(), IsOrganizationAdmin()]
        elif self.action in ['retrieve', 'members']:
            return [IsAuthenticated(), IsOrganizationMember()]
        return super().get_permissions()

    def list(self, request):
        """
        GET /api/v1/organizations/
        List all organizations where user is a member
        """
        queryset = self.get_queryset()

        # Search by name
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(name__icontains=search)

        # Order by created_at (newest first)
        queryset = queryset.order_by('-created_at')

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })

    @transaction.atomic
    def create(self, request):
        """
        POST /api/v1/organizations/
        Create a new organization and add creator as admin member
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Create organization with current user as creator
        organization = serializer.save(created_by=request.user)

        # Automatically add creator as ADMIN member
        Membership.objects.create(
            organization=organization,
            user=request.user,
            role=Membership.ROLE_ADMIN
        )

        logger.info(
            f"Organization created: {organization.id} by {request.user.email}"
        )

        return Response(
            self.get_serializer(organization).data,
            status=status.HTTP_201_CREATED
        )

    def retrieve(self, request, pk=None):
        """
        GET /api/v1/organizations/{id}/
        Retrieve a single organization with members
        """
        try:
            organization = self.get_queryset().get(pk=pk)
        except Organization.DoesNotExist:
            return Response(
                {'error': 'Organization not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        self.check_object_permissions(request, organization)

        serializer = self.get_serializer(organization)
        return Response(serializer.data)

    def update(self, request, pk=None):
        """
        PUT /api/v1/organizations/{id}/
        Update organization (admin only)
        """
        try:
            organization = self.get_queryset().get(pk=pk)
        except Organization.DoesNotExist:
            return Response(
                {'error': 'Organization not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        self.check_object_permissions(request, organization)

        serializer = self.get_serializer(
            organization,
            data=request.data,
            partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        logger.info(
            f"Organization updated: {organization.id} by {request.user.email}"
        )

        return Response(serializer.data)

    def destroy(self, request, pk=None):
        """
        DELETE /api/v1/organizations/{id}/
        Delete organization (owner/admin only)
        """
        try:
            organization = self.get_queryset().get(pk=pk)
        except Organization.DoesNotExist:
            return Response(
                {'error': 'Organization not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        self.check_object_permissions(request, organization)

        organization_name = organization.name
        organization.delete()

        logger.info(
            f"Organization deleted: {organization_name} by {request.user.email}"
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """
        GET /api/v1/organizations/{id}/members/
        List all members of an organization
        """
        try:
            organization = self.get_queryset().get(pk=pk)
        except Organization.DoesNotExist:
            return Response(
                {'error': 'Organization not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        self.check_object_permissions(request, organization)

        memberships = organization.memberships.select_related('user').order_by('-joined_at')
        serializer = MembershipSerializer(memberships, many=True)

        return Response({
            'count': memberships.count(),
            'results': serializer.data
        })

    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """
        POST /api/v1/organizations/{id}/add_member/
        Add a member to the organization (admin only)

        Body:
        {
            "user_email": "user@example.com",
            "role": "VIEWER"  // ADMIN, EDITOR, or VIEWER
        }
        """
        try:
            organization = self.get_queryset().get(pk=pk)
        except Organization.DoesNotExist:
            return Response(
                {'error': 'Organization not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        self.check_object_permissions(request, organization)

        serializer = AddMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_email = serializer.validated_data['user_email']
        role = serializer.validated_data['role']

        # Get user
        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            return Response(
                {'error': f'User with email {user_email} does not exist'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check if already a member
        if Membership.objects.filter(organization=organization, user=user).exists():
            return Response(
                {'error': 'User is already a member of this organization'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create membership
        membership = Membership.objects.create(
            organization=organization,
            user=user,
            role=role
        )

        logger.info(
            f"Member added to organization: {user.email} -> {organization.name} as {role}"
        )

        return Response(
            MembershipSerializer(membership).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['delete'], url_path='remove_member/(?P<user_id>[^/.]+)')
    def remove_member(self, request, pk=None, user_id=None):
        """
        DELETE /api/v1/organizations/{id}/remove_member/{user_id}/
        Remove a member from the organization (admin only)
        """
        try:
            organization = self.get_queryset().get(pk=pk)
        except Organization.DoesNotExist:
            return Response(
                {'error': 'Organization not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        self.check_object_permissions(request, organization)

        # Get membership
        try:
            membership = Membership.objects.get(
                organization=organization,
                user_id=user_id
            )
        except Membership.DoesNotExist:
            return Response(
                {'error': 'Membership not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Prevent removing the owner
        if organization.created_by_id == user_id:
            return Response(
                {'error': 'Cannot remove the organization owner'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Prevent removing yourself if you're the last admin
        if membership.user == request.user:
            admin_count = Membership.objects.filter(
                organization=organization,
                role=Membership.ROLE_ADMIN
            ).count()
            if admin_count <= 1:
                return Response(
                    {'error': 'Cannot remove yourself as the last admin'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        user_email = membership.user.email
        membership.delete()

        logger.info(
            f"Member removed from organization: {user_email} from {organization.name}"
        )

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['put'], url_path='update_member_role/(?P<user_id>[^/.]+)')
    def update_member_role(self, request, pk=None, user_id=None):
        """
        PUT /api/v1/organizations/{id}/update_member_role/{user_id}/
        Update a member's role (admin only)

        Body:
        {
            "role": "EDITOR"  // ADMIN, EDITOR, or VIEWER
        }
        """
        try:
            organization = self.get_queryset().get(pk=pk)
        except Organization.DoesNotExist:
            return Response(
                {'error': 'Organization not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        self.check_object_permissions(request, organization)

        serializer = UpdateMemberRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_role = serializer.validated_data['role']

        # Get membership
        try:
            membership = Membership.objects.get(
                organization=organization,
                user_id=user_id
            )
        except Membership.DoesNotExist:
            return Response(
                {'error': 'Membership not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Prevent demoting yourself if you're the last admin
        if membership.user == request.user and new_role != Membership.ROLE_ADMIN:
            admin_count = Membership.objects.filter(
                organization=organization,
                role=Membership.ROLE_ADMIN
            ).count()
            if admin_count <= 1:
                return Response(
                    {'error': 'Cannot demote yourself as the last admin'},
                    status=status.HTTP_400_BAD_REQUEST
                )

        old_role = membership.role
        membership.role = new_role
        membership.save()

        logger.info(
            f"Member role updated: {membership.user.email} in {organization.name} from {old_role} to {new_role}"
        )

        return Response(MembershipSerializer(membership).data)


class ProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Project CRUD operations

    Endpoints:
    - GET /api/v1/projects/ - List user's projects
    - POST /api/v1/projects/ - Create a new project
    - GET /api/v1/projects/{id}/ - Retrieve project detail
    - PUT /api/v1/projects/{id}/ - Update project (editor/admin only)
    - DELETE /api/v1/projects/{id}/ - Delete project (editor/admin only)
    """

    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Return projects from organizations where user is a member
        """
        user = self.request.user

        # Get all organizations where user is a member
        user_organizations = Organization.objects.filter(
            memberships__user=user
        )

        return Project.objects.filter(
            organization__in=user_organizations
        ).select_related('organization', 'created_by')

    def get_permissions(self):
        """
        Return appropriate permissions based on action
        """
        if self.action in ['update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), IsProjectEditor()]
        elif self.action == 'retrieve':
            return [IsAuthenticated(), IsOrganizationMember()]
        return super().get_permissions()

    def list(self, request):
        """
        GET /api/v1/projects/
        List all projects from user's organizations
        """
        queryset = self.get_queryset()

        # Filter by organization if provided
        organization_id = request.query_params.get('organization', None)
        if organization_id:
            queryset = queryset.filter(organization_id=organization_id)

        # Search by name
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        # Order by created_at (newest first)
        queryset = queryset.order_by('-created_at')

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'count': queryset.count(),
            'results': serializer.data
        })

    def create(self, request):
        """
        POST /api/v1/projects/
        Create a new project
        """
        serializer = self.get_serializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        # Create project with current user as creator
        project = serializer.save(created_by=request.user)

        logger.info(
            f"Project created: {project.id} ({project.name}) in {project.organization.name} by {request.user.email}"
        )

        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED
        )

    def retrieve(self, request, pk=None):
        """
        GET /api/v1/projects/{id}/
        Retrieve a single project
        """
        try:
            project = self.get_queryset().get(pk=pk)
        except Project.DoesNotExist:
            return Response(
                {'error': 'Project not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        self.check_object_permissions(request, project)

        serializer = self.get_serializer(project)
        return Response(serializer.data)

    def update(self, request, pk=None):
        """
        PUT /api/v1/projects/{id}/
        Update project (editor/admin only)
        """
        try:
            project = self.get_queryset().get(pk=pk)
        except Project.DoesNotExist:
            return Response(
                {'error': 'Project not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        self.check_object_permissions(request, project)

        serializer = self.get_serializer(
            project,
            data=request.data,
            partial=True,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        logger.info(
            f"Project updated: {project.id} ({project.name}) by {request.user.email}"
        )

        return Response(serializer.data)

    def destroy(self, request, pk=None):
        """
        DELETE /api/v1/projects/{id}/
        Delete project (editor/admin only)
        """
        try:
            project = self.get_queryset().get(pk=pk)
        except Project.DoesNotExist:
            return Response(
                {'error': 'Project not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check permission
        self.check_object_permissions(request, project)

        project_name = project.name
        project.delete()

        logger.info(
            f"Project deleted: {project_name} by {request.user.email}"
        )

        return Response(status=status.HTTP_204_NO_CONTENT)
