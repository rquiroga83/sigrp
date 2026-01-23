"""
Celery tasks for standups app.
"""
from celery import shared_task
from django.utils import timezone
from django.db.models import Avg, Count, Q


@shared_task
def analyze_standup_sentiment(standup_id: int):
    """
    Analiza el sentimiento de un standup usando NLP.
    """
    from .models import StandupLog
    from .nlp_utils import analyzer
    
    try:
        standup = StandupLog.objects.get(id=standup_id)
        
        # Combinar todo el texto
        text = standup.get_combined_text()
        
        # Analizar sentimiento
        sentiment_result = analyzer.analyze_sentiment(text)
        standup.sentiment_score = sentiment_result['score']
        standup.sentiment_label = sentiment_result['label']
        standup.sentiment_confidence = sentiment_result['confidence']
        
        # Extraer entidades
        entities = analyzer.extract_entities(text)
        standup.detected_entities = entities
        
        # Extraer keywords
        keywords = analyzer.extract_keywords(text)
        standup.keywords = keywords
        
        # Marcar como procesado
        standup.nlp_processed = True
        standup.nlp_processed_at = timezone.now()
        
        standup.save()
        
        return f"Analyzed standup {standup_id}"
    
    except StandupLog.DoesNotExist:
        return f"Standup {standup_id} not found"
    except Exception as e:
        return f"Error analyzing standup {standup_id}: {str(e)}"


@shared_task
def analyze_recent_standups():
    """
    Analiza los standups recientes que no han sido procesados.
    """
    from .models import StandupLog
    
    # Obtener standups de los últimos 7 días sin procesar
    recent_date = timezone.now().date() - timezone.timedelta(days=7)
    unprocessed = StandupLog.objects.filter(
        date__gte=recent_date,
        nlp_processed=False
    )
    
    count = 0
    for standup in unprocessed:
        analyze_standup_sentiment.delay(standup.id)
        count += 1
    
    return f"Queued {count} standups for analysis"


@shared_task
def calculate_team_mood(project_id: int, date_str: str):
    """
    Calcula el mood agregado del equipo para un proyecto en una fecha.
    """
    from .models import StandupLog, TeamMood
    from datetime import datetime
    
    try:
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Obtener todos los standups del proyecto en esa fecha
        standups = StandupLog.objects.filter(
            project_id=project_id,
            date=date,
            nlp_processed=True
        )
        
        if not standups.exists():
            return f"No standups found for project {project_id} on {date}"
        
        # Calcular métricas agregadas
        sentiment_data = standups.aggregate(
            avg_sentiment=Avg('sentiment_score'),
            team_size=Count('id'),
            positive=Count('id', filter=Q(sentiment_label='positive')),
            neutral=Count('id', filter=Q(sentiment_label='neutral')),
            negative=Count('id', filter=Q(sentiment_label__in=['negative', 'very_negative'])),
            blocker_count=Count('id', filter=Q(has_blockers=True)),
            critical_blockers=Count('id', filter=Q(blocker_severity='critical'))
        )
        
        # Extraer keywords comunes
        all_keywords = []
        for standup in standups:
            all_keywords.extend(standup.keywords)
        
        from collections import Counter
        common_keywords = [word for word, _ in Counter(all_keywords).most_common(10)]
        
        # Determinar nivel de alerta
        avg_sentiment = sentiment_data['avg_sentiment'] or 0
        negative_ratio = sentiment_data['negative'] / sentiment_data['team_size']
        critical_blockers = sentiment_data['critical_blockers']
        
        if avg_sentiment < -0.3 or negative_ratio > 0.5 or critical_blockers > 0:
            alert_level = 'red'
        elif avg_sentiment < 0 or negative_ratio > 0.3:
            alert_level = 'yellow'
        else:
            alert_level = 'green'
        
        # Crear o actualizar TeamMood
        team_mood, created = TeamMood.objects.update_or_create(
            project_id=project_id,
            date=date,
            defaults={
                'average_sentiment': sentiment_data['avg_sentiment'],
                'team_size': sentiment_data['team_size'],
                'positive_count': sentiment_data['positive'],
                'neutral_count': sentiment_data['neutral'],
                'negative_count': sentiment_data['negative'],
                'blocker_count': sentiment_data['blocker_count'],
                'critical_blocker_count': sentiment_data['critical_blockers'],
                'common_keywords': common_keywords,
                'alert_level': alert_level
            }
        )
        
        return f"{'Created' if created else 'Updated'} team mood for project {project_id} on {date}"
    
    except Exception as e:
        return f"Error calculating team mood: {str(e)}"
