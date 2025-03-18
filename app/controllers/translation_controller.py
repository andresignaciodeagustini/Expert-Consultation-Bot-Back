from app.services.translation_service import TranslationService

class TranslationController:
    def __init__(self, translation_service=None):
        """
        Inicializar controlador de traducción
        
        :param translation_service: Servicio de traducción
        """
        self.translation_service = translation_service or TranslationService()
        self.last_detected_language = 'en'

    def validate_input(self, data):
        """
        Validar datos de entrada
        
        :param data: Datos de la solicitud
        :return: Resultado de validación
        """
        if not data:
            return {
                'is_valid': False,
                'error': 'No data provided'
            }
        
        required_fields = ['text', 'target_language']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return {
                'is_valid': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }
        
        return {
            'is_valid': True,
            'text': data['text'],
            'target_language': data['target_language']
        }

    def translate(self, data):
        """
        Traducir texto
        
        :param data: Datos de la solicitud
        :return: Resultado de la traducción
        """
        try:
            # Validar entrada
            validation_result = self.validate_input(data)
            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'status_code': 400
                }
            
            # Realizar traducción
            translation_result = self.translation_service.translate_text(
                validation_result['text'], 
                validation_result['target_language']
            )
            
            # Añadir código de estado a la respuesta
            translation_result['status_code'] = (
                200 if translation_result.get('success', False) else 500
            )
            
            return translation_result

        except Exception as e:
            return {
                'success': False,
                'message': 'Error translating text',
                'error': str(e),
                'details': f"Error type: {type(e).__name__}",
                'status_code': 500
            }

    def reset_last_detected_language(self, language='en'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        self.last_detected_language = language