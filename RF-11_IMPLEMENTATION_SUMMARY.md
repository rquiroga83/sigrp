# RF-11: Motor de Validación de Asignaciones - Implementación Completa

## 📋 Resumen

Se implementó exitosamente el **RF-11: Motor de Validación de Asignaciones** que permite asignar recursos a múltiples proyectos simultáneamente con validación matemática contra:

1. **🛑 Sobrecarga (Burnout)**: Hard Block - Impide asignaciones que excedan la capacidad semanal
2. **⚠️ Fragmentación (Context Switching)**: Soft Warning - Alerta cuando hay ≥3 proyectos concurrentes

## 🗂️ Archivos Creados/Modificados

### 1. Modelo de Datos: `apps/projects/models.py`

**Modelo `Allocation` agregado** (líneas 889-1089):

```python
class Allocation(AuditableModel):
    """
    Asignación de Recurso a Proyecto en un rango temporal.
    RF-11: Motor de Validación de Asignaciones
    """
    
    # Relaciones
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    
    # Rango temporal
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Carga horaria
    hours_per_week = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(0.01), MaxValueValidator(168.00)]
    )
    
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)
```

**Validación Matemática en `clean()`**:

```python
def clean(self):
    """
    Validación con detección de:
    1. Sobrecarga (Burnout): Total de horas > capacidad semanal
    2. Fragmentación (Context Switching): >2 proyectos concurrentes
    """
    # 1. Obtener capacidad semanal (default: 40h)
    capacity_weekly = getattr(self.resource, 'capacity_weekly', Decimal('40.00'))
    
    # 2. Buscar asignaciones solapadas con Q objects
    # Solapamiento: start <= new_end AND end >= new_start
    overlapping_query = Q(
        resource=self.resource,
        is_active=True,
        start_date__lte=self.end_date,
        end_date__gte=self.start_date
    )
    
    if self.pk:
        overlapping_query &= ~Q(pk=self.pk)
    
    overlapping_allocations = Allocation.objects.filter(overlapping_query)
    
    # 3. Calcular total de horas solapadas
    overlapping_sum = overlapping_allocations.aggregate(
        total=Sum('hours_per_week')
    )['total'] or Decimal('0.00')
    
    total_hours_with_new = overlapping_sum + self.hours_per_week
    
    # 4. HARD BLOCK: Validar sobrecarga
    if total_hours_with_new > capacity_weekly:
        overload = total_hours_with_new - capacity_weekly
        raise ValidationError({
            'hours_per_week': (
                f'⛔ SOBRECARGA DETECTADA: El recurso {self.resource.full_name} '
                f'ya tiene {overlapping_sum}h/sem asignadas. '
                f'Agregar {self.hours_per_week}h/sem resultaría en {total_hours_with_new}h/sem, '
                f'excediendo la capacidad de {capacity_weekly}h/sem por {overload}h. '
                f'Disponibilidad restante: {capacity_weekly - overlapping_sum}h/sem.'
            )
        })
    
    # 5. SOFT WARNING: Detectar fragmentación
    concurrent_projects = overlapping_allocations.values('project').distinct().count()
    
    if concurrent_projects >= 2:
        warning_msg = (
            f"⚠️ ALERTA DE FRAGMENTACIÓN: Este recurso ya trabaja en {concurrent_projects} "
            f"proyectos concurrentes. Agregar uno más puede causar Context Switching y "
            f"reducir la eficiencia efectiva hasta un 40%."
        )
        if warning_msg not in (self.notes or ''):
            self.notes = f"{warning_msg}\n\n{self.notes or ''}".strip()
```

**Properties útiles**:

```python
@property
def duration_weeks(self) -> int:
    """Calcula duración en semanas."""
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
    """Cuenta cuántas otras asignaciones activas se solapan."""
    # ... implementación
```

---

### 2. Servicio de Disponibilidad: `apps/projects/services.py` (NUEVO)

**Función `calculate_availability()`**:

```python
def calculate_availability(
    resource_id: int,
    start_date: date,
    end_date: date
) -> Dict[str, Any]:
    """
    Calcula la disponibilidad de un recurso en un rango temporal.
    
    Returns:
        Dict con:
        - total_allocated_hours: Horas ya ocupadas (por semana)
        - remaining_capacity: Horas libres disponibles
        - capacity_weekly: Capacidad total semanal
        - active_project_count: Cantidad de proyectos concurrentes
        - concurrent_projects: Lista de proyectos concurrentes
        - is_fragmented: True si tiene >= 3 proyectos
        - utilization_percentage: % de utilización (0-100+)
        - status: 'available', 'partial', 'full', 'overloaded'
        - can_allocate_hours: Horas máximas asignables sin sobrecarga
    """
    # Buscar asignaciones activas que se solapen
    overlapping_allocations = Allocation.objects.filter(
        resource=resource,
        is_active=True,
        start_date__lte=end_date,
        end_date__gte=start_date
    )
    
    # Calcular total de horas asignadas
    total_allocated = overlapping_allocations.aggregate(
        total=Sum('hours_per_week')
    )['total'] or Decimal('0.00')
    
    # Calcular disponibilidad
    remaining_capacity = capacity_weekly - total_allocated
    
    # Contar proyectos concurrentes
    active_project_count = overlapping_allocations.values(
        'project__pk'
    ).distinct().count()
    
    # Detectar fragmentación
    is_fragmented = active_project_count >= 3
    
    # ... más cálculos
```

**Función `get_allocation_recommendations()`**:

```python
def get_allocation_recommendations(
    resource_id: int,
    requested_hours: Decimal,
    start_date: date,
    end_date: date
) -> Dict[str, Any]:
    """
    Analiza si una asignación propuesta es viable y genera recomendaciones.
    
    Returns:
        Dict con:
        - is_viable: True si la asignación es posible
        - block_reason: Motivo de bloqueo si is_viable=False
        - warnings: Lista de advertencias
        - recommendations: Lista de recomendaciones
        - availability: Resultado de calculate_availability
        - projected_utilization: % de utilización proyectada
    """
    availability = calculate_availability(resource_id, start_date, end_date)
    
    # Verificar sobrecarga
    total_with_new = availability['total_allocated_hours'] + requested_hours
    
    if total_with_new > availability['capacity_weekly']:
        is_viable = False
        overload = total_with_new - availability['capacity_weekly']
        block_reason = f"⛔ SOBRECARGA: Exceso de {overload}h/sem"
        # ... más lógica
    
    # Advertencia de fragmentación
    if availability['active_project_count'] >= 2:
        warnings.append("⚠️ FRAGMENTACIÓN: Alto riesgo de Context Switching")
    
    # ... más validaciones
```

---

### 3. Vista HTMX: `apps/projects/views.py`

**Imports agregados**:

```python
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from datetime import datetime
from decimal import Decimal
from .models import Allocation
from .services import calculate_availability, get_allocation_recommendations
```

**Vista `check_resource_availability()`** (líneas 104-203):

```python
@require_http_methods(["GET"])
def check_resource_availability(request):
    """
    Vista HTMX que retorna un fragmento HTML con la disponibilidad del recurso.
    
    RF-11: Chequeo en tiempo real de disponibilidad.
    
    Query Params:
        - resource: ID del recurso
        - start: Fecha de inicio (YYYY-MM-DD)
        - end: Fecha de fin (YYYY-MM-DD)
        - hours: (Opcional) Horas por semana solicitadas
    
    Returns:
        HTML fragment con:
        - Barra de progreso (verde < 80%, amarilla 80-99%, roja > 100%)
        - Alertas de fragmentación si is_fragmented=True
        - Detalles de disponibilidad
    """
    # 1. Obtener parámetros
    resource_id = request.GET.get('resource')
    start_date_str = request.GET.get('start')
    end_date_str = request.GET.get('end')
    requested_hours_str = request.GET.get('hours', '0')
    
    # 2. Validar parámetros
    if not all([resource_id, start_date_str, end_date_str]):
        return render(request, 'projects/partials/availability_check.html', {
            'error': 'Parámetros incompletos'
        })
    
    # 3. Parsear datos
    try:
        resource_id = int(resource_id)
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        requested_hours = Decimal(requested_hours_str) if requested_hours_str else Decimal('0.00')
    except (ValueError, TypeError) as e:
        return render(request, 'projects/partials/availability_check.html', {
            'error': f'Error en formato de datos: {str(e)}'
        })
    
    # 4. Calcular disponibilidad
    if requested_hours > 0:
        result = get_allocation_recommendations(
            resource_id, requested_hours, start_date, end_date
        )
        availability = result['availability']
        # ... más datos
    else:
        availability = calculate_availability(resource_id, start_date, end_date)
    
    # 5. Determinar color de barra
    if projected_utilization >= 100:
        bar_color = 'danger'
    elif projected_utilization >= 80:
        bar_color = 'warning'
    else:
        bar_color = 'success'
    
    # 6. Renderizar fragmento
    return render(request, 'projects/partials/availability_check.html', {
        'availability': availability,
        'is_viable': is_viable,
        'bar_color': bar_color,
        # ... más contexto
    })
```

---

### 4. Template HTMX: `apps/projects/templates/projects/partials/availability_check.html` (NUEVO)

**Fragmento HTML reactivo**:

```django
<!-- Header con nombre y estado -->
<div class="d-flex justify-content-between align-items-center mb-3">
    <h6 class="mb-0">
        <i class="bi bi-person-check me-2"></i>
        <strong>{{ availability.resource_name }}</strong>
    </h6>
    <span class="badge bg-{{ status_color }}">
        {{ availability.status }}
    </span>
</div>

<!-- Barra de Progreso -->
<div class="mb-3">
    <div class="d-flex justify-content-between align-items-center mb-1">
        <small class="text-muted">Utilización Semanal</small>
        <strong class="text-{{ bar_color }}">{{ projected_utilization }}%</strong>
    </div>
    <div class="progress" style="height: 20px;">
        <div class="progress-bar {{ bar_class }} progress-bar-striped 
            {% if projected_utilization >= 100 %}progress-bar-animated{% endif %}"
             style="width: {{ projected_utilization }}%">
            {{ projected_utilization }}%
        </div>
    </div>
</div>

<!-- Detalles de Capacidad -->
<div class="row g-2 mb-3">
    <div class="col-4">
        <div class="text-center p-2 bg-light rounded">
            <small class="text-muted d-block">Capacidad</small>
            <strong>{{ availability.capacity_weekly }}h</strong>
        </div>
    </div>
    <div class="col-4">
        <div class="text-center p-2 bg-light rounded">
            <small class="text-muted d-block">Asignadas</small>
            <strong>{{ availability.total_allocated_hours }}h</strong>
        </div>
    </div>
    <div class="col-4">
        <div class="text-center p-2 bg-light rounded">
            <small class="text-muted d-block">Disponibles</small>
            <strong class="text-success">{{ availability.remaining_capacity }}h</strong>
        </div>
    </div>
</div>

<!-- HARD BLOCK: Error de Sobrecarga -->
{% if block_reason %}
<div class="alert alert-danger mb-2">
    <i class="bi bi-x-circle me-2"></i>
    <strong>Asignación Bloqueada</strong>
    <p class="mb-0 mt-1 small">{{ block_reason }}</p>
</div>
{% endif %}

<!-- SOFT WARNING: Alertas de Fragmentación -->
{% if warnings %}
    {% for warning in warnings %}
    <div class="alert alert-warning mb-2">
        {{ warning }}
    </div>
    {% endfor %}
{% endif %}

<!-- Alerta Especial de Fragmentación -->
{% if availability.is_fragmented %}
<div class="alert alert-warning mb-2">
    <h6 class="alert-heading mb-1">
        <i class="bi bi-exclamation-triangle me-2"></i>
        ⚠️ Alto Riesgo de Ineficiencia
    </h6>
    <p class="mb-0 small">
        Este recurso está asignado a <strong>{{ availability.active_project_count }} proyectos</strong> 
        simultáneamente. La fragmentación extrema puede reducir la productividad hasta un <strong>40%</strong>.
    </p>
</div>
{% endif %}
```

---

### 5. Formulario con HTMX: `apps/projects/templates/projects/allocation_form.html` (NUEVO)

**Integración HTMX en campos**:

```django
{% block extra_head %}
<!-- HTMX para chequeo reactivo -->
<script src="https://unpkg.com/htmx.org@1.9.10"></script>
{% endblock %}

<!-- Recurso con HTMX -->
<select name="resource" 
        id="id_resource" 
        class="form-select" 
        required
        hx-get="{% url 'projects:check_availability' %}"
        hx-trigger="change from:#id_resource, change from:#id_start_date, change from:#id_end_date, change from:#id_hours_per_week"
        hx-include="#id_start_date, #id_end_date, #id_hours_per_week"
        hx-target="#availability-result"
        hx-indicator="#loading-indicator">
    <option value="">Seleccionar recurso...</option>
    <!-- opciones -->
</select>

<!-- Fecha de Inicio -->
<input type="date" 
       name="start_date" 
       id="id_start_date" 
       class="form-control" 
       required
       hx-get="{% url 'projects:check_availability' %}"
       hx-trigger="change"
       hx-include="#id_resource, #id_end_date, #id_hours_per_week"
       hx-target="#availability-result"
       hx-indicator="#loading-indicator">

<!-- Fecha de Fin -->
<input type="date" 
       name="end_date" 
       id="id_end_date" 
       class="form-control" 
       required
       hx-get="{% url 'projects:check_availability' %}"
       hx-trigger="change"
       hx-include="#id_resource, #id_start_date, #id_hours_per_week"
       hx-target="#availability-result"
       hx-indicator="#loading-indicator">

<!-- Horas por Semana -->
<input type="number" 
       name="hours_per_week" 
       id="id_hours_per_week" 
       class="form-control" 
       step="0.5" 
       min="0.01" 
       max="168" 
       required
       hx-get="{% url 'projects:check_availability' %}"
       hx-trigger="change delay:500ms"
       hx-include="#id_resource, #id_start_date, #id_end_date"
       hx-target="#availability-result"
       hx-indicator="#loading-indicator">

<!-- Panel de Resultado (Target) -->
<div id="availability-result">
    <!-- El fragmento HTML se cargará aquí dinámicamente -->
</div>
```

**Atributos HTMX clave**:

- `hx-get`: URL de la vista que retorna el fragmento
- `hx-trigger`: Evento que dispara la petición (`change`, `change delay:500ms`)
- `hx-include`: Otros campos a incluir en la petición
- `hx-target`: Selector CSS donde insertar la respuesta
- `hx-indicator`: Selector del indicador de carga

---

### 6. URLs: `apps/projects/urls.py`

```python
urlpatterns = [
    # ... otras rutas
    
    # RF-11: Motor de Validación de Asignaciones
    path('check-availability/', views.check_resource_availability, name='check_availability'),
]
```

---

### 7. Admin: `apps/projects/admin.py`

```python
from .models import Allocation

@admin.register(Allocation)
class AllocationAdmin(admin.ModelAdmin):
    """Admin para Asignaciones RF-11."""
    list_display = [
        'resource', 'project', 'start_date', 'end_date',
        'hours_per_week', 'is_active'
    ]
    list_filter = ['is_active', 'start_date', 'resource__primary_role']
    search_fields = ['resource__first_name', 'project__code']
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
    )
```

---

## 🎯 Funcionalidad Implementada

### Hard Block (Sobrecarga - Burnout)
- ✅ Detecta cuando horas_totales > capacidad_semanal
- ✅ Lanza `ValidationError` impidiendo guardar
- ✅ Mensaje detallado con cálculo de sobrecarga
- ✅ Indica disponibilidad restante

### Soft Warning (Fragmentación - Context Switching)
- ✅ Detecta cuando recurso trabaja en ≥ 3 proyectos simultáneos
- ✅ Agrega advertencia automática al campo `notes`
- ✅ No impide guardar, solo alerta
- ✅ Cuantifica impacto (hasta 40% de reducción de eficiencia)

### Chequeo en Tiempo Real con HTMX
- ✅ Actualización reactiva al cambiar campos del formulario
- ✅ Barra de progreso con colores semafóricos:
  - Verde: < 80% utilización
  - Amarilla: 80-99% utilización
  - Roja: ≥ 100% utilización (sobrecarga)
- ✅ Tarjetas con métricas:
  - Capacidad semanal
  - Horas asignadas
  - Horas disponibles
- ✅ Lista de proyectos concurrentes
- ✅ Recomendaciones personalizadas

---

## 📐 Matemática de Solapamientos

**Fórmula de detección de solapamiento temporal**:

```
Dos periodos [A_start, A_end] y [B_start, B_end] se solapan si:
A_start <= B_end AND A_end >= B_start
```

**Implementación en Django Q objects**:

```python
overlapping_query = Q(
    resource=self.resource,
    is_active=True,
    start_date__lte=self.end_date,
    end_date__gte=self.start_date
)
```

**Cálculo de carga horaria semanal**:

```
Total_Horas_Solapadas = SUM(hours_per_week) WHERE solapamiento
Nueva_Carga = Total_Horas_Solapadas + Nueva_Asignación.hours_per_week

IF Nueva_Carga > Capacidad_Semanal:
    RAISE ValidationError (Hard Block)
```

---

## 🧪 Casos de Uso de Prueba

### Caso 1: Asignación Normal (OK)
```
Recurso: Juan Pérez
Capacidad: 40h/sem
Asignaciones existentes:
  - Proyecto A: 20h/sem (2026-01-01 → 2026-03-31)

Nueva asignación:
  - Proyecto B: 15h/sem (2026-02-01 → 2026-04-30)

Resultado:
  ✅ Permitida
  Total: 35h/sem (87.5% utilización)
  Advertencia: No
```

### Caso 2: Sobrecarga (BLOQUEADO)
```
Recurso: María González
Capacidad: 40h/sem
Asignaciones existentes:
  - Proyecto A: 25h/sem (2026-01-01 → 2026-03-31)
  - Proyecto B: 20h/sem (2026-02-01 → 2026-04-30)

Nueva asignación:
  - Proyecto C: 10h/sem (2026-03-01 → 2026-05-31)

Resultado:
  ⛔ BLOQUEADA
  Total: 55h/sem (137.5% utilización)
  Sobrecarga: 15h/sem
  Error: ValidationError
```

### Caso 3: Fragmentación (ADVERTENCIA)
```
Recurso: Carlos Rodríguez
Capacidad: 40h/sem
Asignaciones existentes:
  - Proyecto A: 10h/sem
  - Proyecto B: 10h/sem
  - Proyecto C: 10h/sem

Nueva asignación:
  - Proyecto D: 10h/sem

Resultado:
  ✅ Permitida
  Total: 40h/sem (100% utilización)
  ⚠️ FRAGMENTACIÓN: 4 proyectos concurrentes
  Impacto: Hasta 40% de reducción de eficiencia
```

---

## 🔧 Comandos Ejecutados

```bash
# Crear migración
python manage.py makemigrations projects

# Aplicar migración
python manage.py migrate

# Iniciar servidor
python manage.py runserver
```

---

## 🌐 URLs Disponibles

| Ruta | Vista | Descripción |
|------|-------|-------------|
| `/projects/check-availability/` | `check_resource_availability` | Endpoint HTMX para chequeo de disponibilidad |
| `/admin/projects/allocation/` | `AllocationAdmin` | Interfaz admin para gestionar asignaciones |

**Parámetros de la vista HTMX** (`GET`):
- `resource`: ID del recurso (requerido)
- `start`: Fecha de inicio YYYY-MM-DD (requerido)
- `end`: Fecha de fin YYYY-MM-DD (requerido)
- `hours`: Horas por semana solicitadas (opcional)

**Ejemplo de petición**:
```
GET /projects/check-availability/?resource=1&start=2026-02-01&end=2026-04-30&hours=20
```

---

## 📊 Esquema de Base de Datos

```sql
CREATE TABLE projects_allocation (
    id SERIAL PRIMARY KEY,
    project_id INTEGER NOT NULL REFERENCES projects_project(id),
    resource_id INTEGER NOT NULL REFERENCES resources_resource(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    hours_per_week DECIMAL(5, 2) NOT NULL CHECK (hours_per_week >= 0.01 AND hours_per_week <= 168.00),
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    notes TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_allocation_resource_dates ON projects_allocation(resource_id, start_date, end_date);
CREATE INDEX idx_allocation_project_start ON projects_allocation(project_id, start_date);
CREATE INDEX idx_allocation_is_active ON projects_allocation(is_active);
```

---

## ✅ Checklist de Implementación

- [x] Modelo `Allocation` con campos: project, resource, start_date, end_date, hours_per_week
- [x] Validación matemática con Q objects para detectar solapamientos
- [x] Hard Block: `ValidationError` si sobrecarga > capacidad_weekly
- [x] Soft Warning: Mensaje en `notes` si ≥ 3 proyectos concurrentes
- [x] Servicio `calculate_availability()` con métricas detalladas
- [x] Servicio `get_allocation_recommendations()` con análisis completo
- [x] Vista HTMX `check_resource_availability` con respuesta HTML
- [x] Template `availability_check.html` con barra de progreso y alertas
- [x] Formulario `allocation_form.html` con atributos HTMX
- [x] URLs configuradas
- [x] Admin registrado
- [x] Migración creada y aplicada
- [x] Documentación completa

---

## 🎓 Conceptos Clave Implementados

### 1. Matemática de Calendarios
- **Detección de solapamiento temporal** usando lógica de intervalos
- **Agregación de horas** con `Sum()` de Django ORM
- **Cálculo de duración** en semanas con `timedelta`

### 2. HTMX (Hypermedia as the Engine of Application State)
- **Reactividad sin JavaScript** adicional
- **Partial rendering** con fragmentos HTML
- **Event triggering** con `hx-trigger`
- **Form inclusion** con `hx-include`
- **Target swapping** con `hx-target`

### 3. Django Best Practices
- **Q objects** para queries complejas
- **Aggregation** con `aggregate()` y `Sum()`
- **Model validation** con `clean()` y `full_clean()`
- **Service layer** para lógica de negocio compleja
- **Template partials** para componentes reutilizables

---

## 🚀 Próximos Pasos Sugeridos

1. **Agregar campo `capacity_weekly` al modelo `Resource`**:
   ```python
   class Resource(AuditableModel):
       # ... campos existentes
       capacity_weekly = models.DecimalField(
           max_digits=5, decimal_places=2,
           default=Decimal('40.00'),
           validators=[MinValueValidator(Decimal('0.01'))],
           verbose_name="Capacidad Semanal (horas)",
           help_text="Horas disponibles por semana (default: 40h)"
       )
   ```

2. **Crear vista de formulario completa** con POST handler:
   - Procesar formulario de creación de `Allocation`
   - Mostrar mensajes de éxito/error
   - Redirigir a lista de asignaciones

3. **Dashboard de asignaciones**:
   - Vista de calendario con asignaciones
   - Filtros por recurso/proyecto
   - Gráficos de utilización

4. **Notificaciones**:
   - Email cuando recurso supera 80% de utilización
   - Alerta cuando se detecta fragmentación

5. **Reportes**:
   - Informe de utilización por recurso
   - Análisis de fragmentación
   - Proyección de disponibilidad futura

---

## 📝 Notas de Implementación

- El sistema asume `capacity_weekly = 40h` como default si el campo no existe en `Resource`
- La validación se ejecuta automáticamente en `save()` gracias a `full_clean()`
- HTMX carga el fragmento sin reload de página completa
- Los warnings se agregan automáticamente al campo `notes` sin bloquear el guardado
- La barra de progreso es animada cuando hay sobrecarga (>100%)
- Los colores siguen convención semafórica: verde (ok), amarillo (precaución), rojo (peligro)

---

**Implementado por**: GitHub Copilot  
**Fecha**: 22 de enero de 2026  
**Versión Django**: 5.2.10  
**Versión HTMX**: 1.9.10
