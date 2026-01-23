# SIGRP - Sistema Integrado de Gestión de Recursos y Proyectos

Sistema monolítico moderno en Python para la gestión integral de recursos humanos, proyectos y análisis predictivo con **arquitectura de costos dual** (Estimación vs. Ejecución).

## 🎯 Concepto Clave: Lógica Dual de Costos

SIGRP implementa una separación clara entre **estimación/facturación** y **costos reales**:

- **`Role`** (Roles profesionales): Define `standard_rate` → Para **estimar** proyectos y **facturar** al cliente
- **`Resource`** (Personas reales): Define `internal_cost` → **Costo real** para la empresa

Esta arquitectura permite:
- ✅ Estimar proyectos con rates de mercado (Role)
- ✅ Rastrear costos internos reales (Resource)
- ✅ Calcular márgenes de ganancia precisos
- ✅ Analizar variaciones entre lo planeado y lo ejecutado

**Ejemplo práctico**:
```python
# Estimación: Senior Developer @ $150/h × 40h = $6,000
task.required_role = Role("Senior Developer", standard_rate=150)
task.estimated_hours = 40

# Ejecución: Juan Pérez (internal_cost=$80/h) × 45h = $3,600
task.assigned_resource = Resource("Juan", internal_cost=80)
task.logged_hours = 45  # Auto-actualizado por TimeLog

# Análisis:
# Facturar al cliente: $150 × 45h = $6,750
# Costo real: $80 × 45h = $3,600
# Ganancia: $3,150 (47% margen)
```

## 🚀 Stack Tecnológico

- **Backend & Frontend**: Django 5.x + HTMX
- **Base de Datos**: PostgreSQL 15+ (con JSONB para skills_vector)
- **Vector Store**: Qdrant (para embeddings de habilidades)
- **Caché & Cola**: Redis + Celery
- **NLP**: spaCy (análisis de sentimiento en standups)
- **Servidor**: Gunicorn
- **Gestor de Paquetes**: uv (Astral)

## 📁 Estructura del Proyecto

```
sigrp/
├── apps/
│   ├── resources/          # Gestión de recursos humanos
│   │   ├── models.py       # Role, Resource (lógica dual)
│   │   └── admin.py        # Admin para roles y recursos
│   ├── projects/           # Gestión de proyectos
│   │   ├── models.py       # Project, Stage, Task, TimeLog, TimeEntry
│   │   └── admin.py        # Admin para proyectos
│   ├── standups/           # Daily standups con NLP
│   ├── analytics/          # Dashboards y reportes
│   └── core/               # Modelos base (AuditableModel)
├── config/                 # Configuración Django
│   ├── settings.py         # Settings principal
│   ├── urls.py             # URLs del proyecto
│   └── celery.py           # Configuración Celery
├── static/                 # Archivos estáticos (CSS, JS)
├── templates/              # Templates Django + HTMX
├── docker-compose.yml      # PostgreSQL + Redis + Qdrant
├── pyproject.toml          # Dependencias y configuración
├── MODELOS_IMPLEMENTADOS.md # 📚 Documentación detallada de modelos
└── README.md               # Este archivo
```

## 🛠️ Instalación y Configuración

### Opción 1: Setup Automático (Windows)

```powershell
# Ejecutar script de setup
.\setup.ps1
```

### Opción 2: Setup Manual

#### 1. Instalar uv

```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### 2. Clonar y configurar el proyecto

```bash
# Clonar repositorio
git clone https://github.com/rquiroga83/sigrp.git
cd sigrp

# Crear entorno virtual con Python 3.12
uv venv --python 3.12

# Activar entorno
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Instalar dependencias
uv pip install -e ".[dev]"
```

#### 3. Levantar servicios Docker

```bash
# Levantar PostgreSQL, Redis y Qdrant
docker-compose up -d

# Verificar que estén corriendo
docker-compose ps
```

**Servicios disponibles**:
- PostgreSQL: `localhost:5433`
- Redis: `localhost:6379`
- Qdrant HTTP: `localhost:6333`
- Qdrant gRPC: `localhost:6334`

#### 4. Configurar variables de entorno

```bash
# Copiar archivo de ejemplo
cp .env.example .env

# El archivo .env ya tiene configuración correcta:
# - PostgreSQL: sigrp/sigrp@localhost:5433/sigrp_db
# - Redis: localhost:6379
```

#### 5. Aplicar migraciones

```bash
# Generar migraciones (ya están creadas)
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate
```

#### 6. Crear superusuario

```bash
python manage.py createsuperuser
```

#### 7. Descargar modelo spaCy (opcional)

```bash
python -m spacy download es_core_news_sm
```

### 🚀 Ejecutar el Proyecto

#### Servidor Django

```bash
# Desarrollo
python manage.py runserver

$env:Path += ";$env:USERPROFILE\.local\bin"; uv run python manage.py runserver

# Producción (con Gunicorn)
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

#### Celery (en otra terminal - opcional)

```bash
# Activar entorno virtual primero
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS

# Worker (Windows)
celery -A config worker -l info --pool=solo

# Worker (Linux/macOS)
celery -A config worker -l info

# Beat (tareas periódicas)
celery -A config beat -l info
```

## 🎯 Características Principales

### 📊 Gestión de Proyectos con Lógica Dual

#### Jerarquía: `Project → Stage → Task`

**Project** (Fixed Price o Time & Material):
- Fixed Price: Budget límite, precio acordado con cliente
- Time & Material: Facturación por hora trabajada
- Métricas: costo real, costo estimado, margen de ganancia

**Stage** (Etapas del proyecto):
- Agrupación lógica de tareas (ej: Discovery, Development, QA)
- Seguimiento de progreso por etapa
- Costo acumulado vs. planeado

**Task** (Tareas individuales):
- **Estimación**: `required_role` (Role) + `estimated_hours` → `planned_value`
- **Ejecución**: `assigned_resource` (Resource) + `logged_hours` → `actual_cost_projection`
- **Análisis**: `cost_variance`, `hours_variance`, `completion_percentage`

**TimeLog** (Imputación de horas):
- Auto-calcula `cost` = `resource.internal_cost × hours`
- Auto-calcula `billable_amount` = `role.standard_rate × hours`
- Actualiza automáticamente `task.logged_hours`

### 👥 Gestión de Recursos con Roles

**Role** (Roles profesionales):
- Categorías: Management, Technical, Business Analysis, QA, etc.
- Niveles: Entry, Junior, Mid, Senior, Lead, Principal
- `standard_rate`: Tarifa por hora para estimación y facturación

**Resource** (Personas reales):
- Vinculado a `primary_role` (FK a Role)
- `internal_cost`: Costo real por hora (salario + overhead)
- `skills_vector`: JSONB para almacenar habilidades
- `qdrant_point_id`: Integración con Qdrant para búsqueda semántica

### 📈 Métricas Financieras

Todas calculadas automáticamente vía `@property` methods:

**A nivel de Task**:
- `planned_value`: Valor planeado (Role-based)
- `actual_cost_projection`: Costo real (Resource-based)
- `cost_variance`: Diferencia entre costo real y planeado
- `hours_variance`: Diferencia en horas
- `is_over_budget`: Indicador de exceso de presupuesto

**A nivel de Stage**:
- `logged_hours`: Total de horas de todas las tareas
- `actual_cost`: Costo real acumulado
- `planned_value`: Valor planeado total

**A nivel de Project**:
- `total_logged_hours`: Total de horas registradas
- `total_cost`: Costo interno total
- `total_billable`: Monto facturable total
- `profit_margin`: Margen de ganancia (%)

### 🧠 NLP en Standups (Futuro)

- Análisis de sentimiento en daily reports
- Detección automática de riesgos
- Extracción de keywords

## 🧪 Testing

```bash
# Ejecutar tests
pytest

# Con cobertura
pytest --cov=apps --cov-report=html

# Ver reporte de cobertura
# Windows:
start htmlcov\index.html
# Linux/macOS:
open htmlcov/index.html
```

## 📊 Acceso al Sistema

- **Frontend**: http://localhost:8000
- **Admin Django**: http://localhost:8000/admin
- **Qdrant Dashboard**: http://localhost:6333/dashboard

## 📚 Documentación Adicional

- **[MODELOS_IMPLEMENTADOS.md](MODELOS_IMPLEMENTADOS.md)**: Documentación completa de modelos, fórmulas financieras y ejemplos de uso
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Arquitectura del sistema
- **[PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)**: Estructura detallada del proyecto

## 🔧 Comandos Útiles

```bash
# Ver estado de servicios Docker
docker-compose ps

# Ver logs de PostgreSQL
docker-compose logs -f db

# Ver logs de Celery
celery -A config inspect active

# Crear app nueva
python manage.py startapp nombre_app apps/nombre_app

# Colectar estáticos
python manage.py collectstatic

# Limpiar base de datos (desarrollo)
docker-compose down -v
docker-compose up -d
python manage.py migrate
```

## 🗄️ Gestión de Base de Datos

### Backup

```bash
# Backup de PostgreSQL
docker exec sigrp_postgres pg_dump -U sigrp sigrp_db > backup_$(date +%Y%m%d).sql
```

### Restore

```bash
# Restore de PostgreSQL
cat backup_20260122.sql | docker exec -i sigrp_postgres psql -U sigrp sigrp_db
```

## 🔐 Seguridad

- ⚠️ Cambiar `SECRET_KEY` en `.env` para producción
- ⚠️ Configurar `ALLOWED_HOSTS` apropiadamente
- ⚠️ Cambiar credenciales de PostgreSQL en producción
- ⚠️ Habilitar SSL en producción (`SECURE_SSL_REDIRECT=True`)

## 🤝 Contribuir

1. Fork el proyecto
2. Crea tu rama: `git checkout -b feature/AmazingFeature`
3. Commit tus cambios: `git commit -m 'Add: AmazingFeature'`
4. Push a la rama: `git push origin feature/AmazingFeature`
5. Abre un Pull Request

## 📝 Licencia

Propietario - Todos los derechos reservados

## 👨‍💻 Autor

**Rodolfo Quiroga**
- GitHub: [@rquiroga83](https://github.com/rquiroga83)

---

**Versión**: 0.1.0  
**Última actualización**: 22 de enero de 2026
