# Implementación del Módulo Resources con Qdrant

> **Sistema**: SIGRP - Sistema Integrado de Gestión de Recursos y Proyectos  
> **Módulo**: apps/resources  
> **Características**: Búsqueda Semántica de Talento con Sentence Transformers + Qdrant

---

## 📦 Dependencias Instaladas

```bash
uv add sentence-transformers  # Incluye PyTorch automáticamente
```

**Paquetes agregados**:
- `sentence-transformers==5.2.0` - Modelos de embeddings
- `torch==2.10.0` - PyTorch
- `transformers==4.57.6` - Hugging Face Transformers
- `huggingface-hub==0.36.0` - Cliente de Hugging Face
- `scikit-learn==1.8.0` - Para cálculos ML
- `scipy==1.17.0` - Operaciones científicas

---

## 🏗️ Arquitectura Implementada

```
apps/resources/
├── models.py           # ✅ Role y Resource con lógica dual de costos
├── services.py         # ✅ VectorService (Qdrant + Sentence Transformers)
├── signals.py          # ✅ Auto-sincronización con Qdrant
├── apps.py             # ✅ Configuración para cargar signals
├── admin.py            # ✅ Admin para Role y Resource
├── management/
│   └── commands/
│       └── sync_resources_qdrant.py  # ✅ Comando de sincronización masiva
└── (views.py y templates pendientes de implementación HTMX)
```

---

## 📝 Modelos Implementados

### ⚙️ Modelo `Role`

**Ubicación**: `apps/resources/models.py`

**Campos**:
```python
- code: CharField(20, unique)           # Ej: "SR-DEV-001"
- name: CharField(100, unique)          # Ej: "Senior Developer"
- category: CharField (Choices)         # management, technical, business_analysis, qa, design, operations, other
- seniority: CharField (Choices)        # entry, junior, mid, senior, lead, principal
- standard_rate: DecimalField(10,2)     # Tarifa estándar para facturación (USD/hora)
- description: TextField (opcional)
- is_active: BooleanField
```

**Métodos**:
```python
def get_display_name() -> str:
    """Retorna: 'Senior Developer (SR-DEV-001)'"""

def calculate_cost_for_hours(hours: Decimal) -> Decimal:
    """Calcula: standard_rate × hours"""
```

---

### 👤 Modelo `Resource`

**Ubicación**: `apps/resources/models.py`

**Campos**:
```python
- employee_id: CharField(20, unique)
- first_name, last_name: CharField(100)
- email: EmailField (unique)
- phone: CharField(20, opcional)
- primary_role: ForeignKey(Role)                  # Rol principal
- internal_cost: DecimalField(10,2)               # Costo real interno (USD/hora)
- hire_date: DateField (opcional)
- skills_vector: JSONField (lista)                # [{"name": "Python", "level": 5}, ...]
- qdrant_point_id: CharField(100, unique)         # UUID para Qdrant
- status: CharField (Choices)                     # available, partially_allocated, etc.
- availability_percentage: IntegerField (0-100)
- is_active: BooleanField
```

**Propiedades**:
```python
@property
def full_name() -> str:
    """Retorna: 'Juan Pérez'"""

@property
def effective_rate() -> Decimal:
    """Retorna: primary_role.standard_rate"""

@property
def cost_vs_rate_ratio() -> float:
    """Retorna: (internal_cost / effective_rate) × 100"""
```

**Métodos**:
```python
def calculate_cost_for_hours(hours: Decimal) -> Decimal:
    """Calcula costo interno: internal_cost × hours"""

def get_skill_level(skill_name: str) -> int:
    """Obtiene nivel de habilidad (1-5)"""

def add_skill(skill_name: str, level: int):
    """Agrega o actualiza habilidad"""
```

---

## 🤖 Servicio de Vectores (VectorService)

**Ubicación**: `apps/resources/services.py`

### Clase `VectorService`

**Responsabilidades**:
1. Generar embeddings con `sentence-transformers/all-MiniLM-L6-v2`
2. Convertir skills JSON a texto narrativo semántico
3. Sincronizar recursos con Qdrant
4. Realizar búsquedas semánticas

### Método Principal: `skills_to_narrative()`

**Función**: Convierte el JSON de skills en texto narrativo para mejor búsqueda semántica.

**Regla de niveles**:
```python
1 → "Novice"
2 → "Basic knowledge"
3 → "Intermediate"
4 → "Advanced"
5 → "Expert"
```

**Ejemplo**:
```python
# Input:
[
    {"name": "Django", "level": 5},
    {"name": "React", "level": 3},
    {"name": "Python", "level": 5}
]

# Output:
"Expert in Django Backend Framework. Intermediate in React Frontend Framework. Expert in Python Programming Language."
```

**Contexto semántico adicional**:
- "django" → "Backend Framework"
- "react" → "Frontend Framework"
- "python" → "Programming Language"
- "postgresql" → "Database System"
- "aws" → "Cloud Platform"
- etc.

### Método: `upsert_resource(resource)`

**Flujo**:
1. Convierte `skills_vector` a texto narrativo
2. Crea texto completo: `"{name}. Role: {role}. Skills: {narrative}"`
3. Genera embedding con `all-MiniLM-L6-v2` (384 dimensiones)
4. Genera o reutiliza `qdrant_point_id` (UUID)
5. Prepara payload con metadatos
6. Inserta/actualiza en Qdrant colección "resources_skills"

### Método: `search_resources(query, limit=10, filters=None)`

**Flujo**:
1. Genera embedding de la query de búsqueda
2. Aplica filtros opcionales (ej: `{"is_active": True}`)
3. Busca en Qdrant con similaridad COSINE
4. Retorna lista ordenada por score de similitud (0-1)

**Ejemplo de búsqueda**:
```python
results = vector_service.search_resources(
    query="Busco desarrollador python experto con django",
    limit=5,
    filters={"is_active": True}
)

# Resultado:
[
    {
        "full_name": "Juan Pérez",
        "role": "Senior Developer",
        "internal_cost": 80.00,
        "similarity_score": 0.87,  # 87% similar
        "skills_text": "Expert in Python... Expert in Django..."
    },
    ...
]
```

---

## 🔔 Signals Automáticos

**Ubicación**: `apps/resources/signals.py`

### Signal: `post_save(Resource)`

**Trigger**: Cada vez que se guarda un Resource

**Lógica**:
```python
if resource.is_active:
    # Sincronizar con Qdrant
    vector_service.upsert_resource(resource)
else:
    # Si está inactivo, eliminarlo de Qdrant
    if resource.qdrant_point_id:
        vector_service.delete_resource(resource.qdrant_point_id)
```

### Signal: `post_delete(Resource)`

**Trigger**: Cuando se elimina un Resource

**Lógica**:
```python
if resource.qdrant_point_id:
    vector_service.delete_resource(resource.qdrant_point_id)
```

---

## ⚙️ Configuración (settings.py)

```python
# Qdrant Vector Store
QDRANT_HOST = os.getenv('QDRANT_HOST', 'localhost')
QDRANT_PORT = int(os.getenv('QDRANT_PORT', '6333'))
```

**.env**:
```bash
QDRANT_HOST=localhost
QDRANT_PORT=6333
```

---

## 🛠️ Comando de Management

**Comando**: `python manage.py sync_resources_qdrant`

**Propósito**: Sincronizar todos los recursos existentes con Qdrant

**Uso**:
```bash
# Sincronizar solo recursos activos
python manage.py sync_resources_qdrant

# Sincronizar todos (incluyendo inactivos, los eliminará de Qdrant)
python manage.py sync_resources_qdrant --all
```

**Salida ejemplo**:
```
Sincronizando recursos activos...
Total de recursos a procesar: 15
Procesando: Juan Pérez... ✓
Procesando: María García... ✓
Procesando: Pedro López... ✓
...

✓ Sincronización completada:
  - Exitosos: 15
  - Errores: 0
  - Total: 15
```

---

## 🔄 Flujo de Sincronización

```
1. Usuario crea/modifica Resource en Django Admin
   ↓
2. Signal post_save se dispara automáticamente
   ↓
3. VectorService.upsert_resource(resource) ejecuta:
   a. Convierte skills_vector a texto narrativo
   b. Genera embedding (384 dimensiones)
   c. Genera/reutiliza qdrant_point_id (UUID)
   d. Envía a Qdrant colección "resources_skills"
   ↓
4. Resource queda disponible para búsqueda semántica
```

---

## 🔍 Casos de Uso

### Caso 1: Búsqueda Semántica de Talento

**Query**: *"Necesito un desarrollador backend experimentado con Python y bases de datos"*

**Proceso**:
1. VectorService genera embedding de la query
2. Qdrant busca los vectores más similares (COSINE distance)
3. Retorna recursos ordenados por similitud

**Ventaja**: No necesita match exacto de keywords. Entiende semántica.

### Caso 2: Matching Inteligente para Proyectos

```python
from apps.resources.services import vector_service

# Buscar recursos para un proyecto Django con PostgreSQL
results = vector_service.search_resources(
    query="Experto en Django con experiencia en PostgreSQL y APIs REST",
    limit=10,
    filters={"is_active": True, "role_category": "technical"}
)

for result in results:
    print(f"{result['full_name']} - Score: {result['similarity_score']:.2%}")
```

---

## 📊 Estructura de Datos

### Skills Vector Format

**Formato en DB** (JSONField):
```json
[
    {"name": "Python", "level": 5},
    {"name": "Django", "level": 5},
    {"name": "React", "level": 3},
    {"name": "PostgreSQL", "level": 4},
    {"name": "AWS", "level": 3}
]
```

**Conversión a Narrativa**:
```
"Expert in Python Programming Language. Expert in Django Backend Framework. Intermediate in React Frontend Framework. Advanced in PostgreSQL Database System. Intermediate in AWS Cloud Platform."
```

**Embedding Generado**: Vector de 384 dimensiones (float32)

---

## ✅ Checklist de Implementación

- [x] Modelos Core (TimeStampedModel, AuditableModel)
- [x] Modelo Role con métodos requeridos
- [x] Modelo Resource con @property y métodos
- [x] VectorService con sentence-transformers
- [x] Método skills_to_narrative() con contexto semántico
- [x] Integración con Qdrant (upsert, delete, search)
- [x] Signals post_save y post_delete
- [x] Configuración en settings.py
- [x] Comando de management sync_resources_qdrant
- [ ] Views con HTMX para gestión de skills (siguiente paso)
- [ ] Templates HTMX para UI dinámica (siguiente paso)

---

## 🚀 Próximos Pasos

### 1. Crear Migraciones
```bash
python manage.py makemigrations resources
python manage.py migrate
```

### 2. Implementar Views HTMX
- Formulario dinámico de skills con botón "Agregar Skill"
- Vista de búsqueda semántica con resultados en tiempo real
- Endpoint AJAX para reconstruir JSON de skills

### 3. Templates HTMX
- `resource_form.html` - Formulario con skills dinámicos
- `resource_list.html` - Lista con búsqueda semántica
- `partials/skill_row.html` - Fila individual de skill

---

## 📚 Documentación de Referencia

- **Sentence Transformers**: https://www.sbert.net/
- **Qdrant**: https://qdrant.tech/documentation/
- **Modelo all-MiniLM-L6-v2**: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2

---

**Fecha de Implementación**: 22 de enero de 2026  
**Versión**: 1.0  
**Estado**: Backend Completo ✅ | Frontend HTMX Pendiente ⏳
