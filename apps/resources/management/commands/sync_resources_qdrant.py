"""
Comando para sincronizar todos los recursos activos con Qdrant.
Útil para inicialización o re-sincronización masiva.
"""
from django.core.management.base import BaseCommand
from apps.resources.models import Resource
from apps.resources.services import vector_service


class Command(BaseCommand):
    help = 'Sincroniza todos los recursos activos con Qdrant para búsqueda semántica'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Sincronizar todos los recursos, incluyendo inactivos',
        )

    def handle(self, *args, **options):
        sync_all = options.get('all', False)
        
        if sync_all:
            resources = Resource.objects.all()
            self.stdout.write(self.style.WARNING('Sincronizando TODOS los recursos...'))
        else:
            resources = Resource.objects.filter(is_active=True)
            self.stdout.write(self.style.SUCCESS('Sincronizando recursos activos...'))
        
        total = resources.count()
        self.stdout.write(f'Total de recursos a procesar: {total}')
        
        success_count = 0
        error_count = 0
        
        for resource in resources:
            self.stdout.write(f'Procesando: {resource.full_name}...', ending='')
            
            try:
                if resource.is_active:
                    success = vector_service.upsert_resource(resource)
                    if success:
                        self.stdout.write(self.style.SUCCESS(' ✓'))
                        success_count += 1
                    else:
                        self.stdout.write(self.style.ERROR(' ✗'))
                        error_count += 1
                else:
                    # Eliminar inactivos de Qdrant
                    if resource.qdrant_point_id:
                        vector_service.delete_resource(resource.qdrant_point_id)
                        self.stdout.write(self.style.WARNING(' (eliminado)'))
                    else:
                        self.stdout.write(self.style.WARNING(' (skip)'))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f' Error: {e}'))
                error_count += 1
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'✓ Sincronización completada:'))
        self.stdout.write(f'  - Exitosos: {success_count}')
        self.stdout.write(f'  - Errores: {error_count}')
        self.stdout.write(f'  - Total: {total}')
