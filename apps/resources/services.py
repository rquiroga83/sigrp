"""
Servicio de embeddings y sincronización con Qdrant para búsqueda semántica de talento.
"""
import logging
from typing import List, Dict, Any, Optional
from django.conf import settings
import uuid

logger = logging.getLogger(__name__)


class VectorService:
    """
    Servicio para generar embeddings y gestionar sincronización con Qdrant.
    Usa sentence-transformers localmente para búsqueda semántica de recursos.
    """
    
    def __init__(self):
        """Inicializa el modelo de embeddings y cliente Qdrant (lazy loading)."""
        self.model_name = "sentence-transformers/all-MiniLM-L6-v2"
        self.collection_name = "resources_skills"
        self.vector_size = 384  # Dimensión del modelo all-MiniLM-L6-v2
        self._model = None
        self._client = None
    
    @property
    def model(self):
        """Lazy loading del modelo de embeddings."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                logger.info(f"✅ Modelo {self.model_name} cargado exitosamente")
            except Exception as e:
                logger.error(f"❌ Error cargando modelo: {e}")
                self._model = None
        return self._model
    
    @property
    def client(self):
        """Lazy loading del cliente Qdrant."""
        if self._client is None:
            try:
                from qdrant_client import QdrantClient
                qdrant_host = getattr(settings, 'QDRANT_HOST', 'localhost')
                qdrant_port = getattr(settings, 'QDRANT_PORT', 6333)
                
                self._client = QdrantClient(host=qdrant_host, port=qdrant_port)
                self._ensure_collection_exists()
                logger.info(f"✅ Conectado a Qdrant en {qdrant_host}:{qdrant_port}")
            except Exception as e:
                logger.error(f"❌ Error conectando a Qdrant: {e}")
                self._client = None
        return self._client
    
    def _ensure_collection_exists(self):
        """Crea la colección en Qdrant si no existe."""
        from qdrant_client.models import Distance, VectorParams
        try:
            collections = self.client.get_collections().collections
            collection_names = [c.name for c in collections]
            
            if self.collection_name not in collection_names:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=self.vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✅ Colección '{self.collection_name}' creada")
            else:
                logger.info(f"✅ Colección '{self.collection_name}' ya existe")
        except Exception as e:
            logger.error(f"❌ Error creando colección: {e}")
    
    def skills_to_narrative(self, skills_vector: List[Dict[str, Any]]) -> str:
        """
        Convierte el JSON de skills_vector en texto narrativo semántico.
        
        Regla de niveles:
        - 1: Novice/Beginner
        - 2: Basic
        - 3: Intermediate
        - 4: Advanced
        - 5: Expert
        
        Args:
            skills_vector: Lista de dict con 'name' y 'level'
                          Ejemplo: [{"name": "Django", "level": 5}, {"name": "React", "level": 3}]
        
        Returns:
            Texto narrativo semántico
            Ejemplo: "Expert in Django Backend Framework. Intermediate knowledge in React Frontend."
        """
        if not skills_vector:
            return "No specific skills listed."
        
        # Mapeo de niveles a términos semánticos
        level_map = {
            1: "Novice",
            2: "Basic knowledge",
            3: "Intermediate",
            4: "Advanced",
            5: "Expert"
        }
        
        # Contexto adicional para términos técnicos comunes
        tech_context = {
            "django": "Backend Framework",
            "react": "Frontend Framework",
            "python": "Programming Language",
            "javascript": "Programming Language",
            "typescript": "Programming Language",
            "java": "Programming Language",
            "sql": "Database Query Language",
            "postgresql": "Database System",
            "mongodb": "NoSQL Database",
            "aws": "Cloud Platform",
            "azure": "Cloud Platform",
            "docker": "Containerization Technology",
            "kubernetes": "Container Orchestration",
            "api": "Integration Technology",
            "rest": "API Architecture",
            "graphql": "API Query Language",
            "git": "Version Control System",
            "agile": "Development Methodology",
            "scrum": "Agile Framework",
        }
        
        narratives = []
        for skill in skills_vector:
            name = skill.get('name', '').strip()
            level = skill.get('level', 1)
            
            if not name:
                continue
            
            # Obtener descripción del nivel
            level_desc = level_map.get(level, "Familiar with")
            
            # Agregar contexto si está disponible
            name_lower = name.lower()
            context = tech_context.get(name_lower, "")
            
            if context:
                narrative = f"{level_desc} in {name} {context}"
            else:
                narrative = f"{level_desc} in {name}"
            
            narratives.append(narrative)
        
        # Construir texto final
        if len(narratives) == 0:
            return "No specific skills listed."
        elif len(narratives) == 1:
            return narratives[0] + "."
        else:
            return ". ".join(narratives) + "."
    
    def generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Genera embedding para un texto dado.
        
        Args:
            text: Texto a vectorizar
        
        Returns:
            Vector de embeddings (lista de floats) o None si hay error
        """
        if not self.model:
            logger.error("❌ Modelo no disponible")
            return None
        
        try:
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"❌ Error generando embedding: {e}")
            return None
    
    def upsert_resource(self, resource) -> bool:
        """
        Inserta o actualiza un recurso en Qdrant.
        
        Args:
            resource: Instancia del modelo Resource
        
        Returns:
            True si tuvo éxito, False en caso contrario
        """
        if not self.client or not self.model:
            logger.error("❌ Cliente Qdrant o modelo no disponibles")
            return False
        
        try:
            # Generar texto narrativo desde skills_vector
            skills_text = self.skills_to_narrative(resource.skills_vector)
            
            # Agregar información adicional del recurso
            full_text = (
                f"{resource.full_name}. "
                f"Role: {resource.primary_role.name}. "
                f"Skills: {skills_text}"
            )
            
            # Generar embedding
            embedding = self.generate_embedding(full_text)
            if not embedding:
                logger.error(f"❌ No se pudo generar embedding para {resource.full_name}")
                return False
            
            # Generar o reutilizar qdrant_point_id
            if not resource.qdrant_point_id:
                resource.qdrant_point_id = str(uuid.uuid4())
                resource.save(update_fields=['qdrant_point_id'])
            
            # Preparar payload con metadatos
            payload = {
                "resource_id": resource.id,
                "employee_id": resource.employee_id,
                "full_name": resource.full_name,
                "email": resource.email,
                "role": resource.primary_role.name,
                "role_category": resource.primary_role.category,
                "internal_cost": float(resource.internal_cost),
                "is_active": resource.is_active,
                "skills_text": skills_text,
                "skills_count": len(resource.skills_vector),
            }
            
            # Upsert en Qdrant
            from qdrant_client.models import PointStruct
            point = PointStruct(
                id=resource.qdrant_point_id,
                vector=embedding,
                payload=payload
            )
            
            self.client.upsert(
                collection_name=self.collection_name,
                points=[point]
            )
            
            logger.info(f"✅ Resource {resource.full_name} sincronizado en Qdrant")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error upserting resource {resource.id}: {e}")
            return False
    
    def delete_resource(self, qdrant_point_id: str) -> bool:
        """
        Elimina un recurso de Qdrant.
        
        Args:
            qdrant_point_id: ID del punto en Qdrant
        
        Returns:
            True si tuvo éxito, False en caso contrario
        """
        if not self.client:
            logger.error("❌ Cliente Qdrant no disponible")
            return False
        
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=[qdrant_point_id]
            )
            logger.info(f"✅ Resource eliminado de Qdrant: {qdrant_point_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Error eliminando resource: {e}")
            return False
    
    def search_resources(
        self, 
        query: str, 
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Búsqueda semántica de recursos.
        
        Args:
            query: Texto de búsqueda (ej: "Busco desarrollador python experto")
            limit: Cantidad máxima de resultados
            filters: Filtros adicionales (ej: {"is_active": True})
        
        Returns:
            Lista de recursos ordenados por similitud con scores
        """
        if not self.client or not self.model:
            logger.error("❌ Cliente Qdrant o modelo no disponibles")
            return []
        
        try:
            # Generar embedding de la query
            query_embedding = self.generate_embedding(query)
            if not query_embedding:
                logger.error("❌ No se pudo generar embedding para la query")
                return []
            
            # Preparar filtros de Qdrant
            query_filter = None
            if filters:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                conditions = []
                
                for key, value in filters.items():
                    conditions.append(
                        FieldCondition(
                            key=key,
                            match=MatchValue(value=value)
                        )
                    )
                
                if conditions:
                    query_filter = Filter(must=conditions)
            
            # Búsqueda en Qdrant
            results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=limit
            )
            
            # Formatear resultados
            formatted_results = []
            for result in results:
                formatted_results.append({
                    "resource_id": result.payload.get("resource_id"),
                    "employee_id": result.payload.get("employee_id"),
                    "full_name": result.payload.get("full_name"),
                    "email": result.payload.get("email"),
                    "role": result.payload.get("role"),
                    "internal_cost": result.payload.get("internal_cost"),
                    "skills_text": result.payload.get("skills_text"),
                    "similarity_score": result.score,  # 0-1 (COSINE)
                })
            
            logger.info(f"✅ Búsqueda completada: {len(formatted_results)} resultados")
            return formatted_results
            
        except Exception as e:
            logger.error(f"❌ Error en búsqueda semántica: {e}")
            return []


# Instancia singleton del servicio
vector_service = VectorService()
