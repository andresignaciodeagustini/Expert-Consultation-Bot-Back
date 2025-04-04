from typing import Dict
import logging
import re

from src.utils.chatgpt_helper import ChatGPTHelper
from src.services.external.zoho_services import ZohoService
from app.services.excluded_companies_service import ExcludedCompaniesService
# Importar funciones de gestión de idioma global
from app.constants.language import (
    get_last_detected_language, 
    update_last_detected_language, 
    reset_last_detected_language
)

logger = logging.getLogger(__name__)

class SupplyChainExperienceController:
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
            'ask_supply_chain': "Would you like to include supply chain companies?",
            'positive_response': "Perfect! I will include supply chain companies in the search.",
            'negative_response': "Understood. We'll proceed without supply chain companies.",
            'unclear_response': "I'm sorry, could you please clearly answer yes or no about including supply chain companies?",
            'processing_error': "An error occurred while processing your request.",
            'company_list_prefix': "Here are the recommended companies, with verified companies listed first. Do you agree with this list?",
            'nonsense_input': "Please provide a valid response. Would you like to include supply chain companies? Please answer with 'yes' or 'no'."
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
        """
        Detecta si el texto parece no tener sentido usando extract_intention
        
        :param text: Texto a evaluar
        :return: True si parece ser texto sin sentido, False en caso contrario
        """
        if not text:
            return False
            
        # Quitar espacios extras
        text = text.strip()
        
        # Usar extract_intention de ChatGPT para determinar si el texto tiene un significado claro
        intention_result = self.chatgpt.extract_intention(text)
        intention = intention_result.get('intention') if intention_result.get('success') else None
        
        # Si el texto es muy corto y ChatGPT no puede determinar una intención, considerarlo sin sentido
        if len(text) < 3 and not intention:
            return True
        
        # Si ChatGPT puede determinar que es sí/no, no es sin sentido
        if intention in ['yes', 'no']:
            return False
            
        return intention is None

    def process_supply_chain_experience(self, data):
        """
        Procesar experiencia en cadena de suministro
        
        :param data: Datos de la solicitud
        :return: Respuesta procesada
        """
        try:
            print("\n=== Processing Supply Chain Experience ===")
            
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
            
            # Procesar idioma usando el método mejorado
            detected_language = self._process_language(validation_result['data'])
            print(f"Detected Language: {detected_language}")
            
            # IMPORTANTE: Asegurarse de que el idioma detectado se actualice correctamente
            update_last_detected_language(detected_language)
            
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
            print(f"\n=== Error in process_supply_chain_experience ===")
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

    def _process_language(self, data):
        """
        Procesar y detectar idioma usando el método mejorado
        
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
                # Usar process_text_input para manejar la detección de idioma manteniendo la consistencia
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
            self.BASE_MESSAGES['ask_supply_chain'], 
            detected_language
        )
        
        print(f"Base message: {self.BASE_MESSAGES['ask_supply_chain']}")
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
        Procesar respuesta de perspectiva usando la extracción de intención de ChatGPT
        
        :param data: Datos de la solicitud
        :param detected_language: Idioma detectado
        :return: Respuesta procesada
        """
        print("\n=== Perspective Response Processing ===")
        answer = data['answer'].strip()
        print(f"Input answer: '{answer}'")
        print(f"Using language: {detected_language}")
        
        # Usar extract_intention para todas las respuestas
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
        Manejar respuesta positiva en el idioma detectado
        
        :param data: Datos de la solicitud
        :param detected_language: Idioma detectado
        :return: Respuesta con empresas de cadena de suministro
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
        
            # Obtener empresas de cadena de suministro
            supply_companies_result = self.chatgpt.get_supply_chain_companies(
                sector=data.get('sector', 'Financial Services'),
                geography=data.get('region', 'Europe'),
                excluded_companies=excluded_companies
            )
            
            print(f"Supply Companies Result Success: {supply_companies_result.get('success', False)}")
            print(f"Number of companies found: {len(supply_companies_result.get('content', []))}")
            
            if not supply_companies_result.get('success', False):
                error_message = "Error generating supply chain companies"
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
            
            # Estructura igual a la del endpoint original
            return {
                'success': True,
                'message': inclusion_message,
                'message_prefix': prefix_message,
                'detected_language': detected_language,
                'sector': data.get('sector'),
                'region': data.get('region'),
                'suggested_companies': supply_companies_result.get('content', []),
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