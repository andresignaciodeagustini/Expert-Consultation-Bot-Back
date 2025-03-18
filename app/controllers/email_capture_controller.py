import logging
from flask import jsonify
from src.utils.chatgpt_helper import ChatGPTHelper
from app.services.registration_service import RegistrationService
# Importar funciones de gestión de idioma global
from app.constants.language import get_last_detected_language, update_last_detected_language, reset_last_detected_language

class EmailCaptureController:
    def __init__(self):
        self.chatgpt = ChatGPTHelper()
        self.logger = logging.getLogger(__name__)

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
        
        return {
            'is_valid': True,
            'text': data['text']
        }

    def capture_email(self, data):
        """
        Capturar y procesar email
        
        :param data: Datos de la solicitud
        :return: Respuesta procesada
        """
        try:
            # Validar entrada
            validation_result = self.validate_input(data)
            if not validation_result['is_valid']:
                self.logger.error(f"Input validation failed: {validation_result['error']}")
                return {
                    'success': False,
                    'error': validation_result['error']
                }
            
            input_text = validation_result['text']
            
            # Registro de depuración
            self.logger.info(f"Processing email capture for input: {input_text}")
            
            # Extracción de email
            email_extraction_result = self.chatgpt.extract_email(input_text)
            
            if not email_extraction_result['success']:
                self.logger.warning("Email extraction failed")
                return {
                    'success': False,
                    'error': 'No valid email found in text'
                }

            email = email_extraction_result['email']
            
            # Obtener el último idioma detectado
            current_language = get_last_detected_language()
            
            # Procesamiento de idioma
            text_processing_result = self.chatgpt.process_text_input(
                input_text, 
                current_language
            )
            detected_language = text_processing_result.get('detected_language', 'en-US')
            
            # Actualizar idioma global
            update_last_detected_language(detected_language)
            
            # Verificar registro
            is_registered = RegistrationService.is_email_registered(email)
            
            # Preparar mensaje base
            base_message = "Thank you for your email. What is your name?"
            translated_message = self.chatgpt.translate_message(base_message, detected_language)
            
            # Preparar respuesta
            response = {
                'success': True,
                'email': email,
                'is_registered': is_registered,
                'detected_language': detected_language,
                'step': 'request_name',
                'message': translated_message,
                'next_action': 'provide_name'
            }

            # Información adicional si no está registrado
            if not is_registered:
                booking_base_message = "Please book a call to complete your registration"
                booking_message = self.chatgpt.translate_message(booking_base_message, detected_language)
                
                response.update({
                    'action_required': "book_call",
                    'booking_link': "https://calendly.com/your-booking-link",
                    'booking_message': booking_message
                })

            # Registro de éxito
            self.logger.info(f"Email capture successful for email: {email}")
            
            return response

        except Exception as e:
            # Manejo de errores inesperados
            error_message = f"Unexpected error in email capture: {str(e)}"
            self.logger.error(error_message, exc_info=True)
            
            try:
                # Obtener el último idioma detectado para traducir el error
                current_language = get_last_detected_language()
                
                # Intentar traducir mensaje de error
                translated_error = self.chatgpt.translate_message(
                    "An error occurred while processing your request.", 
                    current_language
                )
            except Exception:
                translated_error = "An unexpected error occurred"

            return {
                'success': False,
                'error': translated_error
            }

    def reset_last_detected_language(self, language='en-US'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        reset_last_detected_language()
        self.logger.info(f"Last detected language reset to: {language}")