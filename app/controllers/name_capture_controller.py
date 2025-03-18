from src.utils.chatgpt_helper import ChatGPTHelper

class NameCaptureController:
    def __init__(self):
        self.chatgpt = ChatGPTHelper()
        self.last_detected_language = 'en-US'

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
                'error': 'Missing required field: text'
            }
        
        if 'is_registered' not in data:
            return {
                'is_valid': False,
                'error': 'Missing required field: is_registered'
            }
        
        return {
            'is_valid': True,
            'text': data['text'],
            'is_registered': data['is_registered']
        }

    def capture_name(self, data):
        """
        Capturar y procesar nombre
        
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
            detected_language = self._process_language(validation_result)
            print(f"Detected Language: {detected_language}")
            
            input_text = validation_result['text']
            is_registered = validation_result['is_registered']
            
            # Extracción de nombre
            name_extraction_result = self.chatgpt.extract_name(input_text)
            
            if not name_extraction_result['success']:
                return {
                    'success': False, 
                    'error': 'No valid name found in text',
                    'status_code': 400
                }

            name = name_extraction_result['name']
            
            # Generación de respuesta
            if is_registered:
                response = self._handle_registered_user(name, detected_language)
            else:
                response = self._handle_unregistered_user(name, detected_language)
            
            # Añadir código de estado a la respuesta
            response['status_code'] = 200
            
            return response

        except Exception as e:
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
            
            # Si hay un texto, procesar su idioma
            elif 'text' in data:
                text_processing_result = self.chatgpt.process_text_input(
                    data['text'], 
                    self.last_detected_language
                )
                detected_language = text_processing_result.get('detected_language', 'en-US')
                
                # CLAVE: Priorizar idiomas que NO sean inglés
                if detected_language != 'en-US':
                    self.last_detected_language = detected_language
                
                print(f"Input text: {data['text']}")
                print(f"Detected language: {detected_language}")
            
            else:
                # Usar el último idioma detectado o el predeterminado
                detected_language = self.last_detected_language
                print("No text provided, using previous language")
            
            # Actualizar último idioma detectado
            self.last_detected_language = detected_language
            
            print(f"Final detected language: {detected_language}")
            return detected_language
        
        except Exception as e:
            print(f"Error in language detection: {e}")
            # Fallback a inglés en caso de error
            self.last_detected_language = 'en-US'
            return 'en-US'

    def _handle_registered_user(self, name, detected_language):
        """
        Manejar respuesta para usuario registrado
        
        :param name: Nombre del usuario
        :param detected_language: Idioma detectado
        :return: Diccionario de respuesta
        """
        base_message = f"Welcome back {name}! Would you like to connect with our experts?"
        translated_message = self.chatgpt.translate_message(base_message, detected_language)
        
        yes_option = self.chatgpt.translate_message("yes", detected_language)
        no_option = self.chatgpt.translate_message("no", detected_language)

        return {
            'success': True,
            'name': name,
            'detected_language': detected_language,
            'step': 'ask_expert_connection',
            'message': translated_message,
            'next_action': 'provide_expert_answer',
            'options': [yes_option, no_option]
        }

    def _handle_unregistered_user(self, name, detected_language):
        """
        Manejar respuesta para usuario no registrado
        
        :param name: Nombre del usuario
        :param detected_language: Idioma detectado
        :return: Diccionario de respuesta
        """
        base_message = f"Thank you {name}! To better assist you, we recommend speaking with one of our agents."
        translated_message = self.chatgpt.translate_message(base_message, detected_language)
        
        booking_message = self.chatgpt.translate_message(
            "Would you like to schedule a call?",
            detected_language
        )

        return {
            'success': True,
            'name': name,
            'detected_language': detected_language,
            'step': 'propose_agent_contact',
            'message': translated_message,
            'booking_message': booking_message,
            'next_action': 'schedule_call',
            'action_required': 'book_call',
            'booking_link': "https://calendly.com/your-booking-link"
        }

    def reset_last_detected_language(self, language='en-US'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        print(f"\n=== Resetting Last Detected Language to: {language} ===")
        self.last_detected_language = language