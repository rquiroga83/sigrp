"""
Formularios para la gestión de recursos humanos.
"""
from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
from .models import Resource, Role


class ResourceForm(forms.ModelForm):
    """
    Formulario para crear/editar recursos humanos.
    """

    class Meta:
        model = Resource
        fields = [
            'employee_id', 'first_name', 'last_name', 'email', 'phone',
            'primary_role', 'internal_cost',
            'hire_date', 'location',
            'status', 'availability_percentage',
            'bio', 'profile_picture',
            'skills_vector', 'certifications', 'preferred_technologies',
            'notes'
        ]
        widgets = {
            'employee_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'EMP-001'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Nombre'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Apellido'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'correo@ejemplo.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '+57 300 123 4567'
            }),
            'primary_role': forms.Select(attrs={
                'class': 'form-select'
            }),
            'internal_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1000',
                'placeholder': '0',
                'min': '1'
            }),
            'hire_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bogotá, Colombia'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'availability_percentage': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '100',
                'step': '5'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Biografía profesional del recurso...'
            }),
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'skills_vector': forms.HiddenInput(),
            'certifications': forms.HiddenInput(),
            'preferred_technologies': forms.HiddenInput(),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Notas internas...'
            }),
        }

    # Campos adicionales para gestionar habilidades en el formulario
    skill_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Nombre de la habilidad',
            'id': 'skill_name'
        })
    )
    skill_level = forms.IntegerField(
        required=False,
        min_value=1,
        max_value=5,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'max': '5',
            'placeholder': '1-5',
            'id': 'skill_level'
        })
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Hacer campos opcionales según corresponda
        self.fields['phone'].required = False
        self.fields['hire_date'].required = False
        self.fields['location'].required = False
        self.fields['bio'].required = False
        self.fields['profile_picture'].required = False
        self.fields['notes'].required = False
        self.fields['skills_vector'].required = False
        self.fields['certifications'].required = False
        self.fields['preferred_technologies'].required = False

        # Agregar helptext
        self.fields['employee_id'].help_text = 'Código único del empleado (ej: EMP-001)'
        self.fields['primary_role'].help_text = 'Rol principal del recurso (determina capacidades)'
        self.fields['internal_cost'].help_text = 'Costo real por hora en COP (confidencial)'
        self.fields['availability_percentage'].help_text = 'Porcentaje de tiempo disponible (0-100%)'
        self.fields['skills_vector'].help_text = 'Habilidades técnicas con nivel de competencia'
        self.fields['certifications'].help_text = 'Certificaciones profesionales'
        self.fields['preferred_technologies'].help_text = 'Tecnologías preferidas'

    def clean_email(self):
        """Validar que el email sea único."""
        email = self.cleaned_data.get('email')
        if email:
            # Excluir el recurso actual si estamos editando
            qs = Resource.objects.filter(email=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Ya existe un recurso con este email.')
        return email

    def clean_employee_id(self):
        """Validar que el employee_id sea único."""
        employee_id = self.cleaned_data.get('employee_id')
        if employee_id:
            # Excluir el recurso actual si estamos editando
            qs = Resource.objects.filter(employee_id=employee_id)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Ya existe un recurso con este ID de empleado.')
        return employee_id

    def clean_availability_percentage(self):
        """Validar que el porcentaje esté entre 0 y 100."""
        availability = self.cleaned_data.get('availability_percentage')
        if availability is not None:
            if availability < 0 or availability > 100:
                raise ValidationError('El porcentaje debe estar entre 0 y 100.')
        return availability


class RoleForm(forms.ModelForm):
    """
    Formulario para crear/editar roles profesionales.
    """

    class Meta:
        model = Role
        fields = [
            'code', 'name', 'category', 'seniority',
            'standard_rate', 'description',
            'required_skills', 'is_active', 'notes'
        ]
        widgets = {
            'code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'SBE-001'
            }),
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Senior Backend Engineer'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'seniority': forms.Select(attrs={
                'class': 'form-select'
            }),
            'standard_rate': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '1000',
                'placeholder': '0',
                'min': '1'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Descripción del rol...'
            }),
            'required_skills': forms.HiddenInput(),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Notas internas...'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Hacer campos opcionales
        self.fields['description'].required = False
        self.fields['notes'].required = False
        self.fields['required_skills'].required = False

        # Agregar helptext
        self.fields['code'].help_text = 'Código único del rol (ej: SBE, JQA)'
        self.fields['standard_rate'].help_text = 'Tarifa por hora para estimaciones y facturación al cliente (COP)'
        self.fields['required_skills'].help_text = 'Lista de habilidades técnicas necesarias'

    def clean_code(self):
        """Validar que el código sea único."""
        code = self.cleaned_data.get('code')
        if code:
            # Excluir el rol actual si estamos editando
            qs = Role.objects.filter(code=code)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Ya existe un rol con este código.')
        return code

    def clean_name(self):
        """Validar que el nombre sea único."""
        name = self.cleaned_data.get('name')
        if name:
            # Excluir el rol actual si estamos editando
            qs = Role.objects.filter(name=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise ValidationError('Ya existe un rol con este nombre.')
        return name
