"""
Signals para sincronización automática de Resources con Qdrant.
"""
import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Resource
from .services import vector_service

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Resource)
def sync_resource_to_qdrant(sender, instance, created, **kwargs):
    """
    Signal que se dispara después de guardar un Resource.
    Sincroniza automáticamente con Qdrant para búsqueda semántica.
    """
    # Solo sincronizar si el recurso está activo
    if instance.is_active:
        logger.info(f"🔄 Sincronizando resource {instance.full_name} con Qdrant...")
        success = vector_service.upsert_resource(instance)
        
        if success:
            action = "creado" if created else "actualizado"
            logger.info(f"✅ Resource {instance.full_name} {action} en Qdrant")
        else:
            logger.error(f"❌ Error sincronizando {instance.full_name} con Qdrant")
    else:
        # Si está inactivo y tiene ID en Qdrant, eliminarlo
        if instance.qdrant_point_id:
            logger.info(f"🗑️ Eliminando resource inactivo {instance.full_name} de Qdrant")
            vector_service.delete_resource(instance.qdrant_point_id)


@receiver(post_delete, sender=Resource)
def delete_resource_from_qdrant(sender, instance, **kwargs):
    """
    Signal que se dispara después de eliminar un Resource.
    Elimina el punto correspondiente de Qdrant.
    """
    if instance.qdrant_point_id:
        logger.info(f"🗑️ Eliminando resource {instance.full_name} de Qdrant...")
        success = vector_service.delete_resource(instance.qdrant_point_id)
        
        if success:
            logger.info(f"✅ Resource {instance.full_name} eliminado de Qdrant")
        else:
            logger.error(f"❌ Error eliminando {instance.full_name} de Qdrant")
