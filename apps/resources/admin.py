"""
Admin configuration for Resources app.
"""
from django.contrib import admin
from .models import Resource, ResourceAllocation


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ['employee_id', 'full_name', 'role', 'seniority', 'status', 'availability_percentage', 'is_active']
    list_filter = ['status', 'seniority', 'department', 'is_active']
    search_fields = ['employee_id', 'full_name', 'email', 'role']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('user', 'employee_id', 'full_name', 'email', 'phone', 'profile_picture')
        }),
        ('Información Profesional', {
            'fields': ('role', 'seniority', 'department', 'location', 'bio')
        }),
        ('Habilidades y Certificaciones', {
            'fields': ('skills', 'certifications', 'preferred_technologies')
        }),
        ('Disponibilidad', {
            'fields': ('status', 'availability_percentage')
        }),
        ('Información Financiera', {
            'fields': ('hire_date', 'hourly_cost')
        }),
        ('Notas y Estado', {
            'fields': ('notes', 'is_active')
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ResourceAllocation)
class ResourceAllocationAdmin(admin.ModelAdmin):
    list_display = ['resource', 'project', 'role_in_project', 'start_date', 'end_date', 'allocation_percentage', 'is_active']
    list_filter = ['is_active', 'start_date']
    search_fields = ['resource__full_name', 'project__name', 'role_in_project']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'start_date'
