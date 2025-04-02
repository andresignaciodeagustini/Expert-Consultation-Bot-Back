from src.utils.chatgpt_helper import ChatGPTHelper
# Importar funciones de gestión de idioma global
from app.constants.language import get_last_detected_language, update_last_detected_language, reset_last_detected_language

class ExpertConnectionController:
    def __init__(self):
        self.chatgpt = ChatGPTHelper()

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
                    'status_code': 400,
                    'type': 'bot',
                    'isError': True
                }
            
            # Extraer datos validados
            text = validation_result['text']
            name = validation_result['name']
            
            # Obtener el último idioma detectado
            current_language = get_last_detected_language()
            
            # Procesamiento de idioma
            text_processing_result = self.chatgpt.process_text_input(
                text, 
                current_language
            )
            detected_language = text_processing_result.get('detected_language', current_language)

            # Si el texto es muy corto (menos de 15 caracteres), mantener el idioma anterior
            if len(text) <= 15:
                detected_language = current_language
            
            # Actualizar idioma global
            update_last_detected_language(detected_language)
            
            # Validación preliminar para detectar entrada no válida (solo números o símbolos)
            input_validation = self._validate_text_input(text)
            if not input_validation['is_valid']:
                # Obtener opciones traducidas al idioma detectado
                yes_option = self.chatgpt.translate_message("yes", detected_language)
                no_option = self.chatgpt.translate_message("no", detected_language)
                
                # Mensaje de error traducido
                error_base_message = "I couldn't understand your response. Would you like to connect with our experts? Please answer with yes or no."
                translated_error = self.chatgpt.translate_message(error_base_message, detected_language)
                
                return {
                    'success': False,
                    'message': translated_error,
                    'type': 'bot',
                    'isError': True,
                    'error_type': 'invalid_response_format',
                    'detected_language': detected_language,
                    'options': [yes_option, no_option],
                    'step': 'ask_expert_connection',
                    'next_action': 'provide_expert_answer',
                    'status_code': 400
                }

            # Extracción de intención usando la función existente
            intention_result = self.chatgpt.extract_intention(text)

            # Modificación aquí: Si la intención no es clara, proporcionar un mensaje claro pidiendo sí o no
            if not intention_result['success'] or intention_result.get('intention') == 'unclear':
                # Obtener opciones traducidas al idioma detectado
                yes_option = self.chatgpt.translate_message("yes", detected_language)
                no_option = self.chatgpt.translate_message("no", detected_language)
                
                # Mensaje claro solicitando una respuesta de sí o no
                clarification_message = "Would you like to connect with our experts? Please answer with yes or no."
                translated_message = self.chatgpt.translate_message(clarification_message, detected_language)
                
                return {
                    'success': True,  # Cambiado a True para que no sea un error
                    'message': translated_message,
                    'type': 'bot',
                    'isError': False,  # Cambiado a False
                    'detected_language': detected_language,
                    'options': [yes_option, no_option],
                    'step': 'ask_expert_connection',
                    'next_action': 'provide_expert_answer',
                    'status_code': 200  # Cambiado a 200 para indicar éxito
                }

            intention = intention_result['intention']

            # Generación de respuesta
            response = self._generate_response(intention, name, detected_language)
            
            # Añadir código de estado a la respuesta
            response['status_code'] = 200 if response.get('success', False) else 400
            response['type'] = 'bot'
            response['isError'] = False
            
            return response

        except Exception as e:
            # Obtener el último idioma detectado para traducir el error
            current_language = get_last_detected_language()
            
            error_message = f"An error occurred while processing your request: {str(e)}"
            try:
                error_message = self.chatgpt.translate_message(
                    error_message, 
                    current_language
                )
            except Exception:
                pass

            return {
                'success': False,
                'error': error_message,
                'status_code': 500,
                'type': 'bot',
                'isError': True
            }
    
    def _validate_text_input(self, text):
        """
        Validar si el texto contiene alguna palabra válida y no solo números o símbolos
        
        :param text: Texto a validar
        :return: Diccionario de resultado
        """
        # Eliminar espacios en blanco
        text = text.strip()
        
        # Si el texto está vacío, no es válido
        if not text:
            return {'is_valid': False, 'reason': 'empty_text'}
        
        # Verificar si el texto contiene al menos una letra
        has_letter = any(char.isalpha() for char in text)
        
        if not has_letter:
            return {'is_valid': False, 'reason': 'no_letters'}
        
        # Si tiene letras, considerar como entrada potencialmente válida para procesar
        return {'is_valid': True}

    def _generate_response(self, intention, name, detected_language):
        """
        Generar respuesta basada en la intención
        
        :param intention: Intención detectada
        :param name: Nombre del usuario
        :param detected_language: Idioma detectado
        :return: Diccionario de respuesta
        """
        if intention == 'yes':
            base_message = f"Excellent! Please tell me about the sector or field you are most interested in exploring with our experts."
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
            
            yes_option = self.chatgpt.translate_message("yes", detected_language)
            no_option = self.chatgpt.translate_message("no", detected_language)
            
            return {
                'success': True,
                'message': translated_message,
                'detected_language': detected_language,
                'step': 'clarify',
                'options': [yes_option, no_option],
                'next_action': 'provide_expert_answer'
            }

    def reset_last_detected_language(self, language='en-US'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        print(f"\n=== Resetting Last Detected Language to: {language} ===")
        reset_last_detected_language()