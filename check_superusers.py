"""
Verificar y mostrar superusuarios existentes
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User

superusers = User.objects.filter(is_superuser=True)

print(f"Total de superusuarios: {superusers.count()}\n")

if superusers.exists():
    print("Superusuarios encontrados:")
    for user in superusers:
        print(f"  - Usuario: {user.username}")
        print(f"    Email: {user.email}")
        print(f"    Activo: {'Sí' if user.is_active else 'No'}")
        print(f"    Último login: {user.last_login or 'Nunca'}")
        print()
else:
    print("❌ No hay superusuarios creados.")
    print("\nPara crear uno, ejecuta:")
    print("  uv run python manage.py createsuperuser")
