"""
Admin configuration for Resources app.
"""
from django.contrib import admin
from .models import Role, Resource


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'category', 'seniority', 'standard_rate', 'is_active']
    list_filter = ['category', 'seniority', 'is_active']
    search_fields = ['name', 'code', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('name', 'code', 'category', 'seniority', 'description')
        }),
        ('Información Financiera', {
            'fields': ('standard_rate',)
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Resource)
class ResourceAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'primary_role', 'internal_cost', 'is_active']
    list_filter = ['primary_role', 'is_active']
    search_fields = ['first_name', 'last_name', 'email']
    readonly_fields = ['created_at', 'updated_at', 'full_name']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('first_name', 'last_name', 'email', 'phone')
        }),
        ('Información Profesional', {
            'fields': ('primary_role', 'skills_vector', 'qdrant_point_id')
        }),
        ('Información Financiera', {
            'fields': ('internal_cost',)
        }),
        ('Estado', {
            'fields': ('is_active',)
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
