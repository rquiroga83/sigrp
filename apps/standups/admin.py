"""
Admin configuration for Standups app.
"""
from django.contrib import admin
from .models import StandupLog, TeamMood


@admin.register(StandupLog)
class StandupLogAdmin(admin.ModelAdmin):
    list_display = ['resource', 'project', 'date', 'sentiment_label', 'has_blockers', 'requires_attention', 'nlp_processed']
    list_filter = ['sentiment_label', 'has_blockers', 'requires_attention', 'nlp_processed', 'date']
    search_fields = ['resource__full_name', 'project__name', 'what_i_did', 'blockers']
    readonly_fields = ['sentiment_score', 'sentiment_label', 'sentiment_confidence', 'detected_entities', 
                      'keywords', 'nlp_processed', 'nlp_processed_at', 'created_at', 'updated_at']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('resource', 'project', 'date', 'hours_logged')
        }),
        ('Respuestas del Standup', {
            'fields': ('what_i_did', 'what_i_will_do', 'blockers')
        }),
        ('Análisis de Sentimiento', {
            'fields': ('sentiment_score', 'sentiment_label', 'sentiment_confidence', 
                      'detected_entities', 'keywords'),
            'classes': ('collapse',)
        }),
        ('Indicadores de Riesgo', {
            'fields': ('has_blockers', 'blocker_severity', 'requires_attention')
        }),
        ('Procesamiento NLP', {
            'fields': ('nlp_processed', 'nlp_processed_at')
        }),
        ('Notas', {
            'fields': ('notes',)
        }),
        ('Auditoría', {
            'fields': ('created_at', 'updated_at', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['analyze_sentiment']
    
    def analyze_sentiment(self, request, queryset):
        """Acción para re-analizar sentimiento de standups seleccionados."""
        from .tasks import analyze_standup_sentiment
        
        count = 0
        for standup in queryset:
            analyze_standup_sentiment.delay(standup.id)
            count += 1
        
        self.message_user(request, f"{count} standups enviados para análisis de sentimiento.")
    
    analyze_sentiment.short_description = "Analizar sentimiento de standups seleccionados"


@admin.register(TeamMood)
class TeamMoodAdmin(admin.ModelAdmin):
    list_display = ['project', 'date', 'average_sentiment', 'team_size', 'blocker_count', 'alert_level', 'trend']
    list_filter = ['alert_level', 'trend', 'date']
    search_fields = ['project__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'date'
