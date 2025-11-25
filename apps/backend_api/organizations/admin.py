from django.contrib import admin
from .models import Organization, Membership, Project


class MembershipInline(admin.TabularInline):
    """Inline admin for Membership"""
    model = Membership
    extra = 0
    readonly_fields = ('id', 'joined_at')
    fields = ('user', 'role', 'joined_at')
    can_delete = True
    show_change_link = True


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Admin interface for Organization model"""

    list_display = (
        'name',
        'created_by',
        'member_count',
        'created_at',
    )

    list_filter = (
        'created_at',
    )

    search_fields = (
        'name',
        'created_by__email',
        'created_by__full_name',
    )

    readonly_fields = (
        'id',
        'created_at',
        'updated_at',
        'member_count',
    )

    fieldsets = (
        ('Organization Information', {
            'fields': (
                'id',
                'name',
                'created_by',
                'member_count',
            )
        }),
        ('Settings', {
            'fields': (
                'settings',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )

    inlines = [MembershipInline]

    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    def member_count(self, obj):
        """Display member count"""
        return obj.member_count

    member_count.short_description = 'Members'


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """Admin interface for Membership model"""

    list_display = (
        'user',
        'organization',
        'role',
        'joined_at',
    )

    list_filter = (
        'role',
        'joined_at',
    )

    search_fields = (
        'user__email',
        'user__full_name',
        'organization__name',
    )

    readonly_fields = (
        'id',
        'joined_at',
        'updated_at',
        'is_admin',
        'can_edit',
    )

    fieldsets = (
        ('Membership Information', {
            'fields': (
                'id',
                'organization',
                'user',
                'role',
            )
        }),
        ('Permissions', {
            'fields': (
                'is_admin',
                'can_edit',
            )
        }),
        ('Timestamps', {
            'fields': (
                'joined_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )

    date_hierarchy = 'joined_at'
    ordering = ('-joined_at',)

    def is_admin(self, obj):
        """Display if user is admin"""
        return obj.is_admin

    is_admin.boolean = True
    is_admin.short_description = 'Is Admin'

    def can_edit(self, obj):
        """Display if user can edit"""
        return obj.can_edit

    can_edit.boolean = True
    can_edit.short_description = 'Can Edit'


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    """Admin interface for Project model"""

    list_display = (
        'name',
        'organization',
        'created_by',
        'document_count',
        'case_count',
        'created_at',
    )

    list_filter = (
        'organization',
        'created_at',
    )

    search_fields = (
        'name',
        'organization__name',
        'created_by__email',
        'created_by__full_name',
        'description',
    )

    readonly_fields = (
        'id',
        'created_at',
        'updated_at',
        'document_count',
        'case_count',
    )

    fieldsets = (
        ('Project Information', {
            'fields': (
                'id',
                'organization',
                'name',
                'description',
                'created_by',
            )
        }),
        ('Statistics', {
            'fields': (
                'document_count',
                'case_count',
            )
        }),
        ('Timestamps', {
            'fields': (
                'created_at',
                'updated_at',
            ),
            'classes': ('collapse',)
        }),
    )

    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    def document_count(self, obj):
        """Display document count"""
        return obj.document_count

    document_count.short_description = 'Documents'

    def case_count(self, obj):
        """Display case count"""
        return obj.case_count

    case_count.short_description = 'Cases'
