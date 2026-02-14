"""
Modelos para la gestión de proyectos con lógica financiera dual.
Implementa la separación entre Planificado (Role-based) y Real (Resource-based).
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from decimal import Decimal
from apps.core.models import AuditableModel
from apps.resources.models import Role, Resource


class Project(AuditableModel):
    """
    Proyecto con arquitectura financiera dual: Fixed Price vs Time & Materials.
    
    Fixed Price: Budget fijo, riesgo para el proveedor.
    Time & Materials: Facturación por hora, riesgo para el cliente.
    """
    
    PROJECT_TYPE_CHOICES = [
        ('fixed', 'Fixed Price'),
        ('t_and_m', 'Time & Materials'),
        ('hybrid', 'Hybrid'),
    ]
    
    STATUS_CHOICES = [
        ('draft', 'Borrador'),
        ('planning', 'Planificación'),
        ('active', 'En Ejecución'),
        ('on_hold', 'En Pausa'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('critical', 'Crítica'),
    ]
    
    # Información básica
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="Código del Proyecto",
        help_text="Ej: PRJ-2026-001"
    )
    
    name = models.CharField(
        max_length=200,
        verbose_name="Nombre del Proyecto"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="Descripción"
    )
    
    client_name = models.CharField(
        max_length=200,
        verbose_name="Nombre del Cliente"
    )
    
    # Tipo de proyecto y estado
    project_type = models.CharField(
        max_length=20,
        choices=PROJECT_TYPE_CHOICES,
        default='fixed',
        verbose_name="Tipo de Proyecto"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        verbose_name="Estado"
    )
    
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name="Prioridad"
    )
    
    # --- CONFIGURACIÓN FINANCIERA ---
    
    # Fixed Price: Precio acordado con el cliente
    fixed_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Precio Fijo Acordado (COP)",
        help_text="Solo para proyectos Fixed Price"
    )

    # Fixed Price: Presupuesto interno límite
    budget_limit = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Límite de Presupuesto Interno (COP)",
        help_text="Costo máximo permitido para el proyecto"
    )

    # Time & Materials: Tarifa por hora para el cliente
    hourly_rate = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Tarifa por Hora (COP)",
        help_text="Tarifa aplicada al cliente en proyectos T&M"
    )

    # Time & Materials: Presupuesto máximo estimado
    max_budget = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Presupuesto Máximo Estimado (COP)",
        help_text="Estimación de techo para proyectos T&M"
    )
    
    # Margen de ganancia objetivo
    profit_margin_target = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('30.00'),
        validators=[MinValueValidator(Decimal('0.00')), MaxValueValidator(Decimal('100.00'))],
        verbose_name="Margen de Ganancia Objetivo (%)",
        help_text="Porcentaje de margen esperado"
    )
    
    # Fechas
    start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Inicio"
    )
    
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Fin Estimada"
    )
    
    actual_end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Fin Real"
    )
    
    # Metadatos
    tags = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Etiquetas",
        help_text="Lista de etiquetas para categorización"
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name="Notas Internas"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )

    class Meta:
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['project_type']),
            models.Index(fields=['start_date', 'end_date']),
        ]

    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def clean(self):
        """Validaciones personalizadas."""
        super().clean()
        
        # Validar configuración según tipo de proyecto
        if self.project_type == 'fixed':
            if not self.fixed_price:
                raise ValidationError({
                    'fixed_price': 'Fixed Price projects must have a fixed_price defined.'
                })
            if not self.budget_limit:
                raise ValidationError({
                    'budget_limit': 'Fixed Price projects should have a budget_limit.'
                })
        
        elif self.project_type == 't_and_m':
            if not self.hourly_rate and not self.max_budget:
                raise ValidationError(
                    'Time & Materials projects should have either hourly_rate or max_budget defined.'
                )
        
        # Validar fechas
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValidationError({
                    'end_date': 'End date cannot be before start date.'
                })
    
    # --- PROPIEDADES CALCULADAS (MÉTRICAS FINANCIERAS) ---
    
    @property
    def total_logged_hours(self) -> Decimal:
        """Total de horas registradas en TimeLog y TimeEntry."""
        from django.db.models import Sum
        
        # Horas de TimeLog (asociadas a tareas del proyecto)
        timelog_hours = TimeLog.objects.filter(task__project=self).aggregate(
            total=Sum('hours')
        )['total'] or Decimal('0.00')
        
        # Horas de TimeEntry (asociadas directamente al proyecto)
        timeentry_hours = self.time_entries.aggregate(
            total=Sum('hours')
        )['total'] or Decimal('0.00')
        
        return timelog_hours + timeentry_hours
    
    @property
    def total_cost(self) -> Decimal:
        """
        Costo interno REAL total del proyecto.
        Suma de todos los costos de TimeLog y TimeEntry (basados en Resource.internal_cost).
        """
        from django.db.models import Sum
        
        # Costos de TimeLog (a través de las tareas del proyecto)
        timelog_cost = TimeLog.objects.filter(task__project=self).aggregate(
            total=Sum('cost')
        )['total'] or Decimal('0.00')
        
        # Costos de TimeEntry
        timeentry_cost = self.time_entries.aggregate(
            total=Sum('cost')
        )['total'] or Decimal('0.00')
        
        return timelog_cost + timeentry_cost
    
    @property
    def total_billable(self) -> Decimal:
        """
        Monto FACTURABLE total al cliente.
        Suma de todos los billable_amount de TimeLog y TimeEntry (basados en Role.standard_rate).
        """
        from django.db.models import Sum
        
        # Monto facturable de TimeLog (a través de las tareas del proyecto)
        timelog_billable = TimeLog.objects.filter(task__project=self).aggregate(
            total=Sum('billable_amount')
        )['total'] or Decimal('0.00')
        
        # Monto facturable de TimeEntry
        timeentry_billable = self.time_entries.aggregate(
            total=Sum('billable_amount')
        )['total'] or Decimal('0.00')
        
        return timelog_billable + timeentry_billable
    
    @property
    def profit_margin(self) -> float:
        """
        Margen de ganancia real del proyecto.
        Fórmula: ((total_billable - total_cost) / total_billable) * 100
        """
        if self.total_billable == 0:
            return 0.0
        
        return float(((self.total_billable - self.total_cost) / self.total_billable) * 100)
    
    @property
    def is_over_budget(self) -> bool:
        """Verifica si el proyecto excedió el presupuesto."""
        if self.project_type == 'fixed' and self.budget_limit:
            return self.total_cost > self.budget_limit
        elif self.project_type == 't_and_m' and self.max_budget:
            return self.total_cost > self.max_budget
        return False
    
    @property
    def budget_variance(self) -> Decimal:
        """Diferencia entre presupuesto y costo real."""
        budget = self.budget_limit if self.project_type == 'fixed' else self.max_budget
        if budget:
            return budget - self.total_cost
        return Decimal('0.00')
    
    @property
    def completion_percentage(self) -> float:
        """Porcentaje de completitud basado en tareas."""
        total_tasks = self.tasks.count()
        if total_tasks == 0:
            return 0.0
        
        completed_tasks = self.tasks.filter(status='completed').count()
        return (completed_tasks / total_tasks) * 100


class Stage(AuditableModel):
    """
    Etapa del proyecto (Sprint, Fase, Milestone).
    Agrupa tareas lógicamente.
    """
    
    STATUS_CHOICES = [
        ('planned', 'Planificado'),
        ('in_progress', 'En Progreso'),
        ('completed', 'Completado'),
        ('on_hold', 'En Pausa'),
    ]
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='stages',
        verbose_name="Proyecto"
    )
    
    name = models.CharField(
        max_length=200,
        verbose_name="Nombre de la Etapa",
        help_text="Ej: Sprint 1, Fase de Diseño"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="Descripción"
    )
    
    order = models.IntegerField(
        default=0,
        verbose_name="Orden",
        help_text="Orden de ejecución de la etapa"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='planned',
        verbose_name="Estado"
    )
    
    start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Inicio"
    )
    
    end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Fin"
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name="Notas"
    )

    class Meta:
        verbose_name = "Etapa"
        verbose_name_plural = "Etapas"
        ordering = ['project', 'order', 'name']
        unique_together = [('project', 'name')]
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['project', 'order']),
        ]

    def __str__(self):
        return f"{self.project.code} - {self.name}"
    
    @property
    def total_logged_hours(self) -> Decimal:
        """Total de horas registradas en todas las tareas de esta etapa."""
        from django.db.models import Sum
        return self.tasks.aggregate(total=Sum('logged_hours'))['total'] or Decimal('0.00')
    
    @property
    def total_planned_hours(self) -> Decimal:
        """Total de horas estimadas en todas las tareas de esta etapa."""
        from django.db.models import Sum
        return self.tasks.aggregate(total=Sum('estimated_hours'))['total'] or Decimal('0.00')
    
    @property
    def actual_cost(self) -> Decimal:
        """Costo real acumulado de todas las tareas."""
        total = Decimal('0.00')
        for task in self.tasks.all():
            total += task.actual_cost_projection
        return total
    
    @property
    def planned_value(self) -> Decimal:
        """Valor planeado total de todas las tareas."""
        total = Decimal('0.00')
        for task in self.tasks.all():
            total += task.planned_value
        return total
    
    @property
    def progress_percentage(self) -> float:
        """Porcentaje de progreso basado en horas trabajadas vs estimadas."""
        if self.total_planned_hours == 0:
            return 0.0
        return float((self.total_logged_hours / self.total_planned_hours) * 100)


class Task(AuditableModel):
    """
    Tarea individual con lógica dual de costos.
    
    PLANIFICACIÓN (Lo Estimado):
    - required_role (Role) + estimated_hours → planned_value
    
    EJECUCIÓN (Lo Real):
    - assigned_resource (Resource) + logged_hours → actual_cost_projection
    """
    
    STATUS_CHOICES = [
        ('backlog', 'Backlog'),
        ('todo', 'Por Hacer'),
        ('in_progress', 'En Progreso'),
        ('in_review', 'En Revisión'),
        ('blocked', 'Bloqueado'),
        ('completed', 'Completado'),
        ('cancelled', 'Cancelado'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('critical', 'Crítica'),
    ]
    
    # Relaciones
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name="Proyecto"
    )
    
    stage = models.ForeignKey(
        Stage,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
        verbose_name="Etapa",
        help_text="Etapa a la que pertenece esta tarea"
    )
    
    # Información básica
    title = models.CharField(
        max_length=200,
        verbose_name="Título de la Tarea"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="Descripción"
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='backlog',
        verbose_name="Estado"
    )
    
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name="Prioridad"
    )
    
    # --- PLANIFICACIÓN (ESTIMACIÓN) ---
    
    required_role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name='tasks',
        verbose_name="Rol Requerido",
        help_text="Rol necesario para esta tarea (determina la tarifa de facturación)"
    )
    
    estimated_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Horas Estimadas",
        help_text="Tiempo estimado para completar la tarea"
    )
    
    # --- EJECUCIÓN (REALIDAD) ---
    
    assigned_resource = models.ForeignKey(
        Resource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        verbose_name="Recurso Asignado",
        help_text="Persona real asignada (determina el costo interno)"
    )
    
    logged_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Horas Registradas",
        help_text="Actualizado automáticamente por TimeLog via signals"
    )
    
    # Fechas
    due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Vencimiento"
    )
    
    start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Inicio Real"
    )
    
    completion_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Completitud"
    )
    
    # Metadatos
    tags = models.JSONField(
        default=list,
        blank=True,
        verbose_name="Etiquetas"
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name="Notas"
    )

    class Meta:
        verbose_name = "Tarea"
        verbose_name_plural = "Tareas"
        ordering = ['-priority', 'due_date', 'created_at']
        indexes = [
            models.Index(fields=['project', 'status']),
            models.Index(fields=['project', 'stage']),
            models.Index(fields=['assigned_resource', 'status']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"[{self.project.code}] {self.title}"
    
    def clean(self):
        """Validaciones personalizadas."""
        super().clean()
        
        # Validar que la etapa pertenezca al mismo proyecto
        if self.stage and self.stage.project_id != self.project_id:
            raise ValidationError({
                'stage': 'Stage must belong to the same project as the task.'
            })
    
    # --- PROPIEDADES CALCULADAS (LÓGICA DUAL) ---
    
    @property
    def planned_value(self) -> Decimal:
        """
        VALOR PLANIFICADO (Basado en Rol).
        Fórmula: estimated_hours × required_role.standard_rate
        Esto es lo que SE FACTURARÁ al cliente.
        """
        return self.estimated_hours * self.required_role.standard_rate
    
    @property
    def actual_cost_projection(self) -> Decimal:
        """
        COSTO REAL PROYECTADO (Basado en Recurso).
        Fórmula: logged_hours × assigned_resource.internal_cost
        Esto es lo que CUESTA internamente.
        """
        if not self.assigned_resource:
            return Decimal('0.00')
        return self.logged_hours * self.assigned_resource.internal_cost
    
    @property
    def cost_variance(self) -> Decimal:
        """
        Variación de Costo.
        Fórmula: actual_cost_projection - planned_value
        Positivo = sobre presupuesto, Negativo = bajo presupuesto
        """
        return self.actual_cost_projection - self.planned_value
    
    @property
    def hours_variance(self) -> Decimal:
        """
        Variación de Horas.
        Fórmula: logged_hours - estimated_hours
        """
        return self.logged_hours - self.estimated_hours
    
    @property
    def is_over_budget(self) -> bool:
        """¿Excedió el presupuesto?"""
        return self.actual_cost_projection > self.planned_value
    
    @property
    def completion_percentage(self) -> float:
        """
        Porcentaje de completitud basado en horas.
        Fórmula: (logged_hours / estimated_hours) * 100
        """
        if self.estimated_hours == 0:
            return 0.0
        percentage = float((self.logged_hours / self.estimated_hours) * 100)
        return min(percentage, 100.0)  # Cap at 100%
    
    @property
    def remaining_hours(self) -> Decimal:
        """Horas restantes estimadas."""
        remaining = self.estimated_hours - self.logged_hours
        return max(remaining, Decimal('0.00'))


class TimeLog(AuditableModel):
    """
    Registro de tiempo trabajado en una TAREA específica.
    Auto-calcula cost (interno) y billable_amount (facturación).
    """
    
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='time_logs',
        verbose_name="Tarea"
    )
    
    resource = models.ForeignKey(
        Resource,
        on_delete=models.PROTECT,
        related_name='time_logs',
        verbose_name="Recurso"
    )
    
    date = models.DateField(
        verbose_name="Fecha"
    )
    
    hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Horas Trabajadas"
    )
    
    # --- CAMPOS AUTO-CALCULADOS ---

    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Costo Interno (COP)",
        help_text="Auto-calculado: hours × resource.internal_cost"
    )

    billable_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Monto Facturable (COP)",
        help_text="Auto-calculado: hours × task.required_role.standard_rate"
    )
    
    # Metadata
    description = models.TextField(
        blank=True,
        verbose_name="Descripción del Trabajo",
        help_text="¿Qué se hizo en estas horas?"
    )
    
    is_billable = models.BooleanField(
        default=True,
        verbose_name="Es Facturable",
        help_text="Si es False, no se factura al cliente (overhead interno)"
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name="Notas Internas"
    )

    class Meta:
        verbose_name = "Registro de Tiempo"
        verbose_name_plural = "Registros de Tiempo"
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['task', 'date']),
            models.Index(fields=['resource', 'date']),
            models.Index(fields=['date']),
        ]
    
    # Agregamos una propiedad para acceder al proyecto
    @property
    def project(self):
        """Acceso al proyecto padre a través de la tarea."""
        return self.task.project

    def __str__(self):
        return f"{self.resource.full_name} - {self.hours}h en {self.task.title} ({self.date})"
    
    def clean(self):
        """Validaciones personalizadas."""
        super().clean()
        
        # Validar que las horas sean razonables (max 24h por día)
        if self.hours > 24:
            raise ValidationError({
                'hours': 'Cannot log more than 24 hours in a single day.'
            })
    
    def save(self, *args, **kwargs):
        """
        Sobrescribe save() para auto-calcular cost y billable_amount.
        """
        # Calcular COSTO INTERNO
        self.cost = self.hours * self.resource.internal_cost
        
        # Calcular MONTO FACTURABLE
        if self.is_billable:
            self.billable_amount = self.hours * self.task.required_role.standard_rate
        else:
            self.billable_amount = Decimal('0.00')
        
        super().save(*args, **kwargs)
        
        # Nota: El signal post_save actualizará task.logged_hours automáticamente


class TimeEntry(AuditableModel):
    """
    Entrada de tiempo general al PROYECTO (no asociada a una tarea específica).
    Útil para horas de gestión, overhead, reuniones generales.
    """
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='time_entries',
        verbose_name="Proyecto"
    )
    
    resource = models.ForeignKey(
        Resource,
        on_delete=models.PROTECT,
        related_name='time_entries',
        verbose_name="Recurso"
    )
    
    date = models.DateField(
        verbose_name="Fecha"
    )
    
    hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Horas Trabajadas"
    )
    
    # --- CAMPOS AUTO-CALCULADOS ---

    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Costo Interno (COP)",
        help_text="Auto-calculado: hours × resource.internal_cost"
    )

    billable_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        verbose_name="Monto Facturable (COP)",
        help_text="Auto-calculado según tipo de proyecto"
    )
    
    # Metadata
    description = models.TextField(
        blank=True,
        verbose_name="Descripción del Trabajo"
    )
    
    is_billable = models.BooleanField(
        default=True,
        verbose_name="Es Facturable"
    )
    
    category = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Categoría",
        help_text="Ej: Gestión, Reuniones, Overhead"
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name="Notas"
    )

    class Meta:
        verbose_name = "Entrada de Tiempo"
        verbose_name_plural = "Entradas de Tiempo"
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['project', 'date']),
            models.Index(fields=['resource', 'date']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.resource.full_name} - {self.hours}h en {self.project.name} ({self.date})"
    
    def clean(self):
        """Validaciones personalizadas."""
        super().clean()
        
        # Validar horas razonables
        if self.hours > 24:
            raise ValidationError({
                'hours': 'Cannot log more than 24 hours in a single day.'
            })
    
    def save(self, *args, **kwargs):
        """
        Sobrescribe save() para auto-calcular cost y billable_amount.
        """
        # Calcular COSTO INTERNO
        self.cost = self.hours * self.resource.internal_cost
        
        # Calcular MONTO FACTURABLE según tipo de proyecto
        if self.is_billable:
            if self.project.project_type == 't_and_m' and self.project.hourly_rate:
                # T&M con tarifa definida en el proyecto
                self.billable_amount = self.hours * self.project.hourly_rate
            else:
                # Usar standard_rate del rol principal del recurso
                self.billable_amount = self.hours * self.resource.primary_role.standard_rate
        else:
            self.billable_amount = Decimal('0.00')
        
        super().save(*args, **kwargs)


class Allocation(AuditableModel):
    """
    Asignación de Recurso a Proyecto en un rango temporal.
    
    Permite que un recurso trabaje en múltiples proyectos simultáneamente,
    pero valida matemáticamente contra sobrecarga (burnout) y fragmentación
    (context switching).
    
    RF-11: Motor de Validación de Asignaciones
    """
    
    # Relaciones
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='allocations',
        verbose_name="Proyecto"
    )
    
    resource = models.ForeignKey(
        Resource,
        on_delete=models.CASCADE,
        related_name='allocations',
        verbose_name="Recurso"
    )
    
    # Rango temporal de la asignación
    start_date = models.DateField(
        verbose_name="Fecha de Inicio",
        help_text="Fecha en que inicia la asignación"
    )
    
    end_date = models.DateField(
        verbose_name="Fecha de Fin",
        help_text="Fecha en que termina la asignación"
    )
    
    # Carga horaria
    hours_per_week = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('168.00'))],
        verbose_name="Horas por Semana",
        help_text="Cuántas horas a la semana dedicará a este proyecto (máx 168h = 7×24h)"
    )
    
    # Estado
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activa",
        help_text="Si esta asignación está actualmente vigente"
    )
    
    # Metadatos adicionales
    notes = models.TextField(
        blank=True,
        verbose_name="Notas",
        help_text="Observaciones sobre esta asignación"
    )
    
    class Meta:
        verbose_name = "Asignación"
        verbose_name_plural = "Asignaciones"
        ordering = ['-start_date', 'resource']
        indexes = [
            models.Index(fields=['resource', 'start_date', 'end_date']),
            models.Index(fields=['project', 'start_date']),
            models.Index(fields=['is_active']),
        ]
        
    def __str__(self):
        return f"{self.resource.full_name} → {self.project.code} ({self.hours_per_week}h/sem)"
    
    def clean(self):
        """
        Validación matemática de asignaciones con detección de:
        1. Sobrecarga (Burnout): Total de horas > capacidad semanal
        2. Fragmentación (Context Switching): >2 proyectos concurrentes
        """
        super().clean()
        
        # 1. Validar rango de fechas
        if self.end_date and self.start_date and self.end_date < self.start_date:
            raise ValidationError({
                'end_date': 'La fecha de fin debe ser posterior a la fecha de inicio.'
            })
        
        # 2. Obtener capacidad semanal del recurso (default: 40h)
        capacity_weekly = getattr(self.resource, 'capacity_weekly', Decimal('40.00'))
        
        # 3. Buscar asignaciones solapadas usando Q objects
        from django.db.models import Q, Sum
        
        # Filtrar asignaciones del mismo recurso que se solapen temporalmente
        # Solapamiento: start <= new_end AND end >= new_start
        overlapping_query = Q(
            resource=self.resource,
            is_active=True,
            start_date__lte=self.end_date,
            end_date__gte=self.start_date
        )
        
        # Excluir la asignación actual si estamos editando
        if self.pk:
            overlapping_query &= ~Q(pk=self.pk)
        
        overlapping_allocations = Allocation.objects.filter(overlapping_query)
        
        # 4. Calcular total de horas solapadas
        overlapping_sum = overlapping_allocations.aggregate(
            total=Sum('hours_per_week')
        )['total'] or Decimal('0.00')
        
        total_hours_with_new = overlapping_sum + self.hours_per_week
        
        # 5. HARD BLOCK: Validar sobrecarga (Burnout)
        if total_hours_with_new > capacity_weekly:
            overload = total_hours_with_new - capacity_weekly
            raise ValidationError({
                'hours_per_week': (
                    f'⛔ SOBRECARGA DETECTADA: El recurso {self.resource.full_name} '
                    f'ya tiene {overlapping_sum}h/sem asignadas en el periodo '
                    f'{self.start_date} → {self.end_date}. '
                    f'Agregar {self.hours_per_week}h/sem resultaría en {total_hours_with_new}h/sem, '
                    f'excediendo la capacidad de {capacity_weekly}h/sem por {overload}h. '
                    f'Disponibilidad restante: {capacity_weekly - overlapping_sum}h/sem.'
                )
            })
        
        # 6. SOFT WARNING: Detectar fragmentación (Context Switching)
        # Contar proyectos distintos en asignaciones solapadas
        concurrent_projects = overlapping_allocations.values('project').distinct().count()
        
        # Si ya tiene 2+ proyectos, agregar uno más significa alta fragmentación
        if concurrent_projects >= 2:
            # Django no tiene "warnings" nativos, añadimos al campo notes
            warning_msg = (
                f"⚠️ ALERTA DE FRAGMENTACIÓN: Este recurso ya trabaja en {concurrent_projects} "
                f"proyectos concurrentes durante este periodo. Agregar un proyecto más "
                f"(total: {concurrent_projects + 1}) puede causar Context Switching y "
                f"reducir la eficiencia efectiva hasta un 40%. Se recomienda consolidar asignaciones."
            )
            
            # Agregar warning a notes si no existe
            if warning_msg not in (self.notes or ''):
                self.notes = f"{warning_msg}\n\n{self.notes or ''}".strip()
    
    def save(self, *args, **kwargs):
        """Ejecutar validación antes de guardar."""
        self.clean()
        super().save(*args, **kwargs)
    
    @property
    def duration_weeks(self) -> int:
        """Calcula duración en semanas del periodo de asignación."""
        if self.start_date and self.end_date:
            delta = self.end_date - self.start_date
            return max(1, delta.days // 7)
        return 0
    
    @property
    def total_hours_allocated(self) -> Decimal:
        """Calcula total de horas asignadas en todo el periodo."""
        return self.hours_per_week * Decimal(str(self.duration_weeks))
    
    @property
    def overlaps_with_count(self) -> int:
        """Cuenta cuántas otras asignaciones activas se solapan con esta."""
        from django.db.models import Q
        
        if not self.start_date or not self.end_date:
            return 0
        
        overlapping = Allocation.objects.filter(
            Q(resource=self.resource) &
            Q(is_active=True) &
            Q(start_date__lte=self.end_date) &
            Q(end_date__gte=self.start_date)
        )
        
        if self.pk:
            overlapping = overlapping.exclude(pk=self.pk)
        
        return overlapping.count()
