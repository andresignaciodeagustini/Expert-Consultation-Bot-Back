from app.services.industry_experts_service import IndustryExpertsService
from src.utils.chatgpt_helper import ChatGPTHelper

class IndustryExpertsController:
    def __init__(self, industry_experts_service=None, chatgpt=None):
        self.industry_experts_service = (
            industry_experts_service or 
            IndustryExpertsService()
        )
        self.chatgpt = chatgpt or ChatGPTHelper()
        self.last_detected_language = 'en'

        self.BASE_MESSAGES = {
            'no_data': "No data provided for industry experts search.",
            'missing_fields': "Missing required fields for industry experts search.",
            'processing_error': "An error occurred while searching for industry experts."
        }

    def validate_input(self, data):
        """
        Validar datos de entrada
        
        :param data: Datos de la solicitud
        :return: Resultado de validación
        """
        print("\n=== Input Validation ===")
        if not data:
            print("No data provided")
            return {
                'is_valid': False,
                'error': 'No data provided'
            }
        
        print(f"Received data: {data}")
        
        # Añade aquí validaciones específicas según tus requisitos
        required_fields = ['sector', 'region']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            print(f"Missing fields: {missing_fields}")
            return {
                'is_valid': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }
        
        return {
            'is_valid': True,
            'data': data
        }

    def get_industry_experts(self, data):
        """
        Obtener expertos de la industria
        
        :param data: Datos de la solicitud
        :return: Respuesta de expertos
        """
        try:
            print("\n=== Processing Industry Experts Search ===")
            
            # Validar entrada
            validation_result = self.validate_input(data)
            if not validation_result['is_valid']:
                # Procesar idioma para el mensaje de error
                detected_language = self._process_language(data)
                error_message = self.chatgpt.translate_message(
                    self.BASE_MESSAGES.get(
                        'missing_fields' if 'Missing required fields' in validation_result['error'] 
                        else 'no_data'
                    ), 
                    detected_language
                )
                
                print(f"Validation failed: {validation_result['error']}")
                return {
                    'success': False,
                    'error': error_message,
                    'status_code': 400,
                    'detected_language': detected_language
                }
            
            # Procesar idioma
            detected_language = self._process_language(data)
            data['detected_language'] = detected_language

            # Obtener expertos
            result = self.industry_experts_service.get_industry_experts(data)
            
            # Añadir código de estado a la respuesta
            result['status_code'] = 200 if result.get('success', False) else 400
            result['detected_language'] = detected_language
            
            return result

        except Exception as e:
            print("\n=== Error in Get Industry Experts ===")
            print(f"Error Type: {type(e)}")
            print(f"Error Details: {str(e)}")
            
            # Procesar idioma para el mensaje de error
            detected_language = self._process_language(data)
            error_message = self.chatgpt.translate_message(
                self.BASE_MESSAGES['processing_error'], 
                detected_language
            )
            
            return {
                'success': False,
                'message': error_message,
                'error': str(e),
                'status_code': 500,
                'detected_language': detected_language
            }

    def _process_language(self, data):
        """
        Procesar y detectar idioma
        
        :param data: Datos de la solicitud
        :return: Idioma detectado
        """
        print("\n=== Language Processing ===")
        print(f"Current last_detected_language: {self.last_detected_language}")
        
        # Intentar obtener texto para detección de idioma
        text_to_detect = (
            data.get('sector', '') + ' ' + 
            data.get('region', '') + ' ' + 
            data.get('language', '')
        )
        
        text_processing_result = self.chatgpt.process_text_input(
            text_to_detect if text_to_detect.strip() else "test", 
            self.last_detected_language
        )
        detected_language = text_processing_result.get('detected_language', 'en')
        
        print(f"Detected language: {detected_language}")
        
        self.last_detected_language = detected_language
        return detected_language

    def reset_last_detected_language(self, language='en'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        print(f"\n=== Resetting Last Detected Language to: {language} ===")
        self.last_detected_language = language