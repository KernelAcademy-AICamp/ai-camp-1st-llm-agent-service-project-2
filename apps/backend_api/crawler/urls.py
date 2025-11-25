"""
Crawler URLs

크롤링 시스템 API URL 설정
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DataSourceViewSet, CrawlJobViewSet, CrawlLogViewSet

router = DefaultRouter()
router.register(r'data-sources', DataSourceViewSet, basename='data-source')
router.register(r'crawl-jobs', CrawlJobViewSet, basename='crawl-job')
router.register(r'crawl-logs', CrawlLogViewSet, basename='crawl-log')

urlpatterns = [
    path('', include(router.urls)),
]
