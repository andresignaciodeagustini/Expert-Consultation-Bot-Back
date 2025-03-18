from src.utils.chatgpt_helper import ChatGPTHelper
from src.services.external.zoho_services import ZohoService
from app.services.excluded_companies_service import ExcludedCompaniesService
# Importar funciones de gestión de idioma global
from app.constants.language import (
    get_last_detected_language, 
    update_last_detected_language, 
    reset_last_detected_language
)

class ExcludeCompaniesController:
    def __init__(self, 
                 chatgpt=None, 
                 zoho_service=None, 
                 excluded_companies_service=None):
        self.chatgpt = chatgpt or ChatGPTHelper()
        self.zoho_service = zoho_service or ZohoService()
        self.excluded_companies_service = excluded_companies_service or ExcludedCompaniesService()
        
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
                    'detected_language': get_last_detected_language(),
                    'status_code': 400
                }
            
            # Procesar idioma
            detected_language = self._process_language(validation_result['data'])
            
            # Si no hay respuesta, solicitar exclusiones
            if 'answer' not in validation_result['data']:
                response = self._request_initial_exclusions(detected_language)
                response['status_code'] = 200
                return response
            
            # Procesar respuesta de exclusión
            result = self._process_exclusion_response(
                validation_result['data']['answer'], 
                detected_language
            )
            
            # Añadir código de estado a la respuesta
            result['status_code'] = 200 if result.get('success', False) else 400
            
            return result

        except Exception as e:
            current_language = get_last_detected_language()
            error_message = self.chatgpt.translate_message(
                self.BASE_MESSAGES['processing_error'], 
                current_language
            )
            
            return {
                'success': False,
                'message': error_message,
                'error': str(e),
                'detected_language': current_language,
                'status_code': 500
            }

    def _process_language(self, data):
        """
        Procesar y detectar idioma de manera menos agresiva
        
        :param data: Datos de la solicitud
        :return: Idioma detectado
        """
        print("\n=== Language Processing ===")
        current_language = get_last_detected_language()
        print(f"Current detected language: {current_language}")
        
        try:
            # Priorizar el idioma si está explícitamente proporcionado
            if 'detected_language' in data:
                detected_language = data['detected_language']
                print(f"Language from data: {detected_language}")
                update_last_detected_language(detected_language)
                return detected_language
            
            # Si hay una respuesta, procesar su idioma
            if 'answer' in data:
                text_processing_result = self.chatgpt.process_text_input(
                    data['answer'], 
                    current_language
                )
                detected_language = text_processing_result.get('detected_language', current_language)
                
                print(f"Input answer: {data['answer']}")
                print(f"Detected language: {detected_language}")
                
                # CLAVE: Mantener el idioma original de la conversación
                if detected_language != current_language:
                    print(f"Language detection attempted to change from {current_language} to {detected_language}")
                    detected_language = current_language
                
                # Actualizar el último idioma detectado
                update_last_detected_language(detected_language)
                
                return detected_language
            
            # Usar el último idioma detectado o el predeterminado
            return current_language
        
        except Exception as e:
            print(f"Error in language detection: {e}")
            return current_language

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

    def _process_exclusion_response(self, answer, detected_language):
        """
        Procesar respuesta de exclusión de empresas
        
        :param answer: Respuesta del usuario
        :param detected_language: Idioma detectado
        :return: Respuesta procesada
        """
        processed_response = self.chatgpt.process_company_response(answer)

        if processed_response == "no" or answer.lower() in ['no', 'n']:
            return self._handle_no_exclusions(detected_language)
        
        if isinstance(processed_response, dict):
            return self._handle_company_exclusions(
                processed_response['companies'], 
                detected_language
            )
        
        # Respuesta inválida
        return self._handle_invalid_response(detected_language)

    def _handle_no_exclusions(self, detected_language):
        """
        Manejar caso sin exclusiones
        
        :param detected_language: Idioma detectado
        :return: Respuesta sin exclusiones
        """
        # Limpiar exclusiones globales
        self.excluded_companies_service.clear_excluded_companies()
        
        response_message = self.chatgpt.translate_message(
            self.BASE_MESSAGES['no_exclusions'], 
            detected_language
        )
        
        return {
            'success': True,
            'message': response_message,
            'detected_language': detected_language,
            'has_excluded_companies': False,
            'excluded_companies': None,
            'search_criteria': None,
            'candidates': None
        }

    def _handle_company_exclusions(self, excluded_companies, detected_language):
        """
        Manejar exclusión de empresas
        
        :param excluded_companies: Empresas a excluir
        :param detected_language: Idioma detectado
        :return: Respuesta con exclusiones
        """
        # Actualizar empresas excluidas
        self.excluded_companies_service.add_excluded_companies(excluded_companies)
        
        # Preparar mensaje
        companies_list = ", ".join(excluded_companies)
        base_message = self.BASE_MESSAGES['exclusions_confirmed'].format(
            companies=companies_list
        )
        
        # Obtener candidatos y empresas disponibles
        included_companies, candidates, search_criteria = self._get_filtered_candidates(
            excluded_companies
        )
        
        # Traducir mensaje
        response_message = self.chatgpt.translate_message(base_message, detected_language)
        
        return {
            'success': True,
            'message': response_message,
            'detected_language': detected_language,
            'has_excluded_companies': True,
            'excluded_companies': list(excluded_companies),
            'search_criteria': search_criteria,
            'candidates': candidates,
            'included_companies': included_companies
        }

    def _get_filtered_candidates(self, excluded_companies):
        """
        Obtener candidatos filtrados
        
        :param excluded_companies: Empresas a excluir
        :return: Tupla de (empresas incluidas, candidatos, criterios de búsqueda)
        """
        all_candidates = self.zoho_service.get_candidates()
        available_companies = set()
        
        if isinstance(all_candidates, list):
            for candidate in all_candidates:
                if candidate.get('Current_Employer'):
                    available_companies.add(candidate['Current_Employer'])
        
        # Filtrar excluyendo las empresas especificadas
        included_companies = [
            company for company in available_companies 
            if not self.excluded_companies_service.is_company_excluded(company)
        ]
        
        # Crear criterio de búsqueda
        search_criteria = None
        candidates = None
        
        if included_companies:
            inclusion_criteria = [
                f"(Current_Employer:contains:{company})" 
                for company in included_companies
            ]
            search_criteria = "OR".join(inclusion_criteria)
            
            try:
                candidates = self.zoho_service.search_candidates(search_criteria)
            except Exception as zoho_error:
                candidates = {"error": str(zoho_error)}
        
        return included_companies, candidates, search_criteria

    def _handle_invalid_response(self, detected_language):
        """
        Manejar respuesta inválida
        
        :param detected_language: Idioma detectado
        :return: Respuesta de solicitud inicial
        """
        response_message = self.chatgpt.translate_message(
            self.BASE_MESSAGES['ask_exclusions'], 
            detected_language
        )
        
        return {
            'success': True,
            'message': response_message,
            'detected_language': detected_language,
            'has_excluded_companies': False,
            'excluded_companies': None,
            'search_criteria': None,
            'candidates': None
        }

    def reset_last_detected_language(self, language='en-US'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        print(f"\n=== Resetting Last Detected Language to: {language} ===")
        reset_last_detected_language()