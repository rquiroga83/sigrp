"""
Vistas para gestionar Allocations (RF-11: Resource Leveling)
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from datetime import datetime, date
from decimal import Decimal

from .models import Project, Allocation
from apps.resources.models import Resource
from .services import calculate_availability, get_allocation_recommendations


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
    
    return render(request, 'projects/manage_allocations.html', {
        'project': project,
        'allocations': allocations,
        'resources': resources,
        'total_allocated_hours': total_allocated_hours,
        'active_allocations': active_allocations,
    })


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
            resource=resource,
            start_date=start_date,
            end_date=end_date,
            requested_hours_per_week=hours_per_week
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
            is_confirmed=True
        )
        
        # Validar con clean() que ejecutará las validaciones del modelo
        allocation.full_clean()
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
