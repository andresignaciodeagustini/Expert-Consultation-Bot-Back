from src.utils.chatgpt_helper import ChatGPTHelper

class EvaluationQuestionsController:
    def __init__(self, chatgpt=None):
        self.chatgpt = chatgpt or ChatGPTHelper()
        self.last_detected_language = 'en-US'
        
        self.BASE_MESSAGES = {
            'ask_preference': "Would you like to add evaluation questions for the project?",
            'confirmed_yes': "Excellent! We will proceed with evaluation questions.",
            'confirmed_no': "Understood. We will proceed without evaluation questions.",
            'processing_error': "An error occurred while processing your request.",
            'invalid_response': "Could not determine your preference. Please answer yes or no."
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
        return {
            'is_valid': True,
            'data': data
        }

    def process_evaluation_questions(self, data):
        """
        Procesar preguntas de evaluación
        
        :param data: Datos de la solicitud
        :return: Respuesta procesada
        """
        try:
            print("\n=== Processing Evaluation Questions ===")
            
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
            
            error_message = "An error occurred while processing your request."
            translated_error = self._translate_message(error_message, self.last_detected_language)

            return {
                'success': False,
                'error': translated_error,
                'details': str(e),
                'detected_language': self.last_detected_language,
                'status_code': 500
            }

    def _process_language(self, data):
        """
        Procesar y detectar idioma
        
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
        Solicitar perspectiva inicial
        
        :param detected_language: Idioma detectado
        :param data: Datos de la solicitud
        :return: Respuesta inicial
        """
        print("\n=== Initial Perspective Request ===")
        print(f"Detected language: {detected_language}")
        
        # Traducir el mensaje base
        original_message = self.BASE_MESSAGES['ask_preference']
        translated_message = self._translate_message(original_message, detected_language)
        
        print(f"Original message: {original_message}")
        print(f"Translated message: {translated_message}")
        
        return {
            'success': True,
            'message': translated_message,
            'detected_language': detected_language,
            'sector': data.get('sector'),
            'region': data.get('region'),
            'stage': 'initial_question'
        }

    def _process_perspective_response(self, data, detected_language):
        """
        Procesar respuesta de perspectiva
        
        :param data: Datos de la solicitud
        :param detected_language: Idioma detectado
        :return: Respuesta procesada
        """
        print("\n=== Perspective Response Processing ===")
        print(f"Input answer: {data['answer']}")
        print(f"Detected language: {detected_language}")
        
        # Extraer intención
        intention_result = self.chatgpt.extract_intention(data['answer'])
        print(f"Intention extraction result: {intention_result}")
        
        intention = intention_result.get('intention') if intention_result.get('success') else None
        print(f"Extracted intention: {intention}")

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
        
        return {
            'success': True,
            'message': confirmation_message,
            'detected_language': detected_language,
            'include_companies': True,
            'sector': data.get('sector'),
            'region': data.get('region'),
            'additional_info': {
                'evaluation_required': True,
                'stage': 'questions'
            }
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
        self.last_detected_language = language