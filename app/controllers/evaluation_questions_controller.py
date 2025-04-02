from src.utils.chatgpt_helper import ChatGPTHelper
import re
# Importar funciones de gestión de idioma global
from app.constants.language import (
    get_last_detected_language, 
    update_last_detected_language, 
    reset_last_detected_language
)

class EvaluationQuestionsController:
    def __init__(self, chatgpt=None):
        self.chatgpt = chatgpt or ChatGPTHelper()
        
        self.BASE_MESSAGES = {
            'ask_preference': "Would you like to add evaluation questions for the project?",
            'confirmed_yes': "Excellent! We will proceed with evaluation questions.",
            'confirmed_no': "Understood. We will proceed without evaluation questions.",
            'processing_error': "An error occurred while processing your request.",
            'invalid_response': "Could not determine your preference. Please answer yes or no.",
            'nonsense_input': "Please provide a valid response. Would you like to add evaluation questions for the project? Please answer with 'yes' or 'no'."
        }

    def _translate_message(self, message, detected_language):
        """
        Método genérico para traducir mensajes
        """
        try:
            return self.chatgpt.translate_message(message, detected_language)
        except Exception as e:
            print(f"Translation error: {e}")
            return message

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
        
        # Normalizar entrada
        if 'text' in data and 'answer' not in data:
            data['answer'] = data['text']
        
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
        Detecta si el texto parece no tener sentido
        
        :param text: Texto a evaluar
        :return: True si parece ser texto sin sentido, False en caso contrario
        """
        if not text:
            return False
            
        # Quitar espacios extras
        text = text.strip().lower()
        
        # Respuestas válidas específicas para este controlador
        valid_answers = ['yes', 'y', 'yeah', 'yep', 'si', 'sí', 'no', 'n', 'nope', 'no,', 'noo', 'yes,', 'yess']
        if text in valid_answers:
            return False
            
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

    def process_evaluation_questions(self, data):
        """
        Procesar preguntas de evaluación
        
        :param data: Datos de la solicitud
        :return: Respuesta procesada
        """
        try:
            print("\n=== Processing Evaluation Questions ===")
            
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
                    guidance_message = self._translate_message(
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
            
            # Extraer datos validados
            answer = validation_result['data'].get('answer', '')
            stage = validation_result['data'].get('stage', 'initial_question')
            
            # Manejar diferentes etapas
            if not answer:
                print("No answer provided, requesting initial perspective")
                response = self._request_initial_perspective(detected_language, validation_result['data'])
            else:
                print(f"Processing answer: {answer}")
                response = self._process_perspective_response(validation_result['data'], detected_language)
            
            # Añadir código de estado a la respuesta
            response['status_code'] = 200 if response.get('success', False) else 400
            
            print("\n=== Final Response ===")
            print(f"Response: {response}")
            
            return response

        except Exception as e:
            print(f"\n=== Error in process_evaluation_questions ===")
            print(f"Error details: {str(e)}")
            
            # Usar el mensaje base y traducirlo si es necesario
            current_language = get_last_detected_language()
            error_message = self._translate_message(
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
        Procesar y detectar idioma
        
        :param data: Datos de la solicitud
        :return: Idioma detectado
        """
        print("\n=== Language Processing ===")
        current_language = get_last_detected_language()
        print(f"Current detected language: {current_language}")
        
        # Priorizar idiomas explícitamente proporcionados
        if 'detected_language' in data:
            detected_language = data['detected_language']
            print(f"Language from data: {detected_language}")
            update_last_detected_language(detected_language)
            return detected_language
        
        if 'language' in data:
            detected_language = data['language']
            print(f"Language from 'language' field: {detected_language}")
            update_last_detected_language(detected_language)
            return detected_language
        
        # Intentar obtener texto para detección de idioma
        text_to_detect = ' '.join([
            str(data.get('language', '')),
            ' '.join(data.get('selected_experts', [])),
            ' '.join(data.get('evaluation_questions', {}).keys())
        ])
        
        print(f"=== Language Detection Debug ===")
        print(f"Input Text: {text_to_detect}")
        print(f"Previous Language: {current_language}")
        
        text_processing_result = self.chatgpt.process_text_input(
            text_to_detect if text_to_detect.strip() else "test", 
            current_language
        )
        detected_language = text_processing_result.get('detected_language', current_language)
        
        print(f"Detected Language: {detected_language}")
        
        # Forzar el idioma original si la detección intenta cambiarlo
        if detected_language != current_language:
            print(f"FORCE: Maintaining original language {current_language}")
            detected_language = current_language
        
        # Actualizar el idioma detectado
        update_last_detected_language(detected_language)
        
        return detected_language

    def _request_initial_perspective(self, detected_language, data):
        """
        Solicitar perspectiva inicial
        
        :param detected_language: Idioma detectado
        :param data: Datos de la solicitud
        :return: Respuesta inicial
        """
        print("\n=== Initial Perspective Request ===")
        print(f"Detected language: {detected_language}")
        
        # Traducir el mensaje base al idioma detectado
        initial_message = self._translate_message(
            self.BASE_MESSAGES['ask_preference'], 
            detected_language
        )
        
        print(f"Base message: {self.BASE_MESSAGES['ask_preference']}")
        print(f"Translated message: {initial_message}")
        
        return {
            'success': True,
            'message': initial_message,
            'detected_language': detected_language,
            'sector': data.get('sector'),
            'region': data.get('region'),
            'stage': 'initial_question'
        }

    def _process_perspective_response(self, data, detected_language):
        """
        Procesar respuesta de perspectiva con comprobación directa
        
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
        Manejar respuesta positiva
        
        :param data: Datos de la solicitud
        :param detected_language: Idioma detectado
        :return: Respuesta procesada
        """
        print("\n=== Positive Response Handling ===")
        
        # Traducir mensaje de confirmación
        confirmation_message = self._translate_message(
            self.BASE_MESSAGES['confirmed_yes'], 
            detected_language
        )
        
        print(f"Response message: {confirmation_message}")
        
        return {
        'success': True,
        'message': confirmation_message,
        'detected_language': detected_language,
        'include_companies': True,
        'sector': data.get('sector'),
        'region': data.get('region'),
        'evaluation_required': True,
        'answer_received': 'yes',
        'stage': 'questions'
    }

    def _handle_negative_response(self, detected_language, data):
        """
        Manejar respuesta negativa
        
        :param detected_language: Idioma detectado
        :param data: Datos de la solicitud
        :return: Respuesta procesada
        """
        print("\n=== Negative Response Handling ===")
        
        # Traducir mensaje de confirmación
        confirmation_message = self._translate_message(
            self.BASE_MESSAGES['confirmed_no'], 
            detected_language
        )
        
        print(f"Response message: {confirmation_message}")
        
        return {
            'success': True,
            'message': confirmation_message,
            'detected_language': detected_language,
            'include_companies': False,
            'sector': data.get('sector'),
            'region': data.get('region')
        }

    def _handle_unclear_response(self, detected_language):
        """
        Manejar respuesta poco clara
        
        :param detected_language: Idioma detectado
        :return: Respuesta procesada
        """
        print("\n=== Unclear Response Handling ===")
        
        # Traducir mensaje de aclaración
        clarification_message = self._translate_message(
            self.BASE_MESSAGES['invalid_response'], 
            detected_language
        )
        
        print(f"Response message: {clarification_message}")
        
        return {
            'success': False,
            'message': clarification_message,
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