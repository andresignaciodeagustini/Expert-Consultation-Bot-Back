from src.utils.chatgpt_helper import ChatGPTHelper
# Importar funciones de gestión de idioma global
from app.constants.language import get_last_detected_language, update_last_detected_language, reset_last_detected_language

class SectorExperienceController:
    def __init__(self):
        self.chatgpt = ChatGPTHelper()
        
        self.BASE_MESSAGES = {
            'sector_received': "Thank you.",
            'ask_specific_area': "Would you like to focus on a specific area within the {sector} sector",
            'ask_region': "In which region are you interested? (for example, North America, Europe, Asia, etc.)",
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
        
        if 'sector' not in data:
            return {
                'is_valid': False,
                'error': 'A sector specification is required'
            }
        
        return {
            'is_valid': True,
            'data': data
        }

    def process_sector_experience(self, data):
        try:
            # Validar entrada
            validation_result = self.validate_input(data)
            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'type': 'bot',
                    'isError': True
                }
            
            # Obtener el último idioma detectado globalmente
            current_language = get_last_detected_language()
            
            # Usar translate_sector en lugar de extract_sector
            sector_translation = self.chatgpt.translate_sector(data['sector'])
            
            # Manejar casos donde el sector no es válido
            if not sector_translation['is_valid']:
                return {
                    'success': False,
                    'error': sector_translation['available_sectors'],
                    'type': 'bot',
                    'isError': True
                }

            # Usar el sector traducido
            sector = sector_translation['translated_sector']
            displayed_sector = sector_translation['displayed_sector']
            
            # Generación de respuesta
            response = self._generate_response(displayed_sector, data, current_language)
            
            # Añadir campos adicionales para el frontend
            response['type'] = 'bot'
            response['companies'] = None
            response['isError'] = False
            
            return response

        except Exception as e:
        # Resto del método permanece igual...
            error_message = self.BASE_MESSAGES['processing_error']
            try:
                # Obtener el último idioma detectado para traducir el error
                current_language = get_last_detected_language()
                
                translated_error = self.chatgpt.translate_message(
                    error_message, 
                    current_language
                )
            except Exception:
                translated_error = error_message

            return {
                'success': False,
                'error': translated_error,
                'details': str(e),
                'type': 'bot',
                'isError': True
            }

    def _generate_response(self, sector, data, detected_language):
        """
        Generar respuesta basada en el sector y datos adicionales
        
        :param sector: Sector extraído
        :param data: Datos de la solicitud
        :param detected_language: Idioma detectado
        :return: Diccionario de respuesta
        """
        # Verificar si hay un área específica
        if 'specific_area' in data:
            # Si el área específica es "no" o está vacía
            if not data['specific_area'] or data['specific_area'].lower() == 'no':
                base_message = (
                    f"{self.BASE_MESSAGES['sector_received'].format(sector=sector)} "
                    f"{self.BASE_MESSAGES['ask_region']}"
                )
                next_step = 'region_inquiry'
            else:
                # Si hay un área específica definida
                base_message = (
                    f"We will include \"{data['specific_area']}\" in our search. "
                    f"{self.BASE_MESSAGES['ask_region']}"
                )
                next_step = 'region_inquiry'
        else:
            # Si no se ha proporcionado área específica
            base_message = (
                f"{self.BASE_MESSAGES['sector_received'].format(sector=sector)} "
                f"{self.BASE_MESSAGES['ask_specific_area'].format(sector=sector)}"
            )
            next_step = 'specific_area_inquiry'

        # Traducir mensaje
        response_message = self.chatgpt.translate_message(base_message, detected_language)

        # Procesar información adicional
        additional_messages = {}
        if 'additional_info' in data:
            confirmation_message = "Additional information has been registered successfully"
            additional_messages['confirmation'] = self.chatgpt.translate_message(
                confirmation_message,
                detected_language
            )

        # Construir respuesta
        response = {
            'success': True,
            'message': response_message,
            'has_additional_info': 'additional_info' in data and bool(data['additional_info']),
            'sector': sector,
            'detected_language': detected_language,
            'next_step': next_step,
            'specific_area': data.get('specific_area')
        }

        if additional_messages:
            response['additional_messages'] = additional_messages

        return response

    def reset_last_detected_language(self, language='en-US'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        print(f"\n=== Resetting Last Detected Language to: {language} ===")
        reset_last_detected_language()