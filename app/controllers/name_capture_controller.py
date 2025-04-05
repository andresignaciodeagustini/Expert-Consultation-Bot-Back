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
            
            # Verificar si tenemos datos de idioma en la solicitud
            if 'detected_language' in data and data['detected_language']:
                # Usar el idioma proporcionado en la solicitud
                custom_language = data['detected_language']
                print(f"Using language from request data: {custom_language}")
                detected_language = custom_language
            else:
                # Procesamiento de idioma
                print("\n=== Language Processing ===")
                text_processing_result = self.chatgpt.process_text_input(
                    data['text'], 
                    previous_language
                )
                detected_language = text_processing_result.get('detected_language', previous_language)

                # Solo mantener el idioma anterior si el texto es corto Y no contiene caracteres especiales
                non_latin_pattern = re.compile(r'[^\x00-\x7F]')
                has_non_latin = bool(non_latin_pattern.search(data['text']))

                # Si el texto es muy corto pero contiene caracteres no latinos, confiar en la detección de idioma
                # Si es solo texto latino corto, mantener el idioma anterior para evitar cambios incorrectos
                if len(data['text']) <= 15 and not has_non_latin:
                    detected_language = previous_language
                    print(f"Short latin text detected, maintaining previous language: {previous_language}")
            
            # Verificar si el idioma tiene formato correcto (código de dos letras con región)
            if detected_language and len(detected_language) > 2 and '-' in detected_language:
                lang_code = detected_language
            else:
                # Mapear códigos de idioma simples a formato regional
                language_map = {
                    'es': 'es-ES', 'en': 'en-US', 'fr': 'fr-FR', 'de': 'de-DE', 
                    'it': 'it-IT', 'pt': 'pt-PT'
                }
                lang_code = language_map.get(detected_language.lower(), 'en-US') if detected_language else 'en-US'
                print(f"Mapped language code from {detected_language} to {lang_code}")
            
            # DEBUG: Verificar idioma antes de actualizar global
            print(f"Final detected language before global update: {lang_code}")
            
            # Actualizar idioma global - IMPORTANTE: Forzar una actualización explícita
            update_last_detected_language(lang_code)
            print(f"Updated LAST_DETECTED_LANGUAGE to: {lang_code}")
            
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
                translated_error = self.chatgpt.translate_message(error_base_message, lang_code)
                
                return {
                    'success': False, 
                    'message': translated_error,
                    'type': 'bot',
                    'isError': True,
                    'error_type': 'invalid_name_format',
                    'detected_language': lang_code
                }

            name = name_extraction_result['name']
            is_registered = data['is_registered']
            print(f"Extracted name: {name}")
            print(f"Is registered: {is_registered}")
            
            # DEBUG: Verificar idioma antes de la generación de respuesta
            print(f"Language for response generation: {lang_code}")

            # Generación de respuesta
            print("\n=== Message Translation ===")
            if is_registered:
                response = self._handle_registered_user(name, lang_code)
            else:
                response = self._handle_unregistered_user(name, lang_code)

            # Añadir campos adicionales para el frontend
            response['type'] = 'bot'
            response['companies'] = None
            response['isError'] = False
            
            # Asegurar que el idioma detectado esté en la respuesta
            if 'detected_language' not in response or not response['detected_language']:
                response['detected_language'] = lang_code
            
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
        # DEBUG: Verificar idioma al entrar a _handle_registered_user
        print(f"Language in _handle_registered_user: {detected_language}")
        
        # Verificar si el idioma tiene formato correcto (código de dos letras con región)
        if detected_language and len(detected_language) > 2 and '-' in detected_language:
            lang_code = detected_language
        else:
            # Si no tiene formato correcto, obtener el último idioma detectado globalmente
            lang_code = get_last_detected_language()
            print(f"Using global language instead: {lang_code}")
        
        print(f"Final language code for translation: {lang_code}")
        
        # Comprobar si el nombre es válido o es "No_name"
        if name and name != "No_name":
            base_message = f"Welcome back {name}! Would you like to connect with our experts?"
        else:
            base_message = "Welcome back! Would you like to connect with our experts?"
        
        # DEBUG: Registro antes de traducción
        print(f"Base message before translation: '{base_message}'")
        print(f"Using language for translation: '{lang_code}'")
        
        # Hacer una llamada directa a translate_message con el idioma exacto
        translated_message = self.chatgpt.translate_message(base_message, lang_code)
        print(f"Translated welcome message: '{translated_message}'")
        
        yes_option = self.chatgpt.translate_message("yes", lang_code)
        no_option = self.chatgpt.translate_message("no", lang_code)
        print(f"Translated options: yes='{yes_option}', no='{no_option}'")

        # Asegurar que se actualice el idioma global
        update_last_detected_language(lang_code)

        return {
            'success': True,
            'name': name,
            'detected_language': lang_code,  # Usar el código de idioma verificado
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
        # DEBUG: Verificar idioma al entrar a _handle_unregistered_user
        print(f"Language in _handle_unregistered_user: {detected_language}")
        
        # Verificar si el idioma tiene formato correcto (código de dos letras con región)
        if detected_language and len(detected_language) > 2 and '-' in detected_language:
            lang_code = detected_language
        else:
            # Si no tiene formato correcto, obtener el último idioma detectado globalmente
            lang_code = get_last_detected_language()
            print(f"Using global language instead: {lang_code}")
        
        print(f"Final language code for translation: {lang_code}")
        
        base_message = f"Thank you {name}! To better assist you, we recommend speaking with one of our agents."
        translated_message = self.chatgpt.translate_message(base_message, lang_code)
        print(f"Translated thank you message: '{translated_message}'")
        
        booking_message = self.chatgpt.translate_message(
            "Would you like to schedule a call?",
            lang_code
        )
        print(f"Translated booking message: '{booking_message}'")
        
        # Asegurar que se actualice el idioma global
        update_last_detected_language(lang_code)

        return {
            'success': True,
            'name': name,
            'detected_language': lang_code,  # Usar el código de idioma verificado
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