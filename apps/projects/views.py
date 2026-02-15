"""
Views for projects app.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
from .models import Project, Task, Allocation, Stage, TimeLog
from apps.resources.models import Resource, Role
from .services import calculate_availability, get_allocation_recommendations
from .forms import ProjectForm


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


@login_required
def project_create(request):
    """
    Vista para crear un nuevo proyecto.
    Utiliza formulario con validación dinámica según tipo de proyecto.
    """
    if request.method == 'POST':
        form = ProjectForm(request.POST)

        if form.is_valid():
            try:
                project = form.save(commit=False)

                # Asignar usuario creador si está autenticado
                if request.user.is_authenticated:
                    project.created_by = request.user
                    project.updated_by = request.user

                project.save()

                messages.success(
                    request,
                    f'✅ Proyecto "{project.name}" ({project.code}) creado exitosamente'
                )

                # Redirigir a la página de edición para agregar etapas y tareas
                return redirect('projects:edit', pk=project.pk)

            except ValidationError as e:
                for error in e.messages:
                    messages.error(request, error)
            except Exception as e:
                messages.error(request, f'Error al crear proyecto: {str(e)}')
        else:
            # Mostrar errores del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        # GET: Mostrar formulario vacío
        form = ProjectForm()

    context = {
        'form': form,
        'is_create': True,
    }

    return render(request, 'projects/create.html', context)


@login_required
def project_edit(request, pk):
    """
    Vista para editar el proyecto y gestionar sus etapas y tareas.
    Permite crear/editar/eliminar etapas y tareas en una sola vista.
    """
    project = get_object_or_404(Project, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        # ============== ACTUALIZAR PROYECTO ==============
        if action == 'update_project':
            try:
                project.name = request.POST.get('name', project.name)
                project.description = request.POST.get('description', '')
                project.client_name = request.POST.get('client_name', project.client_name)
                project.project_type = request.POST.get('project_type', project.project_type)
                project.status = request.POST.get('status', project.status)
                project.priority = request.POST.get('priority', project.priority)
                
                # Fechas
                start_date = request.POST.get('start_date')
                if start_date:
                    project.start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
                
                end_date = request.POST.get('end_date')
                if end_date:
                    project.end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                # Presupuestos según tipo
                if project.project_type == 'fixed':
                    fixed_price = request.POST.get('fixed_price')
                    if fixed_price:
                        project.fixed_price = Decimal(fixed_price)
                    budget_limit = request.POST.get('budget_limit')
                    if budget_limit:
                        project.budget_limit = Decimal(budget_limit)
                else:
                    hourly_rate = request.POST.get('hourly_rate')
                    if hourly_rate:
                        project.hourly_rate = Decimal(hourly_rate)
                    max_budget = request.POST.get('max_budget')
                    if max_budget:
                        project.max_budget = Decimal(max_budget)
                
                project.save()
                messages.success(request, f'✅ Proyecto "{project.name}" actualizado exitosamente')
                
            except Exception as e:
                messages.error(request, f'Error al actualizar proyecto: {str(e)}')
        
        # ============== CREAR ETAPA ==============
        elif action == 'create_stage':
            try:
                stage_name = request.POST.get('stage_name')
                stage_description = request.POST.get('stage_description', '')
                stage_order = request.POST.get('stage_order', 0)
                
                if not stage_name:
                    messages.error(request, 'El nombre de la etapa es requerido')
                else:
                    stage = Stage.objects.create(
                        project=project,
                        name=stage_name,
                        description=stage_description,
                        order=int(stage_order),
                        status='planned'
                    )
                    messages.success(request, f'✅ Etapa "{stage.name}" creada exitosamente')
                    
            except Exception as e:
                messages.error(request, f'Error al crear etapa: {str(e)}')
        
        # ============== ACTUALIZAR ETAPA ==============
        elif action == 'update_stage':
            try:
                stage_id = request.POST.get('stage_id')
                stage = Stage.objects.get(pk=stage_id, project=project)
                
                stage.name = request.POST.get('stage_name', stage.name)
                stage.description = request.POST.get('stage_description', '')
                stage.order = int(request.POST.get('stage_order', stage.order))
                stage.status = request.POST.get('stage_status', stage.status)
                
                stage.save()
                messages.success(request, f'✅ Etapa "{stage.name}" actualizada')
                
            except Stage.DoesNotExist:
                messages.error(request, 'Etapa no encontrada')
            except Exception as e:
                messages.error(request, f'Error al actualizar etapa: {str(e)}')
        
        # ============== ELIMINAR ETAPA ==============
        elif action == 'delete_stage':
            try:
                stage_id = request.POST.get('stage_id')
                stage = Stage.objects.get(pk=stage_id, project=project)
                stage_name = stage.name
                
                # Verificar si tiene tareas
                if stage.tasks.exists():
                    messages.warning(
                        request, 
                        f'⚠️ No se puede eliminar la etapa "{stage_name}" porque tiene tareas asignadas'
                    )
                else:
                    stage.delete()
                    messages.success(request, f'✅ Etapa "{stage_name}" eliminada')
                    
            except Stage.DoesNotExist:
                messages.error(request, 'Etapa no encontrada')
            except Exception as e:
                messages.error(request, f'Error al eliminar etapa: {str(e)}')
        
        # ============== CREAR TAREA ==============
        elif action == 'create_task':
            try:
                task_title = request.POST.get('task_title')
                task_description = request.POST.get('task_description', '')
                stage_id = request.POST.get('task_stage')
                role_id = request.POST.get('task_role')
                estimated_hours = request.POST.get('task_estimated_hours')
                priority = request.POST.get('task_priority', 'medium')
                due_date_str = request.POST.get('task_due_date')
                
                if not all([task_title, role_id, estimated_hours]):
                    messages.error(request, 'Título, rol y horas estimadas son requeridos')
                else:
                    role = Role.objects.get(pk=role_id)
                    stage = Stage.objects.get(pk=stage_id) if stage_id else None
                    
                    task = Task.objects.create(
                        project=project,
                        stage=stage,
                        title=task_title,
                        description=task_description,
                        required_role=role,
                        estimated_hours=Decimal(estimated_hours),
                        priority=priority,
                        status='backlog'
                    )
                    
                    if due_date_str:
                        task.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                        task.save()
                    
                    messages.success(request, f'✅ Tarea "{task.title}" creada exitosamente')
                    
            except Role.DoesNotExist:
                messages.error(request, 'Rol no encontrado')
            except Stage.DoesNotExist:
                messages.error(request, 'Etapa no encontrada')
            except Exception as e:
                messages.error(request, f'Error al crear tarea: {str(e)}')
        
        # ============== ACTUALIZAR TAREA ==============
        elif action == 'update_task':
            try:
                task_id = request.POST.get('task_id')
                task = Task.objects.get(pk=task_id, project=project)
                
                task.title = request.POST.get('task_title', task.title)
                task.description = request.POST.get('task_description', '')
                task.priority = request.POST.get('task_priority', task.priority)
                task.status = request.POST.get('task_status', task.status)
                
                stage_id = request.POST.get('task_stage')
                if stage_id:
                    task.stage = Stage.objects.get(pk=stage_id, project=project)
                
                role_id = request.POST.get('task_role')
                if role_id:
                    task.required_role = Role.objects.get(pk=role_id)
                
                estimated_hours = request.POST.get('task_estimated_hours')
                if estimated_hours:
                    task.estimated_hours = Decimal(estimated_hours)
                
                due_date_str = request.POST.get('task_due_date')
                if due_date_str:
                    task.due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
                
                task.save()
                messages.success(request, f'✅ Tarea "{task.title}" actualizada')
                
            except Task.DoesNotExist:
                messages.error(request, 'Tarea no encontrada')
            except Exception as e:
                messages.error(request, f'Error al actualizar tarea: {str(e)}')
        
        # ============== ELIMINAR TAREA ==============
        elif action == 'delete_task':
            try:
                task_id = request.POST.get('task_id')
                task = Task.objects.get(pk=task_id, project=project)
                task_title = task.title
                
                # Verificar si tiene horas registradas
                if task.logged_hours > 0:
                    messages.warning(
                        request,
                        f'⚠️ No se puede eliminar la tarea "{task_title}" porque tiene {task.logged_hours}h registradas'
                    )
                else:
                    task.delete()
                    messages.success(request, f'✅ Tarea "{task_title}" eliminada')
                    
            except Task.DoesNotExist:
                messages.error(request, 'Tarea no encontrada')
            except Exception as e:
                messages.error(request, f'Error al eliminar tarea: {str(e)}')
        
        return redirect('projects:edit', pk=pk)
    
    # GET: Mostrar formulario
    stages = project.stages.prefetch_related('tasks').order_by('order')
    tasks_without_stage = project.tasks.filter(stage__isnull=True)
    roles = Role.objects.all().order_by('category', 'seniority')
    
    context = {
        'project': project,
        'stages': stages,
        'tasks_without_stage': tasks_without_stage,
        'roles': roles,
        'project_types': Project.PROJECT_TYPE_CHOICES,
        'status_choices': Project.STATUS_CHOICES,
        'priority_choices': Project.PRIORITY_CHOICES,
        'stage_status_choices': Stage.STATUS_CHOICES,
        'task_status_choices': Task.STATUS_CHOICES,
        'task_priority_choices': Task.PRIORITY_CHOICES,
    }
    
    return render(request, 'projects/edit.html', context)


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
                        task.save()
                    else:
                        resource = Resource.objects.get(pk=value)
                        
                        # VALIDACIÓN 1: Verificar que el recurso esté asignado al proyecto
                        active_allocations = Allocation.objects.filter(
                            project=project,
                            resource=resource,
                            is_active=True
                        )
                        
                        if not active_allocations.exists():
                            messages.error(
                                request,
                                f"❌ No se puede asignar {resource.full_name} a la tarea '{task.title}': "
                                f"El recurso no tiene una asignación activa en este proyecto. "
                                f"Primero debe asignarlo al proyecto desde 'Gestionar Asignaciones'."
                            )
                            continue
                        
                        # VALIDACIÓN 2: Verificar que la fecha de vencimiento esté dentro del periodo de asignación
                        if task.due_date:
                            valid_allocation = active_allocations.filter(
                                start_date__lte=task.due_date,
                                end_date__gte=task.due_date
                            ).first()
                            
                            if not valid_allocation:
                                # Buscar la allocation más cercana para dar feedback útil
                                closest_allocation = active_allocations.order_by('start_date').first()
                                messages.error(
                                    request,
                                    f"❌ No se puede asignar {resource.full_name} a la tarea '{task.title}': "
                                    f"La fecha de vencimiento ({task.due_date.strftime('%d/%m/%Y')}) está fuera "
                                    f"del periodo de asignación del recurso "
                                    f"({closest_allocation.start_date.strftime('%d/%m/%Y')} - "
                                    f"{closest_allocation.end_date.strftime('%d/%m/%Y')})."
                                )
                                continue
                        
                        # Si pasa todas las validaciones, asignar el recurso
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


# ============================================================================
# RF-11: Gestión de Allocations (Resource Leveling)
# ============================================================================

@login_required
def manage_allocations(request, pk):
    """
    Vista para gestionar las asignaciones de recursos al proyecto.
    Permite ver allocations existentes y crear nuevas con fechas y horas.
    """
    project = get_object_or_404(Project, pk=pk)
    
    # Obtener allocations actuales del proyecto
    allocations = project.allocations.select_related('resource', 'resource__primary_role').order_by('-start_date')
    
    # Recursos disponibles
    resources = Resource.objects.select_related('primary_role').filter(
        is_active=True
    ).order_by('primary_role__name', 'first_name')
    
    # Estadísticas
    total_allocated_hours = sum(a.total_hours_allocated for a in allocations)
    active_allocations = allocations.filter(
        start_date__lte=date.today(),
        end_date__gte=date.today()
    ).count()
    
    context = {
        'project': project,
        'allocations': allocations,
        'resources': resources,
        'total_allocated_hours': total_allocated_hours,
        'active_allocations': active_allocations,
        'today': date.today(),
    }
    
    return render(request, 'projects/manage_allocations.html', context)


@login_required
@require_http_methods(["POST"])
def create_allocation(request, pk):
    """
    Crea una nueva allocation de recurso al proyecto.
    Valida disponibilidad y previene sobrecarga.
    """
    project = get_object_or_404(Project, pk=pk)
    
    try:
        # Obtener datos del formulario
        resource_id = request.POST.get('resource')
        start_date_str = request.POST.get('start_date')
        end_date_str = request.POST.get('end_date')
        hours_per_week = request.POST.get('hours_per_week')
        notes = request.POST.get('notes', '')
        
        # Validar campos requeridos
        if not all([resource_id, start_date_str, end_date_str, hours_per_week]):
            messages.error(request, 'Todos los campos son requeridos')
            return redirect('projects:manage_allocations', pk=pk)
        
        # Obtener recurso
        resource = Resource.objects.get(pk=resource_id, is_active=True)
        
        # Convertir fechas
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        hours_per_week = Decimal(hours_per_week)
        
        # Validar lógica de fechas
        if end_date < start_date:
            messages.error(request, 'La fecha de fin debe ser posterior a la fecha de inicio')
            return redirect('projects:manage_allocations', pk=pk)
        
        if start_date < date.today():
            messages.warning(request, 'La fecha de inicio es en el pasado')
        
        # Obtener recomendaciones antes de crear
        recommendations_data = get_allocation_recommendations(
            resource_id=resource.pk,
            requested_hours=hours_per_week,
            start_date=start_date,
            end_date=end_date
        )
        
        # Verificar si es viable (hard block)
        if not recommendations_data['is_viable']:
            messages.error(
                request, 
                f"No se puede crear la asignación: {recommendations_data['block_reason']}"
            )
            return redirect('projects:manage_allocations', pk=pk)
        
        # Crear allocation
        allocation = Allocation(
            project=project,
            resource=resource,
            start_date=start_date,
            end_date=end_date,
            hours_per_week=hours_per_week,
            notes=notes,
            is_active=True
        )
        
        # Validar con clean() que ejecutará las validaciones del modelo
        allocation.clean()
        allocation.save()
        
        # Mostrar advertencias (soft warnings)
        if recommendations_data['warnings']:
            for warning in recommendations_data['warnings']:
                messages.warning(request, warning)
        
        messages.success(
            request, 
            f"Asignación creada: {resource.full_name} → {hours_per_week}h/semana "
            f"({start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')})"
        )
        
    except Resource.DoesNotExist:
        messages.error(request, 'Recurso no encontrado')
    except ValidationError as e:
        # Errores del modelo (clean())
        for error in e.messages:
            messages.error(request, error)
    except ValueError as e:
        messages.error(request, f'Error en los datos: {str(e)}')
    except Exception as e:
        messages.error(request, f'Error al crear asignación: {str(e)}')
    
    return redirect('projects:manage_allocations', pk=pk)


@login_required
@require_http_methods(["POST"])
def delete_allocation(request, allocation_id):
    """
    Elimina una allocation existente.
    """
    allocation = get_object_or_404(Allocation, pk=allocation_id)
    project_pk = allocation.project.pk
    
    try:
        resource_name = allocation.resource.full_name
        allocation.delete()
        messages.success(request, f'Asignación de {resource_name} eliminada')
    except Exception as e:
        messages.error(request, f'Error al eliminar: {str(e)}')
    
    return redirect('projects:manage_allocations', pk=project_pk)


# ============================================================================
# TIMELOGS - Registro de Horas
# ============================================================================

@login_required
def my_timelogs(request):
    """
    Vista principal de TimeLogs del usuario actual.
    Muestra todas las horas registradas por el recurso.
    """
    # TODO: Obtener el resource del usuario actual
    # Por ahora mostramos todos los timelogs
    timelogs = TimeLog.objects.select_related(
        'resource', 'task', 'task__project'
    ).order_by('-date', '-created_at')
    
    # Filtrar por recurso si existe
    resource_id = request.GET.get('resource_id')
    if resource_id:
        timelogs = timelogs.filter(resource_id=resource_id)
    
    # Filtrar por proyecto
    project_id = request.GET.get('project_id')
    if project_id:
        timelogs = timelogs.filter(task__project_id=project_id)
    
    # Filtrar por rango de fechas
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        timelogs = timelogs.filter(date__gte=date_from)
    if date_to:
        timelogs = timelogs.filter(date__lte=date_to)
    
    # Calcular totales
    total_hours = sum(log.hours for log in timelogs)
    total_cost = sum(log.cost for log in timelogs)
    total_billable = sum(log.billable_amount for log in timelogs)
    
    # Listas para filtros
    resources = Resource.objects.filter(is_active=True).order_by('first_name', 'last_name')
    projects = Project.objects.filter(status__in=['planning', 'active']).order_by('name')
    
    context = {
        'timelogs': timelogs,
        'total_hours': total_hours,
        'total_cost': total_cost,
        'total_billable': total_billable,
        'resources': resources,
        'projects': projects,
        'filters': {
            'resource_id': resource_id,
            'project_id': project_id,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'projects/timelogs/list.html', context)


@login_required
def create_timelog(request):
    """
    Crea un nuevo TimeLog.
    """
    if request.method == 'POST':
        try:
            # Obtener datos del formulario
            resource_id = request.POST.get('resource_id')
            task_id = request.POST.get('task_id')
            date_str = request.POST.get('date')
            hours = request.POST.get('hours')
            description = request.POST.get('description', '')
            is_billable = request.POST.get('is_billable') == 'on'
            notes = request.POST.get('notes', '')
            
            # Validar campos requeridos
            if not all([resource_id, task_id, date_str, hours]):
                messages.error(request, 'Todos los campos obligatorios deben completarse')
                return redirect('projects:create_timelog')
            
            # Obtener objetos
            resource = get_object_or_404(Resource, pk=resource_id)
            task = get_object_or_404(Task, pk=task_id)
            
            # Crear TimeLog
            TimeLog.objects.create(
                resource=resource,
                task=task,
                date=datetime.strptime(date_str, '%Y-%m-%d').date(),
                hours=Decimal(hours),
                description=description,
                is_billable=is_billable,
                notes=notes
            )
            
            messages.success(request, f'Registro de {hours}h creado exitosamente')
            return redirect('projects:my_timelogs')
            
        except ValidationError as e:
            for error in e.messages:
                messages.error(request, error)
        except ValueError as e:
            messages.error(request, f'Error en los datos: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error al crear registro: {str(e)}')
    
    # GET: Mostrar formulario
    resources = Resource.objects.filter(is_active=True).order_by('first_name', 'last_name')
    projects = Project.objects.filter(status__in=['draft', 'planning', 'active']).order_by('name')
    
    context = {
        'resources': resources,
        'projects': projects,
        'today': date.today().isoformat(),
    }
    
    return render(request, 'projects/timelogs/form.html', context)


@login_required
def edit_timelog(request, pk):
    """
    Edita un TimeEntry existente.
    """
    timelog = get_object_or_404(TimeLog, pk=pk)
    
    if request.method == 'POST':
        try:
            # Actualizar campos
            resource_id = request.POST.get('resource_id')
            task_id = request.POST.get('task_id')
            date_str = request.POST.get('date')
            hours = request.POST.get('hours')
            description = request.POST.get('description', '')
            is_billable = request.POST.get('is_billable') == 'on'
            notes = request.POST.get('notes', '')
            
            # Validar campos requeridos
            if not all([resource_id, task_id, date_str, hours]):
                messages.error(request, 'Todos los campos obligatorios deben completarse')
                return redirect('projects:edit_timelog', pk=pk)
            
            # Actualizar objeto
            timelog.resource = get_object_or_404(Resource, pk=resource_id)
            timelog.task = get_object_or_404(Task, pk=task_id)
            timelog.date = datetime.strptime(date_str, '%Y-%m-%d').date()
            timelog.hours = Decimal(hours)
            timelog.description = description
            timelog.is_billable = is_billable
            timelog.notes = notes
            
            timelog.save()
            
            messages.success(request, 'Registro actualizado exitosamente')
            return redirect('projects:my_timelogs')
            
        except ValidationError as e:
            for error in e.messages:
                messages.error(request, error)
        except ValueError as e:
            messages.error(request, f'Error en los datos: {str(e)}')
        except Exception as e:
            messages.error(request, f'Error al actualizar: {str(e)}')
    
    # GET: Mostrar formulario con datos
    resources = Resource.objects.filter(is_active=True).order_by('first_name', 'last_name')
    projects = Project.objects.filter(status__in=['draft', 'planning', 'active']).order_by('name')
    # Cargar las tareas del proyecto actual
    tasks = Task.objects.filter(project=timelog.task.project).select_related('stage', 'required_role').order_by('stage__name', 'title')
    
    context = {
        'timelog': timelog,
        'resources': resources,
        'projects': projects,
        'tasks': tasks,
        'is_edit': True,
    }
    
    return render(request, 'projects/timelogs/form.html', context)


@login_required
@require_http_methods(["POST"])
def delete_timelog(request, pk):
    """
    Elimina un TimeEntry.
    """
    timelog = get_object_or_404(TimeEntry, pk=pk)
    
    try:
        hours = timelog.hours
        date = timelog.date
        timelog.delete()
        messages.success(request, f'Registro de {hours}h del {date} eliminado')
    except Exception as e:
        messages.error(request, f'Error al eliminar: {str(e)}')
    
    return redirect('projects:my_timelogs')


@login_required
def get_project_tasks(request, project_id):
    """
    API endpoint para obtener tareas de un proyecto.
    Usado por AJAX en el formulario.
    """
    from django.http import JsonResponse
    
    tasks = Task.objects.filter(
        project_id=project_id
    ).select_related('stage', 'required_role').values(
        'id', 'title', 'stage__name', 'required_role__name'
    )
    
    return JsonResponse({
        'tasks': list(tasks)
    })


@login_required
def update_task_status(request, project_pk, task_pk):
    """
    Actualiza solo el estado de una tarea.
    Vista simplificada para cambio rápido de estado desde el detalle del proyecto.
    """
    if request.method != 'POST':
        return redirect('projects:detail', pk=project_pk)
    
    try:
        project = get_object_or_404(Project, pk=project_pk)
        task = get_object_or_404(Task, pk=task_pk, project=project)
        
        new_status = request.POST.get('status')
        
        if new_status and new_status in dict(Task.STATUS_CHOICES):
            old_status = task.get_status_display()
            task.status = new_status
            task.save()
            
            messages.success(
                request, 
                f'✅ Estado de "{task.title}" cambiado de "{old_status}" a "{task.get_status_display()}"'
            )
        else:
            messages.error(request, 'Estado inválido')
            
    except Exception as e:
        messages.error(request, f'Error al actualizar estado: {str(e)}')

    return redirect('projects:detail', pk=project_pk)


@login_required
@require_http_methods(["POST"])
def update_task_progress(request, project_pk, task_pk):
    """
    Actualiza el porcentaje de avance manual de una tarea.
    Vista para actualización rápida desde el detalle del proyecto.
    """
    try:
        project = get_object_or_404(Project, pk=project_pk)
        task = get_object_or_404(Task, pk=task_pk, project=project)

        progress = request.POST.get('progress')

        if progress is not None:
            try:
                progress_value = Decimal(progress)

                # Validar rango 0-100
                if progress_value < 0 or progress_value > 100:
                    messages.error(request, 'El porcentaje debe estar entre 0 y 100')
                    return redirect('projects:detail', pk=project_pk)

                task.manual_progress_percentage = progress_value
                task.save()

                messages.success(
                    request,
                    f'✅ Avance de "{task.title}" actualizado a {progress_value}%'
                )

            except (ValueError, InvalidOperation):
                messages.error(request, 'Valor de porcentaje inválido')
        else:
            messages.error(request, 'Porcentaje no proporcionado')

    except Exception as e:
        messages.error(request, f'Error al actualizar progreso: {str(e)}')

    return redirect('projects:detail', pk=project_pk)
