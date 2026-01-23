"""
Utilidades NLP para análisis de sentimiento en standups.
"""
import spacy
from typing import Dict, List, Tuple
from django.conf import settings


class SentimentAnalyzer:
    """
    Analizador de sentimiento usando spaCy.
    Utiliza el modelo de español configurado en settings.
    """
    
    def __init__(self):
        self.nlp = None
        self._load_model()
    
    def _load_model(self):
        """Carga el modelo de spaCy."""
        try:
            model_name = getattr(settings, 'SPACY_MODEL', 'es_core_news_sm')
            self.nlp = spacy.load(model_name)
        except Exception as e:
            print(f"Error loading spaCy model: {e}")
            self.nlp = None
    
    def analyze_sentiment(self, text: str) -> Dict:
        """
        Analiza el sentimiento de un texto.
        
        Returns:
            {
                'score': float (-1 a 1),
                'label': str ('positive', 'neutral', 'negative', 'very_negative'),
                'confidence': float (0 a 1)
            }
        """
        if not self.nlp or not text:
            return {'score': 0.0, 'label': 'neutral', 'confidence': 0.0}
        
        # Palabras positivas y negativas en español
        positive_words = {
            'bien', 'bueno', 'excelente', 'genial', 'fantástico', 'logré', 
            'completé', 'terminé', 'éxito', 'avance', 'progreso', 'fácil'
        }
        negative_words = {
            'mal', 'malo', 'difícil', 'problema', 'error', 'bloqueado', 
            'atascado', 'complicado', 'frustrado', 'imposible', 'lento', 'retraso'
        }
        
        doc = self.nlp(text.lower())
        
        # Contar palabras positivas y negativas
        positive_count = sum(1 for token in doc if token.text in positive_words)
        negative_count = sum(1 for token in doc if token.text in negative_words)
        
        # Calcular score simple
        total_words = len([token for token in doc if not token.is_stop and not token.is_punct])
        if total_words == 0:
            return {'score': 0.0, 'label': 'neutral', 'confidence': 0.5}
        
        score = (positive_count - negative_count) / max(total_words, 1)
        score = max(-1.0, min(1.0, score * 3))  # Normalizar entre -1 y 1
        
        # Determinar label
        if score >= 0.3:
            label = 'positive'
        elif score >= -0.1:
            label = 'neutral'
        elif score >= -0.5:
            label = 'negative'
        else:
            label = 'very_negative'
        
        # Calcular confianza basada en cantidad de palabras clave encontradas
        confidence = min(1.0, (positive_count + negative_count) / max(total_words * 0.2, 1))
        
        return {
            'score': round(score, 3),
            'label': label,
            'confidence': round(confidence, 3)
        }
    
    def extract_entities(self, text: str) -> List[Dict]:
        """
        Extrae entidades nombradas del texto.
        
        Returns:
            Lista de {'text': str, 'label': str}
        """
        if not self.nlp:
            return []
        
        doc = self.nlp(text)
        entities = []
        
        for ent in doc.ents:
            entities.append({
                'text': ent.text,
                'label': ent.label_
            })
        
        return entities
    
    def extract_keywords(self, text: str, top_n: int = 5) -> List[str]:
        """
        Extrae las keywords más importantes del texto.
        
        Returns:
            Lista de keywords ordenadas por relevancia
        """
        if not self.nlp:
            return []
        
        doc = self.nlp(text.lower())
        
        # Filtrar tokens: solo sustantivos, verbos y adjetivos
        keywords = [
            token.text for token in doc 
            if not token.is_stop 
            and not token.is_punct 
            and token.pos_ in ['NOUN', 'VERB', 'ADJ']
            and len(token.text) > 3
        ]
        
        # Contar frecuencias
        from collections import Counter
        keyword_freq = Counter(keywords)
        
        # Retornar top N
        return [word for word, _ in keyword_freq.most_common(top_n)]


# Instancia global del analizador
analyzer = SentimentAnalyzer()
