from src.utils.chatgpt_helper import ChatGPTHelper

class ExpertConnectionController:
    def __init__(self):
        self.chatgpt = ChatGPTHelper()
        self.last_detected_language = 'en'

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
        
        required_fields = ['text', 'name']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            return {
                'is_valid': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }
        
        return {
            'is_valid': True,
            'text': data['text'],
            'name': data['name']
        }

    def ask_expert_connection(self, data):
        """
        Manejar la conexión con expertos
        
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
            
            # Extraer datos validados
            text = validation_result['text']
            name = validation_result['name']
            
            # Procesamiento de idioma
            text_processing_result = self.chatgpt.process_text_input(
                text, 
                self.last_detected_language
            )
            detected_language = text_processing_result.get('detected_language', 'en')
            
            # Actualizar idioma
            self.last_detected_language = detected_language

            # Extracción de intención
            intention_result = self.chatgpt.extract_intention(text)

            if not intention_result['success']:
                translated_error = self.chatgpt.translate_message(
                    intention_result['error'], 
                    detected_language
                )
                return {
                    'success': False,
                    'error': translated_error,
                    'step': 'clarify',
                    'status_code': 400
                }

            intention = intention_result['intention']

            # Generación de respuesta
            response = self._generate_response(intention, name, detected_language)
            
            # Añadir código de estado a la respuesta
            response['status_code'] = 200 if response.get('success', False) else 400
            
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

    def _generate_response(self, intention, name, detected_language):
        """
        Generar respuesta basada en la intención
        
        :param intention: Intención detectada
        :param name: Nombre del usuario
        :param detected_language: Idioma detectado
        :return: Diccionario de respuesta
        """
        if intention == 'yes':
            base_message = f"¡Excelente! ¿En qué sector estás más interesado? Puedes elegir entre sectores como Tecnología, Salud, Finanzas, Educación, o cualquier otro sector que te interese."
            translated_message = self.chatgpt.translate_message(base_message, detected_language)
            
            return {
                'success': True,
                'name': name,
                'detected_language': detected_language,
                'step': 'select_sector',
                'message': translated_message,
                'next_action': 'process_sector_selection'
            }

        elif intention == 'no':
            base_message = f"I understand, {name}. Feel free to come back when you'd like to connect with our experts. Have a great day!"
            translated_message = self.chatgpt.translate_message(base_message, detected_language)
            
            return {
                'success': True,
                'name': name,
                'detected_language': detected_language,
                'step': 'farewell',
                'message': translated_message,
                'next_action': 'end_conversation'
            }

        else:  # intention is 'unclear'
            base_message = "I'm not sure if that's a yes or no. Could you please clarify?"
            translated_message = self.chatgpt.translate_message(base_message, detected_language)
            
            return {
                'success': True,
                'message': translated_message,
                'detected_language': detected_language,
                'step': 'clarify'
            }

    def reset_last_detected_language(self, language='en'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        self.last_detected_language = language