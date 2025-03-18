from langdetect import detect, detect_langs, LangDetectException

class TestController:
    def __init__(self):
        self.last_detected_language = 'en-US'
        self.lang_mapping = {
            # Europeos
            'en': 'en-GB',  # Inglés
            'es': 'es-ES',  # Español
            'fr': 'fr-FR',  # Francés
            'de': 'de-DE',  # Alemán
            'it': 'it-IT',  # Italiano
            'pt': 'pt-PT',  # Portugués
            'nl': 'nl-NL',  # Holandés
            'sv': 'sv-SE',  # Sueco
            'da': 'da-DK',  # Danés
            'no': 'nb-NO',  # Noruego
            'fi': 'fi-FI',  # Finlandés
            'pl': 'pl-PL',  # Polaco
            'cs': 'cs-CZ',  # Checo
            'sk': 'sk-SK',  # Eslovaco
            'hu': 'hu-HU',  # Húngaro
            'ro': 'ro-RO',  # Rumano
            'el': 'el-GR',  # Griego
            'bg': 'bg-BG',  # Búlgaro
            'hr': 'hr-HR',  # Croata
            'sr': 'sr-RS',  # Serbio
            
            # Asiáticos
            'ru': 'ru-RU',  # Ruso
            'uk': 'uk-UA',  # Ucraniano
            'ja': 'ja-JP',  # Japonés
            'ko': 'ko-KR',  # Coreano
            'zh-cn': 'zh-CN',  # Chino (Simplificado)
            'zh-tw': 'zh-TW',  # Chino (Tradicional)
            'hi': 'hi-IN',  # Hindi
            'ar': 'ar-SA',  # Árabe
            'tr': 'tr-TR',  # Turco
            'fa': 'fa-IR',  # Persa
            'he': 'he-IL',  # Hebreo
            'th': 'th-TH',  # Tailandés
            'vi': 'vi-VN',  # Vietnamita
            'id': 'id-ID',  # Indonesio
            'ms': 'ms-MY',  # Malayo
            'bn': 'bn-BD',  # Bengalí
            'ur': 'ur-PK',  # Urdu
            'ta': 'ta-IN',  # Tamil
            'ml': 'ml-IN',  # Malayalam
            'te': 'te-IN',  # Telugu
            'kn': 'kn-IN',  # Kannada
        }

    def detect_language(self, text):
        """
        Detectar idioma usando langdetect con mapeo extenso
        
        :param text: Texto a detectar
        :return: Diccionario con información de detección
        """
        try:
            # Validaciones previas
            if not text or len(text.strip()) == 0:
                return {
                    'success': False,
                    'error': 'Texto vacío',
                    'detected_language': self.last_detected_language,
                    'status_code': 400
                }

            # Detección de idioma
            detected_lang_code = detect(text)

            # Obtener código ISO completo
            detected_language = self.lang_mapping.get(
                detected_lang_code, 
                f'{detected_lang_code}-{detected_lang_code.upper()}'
            )

            # Actualizar último idioma detectado
            self.last_detected_language = detected_language

            return {
                'success': True,
                'detected_language': detected_language,
                'original_code': detected_lang_code,
                'text': text,
                'is_email': '@' in text,
                'status_code': 200
            }

        except LangDetectException:
            # Manejo de excepción si no se puede detectar
            return {
                'success': False,
                'error': 'No se pudo detectar el idioma',
                'detected_language': self.last_detected_language,
                'text': text,
                'status_code': 400
            }
        except Exception as e:
            return {
                'success': False,
                'error': 'Error inesperado en detección de idioma',
                'details': str(e),
                'detected_language': self.last_detected_language,
                'status_code': 500
            }

    def detect_language_probabilities(self, text):
        """
        Obtener probabilidades de idiomas
        
        :param text: Texto a analizar
        :return: Lista de probabilidades de idiomas
        """
        try:
            probabilities = detect_langs(text)
            
            # Convertir a formato más legible con mapeo de códigos
            formatted_probs = [
                {
                    'language': self.lang_mapping.get(prob.lang, prob.lang), 
                    'original_code': prob.lang,
                    'probability': round(prob.prob * 100, 2)
                } 
                for prob in probabilities
            ]
            
            return {
                'success': True,
                'probabilities': formatted_probs,
                'text': text,
                'status_code': 200
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': 'Error al calcular probabilidades',
                'details': str(e),
                'status_code': 500
            }

    def reset_last_detected_language(self, language='en-US'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        self.last_detected_language = language

    def get_supported_languages(self):
        """
        Obtener lista de idiomas soportados
        
        :return: Diccionario de idiomas
        """
        return {
            'success': True,
            'languages': list(self.lang_mapping.values()),
            'total_languages': len(self.lang_mapping),
            'status_code': 200
        }