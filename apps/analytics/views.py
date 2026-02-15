"""
Views for analytics app - Dashboards and Reports
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, Avg, F
from django.db.models.functions import TruncMonth
from decimal import Decimal
from datetime import datetime, timedelta
from apps.projects.models import Project, Task, TimeLog, TimeEntry, Allocation
from apps.resources.models import Resource, Role
from apps.standups.models import StandupLog


@login_required
def dashboard(request):
    """
    Dashboard ejecutivo con métricas consolidadas
    """
    # === PROYECTOS ===
    projects = Project.objects.all()
    
    projects_stats = {
        'total': projects.count(),
        'active': projects.filter(status='active').count(),
        'planning': projects.filter(status='planning').count(),
        'completed': projects.filter(status='completed').count(),
        'on_hold': projects.filter(status='on_hold').count(),
    }
    
    # === MÉTRICAS FINANCIERAS AGREGADAS ===
    total_cost = Decimal('0.00')
    total_billable = Decimal('0.00')
    total_hours = Decimal('0.00')
    
    for project in projects:
        total_cost += project.total_cost
        total_billable += project.total_billable
        total_hours += project.total_logged_hours
    
    total_profit = total_billable - total_cost
    profit_margin = float((total_profit / total_billable * 100)) if total_billable > 0 else 0
    
    financial_stats = {
        'total_cost': total_cost,
        'total_billable': total_billable,
        'total_profit': total_profit,
        'profit_margin': profit_margin,
        'total_hours': total_hours,
    }
    
    # === RECURSOS ===
    resources = Resource.objects.filter(is_active=True)
    
    resources_stats = {
        'total': resources.count(),
        'available': resources.filter(status='available').count(),
        'partially_allocated': resources.filter(status='partially_allocated').count(),
        'fully_allocated': resources.filter(status='fully_allocated').count(),
        'on_leave': resources.filter(status='on_leave').count(),
    }
    
    # === PROYECTOS ACTIVOS CON MÉTRICAS ===
    active_projects = []
    for project in projects.filter(status='active'):
        active_projects.append({
            'project': project,
            'cost': project.total_cost,
            'billable': project.total_billable,
            'profit': project.total_billable - project.total_cost,
            'margin': project.profit_margin,
            'completion': project.completion_percentage,
            'is_over_budget': project.is_over_budget,
        })
    
    # Ordenar por margen (menor a mayor para identificar problemas)
    active_projects.sort(key=lambda x: x['margin'])
    
    # === PROYECTOS EN RIESGO ===
    projects_at_risk = [p for p in active_projects if p['margin'] < 15 or p['is_over_budget']]
    
    # === TAREAS PENDIENTES ===
    tasks_stats = {
        'total': Task.objects.count(),
        'backlog': Task.objects.filter(status='backlog').count(),
        'in_progress': Task.objects.filter(status='in_progress').count(),
        'in_review': Task.objects.filter(status='in_review').count(),
        'blocked': Task.objects.filter(status='blocked').count(),
        'completed': Task.objects.filter(status='completed').count(),
    }
    
    # === STANDUPS RECIENTES (últimos 7 días) ===
    seven_days_ago = datetime.now().date() - timedelta(days=7)
    recent_standups = StandupLog.objects.filter(
        date__gte=seven_days_ago
    ).select_related('resource', 'project')
    
    # Calcular TeamMood promedio
    avg_sentiment = recent_standups.aggregate(
        avg=Avg('sentiment_score')
    )['avg'] or 0
    
    standups_stats = {
        'total_recent': recent_standups.count(),
        'avg_sentiment': avg_sentiment,
        'positive': recent_standups.filter(sentiment_label='positive').count(),
        'neutral': recent_standups.filter(sentiment_label='neutral').count(),
        'negative': recent_standups.filter(sentiment_label='negative').count(),
        'very_negative': recent_standups.filter(sentiment_label='very_negative').count(),
    }
    
    # === ALLOCATIONS ACTIVAS ===
    today = datetime.now().date()
    active_allocations = Allocation.objects.filter(
        is_active=True,
        start_date__lte=today,
        end_date__gte=today
    ).select_related('resource', 'project')
    
    allocations_stats = {
        'total_active': active_allocations.count(),
        'total_hours_per_week': active_allocations.aggregate(
            total=Sum('hours_per_week')
        )['total'] or 0,
    }
    
    context = {
        'projects_stats': projects_stats,
        'financial_stats': financial_stats,
        'resources_stats': resources_stats,
        'active_projects': active_projects[:10],  # Top 10
        'projects_at_risk': projects_at_risk,
        'tasks_stats': tasks_stats,
        'standups_stats': standups_stats,
        'allocations_stats': allocations_stats,
    }
    
    return render(request, 'analytics/dashboard.html', context)


@login_required
def resources_utilization(request):
    """
    Análisis de utilización de recursos
    """
    resources = Resource.objects.filter(is_active=True).select_related('primary_role')
    
    resources_data = []
    for resource in resources:
        # Calcular horas registradas (último mes)
        thirty_days_ago = datetime.now().date() - timedelta(days=30)
        
        hours_logged = TimeLog.objects.filter(
            resource=resource,
            date__gte=thirty_days_ago
        ).aggregate(total=Sum('hours'))['total'] or Decimal('0.00')

        # Calcular capacidad teórica ajustada por disponibilidad (40h/sem × 4 semanas × availability%)
        capacity = Decimal('160.00') * (Decimal(resource.availability_percentage) / Decimal('100.0'))
        utilization = float((hours_logged / capacity * 100)) if capacity > 0 else 0

        # Calcular costos y facturación usando effective_rate
        cost = hours_logged * resource.internal_cost
        billable = hours_logged * resource.effective_rate
        profit = billable - cost
        margin = float((profit / billable * 100)) if billable > 0 else 0
        
        # Proyectos activos (desde Allocations)
        today = datetime.now().date()
        active_allocations = Allocation.objects.filter(
            resource=resource,
            is_active=True,
            start_date__lte=today,
            end_date__gte=today
        ).select_related('project')
        
        # Proyectos desde tareas asignadas (sin importar Allocation)
        from apps.projects.models import Task, Project
        assigned_tasks = Task.objects.filter(
            assigned_resource=resource,
            status__in=['todo', 'in_progress', 'in_review', 'blocked']
        ).select_related('project').values_list('project', flat=True).distinct()
        
        # Combinar proyectos de ambas fuentes
        allocation_projects = set(a.project.pk for a in active_allocations)
        task_projects = set(assigned_tasks)
        all_projects = allocation_projects | task_projects
        
        resources_data.append({
            'resource': resource,
            'hours_logged': hours_logged,
            'utilization': utilization,
            'cost': cost,
            'billable': billable,
            'profit': profit,
            'margin': margin,
            'active_projects': len(all_projects),
            'status': resource.status,
        })
    
    # Ordenar por utilización (menor a mayor)
    resources_data.sort(key=lambda x: x['utilization'])
    
    # Estadísticas agregadas
    avg_utilization = sum(r['utilization'] for r in resources_data) / len(resources_data) if resources_data else 0
    total_cost = sum(r['cost'] for r in resources_data)
    total_billable = sum(r['billable'] for r in resources_data)
    total_profit = sum(r['profit'] for r in resources_data)
    
    context = {
        'resources_data': resources_data,
        'avg_utilization': avg_utilization,
        'total_cost': total_cost,
        'total_billable': total_billable,
        'total_profit': total_profit,
        'underutilized': [r for r in resources_data if r['utilization'] < 60],
        'optimal': [r for r in resources_data if 60 <= r['utilization'] <= 90],
        'overutilized': [r for r in resources_data if r['utilization'] > 90],
    }
    
    return render(request, 'analytics/resources_utilization.html', context)


@login_required
def resource_booking(request):
    """
    Vista de Reserva de Recursos - Muestra las asignaciones (Allocations)
    de recursos en un rango de fechas para identificar disponibilidad
    """
    from datetime import date
    
    # Obtener parámetros de filtro
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    resource_id = request.GET.get('resource')
    show_inactive = request.GET.get('show_inactive', '') == 'on'
    
    # Fechas por defecto: mes actual
    today = date.today()
    if start_date_str:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    else:
        start_date = today.replace(day=1)  # Primer día del mes
    
    if end_date_str:
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    else:
        # Último día del mes siguiente
        if today.month == 12:
            end_date = today.replace(year=today.year + 1, month=2, day=1) - timedelta(days=1)
        elif today.month == 11:
            end_date = today.replace(year=today.year + 1, month=1, day=1) - timedelta(days=1)
        else:
            next_month = today.month + 2
            end_date = today.replace(month=next_month, day=1) - timedelta(days=1)
    
    # Obtener recursos activos
    resources = Resource.objects.filter(is_active=True).select_related('primary_role').order_by('first_name', 'last_name')
    
    if resource_id:
        resources = resources.filter(id=resource_id)
    
    # Construir datos por recurso
    resources_data = []
    fully_assigned = 0
    partially_assigned = 0
    available = 0
    
    for resource in resources:
        # Filtrar allocations que se solapan con el rango de fechas
        allocations_qs = Allocation.objects.filter(
            resource=resource,
            start_date__lte=end_date,
            end_date__gte=start_date
        ).select_related('project').order_by('start_date')
        
        if not show_inactive:
            allocations_qs = allocations_qs.filter(is_active=True)
        
        allocations_list = list(allocations_qs)

        # Calcular la carga máxima simultánea (no la suma total)
        # Necesitamos encontrar el máximo de horas en cualquier punto del tiempo
        max_hours_per_week = Decimal('0.00')

        if allocations_list:
            # Crear lista de eventos (inicio y fin de cada asignación)
            events = []
            for alloc in allocations_list:
                events.append(('start', alloc.start_date, alloc.hours_per_week))
                # El fin es al día siguiente para que no cuente en ese día
                events.append(('end', alloc.end_date + timedelta(days=1), alloc.hours_per_week))

            # Ordenar eventos por fecha
            events.sort(key=lambda x: (x[1], x[0] == 'end'))

            # Sweep line algorithm para encontrar el máximo
            current_hours = Decimal('0.00')
            for event_type, date, hours in events:
                if event_type == 'start':
                    current_hours += hours
                    max_hours_per_week = max(max_hours_per_week, current_hours)
                else:
                    current_hours -= hours

        total_hours_per_week = max_hours_per_week

        # Capacidad ajustada por disponibilidad del recurso
        capacity = Decimal('40.00') * (Decimal(resource.availability_percentage) / Decimal('100.0'))
        
        # Porcentaje de ocupación
        occupancy_percentage = float((total_hours_per_week / capacity * 100)) if capacity > 0 else 0
        
        # Clasificar recurso
        if occupancy_percentage >= 100:
            status = 'overbooked'  # Sobreasignado
            fully_assigned += 1
        elif occupancy_percentage >= 80:
            status = 'optimal'  # Óptimo
            fully_assigned += 1
        elif occupancy_percentage >= 50:
            status = 'partial'  # Parcial
            partially_assigned += 1
        else:
            status = 'available'  # Disponible
            available += 1
        
        # Preparar datos de allocations con información extendida
        allocations_data = []
        for alloc in allocations_list:
            # Calcular días restantes
            days_remaining = (alloc.end_date - today).days if alloc.end_date >= today else 0
            
            allocations_data.append({
                'allocation': alloc,
                'days_remaining': days_remaining,
                'percentage': float((alloc.hours_per_week / capacity * 100)),
            })
        
        resources_data.append({
            'resource': resource,
            'allocations': allocations_data,
            'total_hours_per_week': total_hours_per_week,
            'capacity': capacity,
            'occupancy_percentage': occupancy_percentage,
            'status': status,
        })
    
    # Ordenar por ocupación (de mayor a menor)
    resources_data.sort(key=lambda x: x['occupancy_percentage'], reverse=True)
    
    context = {
        'resources_data': resources_data,
        'all_resources': Resource.objects.filter(is_active=True).order_by('first_name'),
        'start_date': start_date,
        'end_date': end_date,
        'selected_resource_id': int(resource_id) if resource_id else None,
        'show_inactive': show_inactive,
        'total_resources': len(resources_data),
        'fully_assigned': fully_assigned,
        'partially_assigned': partially_assigned,
        'available': available,
    }
    
    return render(request, 'analytics/resource_booking.html', context)


@login_required
def financial_report(request):
    """
    Reporte financiero consolidado
    """
    projects = Project.objects.all()
    
    # Métricas por tipo de proyecto
    fixed_price_projects = projects.filter(project_type='fixed')
    tm_projects = projects.filter(project_type='t_and_m')
    
    fixed_stats = {
        'count': fixed_price_projects.count(),
        'total_budget': sum(p.budget_limit or 0 for p in fixed_price_projects),
        'total_cost': sum(p.total_cost for p in fixed_price_projects),
        'total_billable': sum(p.total_billable for p in fixed_price_projects),
    }
    fixed_stats['profit'] = fixed_stats['total_billable'] - fixed_stats['total_cost']
    fixed_stats['margin'] = float((fixed_stats['profit'] / fixed_stats['total_billable'] * 100)) if fixed_stats['total_billable'] > 0 else 0
    
    tm_stats = {
        'count': tm_projects.count(),
        'total_cost': sum(p.total_cost for p in tm_projects),
        'total_billable': sum(p.total_billable for p in tm_projects),
    }
    tm_stats['profit'] = tm_stats['total_billable'] - tm_stats['total_cost']
    tm_stats['margin'] = float((tm_stats['profit'] / tm_stats['total_billable'] * 100)) if tm_stats['total_billable'] > 0 else 0
    
    # Proyectos con mejor/peor margen
    projects_with_margin = []
    for project in projects.filter(status__in=['active', 'completed']):
        projects_with_margin.append({
            'project': project,
            'cost': project.total_cost,
            'billable': project.total_billable,
            'profit': project.total_billable - project.total_cost,
            'margin': project.profit_margin,
        })
    
    projects_with_margin.sort(key=lambda x: x['margin'], reverse=True)
    
    best_margin = projects_with_margin[:5] if len(projects_with_margin) >= 5 else projects_with_margin
    worst_margin = projects_with_margin[-5:] if len(projects_with_margin) >= 5 else []
    
    # Análisis por rol
    roles = Role.objects.all()
    roles_profitability = []
    
    for role in roles:
        tasks = Task.objects.filter(required_role=role)
        timelogs = TimeLog.objects.filter(task__in=tasks)
        
        total_hours = timelogs.aggregate(total=Sum('hours'))['total'] or Decimal('0.00')
        total_cost = timelogs.aggregate(total=Sum('cost'))['total'] or Decimal('0.00')
        total_billable = timelogs.aggregate(total=Sum('billable_amount'))['total'] or Decimal('0.00')
        
        if total_hours > 0:
            roles_profitability.append({
                'role': role,
                'hours': total_hours,
                'cost': total_cost,
                'billable': total_billable,
                'profit': total_billable - total_cost,
                'margin': float((total_billable - total_cost) / total_billable * 100) if total_billable > 0 else 0,
            })
    
    roles_profitability.sort(key=lambda x: x['margin'], reverse=True)
    
    context = {
        'fixed_stats': fixed_stats,
        'tm_stats': tm_stats,
        'best_margin': best_margin,
        'worst_margin': worst_margin,
        'roles_profitability': roles_profitability,
    }
    
    return render(request, 'analytics/financial_report.html', context)


@login_required
def team_mood(request):
    """
    Análisis de sentimiento del equipo
    """
    # Últimos 30 días de standups
    thirty_days_ago = datetime.now().date() - timedelta(days=30)
    standups = StandupLog.objects.filter(
        date__gte=thirty_days_ago
    ).select_related('resource', 'project')
    
    # Mood por proyecto
    projects = Project.objects.filter(status='active')
    projects_mood = []
    
    for project in projects:
        project_standups = standups.filter(project=project)
        
        if project_standups.exists():
            avg_sentiment = project_standups.aggregate(
                avg=Avg('sentiment_score')
            )['avg'] or 0
            
            mood_counts = {
                'positive': project_standups.filter(sentiment_label='positive').count(),
                'neutral': project_standups.filter(sentiment_label='neutral').count(),
                'negative': project_standups.filter(sentiment_label='negative').count(),
                'very_negative': project_standups.filter(sentiment_label='very_negative').count(),
            }
            
            projects_mood.append({
                'project': project,
                'avg_sentiment': avg_sentiment,
                'total_standups': project_standups.count(),
                'mood_counts': mood_counts,
            })
    
    projects_mood.sort(key=lambda x: x['avg_sentiment'])
    
    # Mood por recurso
    resources = Resource.objects.filter(is_active=True)
    resources_mood = []
    
    for resource in resources:
        resource_standups = standups.filter(resource=resource)
        
        if resource_standups.exists():
            avg_sentiment = resource_standups.aggregate(
                avg=Avg('sentiment_score')
            )['avg'] or 0
            
            resources_mood.append({
                'resource': resource,
                'avg_sentiment': avg_sentiment,
                'total_standups': resource_standups.count(),
            })
    
    resources_mood.sort(key=lambda x: x['avg_sentiment'])
    
    # Tendencia temporal
    mood_by_day = standups.values('date').annotate(
        avg_sentiment=Avg('sentiment_score'),
        count=Count('id')
    ).order_by('date')
    
    context = {
        'projects_mood': projects_mood,
        'resources_mood': resources_mood,
        'mood_by_day': mood_by_day,
        'overall_avg': standups.aggregate(avg=Avg('sentiment_score'))['avg'] or 0,
    }
    
    return render(request, 'analytics/team_mood.html', context)
