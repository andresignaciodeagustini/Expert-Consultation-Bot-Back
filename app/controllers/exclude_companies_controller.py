from src.utils.chatgpt_helper import ChatGPTHelper
from src.services.external.zoho_services import ZohoService
from app.services.excluded_companies_service import ExcludedCompaniesService

class ExcludeCompaniesController:
    def __init__(self, 
                 chatgpt=None, 
                 zoho_service=None, 
                 excluded_companies_service=None):
        self.chatgpt = chatgpt or ChatGPTHelper()
        self.zoho_service = zoho_service or ZohoService()
        self.excluded_companies_service = excluded_companies_service or ExcludedCompaniesService()
        self.last_detected_language = 'en-US'
        
        self.BASE_MESSAGES = {
            'ask_exclusions': "Are there any companies that should be excluded from the search?",
            'no_exclusions': "Understood, there are no companies to exclude.",
            'exclusions_confirmed': "Understood, we will exclude the following companies from the search: {companies}",
            'processing_error': "An error occurred while processing your request."
        }

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
        
        return {
            'is_valid': True,
            'data': data
        }

    def process_exclude_companies(self, data):
        """
        Procesar exclusión de empresas
        
        :param data: Datos de la solicitud
        :return: Respuesta procesada
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
            
            # Procesar idioma
            detected_language = self._process_language(data)
            
            # Si no hay respuesta, solicitar exclusiones
            if 'answer' not in data:
                response = self._request_initial_exclusions(detected_language)
                response['status_code'] = 200
                return response
            
            # Procesar respuesta de exclusión
            result = self._process_exclusion_response(data['answer'], detected_language)
            
            # Añadir código de estado a la respuesta
            result['status_code'] = 200 if result.get('success', False) else 400
            
            return result

        except Exception as e:
            error_message = self.chatgpt.translate_message(
                self.BASE_MESSAGES['processing_error'], 
                self.last_detected_language
            )
            
            return {
                'success': False,
                'message': error_message,
                'error': str(e),
                'detected_language': self.last_detected_language,
                'status_code': 500
            }

    def _process_language(self, data):
        """
        Procesar y detectar idioma
        
        :param data: Datos de la solicitud
        :return: Idioma detectado
        """
        try:
            # Priorizar el idioma si está explícitamente proporcionado
            if 'detected_language' in data:
                detected_language = data['detected_language']
            
            # Si hay una respuesta, procesar su idioma
            elif 'answer' in data:
                text_processing_result = self.chatgpt.process_text_input(
                    data['answer'], 
                    self.last_detected_language
                )
                detected_language = text_processing_result.get('detected_language', 'en-US')
            
            else:
                # Usar el último idioma detectado o el predeterminado
                detected_language = self.last_detected_language
            
            # Actualizar último idioma detectado
            self.last_detected_language = detected_language
            
            return detected_language
        
        except Exception as e:
            # Fallback a inglés en caso de error
            self.last_detected_language = 'en-US'
            return 'en-US'

    def _request_initial_exclusions(self, detected_language):
        """
        Solicitar exclusiones iniciales
        
        :param detected_language: Idioma detectado
        :return: Respuesta inicial
        """
        initial_message = self.chatgpt.translate_message(
            self.BASE_MESSAGES['ask_exclusions'], 
            detected_language
        )
        
        return {
            'success': True,
            'message': initial_message,
            'detected_language': detected_language,
            'has_excluded_companies': False,
            'excluded_companies': None
        }

    # Los demás métodos permanecen igual...

    def reset_last_detected_language(self, language='en-US'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        self.last_detected_language = language