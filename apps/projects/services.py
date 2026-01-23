"""
Servicios de lógica de negocio para proyectos.
RF-11: Cálculo de disponibilidad de recursos con detección de sobrecarga y fragmentación.
"""
from decimal import Decimal
from datetime import date
from django.db.models import Q, Sum
from typing import Dict, Any
from apps.resources.models import Resource


def calculate_availability(
    resource_id: int,
    start_date: date,
    end_date: date
) -> Dict[str, Any]:
    """
    Calcula la disponibilidad de un recurso en un rango temporal.
    
    Args:
        resource_id: ID del recurso a consultar
        start_date: Fecha de inicio del periodo a evaluar
        end_date: Fecha de fin del periodo a evaluar
    
    Returns:
        Dict con:
            - total_allocated_hours: Horas ya ocupadas en ese rango (por semana)
            - remaining_capacity: Horas libres disponibles (por semana)
            - capacity_weekly: Capacidad total semanal del recurso
            - active_project_count: Cantidad de proyectos concurrentes
            - concurrent_projects: Lista de proyectos concurrentes
            - is_fragmented: True si tiene >= 3 proyectos concurrentes
            - utilization_percentage: % de utilización (0-100+)
            - status: 'available', 'partial', 'full', 'overloaded'
            - can_allocate_hours: Horas máximas que se pueden asignar sin sobrecarga
    """
    from apps.projects.models import Allocation
    
    # 1. Obtener el recurso
    try:
        resource = Resource.objects.get(pk=resource_id)
    except Resource.DoesNotExist:
        return {
            'error': 'Recurso no encontrado',
            'total_allocated_hours': Decimal('0.00'),
            'remaining_capacity': Decimal('0.00'),
            'capacity_weekly': Decimal('0.00'),
            'active_project_count': 0,
            'concurrent_projects': [],
            'is_fragmented': False,
            'utilization_percentage': 0,
            'status': 'error',
            'can_allocate_hours': Decimal('0.00'),
        }
    
    # 2. Obtener capacidad semanal (default: 40h)
    capacity_weekly = getattr(resource, 'capacity_weekly', Decimal('40.00'))
    
    # 3. Buscar asignaciones activas que se solapen con el rango
    # Solapamiento: start <= query_end AND end >= query_start
    overlapping_allocations = Allocation.objects.filter(
        resource=resource,
        is_active=True,
        start_date__lte=end_date,
        end_date__gte=start_date
    )
    
    # 4. Calcular total de horas asignadas
    total_allocated = overlapping_allocations.aggregate(
        total=Sum('hours_per_week')
    )['total'] or Decimal('0.00')
    
    # 5. Calcular horas disponibles
    remaining_capacity = capacity_weekly - total_allocated
    
    # 6. Contar proyectos concurrentes
    concurrent_projects_query = overlapping_allocations.values(
        'project__pk',
        'project__code',
        'project__name'
    ).distinct()
    
    active_project_count = concurrent_projects_query.count()
    concurrent_projects = list(concurrent_projects_query)
    
    # 7. Detectar fragmentación (>= 3 proyectos simultáneos)
    is_fragmented = active_project_count >= 3
    
    # 8. Calcular porcentaje de utilización
    utilization_percentage = float(
        (total_allocated / capacity_weekly * Decimal('100.00'))
        if capacity_weekly > 0 else Decimal('0.00')
    )
    
    # 9. Determinar estado del recurso
    if total_allocated == 0:
        status = 'available'
    elif total_allocated < capacity_weekly:
        status = 'partial'
    elif total_allocated == capacity_weekly:
        status = 'full'
    else:
        status = 'overloaded'
    
    # 10. Calcular horas máximas que se pueden asignar
    can_allocate_hours = max(Decimal('0.00'), remaining_capacity)
    
    return {
        'resource_id': resource_id,
        'resource_name': resource.full_name,
        'total_allocated_hours': total_allocated,
        'remaining_capacity': remaining_capacity,
        'capacity_weekly': capacity_weekly,
        'active_project_count': active_project_count,
        'concurrent_projects': concurrent_projects,
        'is_fragmented': is_fragmented,
        'utilization_percentage': round(utilization_percentage, 2),
        'status': status,
        'can_allocate_hours': can_allocate_hours,
    }


def get_allocation_recommendations(
    resource_id: int,
    requested_hours: Decimal,
    start_date: date,
    end_date: date
) -> Dict[str, Any]:
    """
    Analiza si una asignación propuesta es viable y genera recomendaciones.
    
    Args:
        resource_id: ID del recurso
        requested_hours: Horas por semana solicitadas
        start_date: Fecha de inicio propuesta
        end_date: Fecha de fin propuesta
    
    Returns:
        Dict con:
            - is_viable: True si la asignación es posible
            - block_reason: Motivo de bloqueo si is_viable=False
            - warnings: Lista de advertencias (fragmentación, alta carga, etc.)
            - recommendations: Lista de recomendaciones
            - availability: Resultado de calculate_availability
    """
    availability = calculate_availability(resource_id, start_date, end_date)
    
    if 'error' in availability:
        return {
            'is_viable': False,
            'block_reason': availability['error'],
            'warnings': [],
            'recommendations': [],
            'availability': availability,
        }
    
    warnings = []
    recommendations = []
    is_viable = True
    block_reason = None
    
    # 1. Verificar sobrecarga (HARD BLOCK)
    total_with_new = availability['total_allocated_hours'] + requested_hours
    
    if total_with_new > availability['capacity_weekly']:
        is_viable = False
        overload = total_with_new - availability['capacity_weekly']
        block_reason = (
            f"⛔ SOBRECARGA: La asignación requiere {requested_hours}h/sem, "
            f"pero el recurso solo tiene {availability['remaining_capacity']}h/sem disponibles. "
            f"Exceso: {overload}h/sem."
        )
        recommendations.append(
            f"Reducir las horas solicitadas a máximo {availability['can_allocate_hours']}h/sem"
        )
        recommendations.append(
            "O seleccionar otro recurso con mayor disponibilidad"
        )
    
    # 2. Advertencia de fragmentación
    if availability['active_project_count'] >= 2:
        new_project_count = availability['active_project_count'] + 1
        warnings.append(
            f"⚠️ FRAGMENTACIÓN: El recurso ya trabaja en {availability['active_project_count']} "
            f"proyectos concurrentes. Agregar uno más ({new_project_count} total) puede "
            f"reducir la eficiencia hasta un 40% por Context Switching."
        )
        recommendations.append(
            "Considerar consolidar tareas o asignar un recurso menos fragmentado"
        )
    
    # 3. Advertencia de alta utilización (80-99%)
    if is_viable:
        new_utilization = float(
            (total_with_new / availability['capacity_weekly'] * Decimal('100.00'))
            if availability['capacity_weekly'] > 0 else Decimal('0.00')
        )
        
        if new_utilization >= 80 and new_utilization < 100:
            warnings.append(
                f"⚠️ ALTA CARGA: Esta asignación llevaría al recurso a {new_utilization:.1f}% "
                f"de utilización. Queda poco margen para imprevistos."
            )
            recommendations.append(
                "Dejar al menos 20% de capacidad para tareas no planificadas"
            )
    
    # 4. Recomendación positiva
    if is_viable and not warnings:
        recommendations.append(
            f"✅ El recurso tiene capacidad adecuada: "
            f"{availability['remaining_capacity']}h/sem disponibles "
            f"({100 - availability['utilization_percentage']:.1f}% libre)"
        )
    
    return {
        'is_viable': is_viable,
        'block_reason': block_reason,
        'warnings': warnings,
        'recommendations': recommendations,
        'availability': availability,
        'projected_utilization': round(
            float((total_with_new / availability['capacity_weekly'] * Decimal('100.00'))
                  if availability['capacity_weekly'] > 0 else Decimal('0.00')),
            2
        ),
    }
