"""
Views for resources app.
"""
from django.shortcuts import render
from .models import Resource, Role


def resource_list(request):
    """Lista de recursos."""
    resources = Resource.objects.select_related('primary_role').filter(is_active=True)
    
    # Calcular estadísticas
    available_count = resources.filter(status='available').count()
    partially_count = resources.filter(status='partially_allocated').count()
    fully_count = resources.filter(status='fully_allocated').count()
    
    context = {
        'resources': resources,
        'total_count': resources.count(),
        'available_count': available_count,
        'partially_count': partially_count,
        'fully_count': fully_count,
    }
    return render(request, 'resources/list.html', context)


def resource_detail(request, pk):
    """Detalle de un recurso."""
    from django.shortcuts import get_object_or_404
    resource = get_object_or_404(Resource, pk=pk)
    context = {
        'resource': resource,
    }
    return render(request, 'resources/detail.html', context)
