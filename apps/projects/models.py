"""
Modelos para gestión de proyectos (Fixed Price vs Time & Material).
"""
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal
from apps.core.models import AuditableModel


class Project(AuditableModel):
    """
    Modelo de Proyecto con soporte para Fixed Price y Time & Material.
    """
    
    PROJECT_TYPE_CHOICES = [
        ('fixed', 'Precio Fijo'),
        ('t_and_m', 'Time & Material'),
        ('hybrid', 'Híbrido'),
    ]
    
    STATUS_CHOICES = [
        ('planning', 'Planificación'),
        ('active', 'Activo'),
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
        verbose_name="Código de Proyecto"
    )
    name = models.CharField(max_length=255, verbose_name="Nombre del Proyecto")
    description = models.TextField(verbose_name="Descripción")
    
    # Cliente
    client_name = models.CharField(max_length=255, verbose_name="Cliente")
    client_contact = models.CharField(max_length=255, blank=True, verbose_name="Contacto del Cliente")
    client_email = models.EmailField(blank=True, verbose_name="Email del Cliente")
    
    # Tipo de proyecto
    project_type = models.CharField(
        max_length=20,
        choices=PROJECT_TYPE_CHOICES,
        default='fixed',
        verbose_name="Tipo de Proyecto"
    )
    
    # Fechas
    start_date = models.DateField(verbose_name="Fecha de Inicio")
    planned_end_date = models.DateField(verbose_name="Fecha Planeada de Fin")
    actual_end_date = models.DateField(null=True, blank=True, verbose_name="Fecha Real de Fin")
    
    # Estado y prioridad
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='planning',
        verbose_name="Estado"
    )
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name="Prioridad"
    )
    
    # --- CAMPOS PARA PRECIO FIJO ---
    budget_limit = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Presupuesto Límite (USD)",
        help_text="Para proyectos de precio fijo: límite máximo del presupuesto"
    )
    
    fixed_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Precio Fijo Acordado (USD)",
        help_text="Precio acordado con el cliente para proyectos fixed"
    )
    
    estimated_hours = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Horas Estimadas",
        help_text="Estimación interna de horas para proyectos fixed"
    )
    
    # --- CAMPOS PARA TIME & MATERIAL ---
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Tarifa por Hora (USD)",
        help_text="Tarifa cobrada al cliente por hora trabajada en proyectos T&M"
    )
    
    max_hours_cap = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Tope Máximo de Horas",
        help_text="Límite de horas facturables para proyectos T&M (opcional)"
    )
    
    # --- MÉTRICAS ACTUALES ---
    actual_hours_logged = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Horas Registradas",
        help_text="Total de horas trabajadas registradas"
    )
    
    actual_cost = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Costo Real (USD)",
        help_text="Costo interno acumulado (suma de costos de recursos)"
    )
    
    revenue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Ingresos Facturados (USD)",
        help_text="Total facturado al cliente"
    )
    
    # --- SALUD Y MÉTRICAS DEL PROYECTO ---
    health_score = models.IntegerField(
        default=100,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="Score de Salud",
        help_text="Indicador de salud del proyecto (0-100)"
    )
    
    risk_level = models.CharField(
        max_length=20,
        choices=[('low', 'Bajo'), ('medium', 'Medio'), ('high', 'Alto'), ('critical', 'Crítico')],
        default='low',
        verbose_name="Nivel de Riesgo"
    )
    
    # Tecnologías y equipo
    technologies = models.JSONField(
        default=list,
        verbose_name="Tecnologías Utilizadas",
        help_text="Lista de tecnologías del proyecto"
    )
    
    team_size = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)],
        verbose_name="Tamaño del Equipo"
    )
    
    # Notas y documentación
    notes = models.TextField(blank=True, verbose_name="Notas")
    repository_url = models.URLField(blank=True, verbose_name="URL del Repositorio")
    documentation_url = models.URLField(blank=True, verbose_name="URL de Documentación")
    
    # Estado activo
    is_active = models.BooleanField(default=True, verbose_name="Activo")

    class Meta:
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"
        ordering = ['-start_date']
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['status', 'is_active']),
            models.Index(fields=['project_type']),
            models.Index(fields=['start_date', 'planned_end_date']),
        ]

    def __str__(self):
        return f"[{self.code}] {self.name}"

    def get_budget_consumption_percentage(self) -> float:
        """
        Calcula el % de consumo del presupuesto.
        Para Fixed: actual_cost vs budget_limit
        Para T&M: actual_hours vs max_hours_cap (si existe)
        """
        if self.project_type == 'fixed' and self.budget_limit:
            if self.budget_limit > 0:
                return float((self.actual_cost / self.budget_limit) * 100)
        elif self.project_type == 't_and_m' and self.max_hours_cap:
            if self.max_hours_cap > 0:
                return float((self.actual_hours_logged / self.max_hours_cap) * 100)
        return 0.0

    def get_profitability(self) -> Decimal:
        """
        Calcula la rentabilidad del proyecto.
        Profit = Revenue - Actual Cost
        """
        return self.revenue - self.actual_cost

    def get_profit_margin_percentage(self) -> float:
        """
        Calcula el margen de ganancia en porcentaje.
        Margin = (Revenue - Cost) / Revenue * 100
        """
        if self.revenue > 0:
            profit = self.get_profitability()
            return float((profit / self.revenue) * 100)
        return 0.0

    def is_over_budget(self) -> bool:
        """Verifica si el proyecto está sobre presupuesto."""
        if self.project_type == 'fixed' and self.budget_limit:
            return self.actual_cost > self.budget_limit
        return False

    def is_over_hours_cap(self) -> bool:
        """Verifica si se superó el tope de horas en T&M."""
        if self.project_type == 't_and_m' and self.max_hours_cap:
            return self.actual_hours_logged > self.max_hours_cap
        return False

    def get_estimated_revenue(self) -> Decimal:
        """
        Estima el ingreso del proyecto.
        Fixed: fixed_price
        T&M: actual_hours * hourly_rate
        """
        if self.project_type == 'fixed' and self.fixed_price:
            return self.fixed_price
        elif self.project_type == 't_and_m' and self.hourly_rate:
            return self.actual_hours_logged * self.hourly_rate
        return Decimal('0.00')

    def calculate_completion_percentage(self) -> float:
        """
        Calcula el % de avance basado en horas.
        Fixed: actual_hours / estimated_hours
        T&M: basado en fechas
        """
        if self.project_type == 'fixed' and self.estimated_hours:
            if self.estimated_hours > 0:
                return float((self.actual_hours_logged / self.estimated_hours) * 100)
        
        # Fallback: calcular por fechas
        total_days = (self.planned_end_date - self.start_date).days
        if total_days > 0:
            elapsed_days = (timezone.now().date() - self.start_date).days
            return min(float((elapsed_days / total_days) * 100), 100.0)
        
        return 0.0


class Stage(AuditableModel):
    """
    Etapa de Proyecto (ej. Discovery, Development, Testing, Deployment).
    Los proyectos se dividen en etapas para mejor organización.
    """
    
    STATUS_CHOICES = [
        ('not_started', 'No Iniciada'),
        ('in_progress', 'En Progreso'),
        ('completed', 'Completada'),
        ('on_hold', 'En Pausa'),
        ('cancelled', 'Cancelada'),
    ]
    
    # Relación con proyecto
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='stages',
        verbose_name="Proyecto"
    )
    
    # Información de la etapa
    name = models.CharField(
        max_length=100,
        verbose_name="Nombre de la Etapa"
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
    
    # Fechas
    start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Inicio"
    )
    
    planned_end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha Planeada de Fin"
    )
    
    actual_end_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha Real de Fin"
    )
    
    # Estado
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='not_started',
        verbose_name="Estado"
    )
    
    # Presupuesto de la etapa (opcional)
    estimated_hours_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Horas Estimadas Totales",
        help_text="Suma de horas estimadas de todas las tareas"
    )
    
    # Notas
    notes = models.TextField(
        blank=True,
        verbose_name="Notas"
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activa"
    )

    class Meta:
        verbose_name = "Etapa"
        verbose_name_plural = "Etapas"
        ordering = ['project', 'order', 'start_date']
        indexes = [
            models.Index(fields=['project', 'order']),
            models.Index(fields=['status']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['project', 'name'],
                name='unique_stage_name_per_project'
            )
        ]

    def __str__(self):
        return f"{self.project.code} - {self.name}"

    @property
    def actual_hours_total(self) -> Decimal:
        """Suma de horas registradas en todas las tareas de esta etapa."""
        from django.db.models import Sum
        result = self.tasks.aggregate(total=Sum('logged_hours'))['total']
        return result or Decimal('0.00')

    @property
    def completion_percentage(self) -> float:
        """Porcentaje de completitud basado en tareas."""
        total_tasks = self.tasks.count()
        if total_tasks == 0:
            return 0.0
        completed_tasks = self.tasks.filter(status='completed').count()
        return (completed_tasks / total_tasks) * 100


class Task(AuditableModel):
    """
    Tarea (Unidad de Trabajo).
    Implementa lógica dual: Estimación (Role) vs. Ejecución (Resource).
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pendiente'),
        ('in_progress', 'En Progreso'),
        ('blocked', 'Bloqueada'),
        ('review', 'En Revisión'),
        ('completed', 'Completada'),
        ('cancelled', 'Cancelada'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Baja'),
        ('medium', 'Media'),
        ('high', 'Alta'),
        ('critical', 'Crítica'),
    ]
    
    # Relación con etapa
    stage = models.ForeignKey(
        Stage,
        on_delete=models.CASCADE,
        related_name='tasks',
        verbose_name="Etapa"
    )
    
    # Información de la tarea
    title = models.CharField(
        max_length=255,
        verbose_name="Título de la Tarea"
    )
    
    description = models.TextField(
        blank=True,
        verbose_name="Descripción"
    )
    
    # --- ESTIMACIÓN (Basada en Rol) ---
    required_role = models.ForeignKey(
        'resources.Role',
        on_delete=models.PROTECT,
        related_name='estimated_tasks',
        verbose_name="Rol Requerido",
        help_text="Rol necesario para esta tarea (usado en estimación)"
    )
    
    estimated_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Horas Estimadas",
        help_text="Estimación inicial basada en el rol requerido"
    )
    
    # --- EJECUCIÓN (Basada en Recurso) ---
    assigned_resource = models.ForeignKey(
        'resources.Resource',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        verbose_name="Recurso Asignado",
        help_text="Persona real asignada para ejecutar esta tarea"
    )
    
    logged_hours = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        verbose_name="Horas Registradas",
        help_text="Suma de horas registradas en TimeLog"
    )
    
    # Estado y prioridad
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Estado"
    )
    
    priority = models.CharField(
        max_length=20,
        choices=PRIORITY_CHOICES,
        default='medium',
        verbose_name="Prioridad"
    )
    
    # Fechas
    start_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Inicio"
    )
    
    due_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Vencimiento"
    )
    
    completed_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Completitud"
    )
    
    # Metadatos
    tags = models.JSONField(
        default=list,
        verbose_name="Etiquetas",
        help_text="Tags para categorización"
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name="Notas"
    )
    
    is_billable = models.BooleanField(
        default=True,
        verbose_name="Facturable",
        help_text="Si esta tarea se factura al cliente"
    )

    class Meta:
        verbose_name = "Tarea"
        verbose_name_plural = "Tareas"
        ordering = ['stage', 'priority', 'due_date']
        indexes = [
            models.Index(fields=['stage', 'status']),
            models.Index(fields=['assigned_resource', 'status']),
            models.Index(fields=['required_role']),
            models.Index(fields=['due_date']),
        ]

    def __str__(self):
        return f"{self.stage.project.code} - {self.title}"

    # --- PROPIEDADES CALCULADAS: ESTIMACIÓN ---

    @property
    def planned_value(self) -> Decimal:
        """
        Valor Planificado (Estimación).
        Formula: estimated_hours × required_role.standard_rate
        """
        return self.estimated_hours * self.required_role.standard_rate

    @property
    def planned_cost(self) -> Decimal:
        """
        Alias de planned_value para claridad.
        Representa el costo estimado de esta tarea en la planificación.
        """
        return self.planned_value

    # --- PROPIEDADES CALCULADAS: EJECUCIÓN ---

    @property
    def actual_cost_projection(self) -> Decimal:
        """
        Proyección de Costo Real.
        Formula: logged_hours × assigned_resource.internal_cost
        Retorna 0 si no hay recurso asignado.
        """
        if self.assigned_resource:
            return self.logged_hours * self.assigned_resource.internal_cost
        return Decimal('0.00')

    @property
    def actual_cost(self) -> Decimal:
        """
        Alias de actual_cost_projection.
        Representa el costo real consumido hasta el momento.
        """
        return self.actual_cost_projection

    @property
    def cost_variance(self) -> Decimal:
        """
        Varianza de Costo.
        Formula: actual_cost - planned_value
        Positivo = sobrecosto, Negativo = ahorro
        """
        return self.actual_cost - self.planned_value

    @property
    def hours_variance(self) -> Decimal:
        """
        Varianza de Horas.
        Formula: logged_hours - estimated_hours
        Positivo = más horas usadas, Negativo = menos horas
        """
        return self.logged_hours - self.estimated_hours

    @property
    def completion_percentage(self) -> float:
        """
        Porcentaje de completitud basado en horas.
        Formula: (logged_hours / estimated_hours) × 100
        """
        if self.estimated_hours > 0:
            percentage = float((self.logged_hours / self.estimated_hours) * 100)
            return min(percentage, 100.0)  # Cap at 100%
        return 0.0

    @property
    def is_over_budget(self) -> bool:
        """Indica si la tarea está sobre presupuesto."""
        return self.logged_hours > self.estimated_hours

    @property
    def billable_amount(self) -> Decimal:
        """
        Monto facturable al cliente.
        Formula: logged_hours × required_role.standard_rate
        Solo si is_billable=True
        """
        if self.is_billable:
            return self.logged_hours * self.required_role.standard_rate
        return Decimal('0.00')

    def assign_to_resource(self, resource):
        """Asigna la tarea a un recurso y cambia estado a in_progress."""
        self.assigned_resource = resource
        if self.status == 'pending':
            self.status = 'in_progress'
        self.save(update_fields=['assigned_resource', 'status', 'updated_at'])

    def mark_completed(self):
        """Marca la tarea como completada."""
        self.status = 'completed'
        self.completed_date = timezone.now().date()
        self.save(update_fields=['status', 'completed_date', 'updated_at'])


class TimeLog(AuditableModel):
    """
    Imputación de Horas (Registro de tiempo trabajado).
    Vincula Recurso con Tarea para cálculo preciso de costos.
    """
    
    # Relaciones
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='time_logs',
        verbose_name="Tarea"
    )
    
    resource = models.ForeignKey(
        'resources.Resource',
        on_delete=models.CASCADE,
        related_name='time_logs',
        verbose_name="Recurso"
    )
    
    # Información del registro
    date = models.DateField(
        verbose_name="Fecha",
        help_text="Fecha en que se realizó el trabajo"
    )
    
    hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01')), MaxValueValidator(Decimal('24.00'))],
        verbose_name="Horas",
        help_text="Horas trabajadas (máx 24 por día)"
    )
    
    description = models.TextField(
        verbose_name="Descripción del Trabajo",
        help_text="Qué se hizo en estas horas"
    )
    
    # Costos calculados automáticamente
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Costo Interno (USD)",
        help_text="Costo real: hours × resource.internal_cost (auto-calculado)"
    )
    
    billable_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Monto Facturable (USD)",
        help_text="Monto a cobrar: hours × task.required_role.standard_rate (auto-calculado)"
    )
    
    # Estado de facturación
    is_approved = models.BooleanField(
        default=False,
        verbose_name="Aprobado",
        help_text="Si el registro fue aprobado por el PM"
    )
    
    is_invoiced = models.BooleanField(
        default=False,
        verbose_name="Facturado",
        help_text="Si ya fue incluido en una factura"
    )
    
    # Notas
    notes = models.TextField(
        blank=True,
        verbose_name="Notas"
    )

    class Meta:
        verbose_name = "Registro de Tiempo"
        verbose_name_plural = "Registros de Tiempo"
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['task', 'date']),
            models.Index(fields=['resource', 'date']),
            models.Index(fields=['is_approved', 'is_invoiced']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return f"{self.resource.full_name} - {self.task.title} - {self.date} ({self.hours}h)"

    def save(self, *args, **kwargs):
        """Auto-calcula costos antes de guardar."""
        from decimal import Decimal
        
        # Calcular costo interno (usando internal_cost del Resource)
        self.cost = self.resource.internal_cost * self.hours
        
        # Calcular monto facturable (si la tarea es facturable)
        # Usa el standard_rate del Role asociado a la tarea
        if self.task.is_billable:
            self.billable_amount = self.task.required_role.standard_rate * self.hours
        else:
            self.billable_amount = Decimal('0.00')
        
        super().save(*args, **kwargs)
        
        # Actualizar logged_hours en la tarea
        total_hours = self.task.time_logs.aggregate(
            total=models.Sum('hours')
        )['total'] or Decimal('0.00')
        self.task.logged_hours = total_hours
        self.task.save(update_fields=['logged_hours', 'updated_at'])


class TimeEntry(AuditableModel):
    """
    Registro de tiempo trabajado en un proyecto.
    Fundamental para tracking de horas en ambos tipos de proyecto.
    """
    
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='time_entries',
        verbose_name="Proyecto"
    )
    
    resource = models.ForeignKey(
        'resources.Resource',
        on_delete=models.CASCADE,
        related_name='time_entries',
        verbose_name="Recurso"
    )
    
    # Información del registro
    date = models.DateField(verbose_name="Fecha")
    hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Horas"
    )
    
    # Descripción del trabajo
    description = models.TextField(verbose_name="Descripción del Trabajo")
    task_category = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Categoría de Tarea"
    )
    
    # Estado de facturación
    is_billable = models.BooleanField(
        default=True,
        verbose_name="Facturable",
        help_text="Si estas horas deben facturarse al cliente"
    )
    is_invoiced = models.BooleanField(
        default=False,
        verbose_name="Facturado"
    )
    
    # Cálculos financieros
    cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Costo (USD)",
        help_text="Costo interno (resource hourly_cost * hours)"
    )
    
    billable_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Monto Facturable (USD)",
        help_text="Monto a cobrar al cliente (para T&M)"
    )

    class Meta:
        verbose_name = "Registro de Tiempo"
        verbose_name_plural = "Registros de Tiempo"
        ordering = ['-date', '-created_at']
        indexes = [
            models.Index(fields=['project', 'date']),
            models.Index(fields=['resource', 'date']),
            models.Index(fields=['is_billable', 'is_invoiced']),
        ]

    def __str__(self):
        return f"{self.resource.full_name} - {self.project.code} - {self.date} ({self.hours}h)"

    def save(self, *args, **kwargs):
        """Calcula automáticamente el costo al guardar."""
        from decimal import Decimal
        
        # Calcular costo interno (usando internal_cost del Resource)
        self.cost = self.resource.internal_cost * self.hours
        
        # Para T&M, calcular monto facturable usando el rate del proyecto
        if self.project.project_type == 't_and_m' and self.is_billable:
            if self.project.hourly_rate:
                self.billable_amount = self.project.hourly_rate * self.hours
            else:
                # Si no hay rate definido, usar el rate del role primario del recurso
                self.billable_amount = self.resource.primary_role.standard_rate * self.hours
        else:
            self.billable_amount = Decimal('0.00')
        
        super().save(*args, **kwargs)
