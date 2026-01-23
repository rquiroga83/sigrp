from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.projects'
    verbose_name = 'Proyectos'
    
    def ready(self):
        """Importar signals cuando la app esté lista."""
        import apps.projects.signals
