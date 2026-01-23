"""
Modelos para Daily Standups con análisis de sentimiento NLP.
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import AuditableModel


class StandupLog(AuditableModel):
    """
    Registro de Daily Standup con análisis de sentimiento.
    Captura: qué hice, qué haré, bloqueadores.
    """
    
    SENTIMENT_CHOICES = [
        ('positive', 'Positivo'),
        ('neutral', 'Neutral'),
        ('negative', 'Negativo'),
        ('very_negative', 'Muy Negativo'),
    ]
    
    # Relaciones
    resource = models.ForeignKey(
        'resources.Resource',
        on_delete=models.CASCADE,
        related_name='standups',
        verbose_name="Recurso"
    )
    
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='standups',
        verbose_name="Proyecto"
    )
    
    # Fecha del standup
    date = models.DateField(verbose_name="Fecha del Standup")
    
    # Respuestas del standup
    what_i_did = models.TextField(
        verbose_name="¿Qué hice ayer?",
        help_text="Resumen de actividades completadas"
    )
    
    what_i_will_do = models.TextField(
        verbose_name="¿Qué haré hoy?",
        help_text="Plan de trabajo para hoy"
    )
    
    blockers = models.TextField(
        blank=True,
        verbose_name="Bloqueadores",
        help_text="Impedimentos o problemas que enfrento"
    )
    
    # Horas trabajadas ese día
    hours_logged = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(24)],
        verbose_name="Horas Trabajadas"
    )
    
    # --- ANÁLISIS DE SENTIMIENTO (NLP) ---
    sentiment_score = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)],
        verbose_name="Score de Sentimiento",
        help_text="Rango: -1 (muy negativo) a +1 (muy positivo)"
    )
    
    sentiment_label = models.CharField(
        max_length=20,
        choices=SENTIMENT_CHOICES,
        null=True,
        blank=True,
        verbose_name="Etiqueta de Sentimiento"
    )
    
    sentiment_confidence = models.FloatField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name="Confianza del Análisis",
        help_text="Nivel de confianza del modelo NLP (0-1)"
    )
    
    # Entidades detectadas por NLP (tecnologías, personas, conceptos)
    detected_entities = models.JSONField(
        default=list,
        verbose_name="Entidades Detectadas",
        help_text="Términos técnicos o conceptos extraídos por NLP"
    )
    
    # Keywords extraídos
    keywords = models.JSONField(
        default=list,
        verbose_name="Palabras Clave",
        help_text="Keywords principales del texto"
    )
    
    # --- INDICADORES DE RIESGO ---
    has_blockers = models.BooleanField(
        default=False,
        verbose_name="Tiene Bloqueadores"
    )
    
    blocker_severity = models.CharField(
        max_length=20,
        choices=[('low', 'Bajo'), ('medium', 'Medio'), ('high', 'Alto'), ('critical', 'Crítico')],
        null=True,
        blank=True,
        verbose_name="Severidad del Bloqueador"
    )
    
    requires_attention = models.BooleanField(
        default=False,
        verbose_name="Requiere Atención",
        help_text="Flag automático si el sentimiento es muy negativo o hay bloqueadores críticos"
    )
    
    # Metadatos del análisis
    nlp_processed = models.BooleanField(
        default=False,
        verbose_name="Procesado por NLP"
    )
    nlp_processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fecha de Procesamiento NLP"
    )
    
    # Notas adicionales
    notes = models.TextField(blank=True, verbose_name="Notas Adicionales")

    class Meta:
        verbose_name = "Standup Log"
        verbose_name_plural = "Standup Logs"
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['resource', 'date']),
            models.Index(fields=['project', 'date']),
            models.Index(fields=['sentiment_label', 'requires_attention']),
            models.Index(fields=['has_blockers']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['resource', 'project', 'date'],
                name='unique_standup_per_resource_project_date'
            )
        ]

    def __str__(self):
        return f"{self.resource.full_name} - {self.project.code} - {self.date}"

    def get_combined_text(self) -> str:
        """Retorna el texto completo para análisis NLP."""
        parts = [self.what_i_did, self.what_i_will_do]
        if self.blockers:
            parts.append(self.blockers)
        return " ".join(parts)

    def determine_sentiment_label(self):
        """Determina la etiqueta de sentimiento basado en el score."""
        if self.sentiment_score is None:
            return None
        
        if self.sentiment_score >= 0.3:
            return 'positive'
        elif self.sentiment_score >= -0.1:
            return 'neutral'
        elif self.sentiment_score >= -0.5:
            return 'negative'
        else:
            return 'very_negative'

    def check_attention_needed(self):
        """Determina si el standup requiere atención del PM."""
        if self.sentiment_label in ['negative', 'very_negative']:
            return True
        if self.has_blockers and self.blocker_severity in ['high', 'critical']:
            return True
        return False

    def save(self, *args, **kwargs):
        """Auto-calcula flags antes de guardar."""
        self.has_blockers = bool(self.blockers.strip())
        
        if self.sentiment_score is not None and not self.sentiment_label:
            self.sentiment_label = self.determine_sentiment_label()
        
        self.requires_attention = self.check_attention_needed()
        
        super().save(*args, **kwargs)


class TeamMood(AuditableModel):
    """
    Análisis agregado de mood del equipo por proyecto/fecha.
    Generado a partir de múltiples StandupLogs.
    """
    
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='team_moods',
        verbose_name="Proyecto"
    )
    
    date = models.DateField(verbose_name="Fecha")
    
    # Métricas agregadas
    average_sentiment = models.FloatField(
        verbose_name="Sentimiento Promedio",
        help_text="Promedio de sentiment_score del equipo"
    )
    
    team_size = models.IntegerField(
        validators=[MinValueValidator(0)],
        verbose_name="Tamaño del Equipo",
        help_text="Cantidad de standups ese día"
    )
    
    positive_count = models.IntegerField(default=0, verbose_name="Standups Positivos")
    neutral_count = models.IntegerField(default=0, verbose_name="Standups Neutrales")
    negative_count = models.IntegerField(default=0, verbose_name="Standups Negativos")
    
    blocker_count = models.IntegerField(default=0, verbose_name="Total de Bloqueadores")
    critical_blocker_count = models.IntegerField(default=0, verbose_name="Bloqueadores Críticos")
    
    # Trend analysis
    trend = models.CharField(
        max_length=20,
        choices=[('improving', 'Mejorando'), ('stable', 'Estable'), ('declining', 'Declinando')],
        null=True,
        blank=True,
        verbose_name="Tendencia"
    )
    
    # Keywords comunes del día
    common_keywords = models.JSONField(
        default=list,
        verbose_name="Keywords Comunes",
        help_text="Keywords más frecuentes en los standups del día"
    )
    
    # Alertas
    alert_level = models.CharField(
        max_length=20,
        choices=[('green', 'Verde'), ('yellow', 'Amarillo'), ('red', 'Rojo')],
        default='green',
        verbose_name="Nivel de Alerta"
    )

    class Meta:
        verbose_name = "Mood del Equipo"
        verbose_name_plural = "Moods del Equipo"
        ordering = ['-date']
        indexes = [
            models.Index(fields=['project', 'date']),
            models.Index(fields=['alert_level']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'date'],
                name='unique_team_mood_per_project_date'
            )
        ]

    def __str__(self):
        return f"{self.project.code} - {self.date} - Sentiment: {self.average_sentiment:.2f}"
