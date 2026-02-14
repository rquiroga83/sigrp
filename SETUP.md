# Guía de Inicialización SIGRP

## 💡 Sobre `uv run`

Este proyecto utiliza **uv** como gestor de paquetes y entornos virtuales. A diferencia del flujo tradicional de Python, **no necesitas activar manualmente el entorno virtual**.

**Ventajas de `uv run`:**
- ✅ **No requiere activación manual** del entorno virtual
- ✅ **Ejecuta automáticamente** en el contexto correcto del proyecto
- ✅ **Más rápido** que pip tradicional
- ✅ **Consistente** entre diferentes sistemas operativos
- ✅ **Evita errores** por usar el Python incorrecto

**Comparación:**

```bash
# ❌ Flujo tradicional (NO usar)
source .venv/bin/activate
python manage.py runserver

# ✅ Flujo con uv (RECOMENDADO)
uv run python manage.py runserver
```

Si prefieres activar el entorno manualmente, puedes hacerlo, pero **uv run es la forma recomendada**.

---

## 🚀 Setup Rápido (Windows)

### 1. Instalar uv
```powershell
# Ejecutar en PowerShell como administrador
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verificar instalación
uv --version
```

### 2. Clonar y configurar proyecto
```powershell
# Navegar al directorio del proyecto
cd d:\proyectos\sigrp

# Crear entorno virtual con Python 3.12
uv venv --python 3.12

# Instalar dependencias de desarrollo (incluye producción)
# No es necesario activar el entorno, uv lo maneja automáticamente
uv pip install -e ".[dev]"
```

### 3. Configurar variables de entorno
```powershell
# Copiar el archivo de ejemplo
Copy-Item .env.example .env

# Editar .env con tus credenciales
notepad .env
```

**Variables críticas en `.env`:**
```env
SECRET_KEY=tu-clave-secreta-unica-aqui
DEBUG=True
DATABASE_URL=postgresql://sigrp_user:sigrp_pass@localhost:5432/sigrp_db
REDIS_URL=redis://localhost:6379/0
```

### 4. Levantar infraestructura con Docker
```powershell
# Levantar PostgreSQL y Redis
docker-compose up -d

# Verificar que los servicios estén corriendo
docker-compose ps
```

### 5. Inicializar base de datos
```powershell
# Crear migraciones (si es necesario)
uv run python manage.py makemigrations

# Aplicar migraciones
uv run python manage.py migrate

# Crear superusuario
uv run python manage.py createsuperuser
```

### 6. Descargar modelo de spaCy
```powershell
# Descargar modelo de español
uv run python -m spacy download es_core_news_sm

# Verificar instalación
uv run python -c "import spacy; nlp = spacy.load('es_core_news_sm'); print('spaCy OK')"
```

### 7. Recolectar archivos estáticos
```powershell
uv run python manage.py collectstatic --noinput
```

### 8. Ejecutar el servidor de desarrollo
```powershell
# En terminal 1: Django
uv run python manage.py runserver

# En terminal 2: Celery Worker (Windows)
uv run celery -A config worker -l info --pool=solo

# En terminal 3: Celery Beat (tareas periódicas)
uv run celery -A config beat -l info
```

---

## 🐧 Setup Rápido (Linux/macOS)

### 1. Instalar uv
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
uv --version
```

### 2. Configurar proyecto
```bash
cd ~/proyectos/sigrp

# Crear entorno virtual con Python 3.12
uv venv --python 3.12

# Instalar dependencias (uv maneja el entorno automáticamente)
uv pip install -e ".[dev]"
```

### 3. Variables de entorno y Docker
```bash
cp .env.example .env
nano .env

# Levantar servicios
docker-compose up -d
```

### 4. Inicializar DB y spaCy
```bash
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python -m spacy download es_core_news_sm
uv run python manage.py collectstatic --noinput
```

### 5. Ejecutar servicios
```bash
# Terminal 1: Django
uv run python manage.py runserver

# Terminal 2: Celery Worker
uv run celery -A config worker -l info

# Terminal 3: Celery Beat
uv run celery -A config beat -l info
```

---

## 📦 Comandos uv Útiles

```powershell
# Actualizar dependencias
uv pip install --upgrade -e ".[dev]"

# Listar paquetes instalados
uv pip list

# Instalar un paquete nuevo
uv pip install nombre-paquete

# Congelar dependencias actuales
uv pip freeze > requirements.txt

# Desinstalar paquete
uv pip uninstall nombre-paquete

# Verificar entorno
uv pip check
```

---

## 🔧 Comandos Django Comunes

```bash
# Crear nueva app
uv run python manage.py startapp nombre_app

# Crear migraciones
uv run python manage.py makemigrations [app_name]

# Ver SQL de migraciones
uv run python manage.py sqlmigrate app_name migration_number

# Shell interactivo con IPython
uv run python manage.py shell

# Cargar datos de prueba (si tienes fixtures)
uv run python manage.py loaddata fixtures/initial_data.json

# Ejecutar tests
uv run pytest

# Ver rutas disponibles
uv run python manage.py show_urls
```

---

## 🐳 Gestión de Docker

```powershell
# Ver logs de PostgreSQL
docker-compose logs -f postgres

# Ver logs de Redis
docker-compose logs -f redis

# Reiniciar servicios
docker-compose restart

# Detener servicios
docker-compose down

# Detener y eliminar volúmenes (⚠️ borra datos)
docker-compose down -v

# Ejecutar comando en contenedor
docker-compose exec postgres psql -U sigrp_user -d sigrp_db
```

---

## 📊 Verificación del Sistema

```bash
# Verificar configuración de Django
uv run python manage.py check

# Ver migraciones aplicadas
uv run python manage.py showmigrations

# Verificar modelos de spaCy
uv run python -c "import spacy; print(spacy.info())"

# Verificar conexión a PostgreSQL
uv run python manage.py dbshell

# Verificar Celery
uv run celery -A config inspect ping
```

---

## 🎯 URLs de Acceso

- **Frontend**: http://localhost:8000
- **Admin Django**: http://localhost:8000/admin
- **Flower (Celery Monitor)**: http://localhost:5555 (si instalas flower)

---

## 🔥 Troubleshooting

### Error de conexión a PostgreSQL
```powershell
# Verificar que Docker esté corriendo
docker ps

# Revisar logs
docker-compose logs postgres
```

### Error de spaCy
```bash
# Reinstalar modelo
uv run python -m spacy download es_core_news_sm --force

# Verificar ruta de modelos
uv run python -m spacy info es_core_news_sm
```

### Error de Redis
```powershell
# Reiniciar Redis
docker-compose restart redis

# Verificar conexión
docker-compose exec redis redis-cli ping
```

### Celery no procesa tareas
```bash
# Ver workers activos
uv run celery -A config inspect active

# Purgar cola
uv run celery -A config purge

# Reiniciar worker (Windows)
# Ctrl+C y volver a ejecutar
uv run celery -A config worker -l info --pool=solo

# Reiniciar worker (Linux/macOS)
uv run celery -A config worker -l info
```

---

## 📝 Notas Importantes

1. **Windows**: Usa `--pool=solo` para Celery en Windows
2. **Producción**: Cambiar `DEBUG=False` y generar nueva `SECRET_KEY`
3. **spaCy**: El modelo `es_core_news_sm` es ligero; para mejor precisión usar `es_core_news_md` o `es_core_news_lg`
4. **Redis**: Puerto por defecto 6379, ajustar si hay conflictos
5. **PostgreSQL**: Puerto por defecto 5432
