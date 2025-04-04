# Valor por defecto del último idioma detectado
LAST_DETECTED_LANGUAGE = 'en-US'  # Idioma predeterminado (inglés)

def update_last_detected_language(language):
    """
    Función para actualizar el último idioma detectado
    
    :param language: Código de idioma (ej. 'es-ES', 'fr-FR')
    :return: El idioma actualizado
    """
    global LAST_DETECTED_LANGUAGE
    
    # Normalizar el formato del idioma
    if language and isinstance(language, str):
        # Si es solo código ISO (ej. 'en' en lugar de 'en-US')
        if len(language) == 2 and '-' not in language:
            # Mapeo de códigos ISO a códigos regionales
            language_map = {
                'es': 'es-ES', 'en': 'en-US', 'fr': 'fr-FR', 'de': 'de-DE', 
                'it': 'it-IT', 'pt': 'pt-PT', 'ru': 'ru-RU', 'zh': 'zh-CN', 
                'ja': 'ja-JP', 'ko': 'ko-KR', 'ar': 'ar-SA', 'hi': 'hi-IN'
                # Añadir más idiomas según sea necesario
            }
            language = language_map.get(language.lower(), f"{language.lower()}-{language.upper()}")
    
    # Solo actualizar si:
    # 1. El idioma no es None
    # 2. El idioma es una cadena válida
    # 3. El idioma tiene el formato correcto (como 'xx-XX')
    if (language and 
        isinstance(language, str) and 
        len(language) >= 4 and 
        '-' in language):
        LAST_DETECTED_LANGUAGE = language
    
    return LAST_DETECTED_LANGUAGE

def get_last_detected_language():
    """
    Obtener el último idioma detectado
    
    :return: Código de idioma actual
    """
    return LAST_DETECTED_LANGUAGE

def reset_last_detected_language(default_language='en-US'):
    """
    Resetear al idioma por defecto
    
    :param default_language: Idioma por defecto a establecer
    :return: Idioma por defecto
    """
    global LAST_DETECTED_LANGUAGE
    LAST_DETECTED_LANGUAGE = default_language
    return LAST_DETECTED_LANGUAGE