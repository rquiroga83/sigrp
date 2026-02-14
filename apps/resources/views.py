"""
Views for resources app.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Sum, Q
from decimal import Decimal
from .models import Resource, Role
from .forms import ResourceForm, RoleForm


def resource_list(request):
    """Lista de recursos."""
    resources = Resource.objects.select_related('primary_role').filter(is_active=True)

    # Calcular estadísticas
    available_count = resources.filter(status='available').count()
    partially_count = resources.filter(status='partially_allocated').count()
    fully_count = resources.filter(status='fully_allocated').count()

    # Obtener roles activos
    roles = Role.objects.filter(is_active=True).order_by('category', 'seniority')

    context = {
        'resources': resources,
        'total_count': resources.count(),
        'available_count': available_count,
        'partially_count': partially_count,
        'fully_count': fully_count,
        'roles': roles,
    }
    return render(request, 'resources/list.html', context)


def resource_detail(request, pk):
    """Detalle de un recurso."""
    resource = get_object_or_404(Resource, pk=pk)
    context = {
        'resource': resource,
    }
    return render(request, 'resources/detail.html', context)


@login_required
def resource_create(request):
    """
    Vista para crear un nuevo recurso humano.
    Incluye gestión de habilidades y skills_vector.
    """
    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES)

        if form.is_valid():
            try:
                resource = form.save(commit=False)

                # Asignar usuario creador si está autenticado
                if request.user.is_authenticated:
                    resource.created_by = request.user
                    resource.updated_by = request.user

                # Inicializar skills_vector si está vacío
                if not resource.skills_vector:
                    resource.skills_vector = []

                # Inicializar certifications si está vacío
                if not resource.certifications:
                    resource.certifications = []

                # Inicializar preferred_technologies si está vacío
                if not resource.preferred_technologies:
                    resource.preferred_technologies = []

                resource.save()

                messages.success(
                    request,
                    f'✅ Recurso "{resource.full_name}" ({resource.employee_id}) creado exitosamente'
                )

                # Redirigir al detalle del recurso
                return redirect('resources:detail', pk=resource.pk)

            except ValidationError as e:
                for error in e.messages:
                    messages.error(request, error)
            except Exception as e:
                messages.error(request, f'Error al crear recurso: {str(e)}')
        else:
            # Mostrar errores del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        # GET: Mostrar formulario vacío
        form = ResourceForm()

    # Obtener roles activos para el selector
    roles = Role.objects.filter(is_active=True).order_by('category', 'seniority')

    context = {
        'form': form,
        'roles': roles,
        'is_create': True,
    }

    return render(request, 'resources/create.html', context)


@login_required
def role_create(request):
    """
    Vista para crear un nuevo rol profesional.
    Define tarifas estándar para estimación y facturación.
    """
    if request.method == 'POST':
        form = RoleForm(request.POST)

        if form.is_valid():
            try:
                role = form.save(commit=False)

                # Asignar usuario creador si está autenticado
                if request.user.is_authenticated:
                    role.created_by = request.user
                    role.updated_by = request.user

                # Inicializar required_skills si está vacío
                if not role.required_skills:
                    role.required_skills = []

                role.save()

                messages.success(
                    request,
                    f'✅ Rol "{role.name}" ({role.code}) creado exitosamente'
                )

                # Redirigir a la lista de recursos
                return redirect('resources:list')

            except ValidationError as e:
                for error in e.messages:
                    messages.error(request, error)
            except Exception as e:
                messages.error(request, f'Error al crear rol: {str(e)}')
        else:
            # Mostrar errores del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        # GET: Mostrar formulario vacío
        form = RoleForm()

    context = {
        'form': form,
        'is_create': True,
    }

    return render(request, 'resources/create_role.html', context)


@login_required
def role_edit(request, pk):
    """
    Vista para editar un rol profesional existente.
    """
    role = get_object_or_404(Role, pk=pk)

    if request.method == 'POST':
        form = RoleForm(request.POST, instance=role)

        if form.is_valid():
            try:
                role = form.save(commit=False)

                # Asignar usuario que actualiza
                if request.user.is_authenticated:
                    role.updated_by = request.user

                # Inicializar required_skills si está vacío
                if not role.required_skills:
                    role.required_skills = []

                role.save()

                messages.success(
                    request,
                    f'✅ Rol "{role.name}" ({role.code}) actualizado exitosamente'
                )

                # Redirigir a la lista de recursos
                return redirect('resources:list')

            except ValidationError as e:
                for error in e.messages:
                    messages.error(request, error)
            except Exception as e:
                messages.error(request, f'Error al actualizar rol: {str(e)}')
        else:
            # Mostrar errores del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        # GET: Mostrar formulario con datos del rol
        form = RoleForm(instance=role)

    context = {
        'form': form,
        'role': role,
        'is_create': False,
    }

    return render(request, 'resources/edit_role.html', context)


@login_required
def resource_edit(request, pk):
    """
    Vista para editar un recurso humano existente.
    """
    resource = get_object_or_404(Resource, pk=pk)

    if request.method == 'POST':
        form = ResourceForm(request.POST, request.FILES, instance=resource)

        if form.is_valid():
            try:
                resource = form.save(commit=False)

                # Asignar usuario que actualiza
                if request.user.is_authenticated:
                    resource.updated_by = request.user

                # Inicializar skills_vector si está vacío
                if not resource.skills_vector:
                    resource.skills_vector = []

                # Inicializar certifications si está vacío
                if not resource.certifications:
                    resource.certifications = []

                # Inicializar preferred_technologies si está vacío
                if not resource.preferred_technologies:
                    resource.preferred_technologies = []

                resource.save()

                messages.success(
                    request,
                    f'✅ Recurso "{resource.full_name}" ({resource.employee_id}) actualizado exitosamente'
                )

                # Redirigir al detalle del recurso
                return redirect('resources:detail', pk=resource.pk)

            except ValidationError as e:
                for error in e.messages:
                    messages.error(request, error)
            except Exception as e:
                messages.error(request, f'Error al actualizar recurso: {str(e)}')
        else:
            # Mostrar errores del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        # GET: Mostrar formulario con datos del recurso
        form = ResourceForm(instance=resource)

    # Obtener roles activos para el selector
    roles = Role.objects.filter(is_active=True).order_by('category', 'seniority')

    context = {
        'form': form,
        'resource': resource,
        'roles': roles,
        'is_create': False,
    }

    return render(request, 'resources/edit.html', context)


def resource_capacity_chart(request):
    """
    Vista de gráfico de capacidad de recursos.
    Muestra un gráfico de barras apiladas con la asignación de recursos a proyectos.
    Incluye tanto tiempo registrado como asignaciones planificadas.
    """
    from apps.projects.models import TimeLog, TimeEntry, Project, Allocation
    from datetime import datetime, timedelta
    from django.utils import timezone

    # Obtener rango de fechas (por defecto: próximos 30 días para planeación)
    start_date = timezone.now().date()
    end_date = start_date + timedelta(days=30)

    # Permitir filtrar por rango de fechas desde query params
    if request.GET.get('start_date'):
        try:
            start_date = datetime.strptime(request.GET.get('start_date'), '%Y-%m-%d').date()
        except ValueError:
            pass

    if request.GET.get('end_date'):
        try:
            end_date = datetime.strptime(request.GET.get('end_date'), '%Y-%m-%d').date()
        except ValueError:
            pass

    # Obtener recursos activos
    resources = Resource.objects.filter(is_active=True).select_related('primary_role').order_by('first_name', 'last_name')

    # Obtener todos los proyectos que tienen tiempo registrado O asignaciones planificadas
    projects_with_data = set()

    # Proyectos desde TimeLog
    time_logs_in_range = TimeLog.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).select_related('task__project').values_list('task__project', flat=True).distinct()
    projects_with_data.update(time_logs_in_range)

    # Proyectos desde TimeEntry
    time_entries_in_range = TimeEntry.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).values_list('project', flat=True).distinct()
    projects_with_data.update(time_entries_in_range)

    # Proyectos desde Allocation (asignaciones planificadas)
    allocations_in_range = Allocation.objects.filter(
        is_active=True,
        start_date__lte=end_date,
        end_date__gte=start_date
    ).values_list('project', flat=True).distinct()
    projects_with_data.update(allocations_in_range)

    # Obtener objetos de proyecto
    if projects_with_data:
        projects = Project.objects.filter(id__in=projects_with_data).order_by('name')
    else:
        projects = Project.objects.none()

    # Preparar datos para el gráfico
    chart_data = {
        'labels': [],  # Nombres de recursos
        'datasets': [],  # Un dataset por proyecto
        'capacities': []  # Capacidad total de cada recurso
    }

    # Crear datasets: uno para tiempo registrado (sólido) y otro para planificado (semi-transparente)
    actual_data = {}  # Tiempo ya registrado
    planned_data = {}  # Asignaciones planificadas

    for project in projects:
        # Tiempo registrado (color sólido)
        actual_data[project.id] = {
            'label': f'{project.name} (Registrado)',
            'data': [],
            'backgroundColor': generate_color(project.id),
            'borderColor': generate_color(project.id, border=True),
            'borderWidth': 1,
        }
        # Tiempo planificado (color semi-transparente con patrón)
        planned_data[project.id] = {
            'label': f'{project.name} (Planificado)',
            'data': [],
            'backgroundColor': generate_color(project.id, alpha=0.4),
            'borderColor': generate_color(project.id, border=True),
            'borderWidth': 1,
            'borderDash': [5, 5],  # Línea punteada
        }

    # Para cada recurso, calcular horas por proyecto (actual + planificado)
    for resource in resources:
        chart_data['labels'].append(resource.full_name)

        # Calcular capacidad en el período usando semanas completas
        # Usar la misma lógica que las asignaciones: división entera, mínimo 1 semana
        days_in_period = (end_date - start_date).days
        weeks_in_period = max(1, days_in_period // 7)

        # Capacidad semanal = 40h * disponibilidad
        weekly_capacity = Decimal('40.0') * (Decimal(resource.availability_percentage) / Decimal('100.0'))
        period_capacity = weekly_capacity * Decimal(weeks_in_period)
        chart_data['capacities'].append(float(period_capacity))

        # === TIEMPO REGISTRADO (ACTUAL) ===
        # Obtener horas de TimeLog
        time_logs = TimeLog.objects.filter(
            resource=resource,
            date__gte=start_date,
            date__lte=end_date
        ).select_related('task__project')

        # Obtener horas de TimeEntry
        time_entries = TimeEntry.objects.filter(
            resource=resource,
            date__gte=start_date,
            date__lte=end_date
        ).select_related('project')

        # Agregar horas registradas por proyecto
        actual_hours_by_project = {}

        for log in time_logs:
            project_id = log.task.project.id
            if project_id not in actual_hours_by_project:
                actual_hours_by_project[project_id] = Decimal('0.0')
            actual_hours_by_project[project_id] += log.hours

        for entry in time_entries:
            project_id = entry.project.id
            if project_id not in actual_hours_by_project:
                actual_hours_by_project[project_id] = Decimal('0.0')
            actual_hours_by_project[project_id] += entry.hours

        # === ASIGNACIONES PLANIFICADAS ===
        # Obtener allocations activas que se solapen con el período
        allocations = Allocation.objects.filter(
            resource=resource,
            is_active=True,
            start_date__lte=end_date,
            end_date__gte=start_date
        ).select_related('project')

        # Calcular horas planificadas por proyecto
        planned_hours_by_project = {}

        for allocation in allocations:
            project_id = allocation.project.id

            # Calcular cuántas semanas de esta asignación caen en nuestro rango
            # Usar la misma lógica que Allocation.duration_weeks (división entera)
            alloc_start = max(allocation.start_date, start_date)
            alloc_end = min(allocation.end_date, end_date)
            overlap_days = (alloc_end - alloc_start).days

            # División entera con mínimo de 1 semana (igual que el modelo)
            # Si la asignación toca el rango, cuenta mínimo 1 semana completa
            overlap_weeks = max(1, overlap_days // 7)

            # Horas totales = hours_per_week * semanas completas
            hours = allocation.hours_per_week * Decimal(overlap_weeks)

            if project_id not in planned_hours_by_project:
                planned_hours_by_project[project_id] = Decimal('0.0')
            planned_hours_by_project[project_id] += hours

        # Agregar datos a cada dataset
        for project in projects:
            actual_hours = actual_hours_by_project.get(project.id, Decimal('0.0'))
            planned_hours = planned_hours_by_project.get(project.id, Decimal('0.0'))

            actual_data[project.id]['data'].append(float(actual_hours))
            planned_data[project.id]['data'].append(float(planned_hours))

    # Combinar datasets: primero los registrados, luego los planificados
    chart_data['datasets'] = list(actual_data.values()) + list(planned_data.values())

    # Calcular estadísticas
    total_resources = resources.count()
    total_capacity = sum(chart_data['capacities'])
    total_allocated = sum(sum(dataset['data']) for dataset in chart_data['datasets'])
    utilization_rate = (total_allocated / total_capacity * 100) if total_capacity > 0 else 0

    # Contar registros de tiempo para debugging
    total_time_logs = TimeLog.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).count()
    total_time_entries = TimeEntry.objects.filter(
        date__gte=start_date,
        date__lte=end_date
    ).count()

    context = {
        'chart_data': chart_data,
        'resources': resources,
        'projects': projects,
        'start_date': start_date,
        'end_date': end_date,
        'total_resources': total_resources,
        'total_capacity': total_capacity,
        'total_allocated': total_allocated,
        'utilization_rate': utilization_rate,
        'total_time_logs': total_time_logs,
        'total_time_entries': total_time_entries,
        'projects_count': projects.count(),
    }

    return render(request, 'resources/capacity_chart.html', context)


def generate_color(seed, alpha=0.8, border=False):
    """
    Genera un color consistente basado en un seed (para que cada proyecto tenga el mismo color).

    Args:
        seed: Identificador único para generar el color (ej: project.id)
        alpha: Transparencia del color (0.0 a 1.0). Default: 0.8
        border: Si True, retorna RGB sin canal alfa. Si False, retorna RGBA. Default: False

    Returns:
        String con formato 'rgb(r, g, b)' o 'rgba(r, g, b, a)'
    """
    import hashlib

    # Usar hash para generar colores consistentes
    hash_object = hashlib.md5(str(seed).encode())
    hash_hex = hash_object.hexdigest()

    # Extraer valores RGB del hash
    r = int(hash_hex[0:2], 16)
    g = int(hash_hex[2:4], 16)
    b = int(hash_hex[4:6], 16)

    # Ajustar para colores más vibrantes
    r = min(255, r + 50)
    g = min(255, g + 50)
    b = min(255, b + 50)

    # Retornar formato según parámetros
    if border:
        return f'rgb({r}, {g}, {b})'
    else:
        return f'rgba({r}, {g}, {b}, {alpha})'
