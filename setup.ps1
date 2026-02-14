# Script de inicialización automática SIGRP
# Para Windows PowerShell

Write-Host "🚀 Iniciando setup de SIGRP..." -ForegroundColor Green

# 1. Verificar uv instalado
Write-Host "`n📦 Verificando uv..." -ForegroundColor Cyan
if (!(Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "❌ uv no encontrado. Instalando..." -ForegroundColor Yellow
    powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
} else {
    Write-Host "✅ uv ya está instalado" -ForegroundColor Green
}

# 2. Crear entorno virtual
Write-Host "`n🐍 Creando entorno virtual..." -ForegroundColor Cyan
uv venv --python 3.12

# 3. Instalar dependencias (uv maneja el entorno automáticamente)
Write-Host "`n📚 Instalando dependencias..." -ForegroundColor Cyan
uv pip install -e ".[dev]"

# 5. Copiar .env si no existe
Write-Host "`n🔧 Configurando variables de entorno..." -ForegroundColor Cyan
if (!(Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "✅ Archivo .env creado. Por favor edítalo con tus credenciales." -ForegroundColor Yellow
} else {
    Write-Host "✅ Archivo .env ya existe" -ForegroundColor Green
}

# 6. Levantar Docker
Write-Host "`n🐳 Levantando servicios Docker..." -ForegroundColor Cyan
docker-compose up -d

# Esperar a que PostgreSQL esté listo
Write-Host "⏳ Esperando a PostgreSQL..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# 7. Ejecutar migraciones
Write-Host "`n🗄️ Ejecutando migraciones..." -ForegroundColor Cyan
uv run python manage.py makemigrations
uv run python manage.py migrate

# 8. Descargar modelo spaCy
Write-Host "`n🧠 Descargando modelo de spaCy..." -ForegroundColor Cyan
uv run python -m spacy download es_core_news_sm

# 9. Recolectar estáticos
Write-Host "`n📁 Recolectando archivos estáticos..." -ForegroundColor Cyan
uv run python manage.py collectstatic --noinput

Write-Host "`n✨ Setup completado!" -ForegroundColor Green
Write-Host "`nPróximos pasos:" -ForegroundColor Yellow
Write-Host "1. Edita el archivo .env con tus credenciales (si es necesario)"
Write-Host "2. Crea un superusuario: uv run python manage.py createsuperuser"
Write-Host "3. Ejecuta el servidor: uv run python manage.py runserver"
Write-Host "4. En otra terminal, ejecuta Celery: uv run celery -A config worker -l info --pool=solo"
Write-Host "`nAccede a: http://localhost:8000" -ForegroundColor Cyan
Write-Host "`n💡 Tip: Usa 'uv run' antes de cualquier comando Python para ejecutarlo en el entorno virtual" -ForegroundColor Yellow
