"""
Celery tasks for projects app.
"""
from celery import shared_task
from django.utils import timezone
from decimal import Decimal


@shared_task
def calculate_project_health_scores():
    """
    Calcula y actualiza los health scores de todos los proyectos activos.
    Considera: budget, timeline, team sentiment, blocker count.
    """
    from .models import Project
    
    active_projects = Project.objects.filter(status='active', is_active=True)
    
    for project in active_projects:
        health_score = 100
        
        # Factor 1: Budget (30 puntos)
        budget_consumption = project.get_budget_consumption_percentage()
        if budget_consumption > 100:
            health_score -= 30
        elif budget_consumption > 90:
            health_score -= 20
        elif budget_consumption > 80:
            health_score -= 10
        
        # Factor 2: Timeline (30 puntos)
        completion = project.calculate_completion_percentage()
        days_total = (project.planned_end_date - project.start_date).days
        days_elapsed = (timezone.now().date() - project.start_date).days
        expected_completion = (days_elapsed / days_total * 100) if days_total > 0 else 0
        
        if completion < expected_completion - 20:
            health_score -= 30
        elif completion < expected_completion - 10:
            health_score -= 15
        
        # Factor 3: Over budget/hours (20 puntos)
        if project.is_over_budget() or project.is_over_hours_cap():
            health_score -= 20
        
        # Factor 4: Risk level (20 puntos)
        risk_penalties = {'low': 0, 'medium': 5, 'high': 15, 'critical': 20}
        health_score -= risk_penalties.get(project.risk_level, 0)
        
        # Actualizar
        project.health_score = max(0, min(100, health_score))
        project.save(update_fields=['health_score', 'updated_at'])
    
    return f"Updated {active_projects.count()} projects"


@shared_task
def update_project_metrics():
    """
    Actualiza métricas agregadas de proyectos (actual_hours, actual_cost).
    """
    from .models import Project
    from django.db.models import Sum
    
    projects = Project.objects.filter(is_active=True)
    
    for project in projects:
        time_entries = project.time_entries.all()
        
        # Sumar horas totales
        total_hours = time_entries.aggregate(
            total=Sum('hours')
        )['total'] or Decimal('0.00')
        
        # Sumar costo total
        total_cost = time_entries.aggregate(
            total=Sum('cost')
        )['total'] or Decimal('0.00')
        
        # Actualizar proyecto
        project.actual_hours_logged = total_hours
        project.actual_cost = total_cost
        project.save(update_fields=['actual_hours_logged', 'actual_cost', 'updated_at'])
    
    return f"Updated {projects.count()} projects"
