from src.utils.chatgpt_helper import ChatGPTHelper

class CompaniesAgreementController:
    def __init__(self):
        self.chatgpt = ChatGPTHelper()
        self.last_detected_language = 'en-US'
        
        self.BASE_MESSAGES = {
            'positive_response': "Great! Let's proceed with these companies.",
            'negative_response': "I'll help you find different company suggestions.",
            'processing_error': "Error processing your request",
            'intention_error': 'Could not determine if you agree with the list. Please answer yes or no.',
            'input_error': 'Text is required',
            'invalid_input': 'Your input seems invalid. Please respond with yes/no to indicate if you agree with the list of companies.'
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
        
        if 'text' not in data:
            return {
                'is_valid': False,
                'error': self.BASE_MESSAGES['input_error']
            }
        
        return {
            'is_valid': True,
            'text': data['text']
        }

    def process_companies_agreement(self, data):
        """
        Procesar acuerdo sobre lista de empresas
        
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
            
            input_text = validation_result['text']
            
            # Procesamiento de idioma
            text_processing_result = self.chatgpt.process_text_input(
                input_text, 
                self.last_detected_language
            )
            detected_language = text_processing_result.get('detected_language', 'en-US')
            
            # Actualizar idioma
            self.last_detected_language = detected_language
            
            # Extracción de intención
            intention = self.chatgpt.extract_intention(input_text)
            
            # Log de depuración
            print(f"\n=== Intention Extraction ===")
            print(f"Raw Intention: {intention}")
            
            # Validar intención
            if intention is None or (isinstance(intention, dict) and intention.get('success') is False):
                error_message = self.BASE_MESSAGES['intention_error']
                translated_error = self.chatgpt.translate_message(error_message, detected_language)
                return {
                    'success': False,
                    'error': translated_error,
                    'status_code': 400
                }

            # Generar respuesta
            response = self._generate_response(intention, detected_language)
            
            # Añadir código de estado a la respuesta
            response['status_code'] = 200
            
            # Log de depuración de la respuesta final
            print("\n=== Final Response ===")
            print(f"Response: {response}")
            
            return response

        except Exception as e:
            # Manejo de error con traducción
            error_message = self.BASE_MESSAGES['processing_error']
            try:
                translated_error = self.chatgpt.translate_message(
                    error_message, 
                    self.last_detected_language
                )
            except Exception:
                translated_error = error_message

            # Log de error detallado
            print("\n=== Error Handling ===")
            print(f"Error type: {type(e)}")
            print(f"Error details: {str(e)}")
            
            return {
                'success': False,
                'error': translated_error,
                'details': str(e),
                'detected_language': self.last_detected_language,
                'status_code': 500
            }

    def _generate_response(self, intention, detected_language):
        """
        Generar respuesta basada en la intención
        
        :param intention: Resultado de extracción de intención
        :param detected_language: Idioma detectado
        :return: Diccionario de respuesta
        """
        # Depuración de la intención de entrada
        print("\n=== Response Generation ===")
        print(f"Input Intention: {intention}")
        
        # Manejar diferentes formatos de intención
        is_positive = False
        
        # Verificar si intention es None
        if intention is None:
            # Traducir mensaje de error
            error_message = self.BASE_MESSAGES['invalid_input']
            translated_message = self.chatgpt.translate_message(error_message, detected_language)
            
            return {
                'success': False,
                'error': translated_message,
                'detected_language': detected_language
            }
            
        # Si intention es un diccionario
        if isinstance(intention, dict):
            # Verificar si hay un campo 'intention' y es distinto de None
            if 'intention' in intention and intention['intention'] is not None:
                is_positive = intention.get('intention', '').lower() == 'yes'
            else:
                # Si no hay 'intention' o es None, responder con error
                error_message = self.BASE_MESSAGES['invalid_input']
                translated_message = self.chatgpt.translate_message(error_message, detected_language)
                
                return {
                    'success': False,
                    'error': translated_message,
                    'detected_language': detected_language
                }
        else:
            # Si intention no es un diccionario, intentar convertirlo a string
            try:
                is_positive = str(intention).lower() == 'yes'
            except:
                # Si falla la conversión, responder con error
                error_message = self.BASE_MESSAGES['invalid_input']
                translated_message = self.chatgpt.translate_message(error_message, detected_language)
                
                return {
                    'success': False,
                    'error': translated_message,
                    'detected_language': detected_language
                }
        
        # Log de depuración de la interpretación
        print(f"Interpreted as Positive: {is_positive}")
        
        # Seleccionar mensaje base
        response_message = (
            self.BASE_MESSAGES['positive_response'] 
            if is_positive 
            else self.BASE_MESSAGES['negative_response']
        )
        
        # Traducir mensaje
        translated_message = self.chatgpt.translate_message(response_message, detected_language)

        # Preparar respuesta
        response = {
            'success': True,
            'message': translated_message,
            'agreed': {
                'intention': 'yes' if is_positive else 'no'
            },
            'detected_language': detected_language
        }
        
        # Log de depuración de la respuesta generada
        print(f"Generated Response: {response}")
        
        return response

    def reset_last_detected_language(self, language='en-US'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        self.last_detected_language = language