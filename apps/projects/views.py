"""
Views for projects app.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from datetime import datetime
from decimal import Decimal
from .models import Project, Task, Allocation
from apps.resources.models import Resource
from .services import calculate_availability, get_allocation_recommendations


def project_list(request):
    """Lista de proyectos."""
    projects = Project.objects.select_related().prefetch_related('stages', 'tasks').all()
    
    # Estadísticas generales
    stats = {
        'total': projects.count(),
        'active': projects.filter(status='active').count(),
        'planning': projects.filter(status='planning').count(),
        'completed': projects.filter(status='completed').count(),
    }
    
    return render(request, 'projects/list.html', {
        'projects': projects,
        'stats': stats
    })


def project_detail(request, pk):
    """Detalle de un proyecto."""
    project = get_object_or_404(Project, pk=pk)
    stages = project.stages.all().prefetch_related('tasks')
    tasks = project.tasks.select_related('required_role', 'assigned_resource', 'stage').all()
    
    return render(request, 'projects/detail.html', {
        'project': project,
        'stages': stages,
        'tasks': tasks
    })


def assign_resources(request, pk):
    """Vista para asignar recursos a las tareas del proyecto."""
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'POST':
        # Procesar las asignaciones
        for key, value in request.POST.items():
            if key.startswith('task_') and value:
                task_id = key.split('_')[1]
                try:
                    task = Task.objects.get(pk=task_id, project=project)
                    if value == 'none':
                        task.assigned_resource = None
                    else:
                        resource = Resource.objects.get(pk=value)
                        task.assigned_resource = resource
                    task.save()
                except (Task.DoesNotExist, Resource.DoesNotExist):
                    continue
        
        messages.success(request, 'Recursos asignados exitosamente')
        return redirect('projects:assign_resources', pk=pk)
    
    # GET: Mostrar formulario
    tasks = project.tasks.select_related(
        'required_role', 
        'assigned_resource', 
        'stage'
    ).order_by('stage__order', '-priority', 'due_date')
    
    # Obtener recursos disponibles agrupados por rol
    resources = Resource.objects.select_related('primary_role').filter(
        is_active=True
    ).order_by('primary_role__name', 'first_name')
    
    # Agrupar tareas por etapa (lista de tuplas para fácil iteración en template)
    stages_with_tasks = []
    stages = project.stages.all().order_by('order')
    for stage in stages:
        stage_tasks = tasks.filter(stage=stage)
        if stage_tasks.exists():
            stages_with_tasks.append((stage, stage_tasks))
    
    # Tareas sin etapa
    orphan_tasks = tasks.filter(stage__isnull=True)
    
    # Calcular estadísticas
    unassigned_tasks_count = tasks.filter(assigned_resource__isnull=True).count()
    
    return render(request, 'projects/assign_resources.html', {
        'project': project,
        'stages_with_tasks': stages_with_tasks,
        'orphan_tasks': orphan_tasks,
        'resources': resources,
        'unassigned_tasks_count': unassigned_tasks_count,
    })


@require_http_methods(["GET"])
def check_resource_availability(request):
    """
    Vista HTMX que retorna un fragmento HTML con la disponibilidad del recurso.
    
    RF-11: Chequeo en tiempo real de disponibilidad con barra de progreso y alertas.
    
    Query Params:
        - resource: ID del recurso
        - start: Fecha de inicio (YYYY-MM-DD)
        - end: Fecha de fin (YYYY-MM-DD)
        - hours: (Opcional) Horas por semana solicitadas
    
    Returns:
        HTML fragment con:
        - Barra de progreso (verde < 80%, amarilla 80-99%, roja > 100%)
        - Alertas de fragmentación si is_fragmented=True
        - Detalles de disponibilidad
    """
    # 1. Obtener parámetros
    resource_id = request.GET.get('resource')
    start_date_str = request.GET.get('start')
    end_date_str = request.GET.get('end')
    requested_hours_str = request.GET.get('hours', '0')
    
    # 2. Validar parámetros obligatorios
    if not all([resource_id, start_date_str, end_date_str]):
        return render(request, 'projects/partials/availability_check.html', {
            'error': 'Parámetros incompletos: se requiere resource, start y end'
        })
    
    try:
        resource_id = int(resource_id)
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        requested_hours = Decimal(requested_hours_str) if requested_hours_str else Decimal('0.00')
    except (ValueError, TypeError) as e:
        return render(request, 'projects/partials/availability_check.html', {
            'error': f'Error en formato de datos: {str(e)}'
        })
    
    # 3. Calcular disponibilidad
    if requested_hours > 0:
        # Si se especifican horas, usar análisis completo con recomendaciones
        result = get_allocation_recommendations(
            resource_id=resource_id,
            requested_hours=requested_hours,
            start_date=start_date,
            end_date=end_date
        )
        availability = result['availability']
        is_viable = result['is_viable']
        block_reason = result['block_reason']
        warnings = result['warnings']
        recommendations = result['recommendations']
        projected_utilization = result['projected_utilization']
    else:
        # Solo disponibilidad actual
        availability = calculate_availability(
            resource_id=resource_id,
            start_date=start_date,
            end_date=end_date
        )
        is_viable = True
        block_reason = None
        warnings = []
        recommendations = []
        projected_utilization = availability['utilization_percentage']
    
    # 4. Determinar color de barra de progreso
    if 'error' in availability:
        bar_color = 'secondary'
        bar_class = 'bg-secondary'
    elif projected_utilization >= 100:
        bar_color = 'danger'
        bar_class = 'bg-danger'
    elif projected_utilization >= 80:
        bar_color = 'warning'
        bar_class = 'bg-warning'
    else:
        bar_color = 'success'
        bar_class = 'bg-success'
    
    # 5. Renderizar fragmento HTML
    return render(request, 'projects/partials/availability_check.html', {
        'availability': availability,
        'is_viable': is_viable,
        'block_reason': block_reason,
        'warnings': warnings,
        'recommendations': recommendations,
        'projected_utilization': projected_utilization,
        'requested_hours': requested_hours,
        'bar_color': bar_color,
        'bar_class': bar_class,
    })

