from app.services.server_monitoring_service import ServerMonitoringService

class ServerMonitoringController:
    def __init__(self, monitoring_service=None):
        self.monitoring_service = monitoring_service or ServerMonitoringService()
        self.last_detected_language = 'en'

    def validate_input(self):
        """
        Validar entrada para ping
        
        :return: Resultado de validación
        """
        return {
            'is_valid': True
        }

    def ping(self):
        """
        Obtener estado del servidor
        
        :return: Información de estado
        """
        try:
            # Validar entrada (en este caso, siempre será válida)
            validation_result = self.validate_input()
            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'error': 'Invalid input',
                    'status_code': 400
                }

            # Obtener estado del servidor
            result = self.monitoring_service.ping()
            
            # Añadir código de estado a la respuesta
            result['status_code'] = 200 if result.get('success', False) else 500
            
            return result

        except Exception as e:
            return {
                'success': False,
                'error': 'Server monitoring failed',
                'details': str(e),
                'status_code': 500
            }

    def reset_last_detected_language(self, language='en'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        self.last_detected_language = language