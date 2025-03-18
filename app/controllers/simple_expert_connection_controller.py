from src.utils.chatgpt_helper import ChatGPTHelper

class SimpleExpertConnectionController:
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
        
        if 'text' not in data:
            return {
                'is_valid': False,
                'error': 'Text is required'
            }
        
        return {
            'is_valid': True,
            'text': data['text']
        }

    def process_simple_expert_connection(self, data):
        """
        Procesar conexión simple de experto
        
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
                validation_result['text'], 
                self.last_detected_language
            )
            detected_language = text_processing_result.get('detected_language', 'en')
            self.last_detected_language = detected_language

            # Extraer empresas del texto
            companies_response = self.chatgpt.process_company_response(
                validation_result['text']
            )
            
            # Generar respuesta
            result = self._generate_response(
                companies_response, 
                detected_language
            )
            
            # Añadir código de estado a la respuesta
            result['status_code'] = 200 if result.get('success', False) else 400
            
            return result

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'details': str(e),
                'status_code': 500
            }

    def _generate_response(self, companies_response, detected_language):
        """
        Generar respuesta basada en las empresas
        
        :param companies_response: Respuesta de procesamiento de empresas
        :param detected_language: Idioma detectado
        :return: Diccionario de respuesta
        """
        # Caso sin empresas específicas
        if companies_response == "no" or not isinstance(companies_response, dict):
            return {
                'success': True,
                'message': self.chatgpt.translate_message(
                    "No specific companies mentioned. We will provide suggestions based on sector and region.",
                    detected_language
                ),
                'preselected_companies': [],
                'detected_language': detected_language
            }

        # Obtener las empresas mencionadas
        preselected_companies = companies_response.get('companies', [])
        
        # Generar mensaje
        if preselected_companies:
            message = self.chatgpt.translate_message(
                f"We will include these companies in the main suggestions: {', '.join(preselected_companies)}",
                detected_language
            )
        else:
            message = self.chatgpt.translate_message(
                "No specific companies identified. We will provide suggestions based on sector and region.",
                detected_language
            )

        return {
            'success': True,
            'message': message,
            'preselected_companies': preselected_companies,
            'detected_language': detected_language
        }

    def reset_last_detected_language(self, language='en'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        self.last_detected_language = language