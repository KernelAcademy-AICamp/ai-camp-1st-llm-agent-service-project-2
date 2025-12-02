"""
Organization Models
조직, 멤버십, 프로젝트 모델
"""

import uuid
from django.db import models
from django.conf import settings


class Organization(models.Model):
    """
    Organization model for multi-tenancy support

    Allows users to create organizations and collaborate with team members
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    name = models.CharField(
        max_length=255,
        verbose_name='조직명',
        help_text='Organization name'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='owned_organizations',
        verbose_name='생성자',
        help_text='Organization creator (cannot be deleted if organization exists)'
    )

    settings = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='설정',
        help_text='Organization-specific settings (permissions, features, etc.)'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='생성일시'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일시'
    )

    class Meta:
        db_table = 'organizations'
        verbose_name = '조직'
        verbose_name_plural = '조직'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_by', '-created_at']),
        ]

    def __str__(self):
        return f"{self.name}"

    @property
    def member_count(self):
        """Get number of members in this organization"""
        return self.memberships.count()


class Membership(models.Model):
    """
    Membership model for organization members

    Defines user roles within an organization
    """

    # Role choices
    ROLE_ADMIN = 'ADMIN'
    ROLE_EDITOR = 'EDITOR'
    ROLE_VIEWER = 'VIEWER'

    ROLE_CHOICES = [
        (ROLE_ADMIN, 'Administrator'),
        (ROLE_EDITOR, 'Editor'),
        (ROLE_VIEWER, 'Viewer'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name='조직'
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name='사용자'
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_ADMIN,  # 모든 사용자가 ADMIN 권한 (임시 설정)
        verbose_name='역할',
        help_text='User role in organization'
    )

    joined_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='가입일시'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일시'
    )

    class Meta:
        db_table = 'memberships'
        verbose_name = '멤버십'
        verbose_name_plural = '멤버십'
        ordering = ['-joined_at']
        unique_together = [['organization', 'user']]
        indexes = [
            models.Index(fields=['organization', '-joined_at']),
            models.Index(fields=['user', '-joined_at']),
            models.Index(fields=['role']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.organization.name} ({self.get_role_display()})"

    @property
    def is_admin(self):
        """Check if user is admin of this organization"""
        return self.role == self.ROLE_ADMIN

    @property
    def can_edit(self):
        """Check if user can edit resources"""
        return self.role in [self.ROLE_ADMIN, self.ROLE_EDITOR]


class Project(models.Model):
    """
    Project model for organizing documents and cases within an organization

    Projects provide a way to group related work items
    """

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='projects',
        verbose_name='조직'
    )

    name = models.CharField(
        max_length=255,
        verbose_name='프로젝트명',
        help_text='Project name'
    )

    description = models.TextField(
        blank=True,
        verbose_name='설명',
        help_text='Project description'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_projects',
        verbose_name='생성자'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        verbose_name='생성일시'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='수정일시'
    )

    class Meta:
        db_table = 'projects'
        verbose_name = '프로젝트'
        verbose_name_plural = '프로젝트'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['organization', '-created_at']),
            models.Index(fields=['created_by', '-created_at']),
        ]

    def __str__(self):
        return f"{self.name} ({self.organization.name})"

    @property
    def document_count(self):
        """Get number of documents in this project"""
        return self.documents.count()

    @property
    def case_count(self):
        """Get number of cases in this project"""
        return self.cases.count()
