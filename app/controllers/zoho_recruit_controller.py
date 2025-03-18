from app.services.zoho_recruit_service import ZohoRecruitService

class ZohoRecruitController:
    def __init__(self, zoho_recruit_service=None):
        """
        Inicializar controlador de Zoho Recruit
        
        :param zoho_recruit_service: Servicio de Zoho Recruit
        """
        self.zoho_recruit_service = (
            zoho_recruit_service or 
            ZohoRecruitService()
        )
        self.last_detected_language = 'en'

    def validate_input(self, data=None):
        """
        Validar datos de entrada
        
        :param data: Datos de la solicitud (opcional)
        :return: Resultado de validación
        """
        # Para los métodos get_candidates y get_jobs, no se requiere validación específica
        return {
            'is_valid': True
        }

    def validate_search_input(self, criteria):
        """
        Validar criterios de búsqueda
        
        :param criteria: Criterios de búsqueda
        :return: Resultado de validación
        """
        if not criteria:
            return {
                'is_valid': False,
                'error': 'Search criteria are required'
            }
        
        return {
            'is_valid': True,
            'criteria': criteria
        }

    def get_candidates(self):
        """
        Obtener candidatos
        
        :return: Resultado de obtención de candidatos
        """
        try:
            # Validar entrada
            validation_result = self.validate_input()
            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'status_code': 400
                }

            # Obtener candidatos
            result = self.zoho_recruit_service.get_all_candidates()
            
            # Añadir código de estado a la respuesta
            result['status_code'] = 200 if result.get('success', False) else 500
            
            return result

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'details': 'Error retrieving candidates',
                'status_code': 500
            }

    def get_jobs(self):
        """
        Obtener trabajos
        
        :return: Resultado de obtención de trabajos
        """
        try:
            # Validar entrada
            validation_result = self.validate_input()
            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'status_code': 400
                }

            # Obtener trabajos
            result = self.zoho_recruit_service.get_all_jobs()
            
            # Añadir código de estado a la respuesta
            result['status_code'] = 200 if result.get('success', False) else 500
            
            return result

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'details': 'Error retrieving jobs',
                'status_code': 500
            }

    def search_candidates(self, criteria):
        """
        Buscar candidatos
        
        :param criteria: Criterios de búsqueda
        :return: Resultado de búsqueda de candidatos
        """
        try:
            # Validar entrada
            validation_result = self.validate_search_input(criteria)
            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'status_code': 400
                }

            # Buscar candidatos
            result = self.zoho_recruit_service.search_candidates(
                validation_result['criteria']
            )
            
            # Añadir código de estado a la respuesta
            result['status_code'] = 200 if result.get('success', False) else 500
            
            return result

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'details': 'Error searching candidates',
                'status_code': 500
            }

    def reset_last_detected_language(self, language='en'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        self.last_detected_language = language