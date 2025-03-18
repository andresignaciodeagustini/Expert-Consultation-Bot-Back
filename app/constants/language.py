# app/constants/language.py

# Valor por defecto del último idioma detectado
LAST_DETECTED_LANGUAGE = 'en-US'

def update_last_detected_language(language):
    """
    Función para actualizar el último idioma detectado
    
    :param language: Código de idioma (ej. 'es-ES', 'fr-FR')
    :return: None
    """
    global LAST_DETECTED_LANGUAGE
    
    # Solo actualizar si:
    # 1. El idioma no es None
    # 2. El idioma es diferente al actual
    # 3. La detección de idioma es confiable (no es un texto muy corto)
    if (language and 
        language != LAST_DETECTED_LANGUAGE and 
        len(str(language)) > 2):
        LAST_DETECTED_LANGUAGE = language
    
    return LAST_DETECTED_LANGUAGE

def get_last_detected_language():
    """
    Obtener el último idioma detectado
    
    :return: Código de idioma actual
    """
    return LAST_DETECTED_LANGUAGE

def reset_last_detected_language():
    """
    Resetear al idioma por defecto
    
    :return: Idioma por defecto
    """
    global LAST_DETECTED_LANGUAGE
    LAST_DETECTED_LANGUAGE = 'en-US'
    return LAST_DETECTED_LANGUAGE