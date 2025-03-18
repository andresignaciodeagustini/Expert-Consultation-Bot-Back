from app.services.token_service import TokenService

class TokenController:
    def __init__(self):
        self.last_detected_language = 'en'

    def validate_input(self, data=None):
        """
        Validar datos de entrada
        
        :param data: Datos de la solicitud (opcional)
        :return: Resultado de validación
        """
        # Para este controlador, la validación siempre será exitosa
        return {
            'is_valid': True
        }

    @staticmethod
    def refresh_token(data=None):
        """
        Actualizar token de Zoho
        
        :param data: Datos de la solicitud (opcional)
        :return: Respuesta de actualización de token
        """
        try:
            # Validar entrada (en este caso, siempre será válida)
            new_token = TokenService.refresh_zoho_token()
            
            if new_token:
                return {
                    'success': True,
                    'message': 'Recruit Token updated successfully',
                    'new_token': new_token[:10] + '...',
                    'status_code': 200
                }
            
            return {
                'success': False,
                'message': 'Failed to refresh Recruit token',
                'status_code': 400
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'details': 'Error refreshing Zoho token',
                'status_code': 500
            }

    def reset_last_detected_language(self, language='en'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        self.last_detected_language = language