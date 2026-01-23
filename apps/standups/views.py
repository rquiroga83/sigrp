"""
Views for standups app.
"""
from django.shortcuts import render
from django.contrib.auth.decorators import login_required


@login_required
def standup_list(request):
    """Lista de standups."""
    return render(request, 'standups/list.html')


@login_required
def standup_create(request):
    """Crear nuevo standup."""
    return render(request, 'standups/create.html')
