"""
Views for resources app.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def resource_list(request):
    """Lista de recursos."""
    return render(request, 'resources/list.html')


@login_required
def resource_detail(request, pk):
    """Detalle de un recurso."""
    return render(request, 'resources/detail.html', {'resource_id': pk})
