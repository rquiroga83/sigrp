"""
Formularios para la gestión de proyectos.
"""
from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import Project, Stage, Task, TimeLog, TimeEntry, Allocation
from apps.resources.models import Role, Resource


class ProjectForm(forms.ModelForm):
    """
    Formulario para crear/editar proyectos.
    Incluye validación dinámica según el tipo de proyecto.
    """

    class Meta:
        model = Project
        fields = [
            'code', 'name', 'description', 'client_name',
            'project_type', 'status', 'priority',
            'fixed_price', 'budget_limit',
            'hourly_rate', 'max_budget',
            'profit_margin_target',
            'start_date', 'end_date',
            'tags', 'notes'
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'PRJ-2026-001'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del proyecto'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción detallada del proyecto'
            }),
            'client_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre del cliente'
            }),
            'project_type': forms.Select(attrs={
                'class': 'form-select',
                'id': 'id_project_type',
                'hx-get': '#',  # Para HTMX: mostrar/ocultar campos según tipo
                'hx-trigger': 'change',
                'hx-target': '#budget-fields'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'priority': forms.Select(attrs={
                'class': 'form-select'
            }),
            'fixed_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1000',
                'placeholder': '0',
                'min': '1'
            }),
            'budget_limit': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1000',
                'placeholder': '0',
                'min': '1'
            }),
            'hourly_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1000',
                'placeholder': '0',
                'min': '1'
            }),
            'max_budget': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1000',
                'placeholder': '0',
                'min': '1'
            }),
            'profit_margin_target': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': '30.00',
                'min': '0.00',
                'max': '100.00'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'tags': forms.HiddenInput(),  # Se manejará con JS
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notas internas del proyecto'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Hacer campos opcionales según corresponda
        self.fields['description'].required = False
        self.fields['fixed_price'].required = False
        self.fields['budget_limit'].required = False
        self.fields['hourly_rate'].required = False
        self.fields['max_budget'].required = False
        self.fields['start_date'].required = False
        self.fields['end_date'].required = False
        self.fields['tags'].required = False
        self.fields['notes'].required = False

        # Agregar helptext
        self.fields['code'].help_text = 'Código único del proyecto (ej: PRJ-2026-001)'
        self.fields['project_type'].help_text = 'Fixed Price: precio fijo | T&M: facturación por hora'
        self.fields['fixed_price'].help_text = 'Precio acordado con el cliente en COP (solo Fixed Price)'
        self.fields['budget_limit'].help_text = 'Límite de costo interno en COP (solo Fixed Price)'
        self.fields['hourly_rate'].help_text = 'Tarifa por hora al cliente en COP (solo T&M)'
        self.fields['max_budget'].help_text = 'Presupuesto máximo estimado en COP (solo T&M)'
        self.fields['profit_margin_target'].help_text = 'Margen de ganancia objetivo (%)'

    def clean(self):
        """
        Validación personalizada según tipo de proyecto.
        """
        cleaned_data = super().clean()
        project_type = cleaned_data.get('project_type')

        # Validar Fixed Price
        if project_type == 'fixed':
            fixed_price = cleaned_data.get('fixed_price')
            budget_limit = cleaned_data.get('budget_limit')

            if not fixed_price:
                self.add_error('fixed_price', 'Fixed Price projects must have a fixed price defined.')

            if not budget_limit:
                self.add_error('budget_limit', 'Fixed Price projects should have a budget limit.')

            # Limpiar campos de T&M
            cleaned_data['hourly_rate'] = None
            cleaned_data['max_budget'] = None

        # Validar Time & Materials
        elif project_type == 't_and_m':
            hourly_rate = cleaned_data.get('hourly_rate')
            max_budget = cleaned_data.get('max_budget')

            if not hourly_rate and not max_budget:
                raise ValidationError(
                    'Time & Materials projects should have either hourly_rate or max_budget defined.'
                )

            # Limpiar campos de Fixed Price
            cleaned_data['fixed_price'] = None
            cleaned_data['budget_limit'] = None

        # Validar fechas
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')

        if start_date and end_date:
            if end_date < start_date:
                self.add_error('end_date', 'End date cannot be before start date.')

        return cleaned_data


class StageForm(forms.ModelForm):
    """Formulario para crear/editar etapas."""

    class Meta:
        model = Stage
        fields = ['name', 'description', 'order', 'status', 'start_date', 'end_date', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'order': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class TaskForm(forms.ModelForm):
    """Formulario para crear/editar tareas."""

    class Meta:
        model = Task
        fields = [
            'title', 'description', 'stage', 'required_role',
            'estimated_hours', 'assigned_resource', 'status', 'priority',
            'due_date', 'tags', 'notes'
        ]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'stage': forms.Select(attrs={'class': 'form-select'}),
            'required_role': forms.Select(attrs={'class': 'form-select'}),
            'estimated_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.25',
                'min': '0.01'
            }),
            'assigned_resource': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'priority': forms.Select(attrs={'class': 'form-select'}),
            'due_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'tags': forms.HiddenInput(),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }

    def __init__(self, project=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Filtrar stages por proyecto
        if project:
            self.fields['stage'].queryset = Stage.objects.filter(project=project)

        # Recursos activos
        self.fields['assigned_resource'].queryset = Resource.objects.filter(is_active=True)
        self.fields['assigned_resource'].required = False


class TimeLogForm(forms.ModelForm):
    """Formulario para crear/editar registros de tiempo."""

    class Meta:
        model = TimeLog
        fields = ['task', 'resource', 'date', 'hours', 'description', 'is_billable', 'notes']
        widgets = {
            'task': forms.Select(attrs={'class': 'form-select'}),
            'resource': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.25',
                'min': '0.01',
                'max': '24.00'
            }),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_billable': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }


class AllocationForm(forms.ModelForm):
    """Formulario para crear/editar asignaciones de recursos."""

    class Meta:
        model = Allocation
        fields = ['resource', 'start_date', 'end_date', 'hours_per_week', 'notes']
        widgets = {
            'resource': forms.Select(attrs={'class': 'form-select'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'end_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'hours_per_week': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.5',
                'min': '0.01',
                'max': '168.00'
            }),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['resource'].queryset = Resource.objects.filter(is_active=True)
