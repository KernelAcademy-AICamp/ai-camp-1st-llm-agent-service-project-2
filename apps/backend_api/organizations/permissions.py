"""
Custom permissions for Organization, Membership, and Project
"""

from rest_framework import permissions
from .models import Membership


class IsOrganizationAdmin(permissions.BasePermission):
    """
    Permission to check if user is an admin of the organization

    Used for:
    - Adding/removing members
    - Updating member roles
    - Deleting organization
    """

    def has_object_permission(self, request, view, obj):
        """
        Check if user is admin of the organization
        """
        # obj can be Organization or Project
        if hasattr(obj, 'organization'):
            # obj is Project
            organization = obj.organization
        else:
            # obj is Organization
            organization = obj

        # Check if user has admin membership
        try:
            membership = Membership.objects.get(
                organization=organization,
                user=request.user
            )
            return membership.is_admin
        except Membership.DoesNotExist:
            return False


class IsOrganizationMember(permissions.BasePermission):
    """
    Permission to check if user is a member of the organization

    Used for:
    - Viewing organization details
    - Viewing projects
    - Viewing members
    """

    def has_object_permission(self, request, view, obj):
        """
        Check if user is a member of the organization
        """
        # obj can be Organization or Project
        if hasattr(obj, 'organization'):
            # obj is Project
            organization = obj.organization
        else:
            # obj is Organization
            organization = obj

        # Check if user has membership
        return Membership.objects.filter(
            organization=organization,
            user=request.user
        ).exists()


class IsProjectEditor(permissions.BasePermission):
    """
    Permission to check if user can edit projects

    Used for:
    - Updating project details
    - Deleting project

    Allows ADMIN and EDITOR roles
    """

    def has_object_permission(self, request, view, obj):
        """
        Check if user has EDITOR or ADMIN role
        """
        # obj is Project
        organization = obj.organization if hasattr(obj, 'organization') else obj

        # Check if user has EDITOR or ADMIN membership
        try:
            membership = Membership.objects.get(
                organization=organization,
                user=request.user
            )
            return membership.can_edit
        except Membership.DoesNotExist:
            return False


class IsOrganizationOwnerOrAdmin(permissions.BasePermission):
    """
    Permission to check if user is the owner (created_by) or admin of the organization

    Used for:
    - Updating organization settings
    - Deleting organization (only owner can delete)
    """

    def has_object_permission(self, request, view, obj):
        """
        Check if user is owner or admin
        """
        # obj can be Organization or Project
        if hasattr(obj, 'organization'):
            # obj is Project
            organization = obj.organization
        else:
            # obj is Organization
            organization = obj

        # Check if user is the owner
        if organization.created_by == request.user:
            return True

        # Check if user is admin
        try:
            membership = Membership.objects.get(
                organization=organization,
                user=request.user
            )
            return membership.is_admin
        except Membership.DoesNotExist:
            return False
