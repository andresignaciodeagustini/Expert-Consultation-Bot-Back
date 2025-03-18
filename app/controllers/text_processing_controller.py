import logging
from src.utils.chatgpt_helper import ChatGPTHelper
# Importar funciones de gestión de idioma global
from app.constants.language import get_last_detected_language, update_last_detected_language, reset_last_detected_language

class TextProcessingController:
    def __init__(self):
        self.chatgpt = ChatGPTHelper()
        self.logger = logging.getLogger(__name__)
        
        self.BASE_MESSAGES = {
            'region_received': "Thank you for specifying the region.",
            'ask_companies': "Are there specific companies where you would like experts to have experience?",
            'processing_error': "Error processing your request"
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
                'error': 'Text is required'
            }
        
        return {
            'is_valid': True,
            'text': data['text']
        }

    def process_text(self, data):
        """
        Procesar texto para extracción de región
        
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
                    'error': validation_result['error'],
                    'status_code': 400
                }
            
            input_text = validation_result['text']
            
            # Obtener el último idioma detectado globalmente
            current_language = get_last_detected_language()
            
            # Detección multilingüe de región
            region_detection = self.chatgpt.detect_multilingual_region(
                input_text, 
                current_language
            )
            
            # Verificar si la detección de región fue exitosa
            if not region_detection.get('success', False):
                self.logger.warning("Multilingual region detection failed")
                
                # Usar detección de idioma de respaldo
                text_processing_result = self.chatgpt.process_text_input(
                    input_text, 
                    current_language
                )
                
                detected_language = text_processing_result.get('detected_language', 'en-US')
            else:
                # Usar el idioma detectado por la detección multilingüe
                detected_language = region_detection.get('detected_language', 'en-US')
            
            # Actualizar idioma globalmente
            update_last_detected_language(detected_language)
            
            # Registro de idioma detectado
            self.logger.info(f"Detected language: {detected_language}")
            
            # Extracción de región
            if region_detection.get('success', False):
                # Si la detección multilingüe fue exitosa, usar su región
                region = {
                    'success': True,
                    'region': region_detection['region'],
                    'original_location': input_text
                }
            else:
                # De lo contrario, intentar extraer región con el método existente
                region = self.chatgpt.extract_region(input_text)
            
            # Verificar si se pudo extraer la región
            if not region or not region.get('success', False):
                self.logger.warning("Region extraction failed")
                return {
                    'success': False,
                    'error': 'Could not identify a valid region from the provided text',
                    'status_code': 400,
                    'detected_language': detected_language
                }

            # Preparar mensajes base
            base_message = (
                f"{self.BASE_MESSAGES['region_received']} "
                f"{self.BASE_MESSAGES['ask_companies']}"
            )
            
            # Traducir mensaje
            next_question = self.chatgpt.translate_message(base_message, detected_language)
            
            # Preparar respuesta
            response = {
                'success': True,
                'processed_region': region,
                'next_question': next_question,
                'detected_language': detected_language,
                'status_code': 200
            }

            # Registro de éxito
            self.logger.info(f"Text processing successful for region: {region}")
            
            return response

        except Exception as e:
            # Manejo de errores inesperados
            error_message = f"Unexpected error in text processing: {str(e)}"
            self.logger.error(error_message, exc_info=True)
            
            try:
                # Obtener el último idioma detectado globalmente para traducir el error
                current_language = get_last_detected_language()
                
                # Intentar traducir mensaje de error
                translated_error = self.chatgpt.translate_message(
                    self.BASE_MESSAGES['processing_error'], 
                    current_language
                )
            except Exception:
                translated_error = "An unexpected error occurred"
                current_language = 'en-US'

            return {
                'success': False,
                'error': translated_error,
                'details': str(e),
                'detected_language': current_language,
                'status_code': 500
            }

    def reset_last_detected_language(self, language='en-US'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        reset_last_detected_language()
        self.logger.info(f"Last detected language reset to: {language}")