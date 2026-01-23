# Catálogo de Entidades - SIGRP

> **Sistema Integrado de Gestión de Recursos y Proyectos**  
> Documentación completa de todas las entidades del sistema

---

## Índice

1. [Modelos Base](#modelos-base)
2. [Módulo: Resources](#módulo-resources)
3. [Módulo: Projects](#módulo-projects)
4. [Módulo: Standups](#módulo-standups)
5. [Diagrama de Relaciones](#diagrama-de-relaciones)

---

## Modelos Base

Modelos abstractos heredados por todas las entidades del sistema.

### `TimeStampedModel`

**Tipo**: Modelo abstracto  
**Ubicación**: `apps/core/models.py`

Proporciona auditoría temporal automática.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `created_at` | DateTimeField | Fecha y hora de creación (auto) |
| `updated_at` | DateTimeField | Fecha y hora de última actualización (auto) |

---

### `AuditableModel`

**Tipo**: Modelo abstracto  
**Ubicación**: `apps/core/models.py`  
**Hereda**: `TimeStampedModel`

Auditoría completa con información de usuario.

| Campo | Tipo | Relación | Descripción |
|-------|------|----------|-------------|
| `created_at` | DateTimeField | - | Fecha de creación (heredado) |
| `updated_at` | DateTimeField | - | Última actualización (heredado) |
| `created_by` | ForeignKey | → User | Usuario que creó el registro |
| `updated_by` | ForeignKey | → User | Usuario que actualizó el registro |

---

## Módulo: Resources

Gestión de roles profesionales y recursos humanos.

### `Role`

**Ubicación**: `apps/resources/models.py`  
**Hereda**: `AuditableModel`  
**Propósito**: Define roles profesionales con tarifas estándar para estimación y facturación

#### Campos

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `code` | CharField(20) | Unique | Código único del rol (ej: "SR-DEV-001") |
| `name` | CharField(100) | - | Nombre del rol (ej: "Senior Developer") |
| `category` | CharField(50) | Choices | Categoría profesional |
| `seniority` | CharField(20) | Choices | Nivel de experiencia |
| `standard_rate` | DecimalField(10,2) | >= 0.01 | **Tarifa estándar por hora (USD)** |
| `description` | TextField | Opcional | Descripción detallada del rol |
| `is_active` | BooleanField | Default: True | Estado activo/inactivo |

#### Choices

**Category**:
- `management` - Management
- `technical` - Técnico
- `business_analysis` - Análisis de Negocio
- `qa` - QA/Testing
- `design` - Diseño
- `operations` - Operaciones
- `other` - Otro

**Seniority**:
- `entry` - Entry Level
- `junior` - Junior
- `mid` - Mid-level
- `senior` - Senior
- `lead` - Lead
- `principal` - Principal

#### Métodos

```python
def get_display_name() -> str
    """Retorna nombre completo: 'Senior Developer (SR-DEV-001)'"""

def calculate_cost_for_hours(hours: Decimal) -> Decimal
    """Calcula el costo estimado: standard_rate × hours"""
```

#### Índices

- `(category, seniority)` - Para búsquedas por categoría y nivel
- `(code)` - Para búsquedas rápidas por código

#### Uso

```python
# Crear un rol para estimación
senior_dev = Role.objects.create(
    code="SR-DEV-001",
    name="Senior Developer",
    category="technical",
    seniority="senior",
    standard_rate=150.00  # Para facturar al cliente
)
```

---

### `Resource`

**Ubicación**: `apps/resources/models.py`  
**Hereda**: `AuditableModel`  
**Propósito**: Representa personas reales del equipo con costos internos

#### Campos

| Campo | Tipo | Relación | Restricciones | Descripción |
|-------|------|----------|---------------|-------------|
| `employee_id` | CharField(20) | - | Unique | ID de empleado |
| `first_name` | CharField(100) | - | - | Nombre |
| `last_name` | CharField(100) | - | - | Apellido |
| `email` | EmailField | - | Unique | Email corporativo |
| `phone` | CharField(20) | - | Opcional | Teléfono |
| `primary_role` | ForeignKey | → Role | - | **Rol principal del recurso** |
| `internal_cost` | DecimalField(10,2) | - | >= 0.01 | **Costo interno por hora (USD)** |
| `skills_vector` | JSONField | - | Default: {} | Vector de habilidades (PostgreSQL JSONB) |
| `qdrant_point_id` | CharField(50) | - | Único, Opcional | ID en Qdrant vector store |
| `is_active` | BooleanField | - | Default: True | Estado activo/inactivo |

#### Propiedades Calculadas

```python
@property
def full_name() -> str
    """Retorna nombre completo: 'Juan Pérez'"""

@property
def effective_rate() -> Decimal
    """Retorna el standard_rate del primary_role"""

@property
def cost_vs_rate_ratio() -> float
    """Ratio entre costo interno y tarifa de facturación"""
```

#### Métodos

```python
def get_effective_rate() -> Decimal
    """Obtiene la tarifa del rol primario"""

def calculate_cost_for_hours(hours: Decimal) -> Decimal
    """Calcula el costo interno: internal_cost × hours"""

def get_cost_vs_rate_ratio() -> float
    """Retorna: (internal_cost / role.standard_rate) × 100"""
```

#### Índices

- `(employee_id)` - Para búsquedas por ID de empleado
- `(email)` - Para búsquedas por email
- `(primary_role, is_active)` - Para filtros por rol y estado
- `(qdrant_point_id)` - Para integración con Qdrant

#### Uso

```python
# Crear un recurso real
juan = Resource.objects.create(
    employee_id="EMP-001",
    first_name="Juan",
    last_name="Pérez",
    email="juan.perez@company.com",
    primary_role=senior_dev,
    internal_cost=80.00,  # Costo real para la empresa
    skills_vector={"python": 0.9, "django": 0.85, "react": 0.7}
)

# Calcular ratio de ganancia
ratio = juan.get_cost_vs_rate_ratio()  # 53.33% (80/150)
```

---

## Módulo: Projects

Gestión de proyectos, etapas, tareas e imputación de horas.

### `Project`

**Ubicación**: `apps/projects/models.py`  
**Hereda**: `AuditableModel`  
**Propósito**: Proyecto principal con soporte para Fixed Price y Time & Material

#### Campos Básicos

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `code` | CharField(20) | Unique | Código único (ej: "PRJ-2024-001") |
| `name` | CharField(255) | - | Nombre del proyecto |
| `description` | TextField | - | Descripción detallada |
| `client_name` | CharField(255) | - | Nombre del cliente |
| `client_contact` | CharField(255) | Opcional | Contacto del cliente |
| `client_email` | EmailField | Opcional | Email del cliente |
| `project_type` | CharField(20) | Choices | Tipo de proyecto |
| `status` | CharField(20) | Choices | Estado del proyecto |
| `priority` | CharField(20) | Choices | Prioridad |

#### Campos de Fechas

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `start_date` | DateField | Fecha de inicio |
| `planned_end_date` | DateField | Fecha planeada de fin |
| `actual_end_date` | DateField | Fecha real de fin (opcional) |

#### Campos para Fixed Price

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `budget_limit` | DecimalField(12,2) | >= 0.01, Opcional | Presupuesto límite |
| `fixed_price` | DecimalField(12,2) | >= 0.01, Opcional | Precio acordado con cliente |
| `estimated_hours` | DecimalField(10,2) | >= 0, Opcional | Horas estimadas totales |

#### Campos para Time & Material

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `hourly_rate` | DecimalField(10,2) | >= 0.01, Opcional | Tarifa por hora para facturar |
| `max_budget` | DecimalField(12,2) | >= 0, Opcional | Presupuesto máximo (opcional) |

#### Otros Campos

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `profit_margin_target` | DecimalField(5,2) | 0-100 | Margen de ganancia objetivo (%) |
| `notes` | TextField | Opcional | Notas adicionales |
| `is_active` | BooleanField | Default: True | Estado activo |

#### Choices

**Project Type**:
- `fixed` - Precio Fijo
- `t_and_m` - Time & Material
- `hybrid` - Híbrido

**Status**:
- `planning` - Planificación
- `active` - Activo
- `on_hold` - En Pausa
- `completed` - Completado
- `cancelled` - Cancelado

**Priority**:
- `low` - Baja
- `medium` - Media
- `high` - Alta
- `critical` - Crítica

#### Propiedades Calculadas

```python
@property
def total_logged_hours() -> Decimal
    """Total de horas registradas en TimeEntry"""

@property
def total_cost() -> Decimal
    """Suma de costos internos (entry.cost)"""

@property
def total_billable() -> Decimal
    """Monto total facturable"""

@property
def cost_variance() -> Decimal
    """Diferencia entre presupuesto y costo real"""

@property
def profit_margin() -> float
    """Margen de ganancia porcentual"""

@property
def utilization_rate() -> float
    """% de horas usadas vs. estimadas"""

@property
def is_over_budget() -> bool
    """True si excede el presupuesto"""
```

#### Índices

- `(code)` - Para búsquedas por código
- `(status, is_active)` - Para filtros de estado
- `(project_type)` - Para filtros por tipo
- `(start_date, planned_end_date)` - Para rangos de fecha

---

### `Stage`

**Ubicación**: `apps/projects/models.py`  
**Hereda**: `AuditableModel`  
**Propósito**: Etapas dentro de un proyecto (Discovery, Development, QA, etc.)

#### Campos

| Campo | Tipo | Relación | Restricciones | Descripción |
|-------|------|----------|---------------|-------------|
| `project` | ForeignKey | → Project | - | Proyecto al que pertenece |
| `name` | CharField(200) | - | - | Nombre de la etapa |
| `description` | TextField | - | Opcional | Descripción |
| `order` | IntegerField | - | >= 1 | Orden de ejecución |
| `estimated_hours` | DecimalField(10,2) | - | >= 0 | Horas estimadas |
| `start_date` | DateField | - | Opcional | Fecha de inicio |
| `end_date` | DateField | - | Opcional | Fecha de fin |
| `status` | CharField(20) | - | Choices | Estado |

#### Propiedades Calculadas

```python
@property
def logged_hours() -> Decimal
    """Total de horas de todas las tareas"""

@property
def progress_percentage() -> float
    """% de avance (logged / estimated × 100)"""

@property
def actual_cost() -> Decimal
    """Suma de actual_cost_projection de tareas"""

@property
def planned_value() -> Decimal
    """Suma de planned_value de tareas"""
```

#### Restricciones

- `unique_stage_name_per_project`: (project, name) debe ser único

#### Índices

- `(project, order)` - Para ordenamiento
- `(status)` - Para filtros de estado

---

### `Task`

**Ubicación**: `apps/projects/models.py`  
**Hereda**: `AuditableModel`  
**Propósito**: Tarea individual con lógica dual de costos (Estimación vs. Ejecución)

#### Campos Básicos

| Campo | Tipo | Relación | Descripción |
|-------|------|----------|-------------|
| `stage` | ForeignKey | → Stage | Etapa a la que pertenece |
| `title` | CharField(255) | - | Título de la tarea |
| `description` | TextField | - | Descripción detallada |
| `status` | CharField(20) | - | Estado de la tarea |
| `priority` | CharField(20) | - | Prioridad |

#### Campos de ESTIMACIÓN (Planificación)

| Campo | Tipo | Relación | Descripción |
|-------|------|----------|-------------|
| `estimated_hours` | DecimalField(10,2) | - | **Horas estimadas** |
| `required_role` | ForeignKey | → Role | **Rol requerido (para estimar)** |

#### Campos de EJECUCIÓN (Realidad)

| Campo | Tipo | Relación | Descripción |
|-------|------|----------|-------------|
| `assigned_resource` | ForeignKey | → Resource | **Recurso asignado (persona real)** |
| `logged_hours` | DecimalField(10,2) | - | **Horas reales registradas** (auto) |

#### Otros Campos

| Campo | Tipo | Restricciones | Descripción |
|-------|------|---------------|-------------|
| `due_date` | DateField | Opcional | Fecha límite |
| `completed_date` | DateField | Opcional | Fecha de completado |
| `is_billable` | BooleanField | Default: True | Si se factura al cliente |
| `notes` | TextField | Opcional | Notas adicionales |

#### Propiedades Calculadas (🔥 LÓGICA DUAL)

```python
@property
def planned_value() -> Decimal
    """Valor planeado = estimated_hours × required_role.standard_rate"""

@property
def actual_cost_projection() -> Decimal
    """Costo real = logged_hours × assigned_resource.internal_cost"""

@property
def cost_variance() -> Decimal
    """Diferencia = actual_cost_projection - planned_value"""

@property
def hours_variance() -> Decimal
    """Diferencia en horas = logged_hours - estimated_hours"""

@property
def completion_percentage() -> float
    """% completado = (logged_hours / estimated_hours) × 100"""

@property
def is_over_budget() -> bool
    """True si actual_cost_projection > planned_value"""

@property
def billable_value() -> Decimal
    """Lo que se puede facturar = logged_hours × required_role.standard_rate"""
```

#### Choices

**Status**:
- `backlog` - Backlog
- `todo` - Por Hacer
- `in_progress` - En Progreso
- `in_review` - En Revisión
- `completed` - Completado
- `cancelled` - Cancelado

**Priority**:
- `low` - Baja
- `medium` - Media
- `high` - Alta
- `critical` - Crítica

#### Índices

- `(stage, status)` - Para filtros
- `(assigned_resource, status)` - Para workload
- `(required_role)` - Para búsquedas por rol
- `(due_date)` - Para deadlines

#### Ejemplo de Uso

```python
# Estimación (con Role)
task = Task.objects.create(
    stage=development_stage,
    title="Implementar módulo de pagos",
    estimated_hours=40,
    required_role=senior_dev,  # standard_rate = $150
)
# task.planned_value → 40 × 150 = $6,000

# Asignación (con Resource)
task.assigned_resource = juan  # internal_cost = $80
task.save()

# Después de trabajar (TimeLog actualiza logged_hours)
# task.logged_hours = 45 (auto-actualizado)
# task.actual_cost_projection → 45 × 80 = $3,600
# task.cost_variance → -$2,400 (bajo presupuesto ✅)
# task.billable_value → 45 × 150 = $6,750 (lo que se factura)
```

---

### `TimeLog`

**Ubicación**: `apps/projects/models.py`  
**Hereda**: `AuditableModel`  
**Propósito**: Registro de horas trabajadas en una tarea específica

#### Campos

| Campo | Tipo | Relación | Restricciones | Descripción |
|-------|------|----------|---------------|-------------|
| `task` | ForeignKey | → Task | - | Tarea en la que se trabajó |
| `resource` | ForeignKey | → Resource | - | Recurso que trabajó |
| `date` | DateField | - | - | Fecha del trabajo |
| `hours` | DecimalField(5,2) | - | >= 0.01 | Horas trabajadas |
| `description` | TextField | - | - | Descripción del trabajo |
| `cost` | DecimalField(10,2) | - | Auto | **Costo interno (auto)** |
| `billable_amount` | DecimalField(10,2) | - | Auto | **Monto facturable (auto)** |
| `is_approved` | BooleanField | - | Default: False | Aprobado por PM |
| `is_invoiced` | BooleanField | - | Default: False | Ya facturado |
| `notes` | TextField | - | Opcional | Notas adicionales |

#### Método save() - Auto-cálculo

```python
def save(self, *args, **kwargs):
    """Auto-calcula costos antes de guardar."""
    
    # 1. Calcular costo interno
    self.cost = self.resource.internal_cost × self.hours
    
    # 2. Calcular monto facturable (si la tarea es facturable)
    if self.task.is_billable:
        self.billable_amount = self.task.required_role.standard_rate × self.hours
    else:
        self.billable_amount = 0.00
    
    super().save(*args, **kwargs)
    
    # 3. Actualizar logged_hours en la tarea
    total_hours = self.task.time_logs.aggregate(Sum('hours'))['hours__sum']
    self.task.logged_hours = total_hours or 0.00
    self.task.save(update_fields=['logged_hours', 'updated_at'])
```

#### Índices

- `(task, date)` - Para historial por tarea
- `(resource, date)` - Para historial por recurso
- `(is_approved, is_invoiced)` - Para facturación
- `(date)` - Para reportes temporales

#### Ejemplo de Uso

```python
# Registrar horas de trabajo
time_log = TimeLog.objects.create(
    task=payment_task,
    resource=juan,
    date="2024-01-15",
    hours=8,
    description="Implementación de API de pagos Stripe"
)

# Auto-calculado:
# time_log.cost → 8 × 80 = $640 (costo interno)
# time_log.billable_amount → 8 × 150 = $1,200 (facturable)
# payment_task.logged_hours → actualizado automáticamente
```

---

### `TimeEntry`

**Ubicación**: `apps/projects/models.py`  
**Hereda**: `AuditableModel`  
**Propósito**: Registro de horas trabajadas directamente en el proyecto (sin tarea específica)

#### Campos

| Campo | Tipo | Relación | Restricciones | Descripción |
|-------|------|----------|---------------|-------------|
| `project` | ForeignKey | → Project | - | Proyecto en el que se trabajó |
| `resource` | ForeignKey | → Resource | - | Recurso que trabajó |
| `date` | DateField | - | - | Fecha del trabajo |
| `hours` | DecimalField(5,2) | - | >= 0.01 | Horas trabajadas |
| `description` | TextField | - | - | Descripción del trabajo |
| `task_category` | CharField(100) | - | Opcional | Categoría de tarea |
| `is_billable` | BooleanField | - | Default: True | Si es facturable |
| `is_invoiced` | BooleanField | - | Default: False | Ya facturado |
| `cost` | DecimalField(10,2) | - | Auto | Costo interno |
| `billable_amount` | DecimalField(10,2) | - | Auto | Monto facturable |

#### Método save()

```python
def save(self, *args, **kwargs):
    """Calcula automáticamente el costo al guardar."""
    
    # Calcular costo interno
    self.cost = self.resource.internal_cost × self.hours
    
    # Para T&M, calcular monto facturable
    if self.project.project_type == 't_and_m' and self.is_billable:
        if self.project.hourly_rate:
            self.billable_amount = self.project.hourly_rate × self.hours
        else:
            # Usar el rate del role del recurso
            self.billable_amount = self.resource.primary_role.standard_rate × self.hours
    else:
        self.billable_amount = 0.00
    
    super().save(*args, **kwargs)
```

#### Índices

- `(project, date)` - Para historial por proyecto
- `(resource, date)` - Para historial por recurso
- `(is_billable, is_invoiced)` - Para facturación

---

## Módulo: Standups

Gestión de daily standups con análisis de sentimiento NLP.

### `StandupLog`

**Ubicación**: `apps/standups/models.py`  
**Hereda**: `AuditableModel`  
**Propósito**: Registro de daily standup con análisis de sentimiento automático

#### Campos Básicos

| Campo | Tipo | Relación | Descripción |
|-------|------|----------|-------------|
| `resource` | ForeignKey | → Resource | Recurso que reporta |
| `project` | ForeignKey | → Project | Proyecto relacionado |
| `date` | DateField | - | Fecha del standup |

#### Respuestas del Standup

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `what_i_did` | TextField | ¿Qué hice ayer? |
| `what_i_will_do` | TextField | ¿Qué haré hoy? |
| `blockers` | TextField | Bloqueadores o impedimentos |
| `hours_logged` | DecimalField(4,2) | Horas trabajadas ese día (0-24) |

#### Análisis de Sentimiento (NLP)

| Campo | Tipo | Rango | Descripción |
|-------|------|-------|-------------|
| `sentiment_score` | FloatField | -1.0 a +1.0 | Score de sentimiento |
| `sentiment_label` | CharField(20) | Choices | Etiqueta de sentimiento |
| `sentiment_confidence` | FloatField | 0.0 a 1.0 | Confianza del modelo NLP |
| `detected_entities` | JSONField | - | Entidades detectadas (tecnologías, personas) |
| `keywords` | JSONField | - | Palabras clave extraídas |

#### Indicadores de Riesgo

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `has_blockers` | BooleanField | Tiene bloqueadores (auto) |
| `blocker_severity` | CharField(20) | Severidad: low, medium, high, critical |
| `requires_attention` | BooleanField | Requiere atención del PM (auto) |

#### Metadatos NLP

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `nlp_processed` | BooleanField | Ya procesado por NLP |
| `nlp_processed_at` | DateTimeField | Fecha de procesamiento |
| `notes` | TextField | Notas adicionales |

#### Choices

**Sentiment Label**:
- `positive` - Positivo
- `neutral` - Neutral
- `negative` - Negativo
- `very_negative` - Muy Negativo

**Blocker Severity**:
- `low` - Bajo
- `medium` - Medio
- `high` - Alto
- `critical` - Crítico

#### Métodos

```python
def get_combined_text() -> str:
    """Retorna el texto completo para análisis NLP"""

def determine_sentiment_label() -> str:
    """Determina la etiqueta basada en el score"""

def check_attention_needed() -> bool:
    """Determina si requiere atención del PM"""

def save(self, *args, **kwargs):
    """Auto-calcula flags antes de guardar"""
```

#### Restricciones

- `unique_standup_per_resource_project_date`: Un standup por recurso/proyecto/fecha

#### Índices

- `(resource, date)` - Para historial por recurso
- `(project, date)` - Para historial por proyecto
- `(sentiment_label, requires_attention)` - Para alertas
- `(has_blockers)` - Para detección de bloqueos

#### Ejemplo de Uso

```python
standup = StandupLog.objects.create(
    resource=juan,
    project=payment_project,
    date="2024-01-15",
    what_i_did="Implementé la integración con Stripe",
    what_i_will_do="Probaré los webhooks de pagos",
    blockers="Necesito credenciales de producción",
    hours_logged=8,
    blocker_severity="medium"
)

# Procesamiento NLP (asíncrono con Celery)
from apps.standups.tasks import process_standup_sentiment
process_standup_sentiment.delay(standup.id)

# Después del procesamiento:
# standup.sentiment_score → 0.45 (positivo)
# standup.sentiment_label → 'positive'
# standup.requires_attention → True (tiene bloqueador medium)
```

---

### `TeamMood`

**Ubicación**: `apps/standups/models.py`  
**Hereda**: `AuditableModel`  
**Propósito**: Análisis agregado del mood del equipo por proyecto/fecha

#### Campos

| Campo | Tipo | Relación | Descripción |
|-------|------|----------|-------------|
| `project` | ForeignKey | → Project | Proyecto analizado |
| `date` | DateField | - | Fecha del análisis |
| `average_sentiment` | FloatField | - | Sentimiento promedio del equipo |
| `team_size` | IntegerField | - | Cantidad de standups ese día |

#### Contadores

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `positive_count` | IntegerField | Cantidad de standups positivos |
| `neutral_count` | IntegerField | Cantidad de standups neutrales |
| `negative_count` | IntegerField | Cantidad de standups negativos |
| `blocker_count` | IntegerField | Total de bloqueadores |
| `critical_blocker_count` | IntegerField | Bloqueadores críticos |

#### Análisis de Tendencia

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `trend` | CharField(20) | Tendencia: improving, stable, declining |
| `common_keywords` | JSONField | Keywords más frecuentes del día |
| `alert_level` | CharField(20) | Nivel de alerta: green, yellow, red |

#### Choices

**Trend**:
- `improving` - Mejorando
- `stable` - Estable
- `declining` - Declinando

**Alert Level**:
- `green` - Verde (todo bien)
- `yellow` - Amarillo (precaución)
- `red` - Rojo (atención urgente)

#### Restricciones

- `unique_team_mood_per_project_date`: Un análisis por proyecto/fecha

#### Índices

- `(project, date)` - Para historial
- `(alert_level)` - Para alertas

#### Ejemplo de Uso

```python
# Generar análisis del mood del equipo (tarea Celery)
from apps.standups.tasks import generate_team_mood
generate_team_mood.delay(project_id=1, date="2024-01-15")

# Resultado:
team_mood = TeamMood.objects.get(project=payment_project, date="2024-01-15")
# team_mood.average_sentiment → 0.35 (positivo)
# team_mood.team_size → 5
# team_mood.blocker_count → 2
# team_mood.alert_level → 'yellow' (precaución)
```

---

## Diagrama de Relaciones

```
┌─────────────────────────────────────────────────────────────┐
│                    MÓDULO: RESOURCES                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐                    ┌──────────────┐          │
│  │   Role   │◄───────────────────│   Resource   │          │
│  │          │  primary_role      │              │          │
│  │ standard │                    │ internal_cost│          │
│  │  _rate   │                    │              │          │
│  └──────────┘                    └──────┬───────┘          │
│      ▲                                  │                   │
│      │                                  │                   │
└──────┼──────────────────────────────────┼───────────────────┘
       │                                  │
       │                                  │
┌──────┼──────────────────────────────────┼───────────────────┐
│      │        MÓDULO: PROJECTS          │                   │
├──────┼──────────────────────────────────┼───────────────────┤
│      │                                  │                   │
│      │    ┌──────────┐     ┌───────────▼────┐              │
│      │    │ Project  │     │     Stage      │              │
│      │    │          │────►│                │              │
│      │    │ (Fixed/  │     └───────┬────────┘              │
│      │    │  T&M)    │             │                       │
│      │    └────┬─────┘             │                       │
│      │         │                   │                       │
│      │         │      ┌────────────▼────────┐              │
│      │         │      │       Task          │              │
│      │         │      │                     │              │
│      └─────────┼──────┤ required_role (FK)  │              │
│                │      │ assigned_resource   │──────────────┘
│                │      │     (FK)            │
│                │      │                     │
│                │      │ • estimated_hours   │
│                │      │ • logged_hours      │
│                │      │                     │
│                │      │ @property:          │
│                │      │ • planned_value     │
│                │      │ • actual_cost       │
│                │      │ • cost_variance     │
│                │      └────┬─────────┬──────┘
│                │           │         │
│                │     ┌─────▼────┐ ┌──▼────────┐
│                │     │ TimeLog  │ │TimeEntry  │
│                │     │          │ │           │
│                └────►│ task (FK)│ │project(FK)│
│                      │resource  │ │resource   │
│                      │  (FK)    │ │  (FK)     │
│                      │          │ │           │
│                      │ • cost   │ │ • cost    │
│                      │ • bill_  │ │ • bill_   │
│                      │   amount │ │   amount  │
│                      └──────────┘ └───────────┘
│                                                              │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│                    MÓDULO: STANDUPS                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  Resource ──────►┌──────────────┐◄────── Project           │
│                  │ StandupLog   │                           │
│                  │              │                           │
│                  │ • sentiment  │                           │
│                  │   analysis   │                           │
│                  │ • blockers   │                           │
│                  └──────────────┘                           │
│                         │                                    │
│                         │ aggregation                        │
│                         │                                    │
│                  ┌──────▼───────┐                           │
│                  │  TeamMood    │                           │
│                  │              │                           │
│                  │ • average    │                           │
│                  │   sentiment  │                           │
│                  │ • alert_level│                           │
│                  └──────────────┘                           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Resumen de Relaciones Clave

### Lógica Dual de Costos

```
Estimación (Planificación):
─────────────────────────────
Role.standard_rate → Para calcular planned_value
Task.estimated_hours × required_role.standard_rate = planned_value

Ejecución (Realidad):
─────────────────────
Resource.internal_cost → Para calcular actual_cost
Task.logged_hours × assigned_resource.internal_cost = actual_cost_projection

Facturación:
────────────
TimeLog.billable_amount = hours × task.required_role.standard_rate
```

### Jerarquía de Proyectos

```
Project
  └── Stage (múltiples)
       └── Task (múltiples)
            └── TimeLog (múltiples)
```

### Auditoría y Tracking

Todas las entidades heredan de `AuditableModel`:
- `created_at`, `updated_at` (automático)
- `created_by`, `updated_by` (manual/automático)

---

## Índice de Tablas en Base de Datos

| Tabla | Modelo | Descripción |
|-------|--------|-------------|
| `resources_role` | Role | Roles profesionales |
| `resources_resource` | Resource | Recursos humanos |
| `projects_project` | Project | Proyectos |
| `projects_stage` | Stage | Etapas de proyecto |
| `projects_task` | Task | Tareas |
| `projects_timelog` | TimeLog | Imputación de horas (por tarea) |
| `projects_timeentry` | TimeEntry | Imputación de horas (por proyecto) |
| `standups_standuplog` | StandupLog | Daily standups |
| `standups_teammood` | TeamMood | Mood agregado del equipo |

---

**Última actualización**: 22 de enero de 2026  
**Versión del documento**: 1.0  
**SIGRP**: Sistema Integrado de Gestión de Recursos y Proyectos
