# Modelos Django - SIGRP
## Resumen de Implementación

> **Fecha**: $(Get-Date)
> **Estado**: ✅ Modelos implementados con lógica de costos dual

---

## 📋 Estructura de Modelos

### 🎭 Actors y Roles (`apps/resources/models.py`)

#### 1. `Role` - Definición de Roles Profesionales
```python
Campos principales:
- name: Nombre del rol (ej: "Senior Developer", "Junior Analyst")
- category: Categoría (management, technical, business_analysis, etc.)
- seniority: Nivel (entry, junior, mid, senior, lead, principal)
- standard_rate: Tarifa estándar por hora (USD) - Para estimación y facturación
- description: Descripción del rol
```

**Propósito**: Define roles estándar para **estimación** y **facturación al cliente**.

#### 2. `Resource` - Personas Reales del Equipo
```python
Campos principales:
- first_name, last_name: Nombre completo
- email: Email único
- primary_role: FK a Role - rol principal
- internal_cost: Costo interno por hora (USD) - Costo real para la empresa
- allocation_percentage: Disponibilidad (0-100%)
- skills_vector: JSONB para habilidades
- qdrant_point_id: ID para integración con Qdrant (vector store)
- is_active: Estado activo/inactivo
```

**Métodos útiles**:
- `get_effective_rate()`: Retorna el rate del rol primario
- `calculate_cost_for_hours(hours)`: Calcula costo interno
- `get_cost_vs_rate_ratio()`: Ratio entre costo interno y tarifa de facturación

**Propósito**: Representa personas reales con sus **costos internos** (salario + overhead).

---

### 📊 Jerarquía de Proyectos (`apps/projects/models.py`)

#### 3. `Project` - Proyecto Principal
```python
Tipo: Fixed Price | Time & Material | Hybrid

Campos Fixed Price:
- budget_limit: Presupuesto límite
- fixed_price: Precio acordado con cliente
- estimated_hours: Horas estimadas totales

Campos T&M:
- hourly_rate: Tarifa por hora para facturar
- max_budget: Presupuesto máximo (opcional)

Métodos @property:
- total_logged_hours: Total de horas registradas
- total_cost: Suma de costos internos
- total_billable: Monto facturable total
- cost_variance: Diferencia entre presupuesto y costo real
- profit_margin: Margen de ganancia
- utilization_rate: % de horas usadas vs estimadas
```

#### 4. `Stage` - Etapas del Proyecto
```python
Estructura: Project → Stage → Task

Campos:
- project: FK a Project
- name: Nombre de la etapa (ej: "Discovery", "Development")
- order: Orden de ejecución
- estimated_hours: Horas estimadas para la etapa
- start_date, end_date: Fechas planeadas
- status: planning | in_progress | completed | cancelled

Métodos @property:
- logged_hours: Total de horas registradas en tareas
- progress_percentage: % de avance
- actual_cost: Costo real acumulado
- planned_value: Valor planeado total
```

#### 5. `Task` - Tareas con Lógica Dual de Costos
```python
Estructura: Stage → Task

⚡ LÓGICA DUAL - CLAVE DEL SISTEMA:

ESTIMACIÓN (Planificación):
- estimated_hours: Horas estimadas
- required_role: FK a Role → usa role.standard_rate
- planned_value = estimated_hours × required_role.standard_rate

EJECUCIÓN (Realidad):
- assigned_resource: FK a Resource → usa resource.internal_cost
- logged_hours: Horas reales registradas (auto-actualizado)
- actual_cost_projection = logged_hours × assigned_resource.internal_cost

Campos de estado:
- status: backlog | todo | in_progress | in_review | completed | cancelled
- priority: low | medium | high | critical
- is_billable: Si se factura al cliente

Métodos @property clave:
- planned_value: Costo planeado basado en Role
- actual_cost_projection: Costo real basado en Resource
- cost_variance: Diferencia (actual - planned)
- hours_variance: Diferencia en horas
- completion_percentage: % de avance
- is_over_budget: Si excede el presupuesto
```

**EJEMPLO PRÁCTICO**:
```python
# Estimación (Planificación con Role)
task.estimated_hours = 40
task.required_role = Role("Senior Developer", standard_rate=150)
task.planned_value → 40 × 150 = $6,000

# Ejecución (Realidad con Resource)
task.assigned_resource = Resource("Juan Pérez", internal_cost=80)
task.logged_hours = 45  # Auto-actualizado por TimeLog
task.actual_cost_projection → 45 × 80 = $3,600

# Análisis
task.cost_variance → 3,600 - 6,000 = -$2,400 (bajo presupuesto ✅)
task.hours_variance → 45 - 40 = 5 horas extras
```

#### 6. `TimeLog` - Imputación de Horas por Tarea
```python
Vincula: Resource + Task + Horas

Campos:
- task: FK a Task
- resource: FK a Resource
- date: Fecha del trabajo
- hours: Horas trabajadas
- description: Descripción del trabajo
- cost: Costo calculado automáticamente
- billable_amount: Monto facturable calculado
- is_approved: Aprobado por PM
- is_invoiced: Ya facturado

Método save() - AUTO-CALCULA:
1. cost = resource.internal_cost × hours
2. billable_amount = task.required_role.standard_rate × hours (si es facturable)
3. Actualiza task.logged_hours (suma total de time_logs)
```

#### 7. `TimeEntry` - Imputación Directa al Proyecto
```python
Vincula: Resource + Project + Horas

Campos similares a TimeLog pero sin vincular a Task específica.
Útil para horas no asignadas a tareas concretas.

Método save() - AUTO-CALCULA:
1. cost = resource.internal_cost × hours
2. billable_amount = project.hourly_rate × hours (para T&M)
```

---

## 🔄 Flujo de Datos

### 1️⃣ Estimación (Fase de Planificación)
```
PM crea Task:
  ↓
Selecciona required_role (ej: "Senior Developer" @ $150/h)
  ↓
Estima estimated_hours (ej: 40 horas)
  ↓
Sistema calcula planned_value = 40 × $150 = $6,000
```

### 2️⃣ Asignación (Fase de Ejecución)
```
PM asigna Task a un Resource:
  ↓
Selecciona assigned_resource (ej: "Juan Pérez" internal_cost = $80/h)
  ↓
Sistema mantiene planned_value pero prepara cálculo de costo real
```

### 3️⃣ Imputación de Horas (Trabajo Real)
```
Resource registra TimeLog:
  ↓
Fecha: 2024-01-15, Horas: 8, Descripción: "Implementación API"
  ↓
Sistema auto-calcula:
  - cost = $80 × 8 = $640
  - billable_amount = $150 × 8 = $1,200
  ↓
Actualiza task.logged_hours (suma total)
  ↓
Task recalcula actual_cost_projection = logged_hours × internal_cost
```

### 4️⃣ Análisis Financiero
```
Task con 45h registradas:
  ↓
planned_value = 40 × $150 = $6,000 (estimación)
actual_cost_projection = 45 × $80 = $3,600 (realidad)
cost_variance = $3,600 - $6,000 = -$2,400 (bajo presupuesto ✅)
  ↓
PM puede facturar hasta $6,750 (45 × $150) pero costó $3,600
Ganancia real = $6,750 - $3,600 = $3,150 (88% margen)
```

---

## 💰 Fórmulas Financieras Clave

### Task Level
```python
# Estimación (Planificación)
planned_value = estimated_hours × required_role.standard_rate

# Ejecución (Realidad)
actual_cost_projection = logged_hours × assigned_resource.internal_cost

# Análisis
cost_variance = actual_cost_projection - planned_value
hours_variance = logged_hours - estimated_hours
completion_percentage = (logged_hours / estimated_hours) × 100
```

### Stage Level
```python
# Agregación de todas las Tasks de la Stage
logged_hours = sum(task.logged_hours for task in stage.tasks.all())
actual_cost = sum(task.actual_cost_projection for task in stage.tasks.all())
planned_value = sum(task.planned_value for task in stage.tasks.all())
```

### Project Level
```python
# Para Fixed Price
total_logged_hours = sum(entry.hours for entry in project.time_entries.all())
total_cost = sum(entry.cost for entry in project.time_entries.all())
cost_variance = budget_limit - total_cost
profit_margin = ((fixed_price - total_cost) / fixed_price) × 100

# Para T&M
total_billable = sum(entry.billable_amount for entry in project.time_entries.all())
profit_margin = ((total_billable - total_cost) / total_billable) × 100
```

---

## ✅ Características Implementadas

### 🎯 Core Features
- [x] Jerarquía Project → Stage → Task
- [x] Lógica dual Role (estimación) vs Resource (ejecución)
- [x] Auto-cálculo de costos en TimeLog.save()
- [x] @property methods para métricas financieras
- [x] Soporte Fixed Price y Time & Material
- [x] Tracking de horas y costos en tiempo real

### 📊 Financial Tracking
- [x] planned_value (basado en Role.standard_rate)
- [x] actual_cost_projection (basado en Resource.internal_cost)
- [x] cost_variance (diferencia entre plan y ejecución)
- [x] hours_variance (sobretiempo/subtiempo)
- [x] profit_margin (margen de ganancia)
- [x] utilization_rate (uso de recursos)

### 🔗 Integraciones
- [x] Qdrant vector store (qdrant_point_id en Resource)
- [x] PostgreSQL JSONB (skills_vector)
- [x] Audit fields (created_at, updated_at, created_by, updated_by)

---

## 🚀 Próximos Pasos

### 1. Migraciones
```bash
python manage.py makemigrations
python manage.py migrate
```

### 2. Admin Interface
Actualizar `resources/admin.py` y `projects/admin.py` con:
- `RoleAdmin`: list_display para category, seniority, standard_rate
- `ResourceAdmin`: inline para mostrar primary_role y internal_cost
- `TaskAdmin`: fieldsets separando "Estimación" y "Ejecución"
- `TimeLogAdmin`: readonly_fields para cost y billable_amount

### 3. Testing
Crear tests para:
- Cálculo de planned_value en Task
- Auto-actualización de logged_hours
- Cálculo de cost_variance
- Validación de datos (horas negativas, etc.)

### 4. Reports
Implementar vistas para:
- Dashboard de proyecto (cost vs budget)
- Reporte de rentabilidad por recurso
- Análisis de variance (cost, hours)
- Timeline de imputaciones

---

## 📚 Glosario

| Término | Definición |
|---------|-----------|
| **Role** | Rol profesional estándar para estimación (usa `standard_rate`) |
| **Resource** | Persona real del equipo (usa `internal_cost`) |
| **standard_rate** | Tarifa por hora para facturar al cliente y estimar |
| **internal_cost** | Costo real por hora para la empresa (salario + overhead) |
| **planned_value** | Valor planeado = `estimated_hours × standard_rate` |
| **actual_cost_projection** | Costo real proyectado = `logged_hours × internal_cost` |
| **cost_variance** | Diferencia entre costo real y planeado |
| **billable_amount** | Monto que se puede facturar al cliente |
| **Fixed Price** | Proyecto con precio fijo acordado |
| **T&M** | Time & Material - se factura por horas trabajadas |

---

## 🔍 Cómo Usar el Sistema

### Ejemplo: Crear un Proyecto Fixed Price

1. **Crear Roles**:
```python
senior_dev = Role.objects.create(
    name="Senior Developer",
    category="technical",
    seniority="senior",
    standard_rate=150.00
)
```

2. **Crear Resources**:
```python
juan = Resource.objects.create(
    first_name="Juan",
    last_name="Pérez",
    email="juan@example.com",
    primary_role=senior_dev,
    internal_cost=80.00,  # Costo real para la empresa
    allocation_percentage=100
)
```

3. **Crear Proyecto**:
```python
project = Project.objects.create(
    code="PRJ-001",
    name="Sistema de Facturación",
    project_type="fixed",
    fixed_price=50000.00,
    budget_limit=45000.00,
    estimated_hours=300,
    start_date="2024-01-01",
    planned_end_date="2024-03-31"
)
```

4. **Crear Stage y Task**:
```python
stage = Stage.objects.create(
    project=project,
    name="Development",
    order=2,
    estimated_hours=120
)

task = Task.objects.create(
    stage=stage,
    title="Implementar módulo de pagos",
    estimated_hours=40,
    required_role=senior_dev,  # Para estimación
    assigned_resource=juan,    # Para ejecución
    status="in_progress"
)

# Sistema calcula automáticamente:
# task.planned_value → 40 × 150 = $6,000
```

5. **Registrar Horas**:
```python
time_log = TimeLog.objects.create(
    task=task,
    resource=juan,
    date="2024-01-15",
    hours=8,
    description="Implementación de API de pagos"
)

# Sistema auto-calcula en save():
# - cost = 80 × 8 = $640
# - billable_amount = 150 × 8 = $1,200
# - Actualiza task.logged_hours
```

6. **Analizar**:
```python
print(f"Horas registradas: {task.logged_hours}h")
print(f"Valor planeado: ${task.planned_value}")
print(f"Costo real: ${task.actual_cost_projection}")
print(f"Variación: ${task.cost_variance}")
print(f"¿Sobre presupuesto?: {task.is_over_budget}")
```

---

**Documentación generada automáticamente**
**SIGRP - Sistema Integrado de Gestión de Recursos y Proyectos**
