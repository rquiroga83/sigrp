"""
Celery configuration for SIGRP project.
"""
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('sigrp')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Tareas periódicas
app.conf.beat_schedule = {
    'analyze-standups-sentiment': {
        'task': 'apps.standups.tasks.analyze_recent_standups',
        'schedule': crontab(hour=18, minute=0),  # Diariamente a las 6 PM
    },
    'calculate-project-health': {
        'task': 'apps.projects.tasks.calculate_project_health_scores',
        'schedule': crontab(hour=8, minute=0),  # Diariamente a las 8 AM
    },
    'predict-resource-availability': {
        'task': 'apps.resources.tasks.predict_resource_availability',
        'schedule': crontab(day_of_week=1, hour=9, minute=0),  # Lunes a las 9 AM
    },
}

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
