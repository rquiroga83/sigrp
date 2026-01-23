# SIGRP - Sistema Integrado de Gestión de Recursos y Proyectos

Sistema monolítico moderno en Python para la gestión integral de recursos humanos, proyectos y análisis predictivo.

## 🚀 Stack Tecnológico

- **Backend & Frontend**: Django 5.x + HTMX + Vue.js (gráficos)
- **Base de Datos**: PostgreSQL 15+
- **Caché & Cola**: Redis + Celery
- **NLP**: spaCy (análisis de sentimiento)
- **Servidor**: Gunicorn
- **Gestor de Entorno**: uv (Astral)

## 📁 Estructura del Proyecto

```
sigrp/
├── apps/
│   ├── resources/      # Gestión de recursos humanos
│   ├── projects/       # Gestión de proyectos (Fixed/T&M)
│   ├── standups/       # Daily standups con NLP
│   ├── analytics/      # Dashboards y reportes
│   └── core/           # Modelos y utilidades comunes
├── config/             # Configuración Django
├── static/             # Archivos estáticos (CSS, JS, Vue)
├── templates/          # Templates Django + HTMX
├── media/              # Archivos subidos por usuarios
├── docker-compose.yml  # Infraestructura local
└── pyproject.toml      # Configuración del proyecto
```

## 🛠️ Instalación y Configuración

### 1. Instalar uv (si no lo tienes)

```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clonar y configurar el proyecto

```bash
# Clonar repositorio (si aplica)
cd d:\proyectos\sigrp

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

### 3. Configurar base de datos

```bash
# Copiar variables de entorno
cp .env.example .env

# Editar .env con tus credenciales
# Luego levantar servicios con Docker
docker-compose up -d postgres redis

# Aplicar migraciones
python manage.py migrate

# Crear superusuario
python manage.py createsuperuser

# Descargar modelo de spaCy (español)
python -m spacy download es_core_news_sm
```

### 4. Ejecutar el servidor

```bash
# Desarrollo
python manage.py runserver

# Producción (con Gunicorn)
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

### 5. Ejecutar Celery (en otra terminal)

```bash
# Worker
celery -A config worker -l info

# Beat (tareas periódicas)
celery -A config beat -l info
```

## 🎯 Características Principales

### Gestión de Proyectos
- **Precio Fijo**: Budget límite, seguimiento de desviaciones
- **Time & Material**: Facturación por hora, tracking detallado

### Análisis de Recursos
- Vector de habilidades en JSONB para matching inteligente
- Predicción de disponibilidad

### NLP en Standups
- Análisis de sentimiento en daily reports
- Detección automática de riesgos

## 🧪 Testing

```bash
# Ejecutar tests
pytest

# Con cobertura
pytest --cov=apps --cov-report=html
```

## 📊 Acceso al Sistema

- **Frontend**: http://localhost:8000
- **Admin Django**: http://localhost:8000/admin
- **API (futuro)**: http://localhost:8000/api/v1

## 📝 Licencia

Propietario - Todos los derechos reservados
