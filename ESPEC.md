# Especificación de Requisitos de Software (SRS)

**Proyecto:** Sistema Integrado de Gestión de Recursos y Proyectos (SIGRP)  
**Versión:** 2.0  
**Fecha Actualización:** 23 de enero de 2026  
**Enfoque:** Monolito Modular en Python (Django + HTMX)

---

## 1. Visión Ejecutiva

El SIGRP es una plataforma de gestión operativa diseñada para resolver la dicotomía entre modelos de contratación **Precio Fijo (Fixed Price)** y **Bolsa de Horas (Time & Materials)**.
A diferencia de herramientas tradicionales (Jira/Trello), el SIGRP integra la dimensión financiera en tiempo real, permitiendo:

1. Calcular rentabilidad real (Margen) contrastando el **Costo del Recurso** vs. la **Tarifa del Rol**.
2. Gestionar el talento mediante **Vectores de Habilidades** y búsqueda semántica (IA).
3. Detectar riesgos invisibles analizando el sentimiento en los *Daily Standups*.
4. Validar capacidad de recursos previniendo sobrecarga mediante **Resource Leveling**.

---

## 2. Arquitectura Tecnológica (Tech Stack)

Siguiendo la restricción de **"Pure Python"**, se elimina la complejidad de frameworks JS externos, centralizando la lógica en el servidor.

### 2.1 Núcleo y Backend

* **Lenguaje:** Python 3.12+
* **Gestor de Dependencias:** `uv` (Astral) para una gestión de entorno ultra-rápida.
* **Framework Principal:** **Django 5.2.10**. Se elige por su ORM robusto y panel de administración, esenciales para manejar las relaciones complejas de las entidades definidas.
* **API/Interacciones:** **HTMX 1.9.10**. Permite interacciones dinámicas (SPA-like) enviando HTML parcial desde el servidor, evitando la necesidad de React/Vue.

### 2.2 Persistencia y Datos

* **Base de Datos Relacional:** **PostgreSQL 15+**.
  - Almacena usuarios, proyectos, finanzas y registros de tiempo.
  - Uso extensivo de `JSONB` para almacenar metadatos flexibles (skills_vector).
  - Configuración: Puerto 5433 (externo) → 5432 (interno en contenedor)

* **Base de Datos Vectorial:** **Qdrant** *(Planificado)*
  - Almacenará los embeddings de las habilidades (`skills_vector`) de los recursos.
  - Permitirá búsquedas por similitud semántica ("Busco experto en datos" → Encuentra "Python + Pandas").
  - **Estado:** Infraestructura preparada, integración pendiente.

### 2.3 Procesamiento Asíncrono e IA

* **Cola de Tareas:** **Celery** + **Redis** *(Planificado)*
  - Encargado de cálculos pesados: Recálculo de EVM nocturno, procesamiento de NLP.

* **NLP Local:** **Sentence-Transformers** (`all-MiniLM-L6-v2`)
  - Para generación de embeddings de habilidades (384 dimensiones)
  - Ejecución local dentro del contenedor para generar embeddings sin depender de APIs externas costosas.
  - **Estado:** Servicio implementado (`VectorService`) listo para integración con Qdrant.

### 2.4 Infraestructura

* **Contenedores:** Docker Compose orquestando:
  - `db` (PostgreSQL 15)
  - `cache` (Redis) - *Planificado*
  - `vector_db` (Qdrant) - *Planificado*

---

## 3. Módulos y Features Detallados

### 3.1 Módulo: Resources (Gestión de Talento)

**Estado:** ✅ **Backend Completo** | ⏳ **Frontend HTMX Parcial**

Centraliza la información del capital humano, separando el "cargo" de la "persona".

#### **RF-01: Taxonomía Dual (Rol vs. Recurso)** ✅ **IMPLEMENTADO**

**Componentes:**
- **Roles (`apps/resources/models.Role`):** Definición de cargos genéricos con:
  - `code`: Código único (ej: "SR-DEV-001")
  - `name`: Nombre del rol (ej: "Senior Backend Developer")
  - `category`: Categoría (management, technical, business_analysis, qa, design, operations, other)
  - `seniority`: Nivel (entry, junior, mid, senior, lead, principal)
  - `standard_rate`: Tarifa de venta/facturación al cliente (USD/hora)
  - `description`: Descripción del rol
  
- **Recursos (`apps/resources/models.Resource`):** Personas reales vinculadas a un Rol con:
  - `employee_id`: ID único del empleado
  - `first_name`, `last_name`: Nombre completo
  - `email`: Email único
  - `primary_role`: FK a Role - rol principal
  - `internal_cost`: Costo real/Salario por hora (USD/hora)
  - `hire_date`: Fecha de contratación
  - `skills_vector`: JSONB con habilidades `[{"name": "Python", "level": 5}, ...]`
  - `qdrant_point_id`: UUID para integración con Qdrant
  - `status`: Estado (available, partially_allocated, fully_allocated, on_leave, unavailable)
  - `availability_percentage`: Disponibilidad (0-100%)

**Valor:** Permite calcular el margen de ganancia exacto por hora trabajada:
```python
margen = (role.standard_rate - resource.internal_cost) / role.standard_rate × 100
```

**Interfaces:**
- ✅ Admin Interface completa con visualización de skills
- ✅ Vistas básicas (list, detail)
- ⏳ Templates HTMX para gestión dinámica de skills

---

#### **RF-02: Matriz de Habilidades Vectorial** ✅ **IMPLEMENTADO**

**Características:**
- Definición de skills con niveles (1-5) en formato JSON
- Conversión automática a narrativa semántica:
  - Nivel 1 → "Novice"
  - Nivel 2 → "Basic knowledge"
  - Nivel 3 → "Intermediate"
  - Nivel 4 → "Advanced"
  - Nivel 5 → "Expert"

**Ejemplo de conversión:**
```json
[
  {"name": "Python", "level": 5},
  {"name": "Django", "level": 5},
  {"name": "React", "level": 3}
]
```
↓
```
"Expert in Python Programming Language. Expert in Django Backend Framework. Intermediate in React Frontend Framework."
```

**Servicio Implementado:**
- `VectorService` (`apps/resources/services.py`) con métodos:
  - `skills_to_narrative()`: Conversión inteligente de JSON a texto
  - `generate_embedding()`: Genera embeddings con `all-MiniLM-L6-v2`
  - `upsert_resource()`: Sincroniza con Qdrant (cuando esté disponible)
  
**Signals Automáticos:**
- ✅ `post_save`: Sincroniza automáticamente con Qdrant al guardar Resource
- ✅ `post_delete`: Elimina de Qdrant al borrar Resource

**Management Command:**
- ✅ `python manage.py sync_resources_qdrant`: Sincronización masiva

---

#### **RF-03: Buscador Semántico de Talento** ⏳ **PARCIALMENTE IMPLEMENTADO**

**Estado Actual:**
- ✅ Backend: `VectorService.search_resources()` implementado
- ⏳ Infraestructura: Qdrant por configurar
- ⏳ Frontend: Barra de búsqueda HTMX pendiente

**Funcionalidad Planificada:**
- Barra de búsqueda con queries en lenguaje natural
- Resultados ordenados por similitud semántica (0-1)
- Filtros: `is_active`, `role_category`, `availability > X%`

**Ejemplo de uso (cuando esté activo):**
```python
results = vector_service.search_resources(
    query="Necesito desarrollador backend Python con Django",
    limit=10,
    filters={"is_active": True}
)
```

---

#### **RF-11: Motor de Validación de Asignaciones (Resource Leveling)** ✅ **IMPLEMENTADO**

**Modelo:** `apps/projects/models.Allocation`

**Características Implementadas:**

1. **Multigestión de Proyectos:**
   - Un `Resource` puede asignarse a múltiples proyectos simultáneamente
   - Cada asignación define: `start_date`, `end_date`, `hours_per_week`

2. **Validación de Capacidad (Overbooking Check):**
   - Antes de confirmar asignación, valida en `clean()`:
   ```python
   # Detecta solapamientos temporales usando Q objects
   overlapping = Allocation.objects.filter(
       resource=self.resource,
       start_date__lte=self.end_date,
       end_date__gte=self.start_date
   ).exclude(pk=self.pk)
   
   # Suma horas semanales
   total_hours = overlapping.aggregate(
       Sum('hours_per_week')
   )['hours_per_week__sum'] or 0
   total_hours += self.hours_per_week
   
   # Validación HARD: Bloquea si excede capacidad
   if total_hours > capacity_weekly:
       raise ValidationError("Sobrecarga detectada")
   ```

3. **Alertas de Fragmentación:**
   - Si el recurso tiene ≥3 proyectos activos concurrentes:
   ```python
   concurrent_projects = overlapping.values('project').distinct().count()
   if concurrent_projects >= 2:
       # Advertencia de Context Switching
       self.notes += "\n⚠️ Penalización por Context Switching (>2 proyectos)"
   ```

4. **Propiedades Calculadas:**
   - `duration_weeks`: Duración en semanas
   - `total_hours_allocated`: Total de horas asignadas
   - `overlaps_with_count`: Número de asignaciones solapadas

5. **UI Reactiva (HTMX):** ⏳ **PENDIENTE**
   - Vista planificada: `/projects/<id>/assign-resources/`
   - Endpoint HTMX: `/projects/check-availability/`
   - Mostrará barra de disponibilidad en tiempo real

**Servicios de Soporte:**
- ✅ `calculate_availability()`: Calcula disponibilidad de un recurso en rango de fechas
- ✅ `get_allocation_recommendations()`: Genera recomendaciones de asignación

**Validaciones Implementadas:**
- Hard Block: `total_hours > capacity_weekly` → `ValidationError`
- Soft Warning: `concurrent_projects >= 3` → Nota en campo `notes`
- Validación temporal: `end_date >= start_date`

---

### 3.2 Módulo: Projects (Gestión Financiera)

**Estado:** ✅ **IMPLEMENTACIÓN COMPLETA**

El corazón del sistema. Controla la ejecución y el presupuesto con arquitectura financiera dual.

#### **RF-04: Soporte Multimodelo** ✅ **IMPLEMENTADO**

**Modelo:** `apps/projects/models.Project`

**Tipos de Proyecto:**

1. **Fixed Price (`fixed`):**
   - `fixed_price`: Precio acordado con cliente (monto fijo)
   - `budget_limit`: Presupuesto interno máximo permitido
   - `estimated_hours`: Horas totales estimadas
   - **Riesgo:** Proveedor (si excedemos horas, perdemos dinero)
   - **Métricas:** `cost_variance`, `profit_margin`, `is_over_budget`

2. **Time & Materials (`t_and_m`):**
   - `hourly_rate`: Tarifa por hora al cliente
   - `max_budget`: Presupuesto máximo estimado (opcional)
   - **Riesgo:** Cliente (paga por todas las horas trabajadas)
   - **Métricas:** `burn_rate`, `total_billable`, `utilization_rate`

3. **Hybrid (`hybrid`):**
   - Combina elementos de ambos modelos
   - Configuración flexible según necesidades del contrato

**Propiedades Calculadas Automáticamente:**
```python
@property
def total_logged_hours():  # Suma TimeLog + TimeEntry
@property
def total_cost():  # Basado en Resource.internal_cost
@property
def total_billable():  # Basado en Role.standard_rate
@property
def profit_margin():  # ((billable - cost) / billable) × 100
@property
def is_over_budget():  # Compara cost vs budget_limit
@property
def completion_percentage():  # % tareas completadas
```

**Estados:** `draft`, `planning`, `active`, `on_hold`, `completed`, `cancelled`

---

#### **RF-05: Jerarquía de Ejecución** ✅ **IMPLEMENTADO**

**Estructura:** `Project` → `Stage` → `Task`

**1. Project (`apps/projects/models.Project`)**
- Nivel superior con configuración financiera
- Contiene etapas y tareas
- Agrega métricas de todas sus etapas y tareas

**2. Stage (`apps/projects/models.Stage`)**
- Agrupa tareas lógicamente (Sprint, Fase, Milestone)
- Campos: `name`, `order`, `estimated_hours`, `start_date`, `end_date`
- Estados: `planned`, `in_progress`, `completed`, `on_hold`
- **Propiedades calculadas:**
  - `total_logged_hours`: Suma de horas de todas las tareas
  - `total_planned_hours`: Suma de horas estimadas
  - `actual_cost`: Suma de costos reales
  - `planned_value`: Suma de valores planificados
  - `progress_percentage`: Avance de la etapa

**3. Task (`apps/projects/models.Task`)**
- Unidad mínima de trabajo
- Vinculada opcionalmente a una Stage
- Implementa **lógica dual de costos** (ver RF-06)
- Estados: `backlog`, `todo`, `in_progress`, `in_review`, `blocked`, `completed`, `cancelled`
- Prioridades: `low`, `medium`, `high`, `critical`

**Beneficios:**
- Permite diagramas de Gantt agrupados por fases
- Facilita tracking de progreso por etapa
- Organización jerárquica clara

**Admin Interface:**
- ✅ `ProjectAdmin` con inline de `Stage`
- ✅ `StageAdmin` con inline de `Task`
- ✅ `TaskAdmin` con inline de `TimeLog`

---

#### **RF-06: Estimación vs. Realidad (Dual Cost Logic)** ✅ **IMPLEMENTADO**

**Modelo:** `apps/projects/models.Task`

**Concepto Central:** Separación entre PLANIFICACIÓN (basada en Roles) y EJECUCIÓN (basada en Recursos reales)

**PLANIFICACIÓN (Role-based):**
```python
# Campos
task.required_role        # FK a Role (define tarifa facturación)
task.estimated_hours      # Horas estimadas

# Cálculo automático (@property)
task.planned_value = estimated_hours × required_role.standard_rate
# → Esto es lo que SE FACTURARÁ al cliente
```

**EJECUCIÓN (Resource-based):**
```python
# Campos
task.assigned_resource    # FK a Resource (define costo interno)
task.logged_hours         # Auto-actualizado por signals

# Cálculo automático (@property)
task.actual_cost_projection = logged_hours × assigned_resource.internal_cost
# → Esto es lo que CUESTA internamente
```

**ANÁLISIS DE VARIACIONES:**
```python
@property
def cost_variance():
    return actual_cost_projection - planned_value
    # Negativo = ganancia, Positivo = pérdida

@property
def hours_variance():
    return logged_hours - estimated_hours
    # Positivo = sobretiempo

@property
def is_over_budget():
    return actual_cost_projection > planned_value
```

**Ejemplo Numérico:**
```python
# Estimación
task.estimated_hours = 40
task.required_role = Role(name="Senior Dev", standard_rate=150)
→ planned_value = 40 × 150 = $6,000

# Ejecución
task.assigned_resource = Resource(name="Juan Pérez", internal_cost=80)
task.logged_hours = 45  # (actualizado por signals)
→ actual_cost_projection = 45 × 80 = $3,600

# Análisis
cost_variance = 3,600 - 6,000 = -$2,400  # ✅ Ganancia!
hours_variance = 45 - 40 = 5h  # ⚠️ Sobretiempo
```

**Modelos de Registro de Tiempo:**

**1. TimeLog (`apps/projects/models.TimeLog`)**
- Vinculado a Task específica + Resource
- Campos: `date`, `hours`, `description`, `is_billable`
- **Auto-calcula en `save()`:**
  ```python
  self.cost = hours × resource.internal_cost
  self.billable_amount = hours × task.required_role.standard_rate
  ```
- **Signal automático:** Actualiza `task.logged_hours` al guardar

**2. TimeEntry (`apps/projects/models.TimeEntry`)**
- Vinculado a Project (no a Task específica)
- Para horas generales: gestión, overhead, reuniones
- **Auto-calcula según tipo de proyecto:**
  ```python
  # Fixed Price: usa role.standard_rate
  # T&M: usa project.hourly_rate
  ```

**Signals Implementados:**
```python
@receiver(post_save, sender='projects.TimeLog')
def update_task_logged_hours_on_save()
    # Recalcula sum(timelog.hours) para la task

@receiver(post_delete, sender='projects.TimeLog')
def update_task_logged_hours_on_delete()
    # Resta horas eliminadas
```

---

#### **RF-07: Métricas EVM Automatizadas** ⏳ **PARCIALMENTE IMPLEMENTADO**

**Estado Actual:**
- ✅ Métricas financieras básicas implementadas
- ⏳ EVM completo (CPI, SPI, EAC, ETC) pendiente

**Métricas Implementadas:**

**Nivel Project:**
- `total_cost`: Costo real acumulado
- `total_billable`: Monto facturable total
- `profit_margin`: Margen de ganancia %
- `cost_variance`: Diferencia presupuesto vs real
- `completion_percentage`: % tareas completadas
- `utilization_rate`: % horas usadas vs estimadas

**Nivel Stage:**
- `actual_cost`: Costo real de la etapa
- `planned_value`: Valor planificado de la etapa
- `progress_percentage`: Avance de la etapa

**Nivel Task:**
- `planned_value`: PV (Planned Value)
- `actual_cost_projection`: AC (Actual Cost)
- `cost_variance`: CV (Cost Variance)
- `hours_variance`: Variación en horas
- `completion_percentage`: % avance

**Métricas EVM Pendientes:**
- ⏳ **CPI** (Cost Performance Index): `EV / AC`
- ⏳ **SPI** (Schedule Performance Index): `EV / PV`
- ⏳ **EAC** (Estimate at Completion): `BAC / CPI`
- ⏳ **ETC** (Estimate to Complete): `EAC - AC`
- ⏳ **VAC** (Variance at Completion): `BAC - EAC`

**Próximos Pasos:**
- Implementar cálculo de Earned Value (EV) basado en % completitud
- Crear dashboard de métricas EVM
- Añadir gráficos de burndown/burnup

---

### 3.3 Módulo: Standups (Inteligencia de Equipo)

**Estado:** ✅ **MODELOS IMPLEMENTADOS** | ⏳ **NLP PENDIENTE**

Transforma reportes diarios en datos procesables.

#### **RF-08: Bitácora de Standups** ✅ **IMPLEMENTADO**

**Modelo:** `apps/standups/models.Standup`

**Campos:**
- `project`: FK a Project (vincula standup con proyecto)
- `resource`: FK a Resource (quien reporta)
- `date`: Fecha del standup
- `what_did`: TextField - "¿Qué hice ayer?"
- `what_will_do`: TextField - "¿Qué haré hoy?"
- `blockers`: TextField - "¿Tengo bloqueos?"
- `mood`: CharField - Estado de ánimo (positive, neutral, negative, frustrated)
- `sentiment_score`: FloatField - Score de sentimiento (-1 a 1)
- `blockers_entities`: JSONField - Entidades extraídas de bloqueos

**Funcionalidad:**
- Formulario para registro diario estructurado
- Vinculación con proyecto y recurso
- Campo de mood manual + análisis automático

**Admin Interface:**
- ✅ Visualización completa de standups
- ✅ Filtros por proyecto, resource, fecha, mood

---

#### **RF-09: Análisis de Sentimiento (NLP)** ⏳ **PENDIENTE**

**Estado:** Modelo preparado, procesamiento NLP por implementar

**Funcionalidad Planificada:**
- Procesamiento automático del texto (`what_did`, `what_will_do`, `blockers`)
- Detección de frustración o señales de "Burnout"
- Cálculo de `sentiment_score` (-1 a 1):
  - `1.0` = Muy positivo
  - `0.0` = Neutral
  - `-1.0` = Muy negativo

**Clasificación de Mood:**
- `positive`: Tono constructivo y motivado
- `neutral`: Reporte factual sin emociones
- `negative`: Tono desanimado
- `frustrated`: Señales de frustración activa

**Tecnología:**
- Sentence-Transformers para análisis de sentimiento
- Modelos pre-entrenados de clasificación de emociones

**Próximos Pasos:**
- Implementar `StandupAnalysisService`
- Crear signal `post_save` para análisis automático
- Añadir dashboard de sentimiento del equipo

---

#### **RF-10: Detección de Bloqueos** ⏳ **PENDIENTE**

**Estado:** Campo `blockers_entities` preparado en modelo

**Funcionalidad Planificada:**
- Extracción automática de entidades del campo `blockers`
- Identificación de:
  - Tecnologías problemáticas (ej: "PostgreSQL", "API de pagos")
  - Dependencias externas bloqueantes (ej: "equipo de diseño", "proveedor X")
  - Recursos faltantes (ej: "acceso a servidor", "credenciales")

**Almacenamiento:**
```json
{
  "technologies": ["PostgreSQL", "Redis"],
  "external_deps": ["Diseño", "Cliente"],
  "resources": ["Credenciales AWS"]
}
```

**Cálculo de TeamMood:**
- Agregación de sentiment_score por proyecto
- Fórmula: `AVG(sentiment_score)` de últimos N días
- Alertas si `team_mood < -0.3` (señal de problemas)

**Próximos Pasos:**
- Implementar Named Entity Recognition (NER)
- Crear vista agregada de bloqueos por proyecto
- Dashboard de TeamMood con tendencias

---

### 3.4 Módulo: Analytics (Métricas y Reportes)

**Estado:** ⏳ **PLANIFICADO**

**Features Futuros:**

#### **RF-12: Dashboard Ejecutivo** ⏳
- Vista consolidada de todos los proyectos
- Métricas financieras agregadas
- Gráficos de rentabilidad por proyecto

#### **RF-13: Reportes de Rentabilidad** ⏳
- Análisis de margen por recurso
- Comparación costo interno vs facturación
- Identificación de recursos más rentables

#### **RF-14: Análisis de Utilización** ⏳
- % de tiempo productivo vs overhead
- Distribución de horas por proyecto
- Identificación de subutilización

#### **RF-15: Forecasting Financiero** ⏳
- Proyección de costos basada en tendencias
- Predicción de fecha de finalización
- Alertas tempranas de sobre-presupuesto

---

## 4. Especificación de Datos (Modelos)

### 4.1 Módulo Resources

#### **Role**
```python
Campos:
- code: CharField(20, unique)
- name: CharField(100, unique)
- category: CharField(choices: management, technical, etc.)
- seniority: CharField(choices: entry, junior, mid, senior, lead, principal)
- standard_rate: DecimalField(10,2)  # USD/hora para facturación
- description: TextField
- is_active: BooleanField

Métodos:
- get_display_name() → str
- calculate_cost_for_hours(hours) → Decimal
```

#### **Resource**
```python
Campos:
- employee_id: CharField(20, unique)
- first_name: CharField(100)
- last_name: CharField(100)
- email: EmailField(unique)
- phone: CharField(20)
- primary_role: ForeignKey(Role)
- internal_cost: DecimalField(10,2)  # Costo real interno USD/hora
- hire_date: DateField
- skills_vector: JSONField  # [{"name": "Python", "level": 5}, ...]
- qdrant_point_id: CharField(100, unique)  # UUID para Qdrant
- status: CharField(choices: available, partially_allocated, etc.)
- availability_percentage: IntegerField(0-100)
- is_active: BooleanField

Propiedades:
- full_name: str
- effective_rate: Decimal
- cost_vs_rate_ratio: float

Métodos:
- calculate_cost_for_hours(hours) → Decimal
- get_skill_level(skill_name) → int
- add_skill(skill_name, level)
```

### 4.2 Módulo Projects

#### **Project**
```python
Campos Comunes:
- code: CharField(20, unique)
- name: CharField(200)
- description: TextField
- client_name: CharField(200)
- project_type: CharField(choices: fixed, t_and_m, hybrid)
- status: CharField(choices: draft, planning, active, on_hold, completed, cancelled)
- start_date: DateField
- planned_end_date: DateField
- actual_end_date: DateField
- profit_margin_target: DecimalField(5,2)

Fixed Price:
- fixed_price: DecimalField(12,2)
- budget_limit: DecimalField(12,2)
- estimated_hours: DecimalField(10,2)

Time & Materials:
- hourly_rate: DecimalField(10,2)
- max_budget: DecimalField(12,2)

Propiedades Calculadas:
- total_logged_hours: Decimal
- total_cost: Decimal
- total_billable: Decimal
- profit_margin: Decimal
- cost_variance: Decimal
- is_over_budget: bool
- completion_percentage: int
- utilization_rate: float
```

#### **Stage**
```python
Campos:
- project: ForeignKey(Project)
- name: CharField(100)
- order: IntegerField
- description: TextField
- estimated_hours: DecimalField(10,2)
- start_date: DateField
- end_date: DateField
- status: CharField(choices: planned, in_progress, completed, on_hold)

Propiedades:
- total_logged_hours: Decimal
- total_planned_hours: Decimal
- actual_cost: Decimal
- planned_value: Decimal
- progress_percentage: int
```

#### **Task**
```python
Campos:
- project: ForeignKey(Project)
- stage: ForeignKey(Stage, null=True)
- title: CharField(200)
- description: TextField
- status: CharField(choices)
- priority: CharField(choices: low, medium, high, critical)
- estimated_hours: DecimalField(10,2)
- logged_hours: DecimalField(10,2, default=0)  # Auto-actualizado
- required_role: ForeignKey(Role)  # Para planificación
- assigned_resource: ForeignKey(Resource, null=True)  # Para ejecución
- due_date: DateField
- completed_date: DateField
- is_billable: BooleanField

Propiedades (Lógica Dual):
- planned_value: Decimal  # estimated_hours × role.standard_rate
- actual_cost_projection: Decimal  # logged_hours × resource.internal_cost
- cost_variance: Decimal  # actual - planned
- hours_variance: Decimal  # logged - estimated
- is_over_budget: bool
- completion_percentage: int
- remaining_hours: Decimal
```

#### **TimeLog**
```python
Campos:
- task: ForeignKey(Task)
- resource: ForeignKey(Resource)
- date: DateField
- hours: DecimalField(5,2)
- description: TextField
- cost: DecimalField(10,2)  # Auto-calculado
- billable_amount: DecimalField(10,2)  # Auto-calculado
- is_billable: BooleanField
- is_approved: BooleanField
- is_invoiced: BooleanField

Cálculos Automáticos (save()):
- cost = hours × resource.internal_cost
- billable_amount = hours × task.required_role.standard_rate
```

#### **TimeEntry**
```python
Campos:
- project: ForeignKey(Project)
- resource: ForeignKey(Resource)
- date: DateField
- hours: DecimalField(5,2)
- description: TextField
- category: CharField(choices: meeting, management, etc.)
- cost: DecimalField(10,2)  # Auto-calculado
- billable_amount: DecimalField(10,2)  # Auto-calculado
- is_billable: BooleanField
```

#### **Allocation** (RF-11)
```python
Campos:
- project: ForeignKey(Project)
- resource: ForeignKey(Resource)
- start_date: DateField
- end_date: DateField
- hours_per_week: DecimalField(5,2)
- notes: TextField
- is_confirmed: BooleanField

Validaciones (clean()):
- Detecta solapamientos temporales
- Calcula total_hours en rango
- Valida contra capacity_weekly
- Alerta si >= 3 proyectos concurrentes

Propiedades:
- duration_weeks: int
- total_hours_allocated: Decimal
- overlaps_with_count: int
```

### 4.3 Módulo Standups

#### **Standup**
```python
Campos:
- project: ForeignKey(Project)
- resource: ForeignKey(Resource)
- date: DateField
- what_did: TextField
- what_will_do: TextField
- blockers: TextField
- mood: CharField(choices: positive, neutral, negative, frustrated)
- sentiment_score: FloatField(-1 a 1)
- blockers_entities: JSONField

Unique Together: (project, resource, date)
```

---

## 5. Estado de Implementación

### ✅ Completado (Backend)
- [x] Módulo Resources (Role, Resource)
- [x] Módulo Projects (Project, Stage, Task, TimeLog, TimeEntry, Allocation)
- [x] Módulo Standups (Standup)
- [x] Lógica financiera dual (Role vs Resource)
- [x] Signals automáticos (logged_hours, Qdrant sync)
- [x] VectorService (sentence-transformers)
- [x] Admin interfaces completas
- [x] Validación de Resource Leveling (RF-11)
- [x] Cálculo automático de métricas financieras

### ⏳ En Progreso
- [ ] Templates HTMX para gestión de skills
- [ ] Interfaz de asignación de recursos con HTMX
- [ ] Vista de disponibilidad de recursos en tiempo real

### 📋 Pendiente
- [ ] Integración completa con Qdrant (infraestructura)
- [ ] Búsqueda semántica de talento (UI)
- [ ] Análisis de sentimiento NLP
- [ ] Detección automática de bloqueos
- [ ] Dashboard ejecutivo
- [ ] Reportes de rentabilidad
- [ ] Métricas EVM completas (CPI, SPI, EAC, ETC)
- [ ] Forecasting financiero
- [ ] Celery + Redis para tareas asíncronas

---

## 6. Próximos Pasos Prioritarios

1. **Completar Interfaz HTMX de Asignación de Recursos**
   - Formulario dinámico de asignación
   - Validación en tiempo real de disponibilidad
   - Barra visual de carga de recurso

2. **Integrar Qdrant**
   - Levantar contenedor Qdrant
   - Sincronizar recursos existentes
   - Habilitar búsqueda semántica

3. **Implementar Análisis de Sentimiento**
   - Service de análisis de standups
   - Extracción de entidades de bloqueos
   - Dashboard de TeamMood

4. **Dashboard Ejecutivo**
   - Vista consolidada de proyectos
   - Métricas financieras agregadas
   - Gráficos de rentabilidad

5. **Métricas EVM Completas**
   - Cálculo de Earned Value
   - Índices CPI y SPI
   - Proyecciones EAC y ETC

---

**Documento actualizado:** 23 de enero de 2026  
**Versión:** 2.0  
**Mantenedor:** Equipo SIGRP



