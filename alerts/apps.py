from django.apps import AppConfig


class AlertsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'alerts'
    verbose_name = 'Smart Alert System'
    
    def ready(self):
        # Import signals when app is ready
        try:
            from . import signals
        except ImportError:
            pass
