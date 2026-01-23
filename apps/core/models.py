"""
Modelos base abstractos para el sistema SIGRP.
"""
from django.db import models
from django.contrib.auth.models import User


class TimeStampedModel(models.Model):
    """Modelo abstracto con campos de auditoría temporal."""
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Fecha de creación")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Última actualización")

    class Meta:
        abstract = True


class AuditableModel(TimeStampedModel):
    """Modelo abstracto con auditoría completa."""
    
    created_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name="%(class)s_created",
        verbose_name="Creado por"
    )
    updated_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name="%(class)s_updated",
        verbose_name="Actualizado por"
    )

    class Meta:
        abstract = True
