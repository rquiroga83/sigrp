"""
Signals para actualizar automáticamente Task.logged_hours cuando se crean/modifican/eliminan TimeLogs.
"""
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum
from decimal import Decimal


@receiver(post_save, sender='projects.TimeLog')
def update_task_logged_hours_on_save(sender, instance, created, **kwargs):
    """
    Actualiza Task.logged_hours cuando se crea o modifica un TimeLog.
    """
    task = instance.task
    
    # Recalcular total de horas registradas en esta tarea
    total_hours = task.time_logs.aggregate(
        total=Sum('hours')
    )['total'] or Decimal('0.00')
    
    # Actualizar el campo logged_hours
    if task.logged_hours != total_hours:
        # Usamos update() para evitar disparar signals innecesarios
        task.__class__.objects.filter(pk=task.pk).update(
            logged_hours=total_hours
        )


@receiver(post_delete, sender='projects.TimeLog')
def update_task_logged_hours_on_delete(sender, instance, **kwargs):
    """
    Actualiza Task.logged_hours cuando se elimina un TimeLog.
    """
    task = instance.task
    
    # Recalcular total de horas registradas en esta tarea
    total_hours = task.time_logs.aggregate(
        total=Sum('hours')
    )['total'] or Decimal('0.00')
    
    # Actualizar el campo logged_hours
    if task.logged_hours != total_hours:
        task.__class__.objects.filter(pk=task.pk).update(
            logged_hours=total_hours
        )
