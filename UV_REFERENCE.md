# Guía de Referencia Rápida: uv

## 🎯 Qué es uv

**uv** es un gestor de paquetes y entornos virtuales de Python ultrarrápido, escrito en Rust por Astral (los creadores de Ruff).

**Ventajas:**
- ⚡ **10-100x más rápido** que pip
- 🔒 **Resolución de dependencias determinista**
- 🎯 **Compatible con pip** (misma sintaxis)
- 📦 **Gestión automática** de entornos virtuales
- 🔄 **Lock files automáticos** (`uv.lock`)

---

## 📚 Comandos Esenciales

### Instalación de uv

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verificar instalación
uv --version
```

### Gestión de Entornos Virtuales

```bash
# Crear entorno virtual con Python 3.12
uv venv --python 3.12

# Crear con Python específico
uv venv --python 3.11.5

# Ver información del entorno
uv venv --info
```

### Instalación de Paquetes

```bash
# Instalar proyecto en modo editable (desarrollo)
uv pip install -e ".[dev]"

# Instalar solo dependencias de producción
uv pip install -e .

# Instalar paquete específico
uv pip install django

# Instalar con versión específica
uv pip install "django>=5.0,<6.0"

# Instalar desde requirements.txt
uv pip install -r requirements.txt

# Actualizar paquete
uv pip install --upgrade django

# Actualizar todo
uv pip install --upgrade -e ".[dev]"
```

### Ejecución de Comandos (uv run)

**La característica clave de uv**: ejecuta comandos en el contexto del entorno virtual sin activarlo.

```bash
# Django management commands
uv run python manage.py runserver
uv run python manage.py migrate
uv run python manage.py createsuperuser
uv run python manage.py shell

# Celery
uv run celery -A config worker -l info

# Tests
uv run pytest
uv run pytest --cov=apps

# Scripts Python
uv run python script.py

# Módulos Python
uv run python -m spacy download es_core_news_sm

# Cualquier comando instalado
uv run black .
uv run ruff check .
uv run mypy apps/
```

### Gestión de Dependencias

```bash
# Listar paquetes instalados
uv pip list

# Mostrar información de un paquete
uv pip show django

# Congelar dependencias
uv pip freeze

# Exportar a requirements.txt
uv pip freeze > requirements.txt

# Verificar dependencias
uv pip check

# Desinstalar paquete
uv pip uninstall django

# Desinstalar todo
uv pip freeze | uv pip uninstall -r /dev/stdin
```

### Lock Files

```bash
# uv automáticamente genera uv.lock
# NO necesitas ejecutar comandos manualmente

# Para sincronizar con uv.lock
uv sync

# Para actualizar uv.lock
uv lock --upgrade
```

---

## 🆚 Comparación: pip vs uv

| Comando | pip tradicional | uv equivalente |
|---------|----------------|----------------|
| Crear venv | `python -m venv .venv` | `uv venv --python 3.12` |
| Activar venv | `source .venv/bin/activate` | *(no necesario con uv run)* |
| Instalar | `pip install django` | `uv pip install django` |
| Instalar dev | `pip install -e ".[dev]"` | `uv pip install -e ".[dev]"` |
| Ejecutar comando | `python manage.py migrate` | `uv run python manage.py migrate` |
| Listar paquetes | `pip list` | `uv pip list` |
| Freeze | `pip freeze` | `uv pip freeze` |

---

## 🎯 Flujo de Trabajo Recomendado SIGRP

### Setup Inicial (una vez)

```bash
# 1. Crear entorno virtual
uv venv --python 3.12

# 2. Instalar dependencias
uv pip install -e ".[dev]"

# 3. Levantar Docker
docker-compose up -d

# 4. Configurar .env
cp .env.example .env

# 5. Ejecutar migraciones
uv run python manage.py migrate

# 6. Crear superusuario
uv run python manage.py createsuperuser
```

### Desarrollo Diario

```bash
# Terminal 1: Django server
uv run python manage.py runserver

# Terminal 2: Celery worker
uv run celery -A config worker -l info

# Terminal 3: Comandos según necesites
uv run python manage.py makemigrations
uv run python manage.py migrate
uv run python manage.py shell
uv run pytest
```

### Agregar Nuevas Dependencias

```bash
# 1. Instalar paquete
uv pip install nombre-paquete

# 2. Agregar al pyproject.toml manualmente
# Editar la sección dependencies = [...]

# 3. Reinstalar para actualizar lock
uv pip install -e ".[dev]"
```

---

## 🔧 Troubleshooting

### "Command not found: uv"

```bash
# Verificar que uv esté en PATH
# macOS/Linux
echo $PATH | grep -o '[^:]*uv[^:]*'

# Reinstalar uv
curl -LsSf https://astral.sh/uv/install.sh | sh
source $HOME/.cargo/env
```

### "No such file or directory: '.venv'"

```bash
# Crear entorno virtual
uv venv --python 3.12
```

### Conflictos de Versiones

```bash
# Limpiar caché de uv
uv cache clean

# Eliminar entorno y recrear
rm -rf .venv
uv venv --python 3.12
uv pip install -e ".[dev]"
```

### Error "Package not found"

```bash
# Verificar que pyproject.toml tenga el paquete
cat pyproject.toml | grep nombre-paquete

# Reinstalar todo
uv pip install -e ".[dev]"
```

---

## 📖 Recursos Adicionales

- **Documentación oficial:** https://docs.astral.sh/uv/
- **GitHub:** https://github.com/astral-sh/uv
- **Comparación de rendimiento:** https://astral.sh/blog/uv

---

## 💡 Tips y Mejores Prácticas

### 1. Siempre usa `uv run` para consistencia

```bash
# ✅ BIEN
uv run python manage.py migrate

# ❌ EVITAR (a menos que hayas activado manualmente)
python manage.py migrate
```

### 2. No commitear .venv

```bash
# Ya está en .gitignore
echo ".venv/" >> .gitignore
```

### 3. uv.lock es importante

```bash
# SÍ commitear uv.lock (garantiza reproducibilidad)
git add uv.lock
git commit -m "Update dependencies"
```

### 4. Usar pyproject.toml como fuente de verdad

```toml
# Definir todas las dependencias aquí
[project]
dependencies = [
    "django>=5.0,<6.0",
    "celery>=5.3.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "black>=23.12.0",
]
```

### 5. Scripts personalizados

Puedes crear alias en tu shell:

```bash
# .bashrc o .zshrc
alias uvrun='uv run python manage.py'
alias uvserver='uv run python manage.py runserver'
alias uvmigrate='uv run python manage.py migrate'
alias uvshell='uv run python manage.py shell'

# Uso:
uvserver  # en lugar de uv run python manage.py runserver
uvmigrate  # en lugar de uv run python manage.py migrate
```

---

**Versión:** 1.0
**Última actualización:** 14 de febrero de 2026
