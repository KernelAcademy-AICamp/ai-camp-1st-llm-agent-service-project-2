"""
User Admin
Django Admin 설정
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """사용자 Admin"""

    list_display = ['email', 'full_name', 'is_active', 'is_staff', 'date_joined']
    list_filter = ['is_active', 'is_staff', 'date_joined']
    search_fields = ['email', 'full_name', 'lawyer_registration_number']
    ordering = ['-date_joined']

    fieldsets = (
        (None, {
            'fields': ('email', 'password')
        }),
        ('개인정보', {
            'fields': ('full_name', 'lawyer_registration_number', 'specializations')
        }),
        ('권한', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('중요한 날짜', {
            'fields': ('last_login', 'date_joined')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'full_name', 'password1', 'password2'),
        }),
    )
