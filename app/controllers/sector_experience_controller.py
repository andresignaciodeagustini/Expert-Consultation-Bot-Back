from src.utils.chatgpt_helper import ChatGPTHelper
# Importar funciones de gestión de idioma global
from app.constants.language import get_last_detected_language, update_last_detected_language, reset_last_detected_language

class SectorExperienceController:
    def __init__(self):
        self.chatgpt = ChatGPTHelper()
        
        self.BASE_MESSAGES = {
            'sector_received': "Thank you.",
            'ask_specific_area': "Would you like to focus on a specific area within the {sector} sector?",
            'ask_region': "In which region are you interested? (for example, North America, Europe, Asia, etc.)",
            'processing_error': "Error processing your request",
            'invalid_sector': "Please provide a valid sector or industry. For example: Technology, Healthcare, Finance."
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
        
        # Validar que el sector no sea solo números o símbolos
        sector_text = data['sector'].strip()
        if not sector_text:
            return {
                'is_valid': False,
                'error': 'Sector cannot be empty'
            }
        
        # Verificar si el texto contiene al menos una letra
        has_letter = any(char.isalpha() for char in sector_text)
        if not has_letter:
            return {
                'is_valid': False,
                'error': 'invalid_sector_format',
                'reason': 'no_letters'
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
                # Obtener el idioma actual para el mensaje de error
                current_language = get_last_detected_language()
                
                # Si es un error de formato del sector
                if validation_result.get('error') == 'invalid_sector_format':
                    # Traducir mensaje de error personalizado
                    translated_error = self.chatgpt.translate_message(
                        self.BASE_MESSAGES['invalid_sector'], 
                        current_language
                    )
                    
                    return {
                        'success': False,
                        'message': translated_error,
                        'error_type': 'invalid_sector_format',
                        'type': 'bot',
                        'isError': True,
                        'detected_language': current_language,
                        'step': 'select_sector',
                        'next_action': 'process_sector_selection'
                    }
                else:
                    return {
                        'success': False,
                        'error': validation_result['error'],
                        'type': 'bot',
                        'isError': True
                    }
            
            # Obtener el último idioma detectado globalmente
            current_language = get_last_detected_language()
            
            # Procesamiento de idioma para el sector
            if len(data['sector']) > 3:  # Solo procesar idioma si el sector tiene más de 3 caracteres
                text_processing_result = self.chatgpt.process_text_input(
                    data['sector'], 
                    current_language
                )
                detected_language = text_processing_result.get('detected_language', current_language)
                
                # Actualizar idioma global si cambia
                if detected_language != current_language:
                    update_last_detected_language(detected_language)
                    current_language = detected_language
            
            # Usar translate_sector en lugar de extract_sector
            sector_translation = self.chatgpt.translate_sector(data['sector'])
            
            # Manejar casos donde el sector no es válido
            if not sector_translation['is_valid']:
                # Traducir mensaje sobre sectores disponibles
                translated_error = self.chatgpt.translate_message(
                    f"Please select a valid sector: {sector_translation['available_sectors']}, etc.",
                    current_language
                )
                
                return {
                    'success': False,
                    'message': translated_error,
                    'error_type': 'invalid_sector',
                    'type': 'bot',
                    'isError': True,
                    'detected_language': current_language,
                    'step': 'select_sector',
                    'next_action': 'process_sector_selection'
                }

            # Usar el sector traducido
            sector = sector_translation['translated_sector']
            displayed_sector = sector_translation['displayed_sector']
            
            # Verificar si hay un área específica proporcionada
            if 'specific_area' in data and data['specific_area']:
                # Verificar si la respuesta es negativa en cualquier idioma
                is_negative = self.chatgpt.is_negative_response(data['specific_area'])
                
                # Si es una respuesta negativa, tratar como si no hubiera área específica
                if is_negative:
                    data['specific_area'] = 'no'
                else:
                    # Validar que el área específica esté relacionada con el sector
                    area_validation = self.chatgpt.validate_specific_area(data['specific_area'], sector)
                    
                    # Si el área específica no es válida para este sector
                    if not area_validation['is_valid']:
                        return {
                            'success': False,
                            'message': area_validation['message'],
                            'error_type': 'invalid_specific_area',
                            'type': 'bot',
                            'isError': True,
                            'detected_language': current_language,
                            'step': 'specific_area_inquiry',
                            'next_action': 'process_specific_area',
                            'sector': sector
                        }
                    
                    # Si es válida, actualizar data con el área estandarizada
                    data['specific_area'] = area_validation['specific_area']
                    data['displayed_area'] = area_validation['displayed_area']
            
            # Generación de respuesta
            response = self._generate_response(displayed_sector, data, current_language)
            
            # Añadir campos adicionales para el frontend
            response['type'] = 'bot'
            response['companies'] = None
            response['isError'] = False
            
            return response

        except Exception as e:
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
            # Detectar si es una respuesta negativa en cualquier idioma
            is_negative = self.chatgpt.is_negative_response(data['specific_area'])
            
            # Si el área específica es "no", "general", está vacía o es una respuesta negativa en cualquier idioma
            if not data['specific_area'] or data['specific_area'].lower() in ['no', 'general'] or is_negative:
                base_message = (
                    f"{self.BASE_MESSAGES['sector_received']} "
                    f"{self.BASE_MESSAGES['ask_region']}"
                )
                next_step = 'region_inquiry'
            else:
                # Si hay un área específica definida, usar el área mostrada si está disponible
                displayed_area = data.get('displayed_area', data['specific_area'])
                
                base_message = (
                    f"We will include \"{displayed_area}\" in our search. "
                    f"{self.BASE_MESSAGES['ask_region']}"
                )
                next_step = 'region_inquiry'
        else:
            # Si no se ha proporcionado área específica
            base_message = (
                f"{self.BASE_MESSAGES['sector_received']} "
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

        # Añadir el área mostrada si está disponible
        if 'displayed_area' in data:
            response['displayed_area'] = data['displayed_area']

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