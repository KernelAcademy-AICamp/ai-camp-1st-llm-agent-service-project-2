"""
API v1 URL Configuration
"""

from django.urls import path
from . import auth

urlpatterns = [
    # Authentication
    path('auth/signup', auth.signup, name='signup'),
    path('auth/login', auth.login, name='login'),
    path('auth/logout', auth.logout, name='logout'),
    path('auth/me', auth.me, name='me'),
    path('auth/profile', auth.update_profile, name='update_profile'),
    path('auth/change-password', auth.change_password, name='change_password'),
]
