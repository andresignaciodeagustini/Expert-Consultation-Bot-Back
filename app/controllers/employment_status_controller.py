from src.utils.chatgpt_helper import ChatGPTHelper
from src.services.external.zoho_services import ZohoService
import re
# Importar funciones de gestión de idioma global
from app.constants.language import (
    get_last_detected_language, 
    update_last_detected_language, 
    reset_last_detected_language
)

class EmploymentStatusController:
    def __init__(self):
        self.chatgpt = ChatGPTHelper()
        self.zoho_service = ZohoService()
        
        self.BASE_MESSAGES = {
            'ask_preference': "Would you prefer experts who currently work at these companies, who worked there previously, or both options?",
            'status_options': {
                'current': "Thank you, I will search for experts who currently work at these companies",
                'previous': "Thank you, I will search for experts who previously worked at these companies",
                'both': "Thank you, I will search for both current employees and former employees of these companies"
            },
            'normalize_prompt': "Translate this employment preference to one of these options: 'current', 'previous', or 'both': ",
            'invalid_option': "Please select one of the available options: current, previous, or both.",
            'nonsense_input': "Please provide a valid response. Would you prefer experts who currently work at these companies, who worked there previously, or both options?",
            'processing_error': "Error processing your response"
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
        
        # Verificar si tiene un status y si es texto sin sentido
        if 'status' in data and self._is_nonsense_text(data['status']):
            print("Nonsense text detected in status")
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
        Detecta si el texto parece no tener sentido
        
        :param text: Texto a evaluar
        :return: True si parece ser texto sin sentido, False en caso contrario
        """
        if not text:
            return False
            
        # Quitar espacios extras
        text = text.strip().lower()
        
        # Texto muy corto (menor a 3 caracteres)
        if len(text) < 3:
            return True
            
        # Solo números
        if re.match(r'^[0-9]+$', text):
            return True
            
        # Palabras cortas sin contexto como "dogs", "cat", etc.
        if re.match(r'^[a-z]+$', text.lower()) and len(text) < 5:
            return True
            
        # Verificar patrones comunes de teclado
        keyboard_patterns = ['asdf', 'qwer', 'zxcv', '1234', 'hjkl', 'uiop']
        for pattern in keyboard_patterns:
            if pattern in text.lower():
                return True
            
        # Texto aleatorio (una sola palabra larga sin espacios)
        if len(text.split()) == 1 and len(text) > 8:
            # Verificar si tiene una distribución de caracteres poco natural
            # Caracteres raros o poco comunes en muchos idiomas
            rare_chars = len(re.findall(r'[qwxzjkvfy]', text.lower()))
            if rare_chars / len(text) > 0.3:  # Alta proporción de caracteres poco comunes
                return True
            
            # Patrones repetitivos
            if any(text.count(c) > len(text) * 0.4 for c in text):  # Un carácter repetido muchas veces
                return True
                
        return False

    def process_employment_status(self, data):
        """
        Procesar estado de empleo
        
        :param data: Datos de la solicitud
        :return: Respuesta procesada
        """
        try:
            print("\n=== Processing Employment Status ===")
            
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
                        'has_status': False,
                        'detected_language': detected_language,
                        'status_code': 400
                    }
                
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'detected_language': get_last_detected_language(),
                    'status_code': 400
                }
            
            # Procesamiento de idioma
            detected_language = self._process_language(validation_result['data'])
            print(f"Detected Language: {detected_language}")
            
            # Si no hay estado, solicitar preferencia
            if 'status' not in validation_result['data']:
                print("No status provided, requesting initial preference")
                response = self._request_initial_preference(detected_language)
                response['status_code'] = 200
                return response

            # Procesar estado de empleo
            print(f"Processing status: {validation_result['data']['status']}")
            status = self._extract_employment_status(validation_result['data']['status'])
            print(f"Extracted status: {status}")
            
            # Generar respuesta
            result = self._generate_response(status, detected_language)
            
            # Añadir código de estado a la respuesta
            result['status_code'] = 200 if result.get('success', False) else 400
            
            return result

        except Exception as e:
            print(f"\n=== Error in process_employment_status ===")
            print(f"Error details: {str(e)}")
            
            error_message = self.chatgpt.translate_message(
                self.BASE_MESSAGES['processing_error'], 
                get_last_detected_language()
            )
            
            return {
                'success': False,
                'message': error_message,
                'error': str(e),
                'detected_language': get_last_detected_language(),
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
                return detected_language
            
            # Si hay un estado, procesar su idioma
            elif 'status' in data:
                text_processing_result = self.chatgpt.process_text_input(
                    data['status'], 
                    current_language
                )
                detected_language = text_processing_result.get('detected_language', current_language)
                
                print(f"Input status: {data['status']}")
                print(f"Detected language: {detected_language}")
                
                return detected_language
            
            else:
                # Usar el último idioma detectado o el predeterminado
                print("No status provided, using previous language")
                return current_language
        
        except Exception as e:
            print(f"Error in language detection: {e}")
            # Fallback al idioma actual en caso de error
            return current_language

    def _request_initial_preference(self, detected_language):
        """
        Solicitar preferencia inicial de estado de empleo
        
        :param detected_language: Idioma detectado
        :return: Respuesta inicial
        """
        print("\n=== Initial Preference Request ===")
        print(f"Detected language: {detected_language}")
        
        # Traducir el mensaje base directamente
        translated_question = self.chatgpt.translate_message(
            self.BASE_MESSAGES['ask_preference'], 
            detected_language
        )
        
        print(f"Original message: {self.BASE_MESSAGES['ask_preference']}")
        print(f"Translated message: {translated_question}")
        
        return {
            'success': True,
            'message': translated_question,
            'has_status': False,
            'detected_language': detected_language
        }

    def _extract_employment_status(self, status_text):
        """
        Extraer estado de empleo
        
        :param status_text: Texto de estado de empleo
        :return: Estado de empleo normalizado
        """
        print("\n=== Employment Status Extraction ===")
        print(f"Input status text: {status_text}")
        
        # Traducir la respuesta del usuario al inglés SOLO para procesar la intención
        translated_status = self.chatgpt.translate_message(status_text, 'en-US')
        print(f"Translated status text: {translated_status}")
        
        # Intentar extraer estado de trabajo
        status = self.chatgpt.extract_work_timing(translated_status)
        print(f"Extracted by work timing: {status}")
        
        if not status:
            status = self._normalize_status(translated_status)
            print(f"Normalized status: {status}")

            if status is None:
                normalize_prompt = (
                    self.BASE_MESSAGES['normalize_prompt'] + 
                    translated_status
                )
                normalized_status = self.chatgpt.translate_message(
                    normalize_prompt, 
                    'en-US'
                ).strip().lower()
                print(f"Normalized prompt result: {normalized_status}")
                
                status = self._normalize_status(normalized_status)
                print(f"Final normalized status: {status}")
        
        return status

    def _normalize_status(self, status_text):
        """
        Normalizar estado de empleo
        
        :param status_text: Texto de estado de empleo
        :return: Estado de empleo normalizado
        """
        print("\n=== Status Normalization ===")
        print(f"Input status text: {status_text}")
        
        status_text = status_text.strip().lower()
        
        status_mapping = {
            'current': ['current', 'currently', 'presente', 'actual', 'now', 'present'],
            'previous': ['previous', 'previously', 'former', 'past', 'anterior', 'antes'],
            'both': ['both', 'all', 'todos', 'ambos', 'both options', 'all options']
        }
        
        for status, variants in status_mapping.items():
            if any(variant in status_text for variant in variants):
                print(f"Matched status: {status}")
                return status
        
        print("No status match found")
        return None

    def _generate_response(self, status, detected_language):
        """
        Generar respuesta basada en el estado de empleo
        
        :param status: Estado de empleo
        :param detected_language: Idioma detectado
        :return: Respuesta generada
        """
        print("\n=== Response Generation ===")
        print(f"Employment Status: {status}")
        print(f"Detected Language: {detected_language}")

        if status:
            # Convertir el status a criterios de búsqueda
            search_criteria = self._get_search_criteria(status)
            
            try:
                candidates = self.zoho_service.search_candidates(search_criteria)
                
                # Obtener el mensaje de estado correspondiente
                status_message = self.BASE_MESSAGES['status_options'][status]
                
                print(f"Original status message: {status_message}")
                
                # Traducir el mensaje
                response_message = self.chatgpt.translate_message(status_message, detected_language)
                
                print(f"Translated status message: {response_message}")
                
                return {
                    'success': True,
                    'message': response_message,
                    'has_status': True,
                    'employment_status': status,
                    'detected_language': detected_language,
                    'candidates': candidates,
                    'search_criteria': search_criteria
                }
            
            except Exception as zoho_error:
                print(f"Zoho Search Error: {zoho_error}")
                
                status_message = self.BASE_MESSAGES['status_options'][status]
                response_message = self.chatgpt.translate_message(status_message, detected_language)
                
                return {
                    'success': True,
                    'message': response_message,
                    'has_status': True,
                    'employment_status': status,
                    'detected_language': detected_language,
                    'zoho_error': str(zoho_error)
                }
        else:
            # Manejar caso de estado inválido
            error_message = self.chatgpt.translate_message(
                self.BASE_MESSAGES['invalid_option'], 
                detected_language
            )
            
            return {
                'success': False,
                'message': error_message,
                'has_status': False,
                'detected_language': detected_language
            }

    def _get_search_criteria(self, status):
        """
        Obtener criterios de búsqueda basados en el estado
        
        :param status: Estado de empleo
        :return: Criterios de búsqueda
        """
        print("\n=== Search Criteria Generation ===")
        print(f"Status: {status}")
        
        if status == 'current':
            return "(Candidate_Status:equals:Active)"
        elif status == 'previous':
            return "(Candidate_Status:equals:Inactive)"
        else:  # both
            return "(Candidate_Status:equals:Active)OR(Candidate_Status:equals:Inactive)"

    def reset_last_detected_language(self, language='en-US'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        print(f"\n=== Resetting Last Detected Language to: {language} ===")
        reset_last_detected_language()