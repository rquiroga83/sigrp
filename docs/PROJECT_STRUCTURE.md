# Estructura Completa del Proyecto SIGRP

```
sigrp/
│
├── 📁 apps/                          # Aplicaciones Django modulares
│   ├── 📁 core/                      # App core (base models, utils)
│   │   ├── __init__.py
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── models.py                 # TimeStampedModel, AuditableModel
│   │   ├── urls.py
│   │   └── views.py                  # Home view
│   │
│   ├── 📁 resources/                 # Gestión de recursos humanos
│   │   ├── __init__.py
│   │   ├── admin.py                  # Resource, ResourceAllocation admin
│   │   ├── apps.py
│   │   ├── models.py                 # Resource (skills JSONB), ResourceAllocation
│   │   ├── tasks.py                  # Celery: predict_resource_availability
│   │   ├── urls.py
│   │   └── views.py                  # Lista y detalle de recursos
│   │
│   ├── 📁 projects/                  # Gestión de proyectos Fixed/T&M
│   │   ├── __init__.py
│   │   ├── admin.py                  # Project, TimeEntry admin
│   │   ├── apps.py
│   │   ├── models.py                 # Project (Fixed/T&M logic), TimeEntry
│   │   ├── tasks.py                  # Celery: health scores, metrics update
│   │   ├── urls.py
│   │   └── views.py                  # Lista y detalle de proyectos
│   │
│   ├── 📁 standups/                  # Daily standups + NLP
│   │   ├── __init__.py
│   │   ├── admin.py                  # StandupLog, TeamMood admin
│   │   ├── apps.py
│   │   ├── models.py                 # StandupLog (NLP fields), TeamMood
│   │   ├── nlp_utils.py              # SentimentAnalyzer (spaCy)
│   │   ├── tasks.py                  # Celery: sentiment analysis, team mood
│   │   ├── urls.py
│   │   └── views.py                  # Crear y listar standups
│   │
│   └── 📁 analytics/                 # Dashboards y reportes
│       ├── __init__.py
│       ├── admin.py
│       ├── apps.py
│       ├── models.py                 # Sin modelos (usa agregaciones)
│       ├── urls.py
│       └── views.py                  # Dashboard, reportes
│
├── 📁 config/                        # Configuración Django
│   ├── __init__.py                   # Celery app initialization
│   ├── asgi.py                       # ASGI config
│   ├── celery.py                     # Celery config + beat schedule
│   ├── settings.py                   # Settings principal (DB, Redis, Apps)
│   ├── urls.py                       # URL routing principal
│   └── wsgi.py                       # WSGI config
│
├── 📁 static/                        # Archivos estáticos
│   ├── 📁 css/
│   │   └── styles.css                # Estilos personalizados
│   ├── 📁 js/
│   │   └── main.js                   # JavaScript + HTMX + Vue helpers
│   └── 📁 img/                       # Imágenes (crear según necesidad)
│
├── 📁 templates/                     # Templates Django
│   ├── base.html                     # Base template (Bootstrap + HTMX + Vue)
│   ├── 📁 core/
│   │   └── home.html                 # Página principal
│   ├── 📁 resources/
│   │   ├── list.html                 # Lista de recursos
│   │   └── detail.html               # Detalle de recurso
│   ├── 📁 projects/
│   │   ├── list.html                 # Lista de proyectos
│   │   └── detail.html               # Detalle de proyecto
│   ├── 📁 standups/
│   │   ├── list.html                 # Lista de standups
│   │   └── create.html               # Crear standup
│   └── 📁 analytics/
│       ├── dashboard.html            # Dashboard principal
│       ├── projects_report.html      # Reporte de proyectos
│       └── resources_report.html     # Reporte de recursos
│
├── 📁 media/                         # Archivos subidos (git ignored)
│   └── resources/
│       └── profiles/                 # Fotos de perfil
│
├── 📁 staticfiles/                   # Archivos estáticos recolectados (git ignored)
│
├── 📁 .venv/                         # Entorno virtual (git ignored)
│
├── 📄 .env                           # Variables de entorno (git ignored)
├── 📄 .env.example                   # Template de variables
├── 📄 .gitignore                     # Git ignore
├── 📄 .python-version                # Versión de Python (3.12)
│
├── 📄 manage.py                      # Django management script
├── 📄 pyproject.toml                 # Configuración uv + dependencies
│
├── 📄 docker-compose.yml             # PostgreSQL + Redis + pgAdmin
│
├── 📄 README.md                      # Documentación principal
├── 📄 SETUP.md                       # Guía de setup detallada
├── 📄 ARCHITECTURE.md                # Arquitectura de modelos
│
├── 📄 setup.ps1                      # Script de setup Windows
└── 📄 setup.sh                       # Script de setup Linux/macOS
```

## 📊 Estadísticas del Proyecto

- **Total Apps Django**: 5 (core, resources, projects, standups, analytics)
- **Total Modelos**: 7 (Resource, ResourceAllocation, Project, TimeEntry, StandupLog, TeamMood, base models)
- **Tecnologías**: Django 5, HTMX, Vue.js, PostgreSQL, Redis, Celery, spaCy
- **Lenguaje**: Python 3.12+
- **Gestor**: uv (Astral)

## 🎯 Próximos Pasos Después del Setup

1. **Ejecutar setup automático**:
   ```powershell
   .\setup.ps1
   ```

2. **Crear superusuario**:
   ```powershell
   python manage.py createsuperuser
   ```

3. **Levantar servidor**:
   ```powershell
   python manage.py runserver
   ```

4. **Levantar Celery** (nueva terminal):
   ```powershell
   celery -A config worker -l info --pool=solo
   ```

5. **Acceder a**:
   - Frontend: http://localhost:8000
   - Admin: http://localhost:8000/admin
   - pgAdmin: http://localhost:5050 (admin@sigrp.local / admin)

## 🔧 Comandos de Desarrollo

```powershell
# Crear migraciones
python manage.py makemigrations

# Aplicar migraciones
python manage.py migrate

# Shell Django
python manage.py shell

# Tests
pytest

# Format code
black .

# Lint
ruff check .

# Type checking
mypy apps/
```

## 📚 Documentación Adicional

- [README.md](README.md) - Overview del proyecto
- [SETUP.md](SETUP.md) - Guía detallada de instalación
- [ARCHITECTURE.md](ARCHITECTURE.md) - Arquitectura de datos y diagramas
- Documentación Django: https://docs.djangoproject.com/
- Documentación HTMX: https://htmx.org/docs/
- Documentación spaCy: https://spacy.io/

---

**¡El arquetipo está listo para comenzar el desarrollo! 🚀**
