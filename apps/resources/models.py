"""
Modelos para la gestión de recursos humanos con lógica financiera dual.
Implementa la separación entre Rol (tarifa estándar) y Recurso (costo interno).
"""
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
from apps.core.models import AuditableModel


class Role(AuditableModel):
    """
    Rol Profesional (ej. Senior Backend Developer, Junior QA).
    Define la tarifa estándar de venta/estimación.
    Se usa para planificación y presupuestos.
    """
    
    SENIORITY_CHOICES = [
        ('entry', 'Entry Level'),
        ('junior', 'Junior'),
        ('mid', 'Mid-Level'),
        ('senior', 'Senior'),
        ('lead', 'Lead'),
        ('principal', 'Principal'),
    ]
    
    CATEGORY_CHOICES = [
        ('management', 'Management'),
        ('technical', 'Technical'),
        ('business_analysis', 'Business Analysis'),
        ('qa', 'QA/Testing'),
        ('design', 'Design'),
        ('operations', 'Operations'),
        ('other', 'Other'),
    ]
    
    # Información del rol
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nombre del Rol",
        help_text="Ej: Senior Backend Developer, Junior QA Engineer"
    )
    
    code = models.CharField(
        max_length=20,
        unique=True,
        blank=False,  # Campo obligatorio
        verbose_name="Código del Rol",
        help_text="Ej: SBE, JQA (obligatorio)"
    )
    
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        verbose_name="Categoría"
    )
    
    seniority = models.CharField(
        max_length=20,
        choices=SENIORITY_CHOICES,
        default='mid',
        verbose_name="Nivel de Seniority"
    )
    
    # --- TARIFA ESTÁNDAR DE VENTA/ESTIMACIÓN ---
    standard_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Tarifa Estándar por Hora (USD)",
        help_text="Tarifa usada para estimaciones y presupuestos al cliente"
    )
    
    # Descripción y habilidades esperadas
    description = models.TextField(
        blank=True,
        verbose_name="Descripción del Rol"
    )
    
    required_skills = models.JSONField(
        default=list,
        verbose_name="Habilidades Requeridas",
        help_text="Lista de habilidades técnicas necesarias para este rol"
    )
    
    # Estado del rol
    is_active = models.BooleanField(
        default=True,
        verbose_name="Rol Activo",
        help_text="Si este rol está disponible para asignación en estimaciones"
    )
    
    # Metadatos
    notes = models.TextField(
        blank=True,
        verbose_name="Notas Internas"
    )

    class Meta:
        verbose_name = "Rol"
        verbose_name_plural = "Roles"
        ordering = ['seniority', 'name']
        indexes = [
            models.Index(fields=['category', 'seniority']),
            models.Index(fields=['code']),
        ]

    def __str__(self):
        return f"{self.name} ({self.code}) - ${self.standard_rate}/hr"
    
    def get_display_name(self) -> str:
        """Retorna nombre completo del rol: 'Senior Developer (SR-DEV-001)'."""
        return f"{self.name} ({self.code})"
    
    def calculate_cost_for_hours(self, hours: Decimal) -> Decimal:
        """Calcula el costo estimado: standard_rate × hours."""
        return self.standard_rate * hours

    def get_seniority_multiplier(self) -> Decimal:
        """Retorna multiplicador según seniority (para cálculos futuros)."""
        multipliers = {
            'junior': Decimal('0.7'),
            'mid': Decimal('1.0'),
            'senior': Decimal('1.3'),
            'lead': Decimal('1.6'),
            'architect': Decimal('2.0'),
            'principal': Decimal('2.5'),
        }
        return multipliers.get(self.seniority, Decimal('1.0'))


class Resource(AuditableModel):
    """
    Recurso Humano (Persona real asignada a proyectos).
    Vinculado a un Rol pero con costo interno específico.
    Se usa para tracking de ejecución real y costos.
    """
    
    STATUS_CHOICES = [
        ('available', 'Disponible'),
        ('partially_allocated', 'Parcialmente Asignado'),
        ('fully_allocated', 'Totalmente Asignado'),
        ('on_leave', 'En Licencia'),
        ('unavailable', 'No Disponible'),
    ]
    
    # --- RELACIÓN CON ROL ---
    primary_role = models.ForeignKey(
        Role,
        on_delete=models.PROTECT,
        related_name='resources',
        verbose_name="Rol Principal",
        help_text="Rol principal del recurso (determina capacidades)"
    )
    
    # Información básica
    employee_id = models.CharField(
        max_length=20,
        unique=True,
        verbose_name="ID de Empleado"
    )
    
    first_name = models.CharField(
        max_length=100,
        verbose_name="Nombre",
        default=''
    )
    
    last_name = models.CharField(
        max_length=100,
        verbose_name="Apellido",
        default=''
    )
    
    email = models.EmailField(
        unique=True,
        verbose_name="Email Corporativo"
    )
    
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name="Teléfono"
    )
    
    # --- COSTO INTERNO REAL ---
    internal_cost = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name="Costo Interno por Hora (USD)",
        help_text="Costo real por hora de este recurso específico (confidencial)"
    )
    
    # Datos de contratación
    hire_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fecha de Contratación"
    )
    
    # Vector de habilidades real (JSONB)
    # Estructura: [{"name": "Python", "level": 5}, {"name": "Django", "level": 4}]
    # Escala: 1-5 donde 5 es experto
    skills_vector = models.JSONField(
        default=list,
        verbose_name="Vector de Habilidades",
        help_text="Lista de habilidades con nivel de competencia (1-5)"
    )
    
    # Certificaciones
    certifications = models.JSONField(
        default=list,
        verbose_name="Certificaciones",
        help_text="Lista de certificaciones profesionales"
    )
    
    # --- INTEGRACIÓN CON QDRANT (Vector Store) ---
    qdrant_point_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        verbose_name="ID en Qdrant",
        help_text="ID del vector embedding de este recurso en Qdrant"
    )
    
    # Estado y disponibilidad
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='available',
        verbose_name="Estado de Disponibilidad"
    )
    
    availability_percentage = models.IntegerField(
        default=100,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name="% Disponibilidad",
        help_text="Porcentaje de tiempo disponible para nuevas asignaciones (0-100%)"
    )
    
    # Información adicional
    bio = models.TextField(
        blank=True,
        verbose_name="Biografía Profesional"
    )
    
    profile_picture = models.ImageField(
        upload_to='resources/profiles/',
        blank=True,
        null=True,
        verbose_name="Foto de Perfil"
    )
    
    location = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Ubicación"
    )
    
    preferred_technologies = models.JSONField(
        default=list,
        verbose_name="Tecnologías Preferidas"
    )
    
    notes = models.TextField(
        blank=True,
        verbose_name="Notas Internas"
    )
    
    # Estado activo
    is_active = models.BooleanField(
        default=True,
        verbose_name="Activo"
    )

    class Meta:
        verbose_name = "Recurso"
        verbose_name_plural = "Recursos"
        ordering = ['last_name', 'first_name']
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['email']),
            models.Index(fields=['status', 'availability_percentage']),
            models.Index(fields=['primary_role', 'is_active']),
            models.Index(fields=['qdrant_point_id']),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.employee_id}) - {self.primary_role.name}"
    
    @property
    def full_name(self) -> str:
        """Retorna nombre completo."""
        return f"{self.first_name} {self.last_name}"
    
    @property
    def effective_rate(self) -> Decimal:
        """Retorna el standard_rate del primary_role."""
        return self.primary_role.standard_rate
    
    @property
    def cost_vs_rate_ratio(self) -> float:
        """Ratio entre costo interno y tarifa de facturación (maneja división por cero)."""
        if self.primary_role.standard_rate > 0:
            return float((self.internal_cost / self.primary_role.standard_rate) * 100)
        return 0.0

    def get_effective_rate(self) -> Decimal:
        """Retorna la tarifa efectiva (del rol principal)."""
        return self.primary_role.standard_rate

    def get_skill_level(self, skill_name: str) -> int:
        """Obtiene el nivel de una habilidad específica."""
        for skill in self.skills_vector:
            if skill.get('name', '').lower() == skill_name.lower():
                return skill.get('level', 0)
        return 0

    def add_skill(self, skill_name: str, level: int):
        """Agrega o actualiza una habilidad."""
        if not (1 <= level <= 5):
            return
        
        # Buscar si ya existe
        for skill in self.skills_vector:
            if skill.get('name', '').lower() == skill_name.lower():
                skill['level'] = level
                self.save(update_fields=['skills_vector', 'updated_at'])
                return
        
        # Si no existe, agregar
        self.skills_vector.append({"name": skill_name, "level": level})
        self.save(update_fields=['skills_vector', 'updated_at'])

    def get_total_skills(self) -> int:
        """Retorna el número total de habilidades."""
        return len(self.skills_vector)

    def get_average_skill_level(self) -> float:
        """Calcula el nivel promedio de habilidades."""
        if not self.skills_vector:
            return 0.0
        total = sum(skill.get('level', 0) for skill in self.skills_vector)
        return total / len(self.skills_vector)

    def is_available_for_allocation(self, required_percentage: int = 50) -> bool:
        """Verifica si el recurso tiene suficiente disponibilidad para asignación."""
        return (
            self.is_active and
            self.status in ['available', 'partially_allocated'] and
            self.availability_percentage >= required_percentage
        )

    def calculate_cost_for_hours(self, hours: Decimal) -> Decimal:
        """Calcula el costo interno real para un número de horas."""
        return self.internal_cost * hours

    def get_cost_vs_rate_ratio(self) -> float:
        """Retorna la relación costo/tarifa en porcentaje (útil para análisis de margen)."""
        if self.primary_role.standard_rate > 0:
            return float((self.internal_cost / self.primary_role.standard_rate) * 100)
        return 0.0
