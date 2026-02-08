"""
URL configuration for organizations app
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import OrganizationViewSet, ProjectViewSet

# Create router and register viewsets
router = DefaultRouter()
router.register(r'organizations', OrganizationViewSet, basename='organization')
router.register(r'projects', ProjectViewSet, basename='project')

app_name = 'organizations'

urlpatterns = [
    path('', include(router.urls)),
]
