from src.utils.chatgpt_helper import ChatGPTHelper
from src.services.external.zoho_services import ZohoService
from app.services.excluded_companies_service import ExcludedCompaniesService

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
        self.last_detected_language = 'en-US'

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
        return {
            'is_valid': True,
            'data': data
        }

    def process_client_perspective(self, data):
        """
        Procesar perspectiva del cliente
        
        :param data: Datos de la solicitud
        :return: Respuesta procesada
        """
        try:
            print("\n=== Processing Client Perspective ===")
            
            # Validar entrada
            validation_result = self.validate_input(data)
            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'status_code': 400
                }
            
            # Procesar idioma
            detected_language = self._process_language(validation_result['data'])
            print(f"Detected Language: {detected_language}")
            
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
            
            error_message = "An error occurred while processing your request."
            try:
                error_message = self.chatgpt.translate_message(
                    error_message, 
                    self.last_detected_language
                )
            except Exception:
                pass

            return {
                'success': False,
                'error': error_message,
                'details': str(e),
                'detected_language': self.last_detected_language,
                'status_code': 500
            }

    def _process_language(self, data):
        """
        Procesar y detectar idioma con priorización de idiomas no ingleses
        
        :param data: Datos de la solicitud
        :return: Idioma detectado
        """
        print("\n=== Language Processing ===")
        print(f"Current last_detected_language: {self.last_detected_language}")
        
        try:
            # Priorizar el idioma si está explícitamente proporcionado
            if 'detected_language' in data:
                detected_language = data['detected_language']
                print(f"Language from data: {detected_language}")
            
            # Si hay una respuesta, procesar su idioma
            elif 'answer' in data:
                text_processing_result = self.chatgpt.process_text_input(
                    data['answer'], 
                    self.last_detected_language
                )
                detected_language = text_processing_result.get('detected_language', 'en-US')
                
                # CLAVE: Priorizar idiomas que NO sean inglés
                if detected_language != 'en-US':
                    self.last_detected_language = detected_language
                
                print(f"Input answer: {data['answer']}")
                print(f"Detected language: {detected_language}")
            
            else:
                # Usar el último idioma detectado o el predeterminado
                detected_language = self.last_detected_language
                print("No answer provided, using previous language")
            
            # Actualizar último idioma detectado
            self.last_detected_language = detected_language
            
            print(f"Final detected language: {detected_language}")
            return detected_language
        
        except Exception as e:
            print(f"Error in language detection: {e}")
            # Fallback a inglés en caso de error
            self.last_detected_language = 'en-US'
            return 'en-US'

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
        original_message = "Would you like to include client-side companies?"
        translated_message = self.chatgpt.translate_message(original_message, detected_language)
        
        print(f"Original message: {original_message}")
        print(f"Translated message: {translated_message}")
        
        return {
            'success': True,
            'message': translated_message,
            'detected_language': detected_language,
            'sector': data.get('sector'),
            'region': data.get('region'),
            'stage': 'question'
        }

    def _process_perspective_response(self, data, detected_language):
        """
        Procesar respuesta de perspectiva manteniendo el idioma original
        
        :param data: Datos de la solicitud
        :param detected_language: Idioma detectado
        :return: Respuesta procesada
        """
        print("\n=== Perspective Response Processing ===")
        print(f"Input answer: {data['answer']}")
        print(f"Detected language: {detected_language}")
        
        # Traducir la respuesta del usuario al inglés SOLO para procesar la intención
        translated_answer = self.chatgpt.translate_message(data['answer'], 'en-US')
        print(f"Translated answer: {translated_answer}")
        
        # Extraer intención
        intention_result = self.chatgpt.extract_intention(translated_answer)
        print(f"Intention extraction result: {intention_result}")
        
        intention = intention_result.get('intention') if intention_result.get('success') else None
        print(f"Extracted intention: {intention}")

        # Manejar respuesta basado en la intención, manteniendo el idioma original
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
        :return: Respuesta procesada
        """
        print("\n=== Positive Response Handling ===")
        
        # Mensaje de confirmación en el idioma detectado
        confirmation_message = "Great! We'll include client-side companies in the search."
        translated_message = self.chatgpt.translate_message(confirmation_message, detected_language)
        
        return {
            'success': True,
            'message': translated_message,
            'detected_language': detected_language,
            'include_client_companies': True,
            'sector': data.get('sector'),
            'region': data.get('region')
        }

    def _handle_negative_response(self, detected_language, data):
        """
        Manejar respuesta negativa en el idioma detectado
        
        :param detected_language: Idioma detectado
        :param data: Datos de la solicitud
        :return: Respuesta procesada
        """
        print("\n=== Negative Response Handling ===")
        
        # Mensaje de confirmación en el idioma detectado
        confirmation_message = "Understood. We'll proceed without client-side companies."
        translated_message = self.chatgpt.translate_message(confirmation_message, detected_language)
        
        return {
            'success': True,
            'message': translated_message,
            'detected_language': detected_language,
            'include_client_companies': False,
            'sector': data.get('sector'),
            'region': data.get('region')
        }

    def _handle_unclear_response(self, detected_language):
        """
        Manejar respuesta poco clara en el idioma detectado
        
        :param detected_language: Idioma detectado
        :return: Respuesta procesada
        """
        print("\n=== Unclear Response Handling ===")
        
        # Mensaje de solicitud de aclaración en el idioma detectado
        clarification_message = "I'm sorry, could you please clearly answer yes or no about including client-side companies?"
        translated_message = self.chatgpt.translate_message(clarification_message, detected_language)
        
        return {
            'success': False,
            'message': translated_message,
            'detected_language': detected_language,
            'stage': 'clarification'
        }

    def reset_last_detected_language(self, language='en-US'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        print(f"\n=== Resetting Last Detected Language to: {language} ===")
        self.last_detected_language = language