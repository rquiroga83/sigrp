"""
Admin configuration for Projects app.
"""
from django.contrib import admin
from .models import Project, TimeEntry


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'client_name', 'project_type', 'status', 'health_score', 'is_active']
    list_filter = ['project_type', 'status', 'priority', 'risk_level', 'is_active']
    search_fields = ['code', 'name', 'client_name', 'description']
    readonly_fields = ['actual_hours_logged', 'actual_cost', 'revenue', 'health_score', 'created_at', 'updated_at']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('code', 'name', 'description', 'project_type')
        }),
        ('Cliente', {
            'fields': ('client_name', 'client_contact', 'client_email')
        }),
        ('Planificación', {
            'fields': ('start_date', 'planned_end_date', 'actual_end_date', 'status', 'priority')
        }),
        ('Precio Fijo (Fixed)', {
            'fields': ('fixed_price', 'budget_limit', 'estimated_hours'),
            'classes': ('collapse',)
        }),
        ('Time & Material', {
            'fields': ('hourly_rate', 'max_hours_cap'),
            'classes': ('collapse',)
        }),
        ('Métricas Actuales', {
            'fields': ('actual_hours_logged', 'actual_cost', 'revenue')
        }),
        ('Salud del Proyecto', {
            'fields': ('health_score', 'risk_level', 'team_size')
        }),
        ('Técnico', {
            'fields': ('technologies', 'repository_url', 'documentation_url')
        }),
        ('Notas', {
            'fields': ('notes', 'is_active')
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ['project', 'resource', 'date', 'hours', 'is_billable', 'is_invoiced', 'cost']
    list_filter = ['is_billable', 'is_invoiced', 'date', 'project']
    search_fields = ['project__name', 'resource__full_name', 'description']
    readonly_fields = ['cost', 'billable_amount', 'created_at', 'updated_at']
    date_hierarchy = 'date'
