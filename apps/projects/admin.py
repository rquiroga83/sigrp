"""
Admin configuration for Projects app.
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import Project, Stage, Task, TimeLog, TimeEntry, Allocation


class StageInline(admin.TabularInline):
    """Inline para gestionar etapas dentro de un proyecto."""
    model = Stage
    extra = 1
    fields = ['name', 'order', 'status', 'start_date', 'end_date']
    ordering = ['order']


class TaskInline(admin.TabularInline):
    """Inline para gestionar tareas dentro de una etapa."""
    model = Task
    extra = 0
    fields = ['title', 'status', 'required_role', 'estimated_hours', 'assigned_resource', 'logged_hours', 'due_date']
    readonly_fields = ['logged_hours']
    ordering = ['-priority', 'due_date']


class TimeLogInline(admin.TabularInline):
    """Inline para ver registros de tiempo de una tarea."""
    model = TimeLog
    extra = 0
    fields = ['date', 'resource', 'hours', 'cost', 'billable_amount', 'is_billable']
    readonly_fields = ['cost', 'billable_amount']
    ordering = ['-date']


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['code', 'name', 'client_name', 'project_type', 'status', 'display_total_cost', 'display_profit_margin', 'is_active']
    list_filter = ['project_type', 'status', 'priority', 'is_active']
    search_fields = ['code', 'name', 'client_name', 'description']
    readonly_fields = ['display_total_logged_hours', 'display_total_cost', 'display_total_billable', 'display_profit_margin', 'display_completion', 'created_at', 'updated_at']
    date_hierarchy = 'start_date'
    inlines = [StageInline]
    
    fieldsets = (
        ('InformaciÃ³n BÃ¡sica', {
            'fields': ('code', 'name', 'description', 'client_name')
        }),
        ('ConfiguraciÃ³n del Proyecto', {
            'fields': ('project_type', 'status', 'priority')
        }),
        ('Fechas', {
            'fields': ('start_date', 'end_date', 'actual_end_date')
        }),
        ('ConfiguraciÃ³n Financiera - Fixed Price', {
            'fields': ('fixed_price', 'budget_limit'),
            'classes': ('collapse',),
            'description': 'ConfiguraciÃ³n para proyectos de Precio Fijo'
        }),
        ('ConfiguraciÃ³n Financiera - Time & Materials', {
            'fields': ('hourly_rate', 'max_budget'),
            'classes': ('collapse',),
            'description': 'ConfiguraciÃ³n para proyectos Time & Materials'
        }),
        ('Objetivos', {
            'fields': ('profit_margin_target',)
        }),
        ('MÃ©tricas Actuales (Solo Lectura)', {
            'fields': ('display_total_logged_hours', 'display_total_cost', 'display_total_billable', 'display_profit_margin', 'display_completion'),
            'classes': ('collapse',)
        }),
        ('Metadatos', {
            'fields': ('tags', 'notes', 'is_active')
        }),
        ('AuditorÃ­a', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def display_total_cost(self, obj):
        """Muestra el costo total con formato."""
        return f"${obj.total_cost:,.2f}"
    display_total_cost.short_description = 'Costo Total'
    
    def display_profit_margin(self, obj):
        """Muestra el margen de ganancia con formato."""
        margin = obj.profit_margin
        color = 'green' if margin > obj.profit_margin_target else 'red'
        return f'<span style="color: {color};">{margin:.2f}%</span>'
    display_profit_margin.short_description = 'Margen'
    display_profit_margin.allow_tags = True
    
    def display_total_logged_hours(self, obj):
        """Muestra horas registradas."""
        return f"{obj.total_logged_hours:.2f}h"
    display_total_logged_hours.short_description = 'Horas Registradas'
    
    def display_total_billable(self, obj):
        """Muestra monto facturable."""
        return f"${obj.total_billable:,.2f}"
    display_total_billable.short_description = 'Total Facturable'
    
    def display_completion(self, obj):
        """Muestra porcentaje de completitud."""
        return f"{obj.completion_percentage:.1f}%"
    display_completion.short_description = 'Completitud'


@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'order', 'status', 'display_progress']
    list_filter = ['status', 'project']
    search_fields = ['name', 'project__name', 'description']
    readonly_fields = ['display_total_logged_hours', 'display_total_planned_hours', 'display_actual_cost', 'display_planned_value', 'created_at', 'updated_at']
    inlines = [TaskInline]
    
    fieldsets = (
        ('InformaciÃ³n BÃ¡sica', {
            'fields': ('project', 'name', 'description', 'order')
        }),
        ('Estado y Fechas', {
            'fields': ('status', 'start_date', 'end_date')
        }),
        ('MÃ©tricas (Solo Lectura)', {
            'fields': ('display_total_logged_hours', 'display_total_planned_hours', 'display_actual_cost', 'display_planned_value'),
            'classes': ('collapse',)
        }),
        ('Notas', {
            'fields': ('notes',)
        }),
        ('AuditorÃ­a', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def display_progress(self, obj):
        """Muestra progreso de la etapa."""
        return f"{obj.progress_percentage:.1f}%"
    display_progress.short_description = 'Progreso'
    
    def display_total_logged_hours(self, obj):
        return f"{obj.total_logged_hours:.2f}h"
    display_total_logged_hours.short_description = 'Horas Registradas'
    
    def display_total_planned_hours(self, obj):
        return f"{obj.total_planned_hours:.2f}h"
    display_total_planned_hours.short_description = 'Horas Planificadas'
    
    def display_actual_cost(self, obj):
        return f"${obj.actual_cost:,.2f}"
    display_actual_cost.short_description = 'Costo Real'
    
    def display_planned_value(self, obj):
        return f"${obj.planned_value:,.2f}"
    display_planned_value.short_description = 'Valor Planificado'


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ['title', 'project', 'stage', 'status', 'priority', 'required_role', 'assigned_resource', 'display_completion', 'display_variance']
    list_filter = ['status', 'priority', 'project', 'stage', 'required_role']
    search_fields = ['title', 'description', 'project__name']
    readonly_fields = ['logged_hours', 'display_planned_value', 'display_actual_cost', 'display_cost_variance', 'display_hours_variance', 'display_completion', 'created_at', 'updated_at']
    date_hierarchy = 'due_date'
    inlines = [TimeLogInline]
    
    fieldsets = (
        ('InformaciÃ³n BÃ¡sica', {
            'fields': ('project', 'stage', 'title', 'description')
        }),
        ('Estado', {
            'fields': ('status', 'priority')
        }),
        ('PlanificaciÃ³n (EstimaciÃ³n)', {
            'fields': ('required_role', 'estimated_hours', 'display_planned_value'),
            'description': 'Define el costo planificado basado en el rol'
        }),
        ('EjecuciÃ³n (Realidad)', {
            'fields': ('assigned_resource', 'logged_hours', 'display_actual_cost'),
            'description': 'Refleja el costo real basado en el recurso asignado'
        }),
        ('Variaciones (Solo Lectura)', {
            'fields': ('display_cost_variance', 'display_hours_variance', 'display_completion'),
            'classes': ('collapse',)
        }),
        ('Fechas', {
            'fields': ('due_date', 'start_date', 'completion_date')
        }),
        ('Metadatos', {
            'fields': ('tags', 'notes')
        }),
        ('AuditorÃ­a', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def display_planned_value(self, obj):
        return f"${obj.planned_value:,.2f}"
    display_planned_value.short_description = 'Valor Planificado'
    
    def display_actual_cost(self, obj):
        return f"${obj.actual_cost_projection:,.2f}"
    display_actual_cost.short_description = 'Costo Real'
    
    def display_cost_variance(self, obj):
        variance = obj.cost_variance
        color = 'red' if variance > 0 else 'green'
        return f'<span style="color: {color};">${variance:,.2f}</span>'
    display_cost_variance.short_description = 'VariaciÃ³n Costo'
    display_cost_variance.allow_tags = True
    
    def display_hours_variance(self, obj):
        variance = obj.hours_variance
        color = 'red' if variance > 0 else 'green'
        return f'<span style="color: {color};">{variance:.2f}h</span>'
    display_hours_variance.short_description = 'VariaciÃ³n Horas'
    display_hours_variance.allow_tags = True
    
    def display_completion(self, obj):
        pct = obj.completion_percentage
        return f"{pct:.1f}%"
    display_completion.short_description = 'Completitud'
    
    def display_variance(self, obj):
        """Muestra si estÃ¡ sobre/bajo presupuesto."""
        if obj.is_over_budget:
            return 'âš ï¸ Sobre presupuesto'
        return 'âœ… En presupuesto'
    display_variance.short_description = 'Estado'


@admin.register(TimeLog)
class TimeLogAdmin(admin.ModelAdmin):
    list_display = ['task', 'resource', 'date', 'hours', 'display_cost', 'display_billable', 'is_billable']
    list_filter = ['is_billable', 'date', 'task__project', 'resource']
    search_fields = ['task__title', 'resource__first_name', 'resource__last_name', 'description']
    readonly_fields = ['cost', 'billable_amount', 'created_at', 'updated_at']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Registro', {
            'fields': ('task', 'resource', 'date', 'hours')
        }),
        ('DescripciÃ³n', {
            'fields': ('description', 'is_billable')
        }),
        ('Montos Calculados (Solo Lectura)', {
            'fields': ('cost', 'billable_amount'),
            'description': 'Auto-calculados al guardar'
        }),
        ('Notas', {
            'fields': ('notes',)
        }),
        ('AuditorÃ­a', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def display_cost(self, obj):
        return f"${obj.cost:,.2f}"
    display_cost.short_description = 'Costo Interno'
    
    def display_billable(self, obj):
        return f"${obj.billable_amount:,.2f}"
    display_billable.short_description = 'Monto Facturable'


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ['project', 'resource', 'date', 'hours', 'category', 'display_cost', 'display_billable', 'is_billable']
    list_filter = ['is_billable', 'date', 'project', 'category', 'resource']
    search_fields = ['project__name', 'resource__first_name', 'resource__last_name', 'description', 'category']
    readonly_fields = ['cost', 'billable_amount', 'created_at', 'updated_at']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Registro', {
            'fields': ('project', 'resource', 'date', 'hours', 'category')
        }),
        ('DescripciÃ³n', {
            'fields': ('description', 'is_billable')
        }),
        ('Montos Calculados (Solo Lectura)', {
            'fields': ('cost', 'billable_amount'),
            'description': 'Auto-calculados al guardar'
        }),
        ('Notas', {
            'fields': ('notes',)
        }),
        ('AuditorÃ­a', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def display_cost(self, obj):
        return f"${obj.cost:,.2f}"
    display_cost.short_description = 'Costo Interno'
    
    def display_billable(self, obj):
        return f"${obj.billable_amount:,.2f}"
    display_billable.short_description = 'Monto Facturable'


@admin.register(Allocation)
class AllocationAdmin(admin.ModelAdmin):
    '''
    Admin para Asignaciones de Recursos a Proyectos.
    RF-11: Motor de Validación de Asignaciones.
    '''
    list_display = ['resource', 'project', 'start_date', 'end_date', 'hours_per_week', 'is_active']
    list_filter = ['is_active', 'start_date', 'resource__primary_role', 'project__status']
    search_fields = ['resource__first_name', 'resource__last_name', 'project__code', 'project__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Asignación', {
            'fields': ('project', 'resource', 'is_active')
        }),
        ('Periodo', {
            'fields': ('start_date', 'end_date')
        }),
        ('Carga Horaria', {
            'fields': ('hours_per_week',)
        }),
        ('Notas', {
            'fields': ('notes',),
            'description': 'Advertencias de fragmentación se agregarán automáticamente'
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

