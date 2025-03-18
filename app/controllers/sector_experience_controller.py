from src.utils.chatgpt_helper import ChatGPTHelper

class SectorExperienceController:
    def __init__(self):
        self.chatgpt = ChatGPTHelper()
        self.last_detected_language = 'en'
        
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
        """
        Procesar la experiencia en un sector
        
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
            
            # Procesamiento de idioma
            text_processing_result = self.chatgpt.process_text_input(
                data['sector'], 
                self.last_detected_language
            )
            detected_language = text_processing_result.get('detected_language', 'en')
            
            # Actualizar idioma
            self.last_detected_language = detected_language
            
            # Extracción de sector
            sector = self.chatgpt.extract_sector(data['sector'])
            
            if not sector:
                error_message = 'Could not identify a valid sector from the provided text'
                translated_error = self.chatgpt.translate_message(error_message, detected_language)
                return {
                    'success': False,
                    'error': translated_error,
                    'status_code': 400
                }

            # Generación de respuesta
            response = self._generate_response(sector, data, detected_language)
            
            # Añadir código de estado a la respuesta
            response['status_code'] = 200
            
            return response

        except Exception as e:
            error_message = self.BASE_MESSAGES['processing_error']
            try:
                translated_error = self.chatgpt.translate_message(
                    error_message, 
                    self.last_detected_language
                )
            except Exception:
                translated_error = error_message

            return {
                'success': False,
                'error': translated_error,
                'details': str(e),
                'status_code': 500
            }

    def _generate_response(self, sector, data, detected_language):
        """
        Generar respuesta basada en el sector y datos adicionales
        
        :param sector: Sector extraído
        :param data: Datos de la solicitud
        :param detected_language: Idioma detectado
        :return: Diccionario de respuesta
        """
        # Determinar el siguiente paso
        if 'specific_area' not in data:
            base_message = (
                f"{self.BASE_MESSAGES['sector_received'].format(sector=sector)} "
                f"{self.BASE_MESSAGES['ask_specific_area'].format(sector=sector)}"
            )
            next_step = 'specific_area_inquiry'
        else:
            base_message = (
                f"{self.BASE_MESSAGES['sector_received'].format(sector=sector)} "
                f"{self.BASE_MESSAGES['ask_region']}"
            )
            next_step = 'region_inquiry'

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

    def reset_last_detected_language(self, language='en'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        self.last_detected_language = language