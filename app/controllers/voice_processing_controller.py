from src.handlers.voice_handler import VoiceHandler

class VoiceProcessingController:
    def __init__(self, voice_handler=None):
        """
        Inicializar controlador de procesamiento de voz
        
        :param voice_handler: Manejador de voz
        """
        self.voice_handler = voice_handler or VoiceHandler()
        self.last_detected_language = 'en'

    def validate_input(self, request):
        """
        Validar datos de entrada
        
        :param request: Solicitud Flask
        :return: Resultado de validación
        """
        if not request:
            return {
                'is_valid': False,
                'error': 'No request provided'
            }
        
        # Verificar si hay archivos de audio
        if 'file' not in request.files:
            return {
                'is_valid': False,
                'error': 'No audio file provided'
            }
        
        return {
            'is_valid': True,
            'request': request
        }

    def process_voice(self, request):
        """
        Procesar solicitud de voz
        
        :param request: Solicitud Flask
        :return: Resultado del procesamiento de voz
        """
        try:
            # Validar entrada
            validation_result = self.validate_input(request)
            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'status_code': 400
                }
            
            # Obtener el tipo de procesamiento
            process_type = request.args.get('type', 'username')
            
            # Manejar solicitud de voz
            voice_result = self.voice_handler.handle_voice_request(
                request, 
                step=process_type
            )
            
            # Preparar respuesta
            response = self._prepare_voice_response(voice_result, process_type)
            
            # Añadir código de estado a la respuesta
            response['status_code'] = 200 if response.get('success', False) else 400
            
            return response

        except Exception as e:
            error_response = self._handle_error(e)
            error_response['status_code'] = 500
            return error_response

    def _prepare_voice_response(self, voice_result, process_type):
        """
        Preparar respuesta de procesamiento de voz
        
        :param voice_result: Resultado del procesamiento de voz
        :param process_type: Tipo de procesamiento
        :return: Respuesta de procesamiento
        """
        response = {
            'success': True,
            'detected_language': voice_result.get('detected_language', 'es'),
            'transcription': voice_result.get('transcription'),
            'original_transcription': voice_result.get('original_transcription')
        }

        # Agregar username solo si el tipo de procesamiento es 'username'
        if process_type == 'username':
            response['username'] = voice_result.get('username')

        return response

    def _handle_error(self, error):
        """
        Manejar errores de procesamiento de voz
        
        :param error: Excepción ocurrida
        :return: Respuesta de error
        """
        return {
            'success': False,
            'error': str(error),
            'details': f"Error type: {type(error).__name__}"
        }

    def reset_last_detected_language(self, language='en'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        self.last_detected_language = language