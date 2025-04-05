import traceback
from src.utils.chatgpt_helper import ChatGPTHelper
# Importar funciones de gestión de idioma global
from app.constants.language import get_last_detected_language, update_last_detected_language
import re

class NameCaptureController:
    def __init__(self):
        self.chatgpt = ChatGPTHelper()

    def capture_name(self, data):
        """
        Capturar y procesar nombre
        
        :param data: Datos de la solicitud
        :return: Respuesta procesada
        """
        try:
            print("\n=== Language Detection Debug ===")
            # Obtener el último idioma detectado globalmente
            previous_language = get_last_detected_language()
            print(f"Previous detected language (global): {previous_language}")
            
            # Validar datos de entrada
            if 'text' not in data or 'is_registered' not in data:
                print("Error: Missing required fields")
                return {
                    'success': False,
                    'message': 'Text and registration status are required',
                    'type': 'bot',
                    'isError': True
                }

            print(f"Received data: {data}")
            print(f"Language from request: {previous_language}")
            
            # SOLUCIÓN: Prioridad estricta para el idioma
            # 1. Usar el idioma proporcionado en la solicitud si existe
            # 2. Para textos que parecen ser solo un nombre, mantener ESTRICTAMENTE el idioma anterior
            # 3. Para otros textos, usar el proceso normal de detección
            
            if 'detected_language' in data and data['detected_language']:
                # Usar el idioma proporcionado en la solicitud con prioridad máxima
                detected_language = data['detected_language']
                print(f"STRICT RULE: Using language from request data: {detected_language}")
            else:
                # Verificar si el texto parece ser solo un nombre (corto, sin @ o números)
                is_likely_just_name = (len(data['text']) <= 30 and 
                                      '@' not in data['text'] and 
                                      not any(char.isdigit() for char in data['text']))
                
                if is_likely_just_name:
                    # REGLA ESTRICTA: Para textos que parecen ser solo un nombre, mantener el idioma anterior
                    detected_language = previous_language
                    print(f"STRICT RULE: Text appears to be just a name, STRICTLY maintaining previous language: {previous_language}")
                else:
                    # Para textos más complejos, usar el proceso normal
                    print("\n=== Language Processing for Complex Text ===")
                    text_processing_result = self.chatgpt.process_text_input(
                        data['text'], 
                        previous_language
                    )
                    detected_language = text_processing_result.get('detected_language', previous_language)
                    print(f"Processed language from helper: {detected_language}")
            
            # IMPORTANTE: Actualizar el idioma global con el valor que hemos determinado
            # El ChatGPTHelper es responsable de formatear correctamente el código de idioma
            update_last_detected_language(detected_language)
            print(f"Updated global language to: {detected_language}")
            
            # Verificar que la actualización fue exitosa
            current_language = get_last_detected_language()
            print(f"Verified current global language: {current_language}")

            # Extracción de nombre
            print("\n=== Name Extraction ===")
            name_extraction_result = self.chatgpt.extract_name(data['text'])
            print(f"Name extraction result: {name_extraction_result}")

            if not name_extraction_result['success']:
                print("Error: No valid name found")
                
                # Crear mensaje de error personalizado según el idioma detectado
                error_base_message = "Please provide a valid name (avoid using only numbers or symbols)"
                translated_error = self.chatgpt.translate_message(error_base_message, detected_language)
                
                return {
                    'success': False, 
                    'message': translated_error,
                    'type': 'bot',
                    'isError': True,
                    'error_type': 'invalid_name_format',
                    'detected_language': detected_language
                }

            name = name_extraction_result['name']
            is_registered = data['is_registered']
            print(f"Extracted name: {name}")
            print(f"Is registered: {is_registered}")
            
            # DEBUG: Verificar idioma antes de la generación de respuesta
            print(f"Language for response generation: {detected_language}")

            # Generación de respuesta - pasar el idioma determinado directamente
            print("\n=== Message Translation ===")
            if is_registered:
                response = self._handle_registered_user(name, detected_language)
            else:
                response = self._handle_unregistered_user(name, detected_language)

            # Añadir campos adicionales para el frontend
            response['type'] = 'bot'
            response['companies'] = None
            response['isError'] = False
            
            # Asegurar que el idioma detectado esté en la respuesta
            if 'detected_language' not in response or not response['detected_language']:
                response['detected_language'] = detected_language
            
            # DEBUG: Verificar el idioma en la respuesta final
            print(f"Final response language: {response.get('detected_language')}")

            print("\n=== Final Response ===")
            print(f"Sending response: {response}")
            return response

        except Exception as e:
            print(f"\n=== Detailed Error Handling ===")
            print(f"Full error details: {traceback.format_exc()}")
            
            error_message = f"An error occurred while processing your request: {str(e)}"
            try:
                error_message = self.chatgpt.translate_message(
                    error_message, 
                    previous_language
                )
            except Exception:
                pass

            print(f"Translated error message: {error_message}")
            return {
                'success': False,
                'error': error_message,
                'type': 'bot',
                'isError': True
            }

    def _handle_registered_user(self, name, detected_language):
        """
        Manejar respuesta para usuario registrado
        
        :param name: Nombre del usuario
        :param detected_language: Idioma detectado
        :return: Diccionario de respuesta
        """
        # SOLUCIÓN: Confiar ESTRICTAMENTE en el idioma pasado por la función principal
        print(f"STRICT RULE: Using passed language in _handle_registered_user: {detected_language}")
        
        # Comprobar si el nombre es válido o es "No_name"
        if name and name != "No_name":
            base_message = f"Welcome back {name}! Would you like to connect with our experts?"
        else:
            base_message = "Welcome back! Would you like to connect with our experts?"
        
        # DEBUG: Registro antes de traducción
        print(f"Base message before translation: '{base_message}'")
        print(f"Using language for translation: '{detected_language}'")
        
        # Hacer una llamada directa a translate_message con el idioma exacto
        translated_message = self.chatgpt.translate_message(base_message, detected_language)
        print(f"Translated welcome message: '{translated_message}'")
        
        yes_option = self.chatgpt.translate_message("yes", detected_language)
        no_option = self.chatgpt.translate_message("no", detected_language)
        print(f"Translated options: yes='{yes_option}', no='{no_option}'")

        # No es necesario actualizar el idioma global aquí, ya se hizo en la función principal

        return {
            'success': True,
            'name': name,
            'detected_language': detected_language,  # Usar directamente el idioma pasado
            'step': 'ask_expert_connection',
            'message': translated_message,
            'next_action': 'provide_expert_answer',
            'options': [yes_option, no_option],
            'type': 'bot',
            'companies': None,
            'isError': False
        }

    def _handle_unregistered_user(self, name, detected_language):
        """
        Manejar respuesta para usuario no registrado
        
        :param name: Nombre del usuario
        :param detected_language: Idioma detectado
        :return: Diccionario de respuesta
        """
        # SOLUCIÓN: Confiar ESTRICTAMENTE en el idioma pasado por la función principal
        print(f"STRICT RULE: Using passed language in _handle_unregistered_user: {detected_language}")
        
        base_message = f"Thank you {name}! To better assist you, we recommend speaking with one of our agents."
        translated_message = self.chatgpt.translate_message(base_message, detected_language)
        print(f"Translated thank you message: '{translated_message}'")
        
        booking_message = self.chatgpt.translate_message(
            "Would you like to schedule a call?",
            detected_language
        )
        print(f"Translated booking message: '{booking_message}'")
        
        # No es necesario actualizar el idioma global aquí, ya se hizo en la función principal

        return {
            'success': True,
            'name': name,
            'detected_language': detected_language,  # Usar directamente el idioma pasado
            'step': 'propose_agent_contact',
            'message': translated_message,
            'booking_message': booking_message,
            'next_action': 'schedule_call',
            'action_required': 'book_call',
            'booking_link': "https://calendly.com/your-booking-link",
            'type': 'bot',
            'companies': None,
            'isError': False
        }