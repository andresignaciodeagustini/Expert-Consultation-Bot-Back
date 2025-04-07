# language.py - Módulo mejorado de detección y consistencia de idioma

import re
from typing import Dict, List, Optional, Tuple
import os

# Estado del módulo de idioma
class LanguageState:
    def __init__(self):
        self.current_language = 'en-US'  # Idioma actual
        self.language_history = []       # Historial de idiomas detectados
        self.conversation_context = []   # Historial simplificado de la conversación
        self.max_history = 10           # Número máximo de entradas en el historial
        
        # Mapeo de códigos ISO a códigos regionales
        self.language_map = {
            'es': 'es-ES', 'en': 'en-US', 'fr': 'fr-FR', 'de': 'de-DE', 
            'it': 'it-IT', 'pt': 'pt-PT', 'ru': 'ru-RU', 'zh': 'zh-CN', 
            'ja': 'ja-JP', 'ko': 'ko-KR', 'ar': 'ar-SA', 'hi': 'hi-IN',
            # Más idiomas comunes
            'nl': 'nl-NL', 'pl': 'pl-PL', 'tr': 'tr-TR', 'sv': 'sv-SE',
            'da': 'da-DK', 'fi': 'fi-FI', 'no': 'no-NO', 'cs': 'cs-CZ',
            'hu': 'hu-HU', 'el': 'el-GR', 'he': 'he-IL', 'th': 'th-TH',
            'vi': 'vi-VN', 'id': 'id-ID', 'ms': 'ms-MY', 'uk': 'uk-UA'
        }
        
        # Patrones lingüísticos específicos (caracteres y patrones por idioma)
        self.language_patterns = {
            'es': {
                'chars': set('áéíóúüñ¿¡'),
                'common_words': ['el', 'la', 'los', 'las', 'un', 'una', 'y', 'o', 'pero', 'porque', 'como', 'qué', 'cuándo', 'dónde', 'quién']
            },
            'en': {
                'chars': set(),  # Inglés usa principalmente ASCII básico
                'common_words': ['the', 'a', 'an', 'and', 'or', 'but', 'because', 'what', 'when', 'where', 'who', 'how']
            },
            'fr': {
                'chars': set('éèêëàâäôöùûüÿçÉÈÊËÀÂÄÔÖÙÛÜŸÇ'),
                'common_words': ['le', 'la', 'les', 'un', 'une', 'et', 'ou', 'mais', 'parce', 'que', 'quand', 'où', 'qui', 'comment']
            },
            'de': {
                'chars': set('äöüßÄÖÜ'),
                'common_words': ['der', 'die', 'das', 'ein', 'eine', 'und', 'oder', 'aber', 'weil', 'was', 'wann', 'wo', 'wer', 'wie']
            },
            'it': {
                'chars': set('àèéìòù'),
                'common_words': ['il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una', 'e', 'o', 'ma', 'perché', 'cosa', 'quando', 'dove', 'chi', 'come']
            },
            'pt': {
                'chars': set('áàâãéêíóôõúüç'),
                'common_words': ['o', 'a', 'os', 'as', 'um', 'uma', 'e', 'ou', 'mas', 'porque', 'que', 'quando', 'onde', 'quem', 'como']
            }
            # Puedes agregar más idiomas según necesites
        }
        
        # Palabras ambiguas que son similares en varios idiomas
        self.ambiguous_words = set([
            # Afirmación/negación
            'no', 'yes', 'si', 'oui', 'non', 'ja', 'nein', 'ok', 'okay',
            
            # Saludos cortos
            'hi', 'hey', 'bye', 'hola', 'adios', 'ciao', 'salut',
            
            # Números y medidas
            'one', 'two', 'three', 'uno', 'dos', 'tres', 'un', 'deux', 'trois',
            
            # Pronombres
            'i', 'you', 'he', 'she', 'we', 'they', 'yo', 'tu', 'él', 'ella', 'je', 'tu', 'il', 'elle',
            
            # Palabras técnicas/internacionales
            'tech', 'it', 'software', 'data', 'cloud', 'web', 'online', 'app', 'net', 'digital',
            'email', 'internet', 'wifi', 'blog', 'post', 'chat', 'video', 'audio', 'photo',
            
            # Emojis y símbolos (como strings)
            ':)', ':(', ':D', ';)', '?', '!', '...'
        ])

# Instancia global del estado de idioma
_language_state = LanguageState()

def normalize_language_code(language_code: str) -> str:
    """
    Normaliza el código de idioma al formato estándar (xx-XX)
    
    Args:
        language_code: Código de idioma en cualquier formato
        
    Returns:
        Código de idioma normalizado
    """
    if not language_code or not isinstance(language_code, str):
        return _language_state.current_language
    
    # Eliminar espacios y convertir a minúsculas
    language_code = language_code.strip().lower()
    
    # Si ya tiene formato regional (xx-XX)
    if '-' in language_code and len(language_code) >= 4:
        base_code = language_code.split('-')[0]
        # Verificar si el código base existe en nuestro mapeo
        if base_code in _language_state.language_map:
            return _language_state.language_map[base_code]
        return language_code
    
    # Si es solo código ISO (xx)
    if len(language_code) == 2:
        return _language_state.language_map.get(
            language_code, 
            f"{language_code}-{language_code.upper()}"
        )
    
    # Si no se puede normalizar, devolver el idioma actual
    return _language_state.current_language

def is_text_ambiguous(text: str) -> bool:
    """
    Determina si un texto es ambiguo para la detección de idioma
    
    Args:
        text: Texto a analizar
        
    Returns:
        True si el texto es ambiguo, False en caso contrario
    """
    # Eliminar espacios y convertir a minúsculas
    cleaned_text = text.strip().lower()
    
    # Criterios de ambigüedad:
    # 1. Texto muy corto
    if len(cleaned_text) <= 4:
        return True
        
    # 2. Texto es una palabra ambigua conocida
    if cleaned_text in _language_state.ambiguous_words:
        return True
    
    # 3. Texto contiene principalmente símbolos o números
    alpha_ratio = sum(c.isalpha() for c in cleaned_text) / max(len(cleaned_text), 1)
    if alpha_ratio < 0.5:
        return True
        
    # 4. Texto es muy corto (una sola palabra)
    if len(cleaned_text.split()) <= 1:
        return True
        
    return False

def analyze_language_patterns(text: str) -> Dict[str, float]:
    """
    Analiza los patrones lingüísticos en el texto para determinar el idioma probable
    
    Args:
        text: Texto a analizar
        
    Returns:
        Diccionario con puntuaciones para cada idioma
    """
    # Texto limpio para análisis
    cleaned_text = text.lower()
    words = re.findall(r'\b\w+\b', cleaned_text)
    
    scores = {}
    
    # Analizar patrones para cada idioma
    for lang, patterns in _language_state.language_patterns.items():
        score = 0.0
        
        # Puntuación por caracteres específicos
        char_matches = sum(1 for c in cleaned_text if c in patterns['chars'])
        char_score = char_matches / max(len(cleaned_text), 1) * 100
        
        # Puntuación por palabras comunes
        word_matches = sum(1 for word in words if word in patterns['common_words'])
        word_score = word_matches / max(len(words), 1) * 100
        
        # Combinación de puntuaciones (caracteres tienen más peso para idiomas distintivos)
        if patterns['chars']:
            score = (char_score * 0.7) + (word_score * 0.3)
        else:
            score = word_score
            
        scores[lang] = score
    
    return scores

def evaluate_context_consistency(detected_lang: str) -> float:
    """
    Evalúa la consistencia del idioma detectado con el contexto previo
    
    Args:
        detected_lang: Código ISO del idioma detectado
        
    Returns:
        Puntuación de consistencia (0-1)
    """
    if not _language_state.language_history:
        return 0.5  # Neutral si no hay historial
    
    # Contar frecuencia de idiomas en el historial
    lang_counts = {}
    for lang in _language_state.language_history:
        base_lang = lang.split('-')[0]
        lang_counts[base_lang] = lang_counts.get(base_lang, 0) + 1
    
    # Calcular consistencia basada en frecuencia
    detected_base = detected_lang.split('-')[0]
    total_entries = len(_language_state.language_history)
    
    consistency = lang_counts.get(detected_base, 0) / total_entries
    
    # Dar más peso a entradas recientes
    if _language_state.language_history and detected_base == _language_state.language_history[-1].split('-')[0]:
        consistency += 0.2  # Bonus por coincidencia con el último idioma
    
    return min(consistency, 1.0)  # Limitar a 1.0

def detect_language(text: str) -> Tuple[str, float]:
    """
    Detecta el idioma del texto usando análisis de patrones lingüísticos
    
    Args:
        text: Texto a analizar
        
    Returns:
        Tuple con (código_idioma, confianza)
    """
    # Si el texto está vacío, mantener el idioma actual
    if not text or not text.strip():
        return _language_state.current_language, 1.0
    
    # Para textos ambiguos, preferir el idioma actual
    if is_text_ambiguous(text):
        return _language_state.current_language, 0.8
    
    # Analizar patrones lingüísticos
    lang_scores = analyze_language_patterns(text)
    
    if not lang_scores:
        return _language_state.current_language, 0.5
    
    # Encontrar el idioma con mayor puntuación
    best_lang = max(lang_scores.items(), key=lambda x: x[1])
    lang_code, score = best_lang
    
    # Normalizar la confianza a un rango de 0-1
    confidence = min(score / 100, 1.0)
    
    # Evaluar consistencia con el contexto
    context_score = evaluate_context_consistency(lang_code)
    
    # Combinar puntuación de patrones y consistencia
    combined_confidence = (confidence * 0.7) + (context_score * 0.3)
    
    # Si la confianza es muy baja, mantener el idioma actual
    if combined_confidence < 0.4:
        return _language_state.current_language, 0.5
    
    # Obtener código regional del idioma
    detected_language = normalize_language_code(lang_code)
    
    return detected_language, combined_confidence

def update_last_detected_language(language: Optional[str] = None, text: Optional[str] = None) -> str:
    """
    Actualiza el último idioma detectado con lógica avanzada
    
    Args:
        language: Código de idioma proporcionado externamente (opcional)
        text: Texto para detectar idioma (si no se proporciona language)
        
    Returns:
        Código de idioma actualizado
    """
    detected_language = _language_state.current_language
    confidence = 0.5
    
    # Si se proporciona texto pero no idioma, detectar idioma
    if text and not language:
        detected_language, confidence = detect_language(text)
    # Si se proporciona idioma, normalizar
    elif language:
        detected_language = normalize_language_code(language)
        confidence = 0.9  # Alta confianza para detecciones externas
    
    # Actualizar el historial solo si hay suficiente confianza
    if confidence >= 0.5:
        _language_state.current_language = detected_language
        _language_state.language_history.append(detected_language)
        
        # Mantener historial con tamaño máximo
        if len(_language_state.language_history) > _language_state.max_history:
            _language_state.language_history.pop(0)
    
    # Actualizar contexto de conversación si se proporciona texto
    if text:
        _language_state.conversation_context.append(text[:100])  # Guardar solo los primeros 100 caracteres
        
        # Mantener contexto con tamaño máximo
        if len(_language_state.conversation_context) > _language_state.max_history:
            _language_state.conversation_context.pop(0)
    
    return _language_state.current_language

def get_last_detected_language() -> str:
    """
    Obtiene el último idioma detectado
    
    Returns:
        Código de idioma actual
    """
    return _language_state.current_language

def get_language_history() -> List[str]:
    """
    Obtiene el historial de idiomas detectados
    
    Returns:
        Lista de códigos de idioma detectados
    """
    return _language_state.language_history.copy()

def reset_last_detected_language(default_language: str = 'en-US') -> str:
    """
    Resetear al idioma por defecto
    
    :param default_language: Idioma por defecto a establecer
    :return: Idioma por defecto
    """
    return reset_language_state(default_language)

def reset_language_state(default_language: str = 'en-US') -> str:
    """
    Reinicia el estado del idioma
    
    Args:
        default_language: Idioma por defecto
        
    Returns:
        Idioma por defecto establecido
    """
    _language_state.current_language = default_language
    _language_state.language_history = []
    _language_state.conversation_context = []
    return default_language

def process_message(text: str) -> Dict:
    """
    Procesa un mensaje completo con detección de idioma avanzada
    
    Args:
        text: Texto del mensaje
        
    Returns:
        Diccionario con información de detección
    """
    previous_language = _language_state.current_language
    
    # Si el texto está vacío, mantener el idioma actual
    if not text or not text.strip():
        return {
            "success": True,
            "text": text,
            "detected_language": previous_language,
            "previous_language": previous_language,
            "confidence": 1.0
        }
    
    # Para textos ambiguos, preferir mantener el idioma actual
    if is_text_ambiguous(text):
        return {
            "success": True,
            "text": text,
            "detected_language": previous_language,
            "previous_language": previous_language,
            "confidence": 0.8,
            "is_ambiguous": True
        }
    
    # Detectar idioma con análisis de patrones
    detected_language, confidence = detect_language(text)
    
    # Actualizar el estado global
    updated_language = update_last_detected_language(detected_language)
    
    return {
        "success": True,
        "text": text,
        "detected_language": updated_language,
        "previous_language": previous_language,
        "confidence": confidence,
        "is_ambiguous": False
    }