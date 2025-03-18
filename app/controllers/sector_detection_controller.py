from app.services.sector_detection_service import SectorDetectionService

class SectorDetectionController:
    def __init__(self, sector_detection_service=None):
        """
        Inicializar controlador de detección de sector
        
        :param sector_detection_service: Servicio de detección de sector
        """
        self.sector_detection_service = (
            sector_detection_service or 
            SectorDetectionService()
        )
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
        
        if 'text' not in data:
            return {
                'is_valid': False,
                'error': 'Text input is required'
            }
        
        return {
            'is_valid': True,
            'text': data['text']
        }

    def detect_sector(self, data):
        """
        Detectar sector
        
        :param data: Datos de la solicitud
        :return: Resultado de detección de sector
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

            # Detectar sector
            detection_result = self.sector_detection_service.detect_sector(
                validation_result['text']
            )
            
            # Añadir código de estado a la respuesta
            detection_result['status_code'] = (
                200 if detection_result.get('success', False) else 400
            )
            
            return detection_result

        except Exception as e:
            return {
                'success': False,
                'message': f'Error processing sector: {str(e)}',
                'error': str(e),
                'status_code': 500
            }

    def reset_last_detected_language(self, language='en'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        self.last_detected_language = language