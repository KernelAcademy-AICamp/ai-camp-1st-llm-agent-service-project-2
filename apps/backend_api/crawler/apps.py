from django.apps import AppConfig


class CrawlerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'crawler'
    verbose_name = '크롤링 시스템'
