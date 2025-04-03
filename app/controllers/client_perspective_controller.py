from src.utils.chatgpt_helper import ChatGPTHelper
from src.services.external.zoho_services import ZohoService
from app.services.excluded_companies_service import ExcludedCompaniesService
import re
# Importar funciones de gestión de idioma global
from app.constants.language import (
    get_last_detected_language, 
    reset_last_detected_language,
    update_last_detected_language
)

class ClientPerspectiveController:
    def __init__(
        self, 
        chatgpt=None, 
        zoho_service=None, 
        excluded_companies_service=None
    ):
        self.chatgpt = chatgpt or ChatGPTHelper()
        self.zoho_service = zoho_service or ZohoService()
        self.excluded_companies_service = excluded_companies_service or ExcludedCompaniesService()
        
        # Añadir mensajes base como en ExcludeCompaniesController
        self.BASE_MESSAGES = {
            'ask_client_perspective': "Would you like to include client-side companies?",
            'positive_response': "Great! We'll include client-side companies in the search.",
            'negative_response': "Understood. We'll proceed without client-side companies.",
            'unclear_response': "I'm sorry, could you please clearly answer yes or no about including client-side companies?",
            'processing_error': "An error occurred while processing your request.",
            'company_list_prefix': "Here are the recommended client companies, with verified companies listed first. Do you agree with this list?",
            'nonsense_input': "Please provide a valid response. Would you like to include client-side companies? Please answer with 'yes' or 'no'."
        }

    def validate_input(self, data):
        """
        Validar datos de entrada
        
        :param data: Datos de la solicitud
        :return: Resultado de validación
        """
        print("\n=== Input Validation ===")
        if not data:
            print("No data provided")
            return {
                'is_valid': False,
                'error': 'No data provided'
            }
        
        print(f"Received data: {data}")
        
        # Verificar si el campo 'answer' contiene texto sin sentido
        if 'answer' in data and self._is_nonsense_text(data['answer']):
            print("Nonsense text detected in answer")
            return {
                'is_valid': False,
                'error': 'nonsense_input',
                'data': data
            }
        
        return {
            'is_valid': True,
            'data': data
        }
        
    def _is_nonsense_text(self, text):
        if not text:
            return False
        
        # Quitar espacios extras
        text = text.strip().lower()
        
        # Respuestas válidas para múltiples idiomas
        valid_answers = {
            # Inglés
            'en': ['yes', 'y', 'yeah', 'yep', 'no', 'n', 'nope'],
            # Español
            'es': ['sí', 'si', 'no'],
            # Ruso
            'ru': ['да', 'нет'],
            # Alemán
            'de': ['ja', 'nein'],
            # Francés
            'fr': ['oui', 'non'],
            # Italiano
            'it': ['sì', 'no'],
            # Portugués
            'pt': ['sim', 'não'],
            # Otros idiomas...
        }
        
        # Función para verificar respuestas válidas en cualquier idioma
        def is_valid_answer(text):
            for lang_answers in valid_answers.values():
                if text in lang_answers:
                    return True
            return False
        
        if is_valid_answer(text):
            return False
        
        # Texto muy corto (menor a 3 caracteres)
        if len(text) < 3 and not is_valid_answer(text):
            return True
        
        return False

    def _process_language(self, data):
        """
        Procesar y detectar idioma usando exactamente el mismo método de ExcludeCompaniesController
        
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
            
            # También verificar si hay un idioma en 'language'
            if 'language' in data:
                detected_language = data['language']
                print(f"Language from data 'language' field: {detected_language}")
                update_last_detected_language(detected_language)
                return detected_language
            
            # Si hay una respuesta, procesar su idioma
            if 'answer' in data:
                # Manejar casos especiales de palabras cortas
                answer = data['answer'].strip().lower()
                if answer in ['no', 'n', 'yes', 'y', 'si', 'sí']:
                    print(f"Special case word detected: '{answer}'. Maintaining current language: {current_language}")
                    return current_language
                
                # Para respuestas normales, usar la detección
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

    def process_client_perspective(self, data):
        """
        Procesar perspectiva del cliente
        
        :param data: Datos de la solicitud
        :return: Respuesta procesada
        """
        try:
            print("\n=== Processing Client Perspective ===")
            
            # Importante: Verificar si hay un idioma explícito en los datos
            if data and isinstance(data, dict):
                if 'language' in data:
                    explicit_language = data['language']
                    print(f"Using explicit language from data: {explicit_language}")
                    update_last_detected_language(explicit_language)
                elif 'detected_language' in data:
                    explicit_language = data['detected_language']
                    print(f"Using detected_language from data: {explicit_language}")
                    update_last_detected_language(explicit_language)
                # Verificar en filtersApplied dentro de phase3_data
                elif 'phase3_data' in data and isinstance(data['phase3_data'], dict):
                    filters = data['phase3_data'].get('filtersApplied', {})
                    if filters and isinstance(filters, dict) and 'detected_language' in filters:
                        explicit_language = filters['detected_language']
                        print(f"Using language from phase3_data.filtersApplied: {explicit_language}")
                        update_last_detected_language(explicit_language)
            
            # Validar entrada
            validation_result = self.validate_input(data)
            if not validation_result['is_valid']:
                # Verificar si es por texto sin sentido
                if validation_result.get('error') == 'nonsense_input':
                    # Procesar idioma para el mensaje de error
                    detected_language = self._process_language(validation_result['data'])
                    
                    # Mensaje guía para el usuario, que reestablece la pregunta original
                    guidance_message = self.chatgpt.translate_message(
                        self.BASE_MESSAGES['nonsense_input'], 
                        detected_language
                    )
                    
                    return {
                        'success': False,
                        'message': guidance_message,
                        'detected_language': detected_language,
                        'stage': 'clarification',
                        'status_code': 400
                    }
                
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'status_code': 400
                }
            
            # Procesar idioma - usando exactamente el mismo método que ExcludeCompaniesController
            detected_language = self._process_language(validation_result['data'])
            print(f"Detected Language: {detected_language}")
            
            # IMPORTANTE: Asegurarse de que el idioma detectado se actualice correctamente
            update_last_detected_language(detected_language)
            
            # Inicializar client_companies_result con un valor predeterminado
            client_companies_result = {
                'success': False,
                'content': []
            }
            
            # Si no hay respuesta, solicitar perspectiva
            if not validation_result['data'].get('answer'):
                print("No answer provided, requesting initial perspective")
                response = self._request_initial_perspective(detected_language, validation_result['data'])
            else:
                # Procesar respuesta de perspectiva
                print(f"Processing answer: {validation_result['data']['answer']}")
                response = self._process_perspective_response(validation_result['data'], detected_language)
            
            # Añadir código de estado a la respuesta
            response['status_code'] = 200 if response.get('success', False) else 400
            
            print("\n=== Final Response ===")
            print(f"Response: {response}")
            
            return response

        except Exception as e:
            print(f"\n=== Error in process_client_perspective ===")
            print(f"Error details: {str(e)}")
            
            # Usar el mensaje base y traducirlo si es necesario
            current_language = get_last_detected_language()
            error_message = self.chatgpt.translate_message(
                self.BASE_MESSAGES['processing_error'], 
                current_language
            )

            return {
                'success': False,
                'error': error_message,
                'details': str(e),
                'detected_language': current_language,
                'status_code': 500
            }

    def _handle_negative_response(self, detected_language, data):
        """
        Manejar respuesta negativa en el idioma detectado
        
        :param detected_language: Idioma detectado
        :param data: Datos de la solicitud
        :return: Respuesta procesada
        """
        print("\n=== Negative Response Handling ===")
        
        # Traducir mensaje de respuesta negativa
        response_message = self.chatgpt.translate_message(
            self.BASE_MESSAGES['negative_response'], 
            detected_language
        )
        
        print(f"Response message: {response_message}")
        
        return {
            'success': True,
            'message': response_message,
            'detected_language': detected_language,
            'include_client_companies': False,
            'suggested_companies': [],
            'sector': data.get('sector'),
            'region': data.get('region'),
            'stage': 'response'
        }

    def _handle_unclear_response(self, detected_language):
        """
        Manejar respuesta poco clara en el idioma detectado
        
        :param detected_language: Idioma detectado
        :return: Respuesta procesada
        """
        print("\n=== Unclear Response Handling ===")
        
        # Traducir mensaje de solicitud de aclaración
        response_message = self.chatgpt.translate_message(
            self.BASE_MESSAGES['unclear_response'], 
            detected_language
        )
        
        print(f"Response message: {response_message}")
        
        return {
            'success': False,
            'message': response_message,
            'detected_language': detected_language,
            'stage': 'clarification'
        }

    def reset_last_detected_language(self, language='en-US'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        print(f"\n=== Resetting Last Detected Language to: {language} ===")
        reset_last_detected_language()

    def _request_initial_perspective(self, detected_language, data):
        """
        Solicitar perspectiva inicial en el idioma detectado
        
        :param detected_language: Idioma detectado
        :param data: Datos de la solicitud
        :return: Respuesta inicial
        """
        print("\n=== Initial Perspective Request ===")
        print(f"Detected language: {detected_language}")
        
        # Traducir el mensaje base al idioma detectado
        initial_message = self.chatgpt.translate_message(
            self.BASE_MESSAGES['ask_client_perspective'], 
            detected_language
        )
        
        print(f"Base message: {self.BASE_MESSAGES['ask_client_perspective']}")
        print(f"Translated message: {initial_message}")
        
        return {
            'success': True,
            'message': initial_message,
            'detected_language': detected_language,
            'sector': data.get('sector'),
            'region': data.get('region'),
            'stage': 'question'
        }

    def _process_perspective_response(self, data, detected_language):
        """
        Procesar respuesta de perspectiva directamente con comprobación de palabras clave
        
        :param data: Datos de la solicitud
        :param detected_language: Idioma detectado
        :return: Respuesta procesada
        """
        print("\n=== Perspective Response Processing ===")
        answer = data['answer'].strip().lower()
        print(f"Input answer: '{answer}'")
        print(f"Using language: {detected_language}")
        
        # Detectar directamente respuestas negativas comunes
        if answer in ['no', 'n', 'nope', 'no,', 'noo']:
            print("Direct negative response detected")
            return self._handle_negative_response(detected_language, data)
            
        # Detectar directamente respuestas positivas comunes
        if answer in ['yes', 'y', 'yeah', 'yep', 'si', 'sí', 'yes,', 'yess']:
            print("Direct positive response detected")
            return self._handle_positive_response(data, detected_language)
        
        # Para respuestas más complejas, usar el chatgpt para extraer la intención
        intention_result = self.chatgpt.extract_intention(answer)
        intention = intention_result.get('intention') if intention_result.get('success') else None
        
        print(f"Extracted intention: {intention}")

        # Manejar respuesta basado en la intención
        if intention == 'yes':
            return self._handle_positive_response(data, detected_language)
        elif intention == 'no':
            return self._handle_negative_response(detected_language, data)
        else:
            return self._handle_unclear_response(detected_language)

    def _handle_positive_response(self, data, detected_language):
        """
        Manejar respuesta positiva en el idioma detectado y obtener empresas cliente
        
        :param data: Datos de la solicitud
        :param detected_language: Idioma detectado
        :return: Respuesta con empresas cliente
        """
        print("\n=== Positive Response Handling ===")
        print(f"Sector: {data.get('sector', 'Financial Services')}")
        print(f"Region: {data.get('region', 'Europe')}")
        
        try:
            # Obtener empresas excluidas si están disponibles
            excluded_companies = []
            try:
                excluded_companies = self.excluded_companies_service.get_excluded_companies()
                print(f"Found {len(excluded_companies)} excluded companies")
            except Exception as e:
                print(f"Error getting excluded companies: {e}")
        
            # Usar get_client_side_companies
            client_companies_result = self.chatgpt.get_client_side_companies(
                sector=data.get('sector', 'Financial Services'),
                geography=data.get('region', 'Europe'),
                excluded_companies=excluded_companies
            )
            
            print(f"Client Companies Result Success: {client_companies_result.get('success', False)}")
            print(f"Number of companies found: {len(client_companies_result.get('content', []))}")
            
            if not client_companies_result.get('success', False):
                error_message = "Error generating client companies"
                translated_error = self.chatgpt.translate_message(error_message, detected_language)
                
                return {
                    'success': False,
                    'message': translated_error,
                    'detected_language': detected_language,
                    'status_code': 400
                }

            # Traducir mensajes al idioma detectado
            inclusion_message = self.chatgpt.translate_message(
                self.BASE_MESSAGES['positive_response'], 
                detected_language
            )
            
            prefix_message = self.chatgpt.translate_message(
                self.BASE_MESSAGES['company_list_prefix'], 
                detected_language
            )
            
            return {
                'success': True,
                'message': inclusion_message,
                'message_prefix': prefix_message,
                'detected_language': detected_language,
                'sector': data.get('sector'),
                'region': data.get('region'),
                'suggested_companies': client_companies_result.get('content', []),
                'include_client_companies': True,
                'stage': 'response',
                'status_code': 200
            }
        except Exception as e:
            print(f"Error in _handle_positive_response: {str(e)}")
            error_message = self.chatgpt.translate_message(
                self.BASE_MESSAGES['processing_error'],
                detected_language
            )
            return {
                'success': False,
                'message': error_message,
                'error': str(e),
                'detected_language': detected_language,
                'status_code': 500
            }

    def _handle_negative_response(self, detected_language, data):
        """
        Manejar respuesta negativa en el idioma detectado con manejo de errores y registro detallado
        
        :param detected_language: Idioma detectado
        :param data: Datos de la solicitud
        :return: Respuesta procesada
        """
        try:
            print("\n=== Negative Response Handling ===")
            
            # Imprimir información de contexto
            print(f"Detected Language: {detected_language}")
            print(f"Input Data: {data}")
            
            # Traducir mensaje de respuesta negativa con manejo de errores
            try:
                response_message = self.chatgpt.translate_message(
                    self.BASE_MESSAGES['negative_response'], 
                    detected_language
                )
                print(f"Translated Response Message: {response_message}")
            except Exception as translation_error:
                print(f"Translation Error: {translation_error}")
                # Usar mensaje por defecto si la traducción falla
                response_message = self.BASE_MESSAGES['negative_response']
            
            # Preparar datos de respuesta con información contextual
            response = {
                'success': True,
                'message': response_message,
                'detected_language': detected_language,
                'include_client_companies': False,
                'suggested_companies': [],
                'sector': data.get('sector'),
                'region': data.get('region'),
                'stage': 'response',
                'status_code': 200
            }
            
            # Registro adicional para depuración
            print("\n=== Negative Response Details ===")
            print(f"Sector: {response['sector']}")
            print(f"Region: {response['region']}")
            print(f"Success: {response['success']}")
            
            return response
        
        except Exception as e:
            print(f"\n=== Error in _handle_negative_response ===")
            print(f"Unexpected error: {str(e)}")
            
            # Manejo de errores inesperados
            error_message = self.chatgpt.translate_message(
                self.BASE_MESSAGES['processing_error'], 
                detected_language
            )
            
            return {
                'success': False,
                'message': error_message,
                'error': str(e),
                'detected_language': detected_language,
                'status_code': 500
            }