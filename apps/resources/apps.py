from django.apps import AppConfig


class ResourcesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.resources'
    verbose_name = 'Recursos Humanos'
    
    def ready(self):
        """Importar signals cuando la app esté lista."""
        import apps.resources.signals  # noqa
