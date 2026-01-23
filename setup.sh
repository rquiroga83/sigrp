#!/bin/bash
# Script de inicialización automática SIGRP
# Para Linux/macOS

set -e

echo "🚀 Iniciando setup de SIGRP..."

# 1. Verificar uv instalado
echo ""
echo "📦 Verificando uv..."
if ! command -v uv &> /dev/null; then
    echo "❌ uv no encontrado. Instalando..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source $HOME/.cargo/env
else
    echo "✅ uv ya está instalado"
fi

# 2. Crear entorno virtual
echo ""
echo "🐍 Creando entorno virtual..."
uv venv --python 3.12

# 3. Activar entorno
echo ""
echo "⚡ Activando entorno virtual..."
source .venv/bin/activate

# 4. Instalar dependencias
echo ""
echo "📚 Instalando dependencias..."
uv pip install -e ".[dev]"

# 5. Copiar .env si no existe
echo ""
echo "🔧 Configurando variables de entorno..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✅ Archivo .env creado. Por favor edítalo con tus credenciales."
else
    echo "✅ Archivo .env ya existe"
fi

# 6. Levantar Docker
echo ""
echo "🐳 Levantando servicios Docker..."
docker-compose up -d

# Esperar a que PostgreSQL esté listo
echo "⏳ Esperando a PostgreSQL..."
sleep 5

# 7. Ejecutar migraciones
echo ""
echo "🗄️ Ejecutando migraciones..."
python manage.py makemigrations
python manage.py migrate

# 8. Descargar modelo spaCy
echo ""
echo "🧠 Descargando modelo de spaCy..."
python -m spacy download es_core_news_sm

# 9. Recolectar estáticos
echo ""
echo "📁 Recolectando archivos estáticos..."
python manage.py collectstatic --noinput

echo ""
echo "✨ Setup completado!"
echo ""
echo "Próximos pasos:"
echo "1. Edita el archivo .env con tus credenciales"
echo "2. Crea un superusuario: python manage.py createsuperuser"
echo "3. Ejecuta el servidor: python manage.py runserver"
echo "4. En otra terminal, ejecuta Celery: celery -A config worker -l info"
echo ""
echo "Accede a: http://localhost:8000"
