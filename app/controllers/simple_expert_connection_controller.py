from src.utils.chatgpt_helper import ChatGPTHelper
import re

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

    def _is_nonsense_text(self, text):
        """
        Detecta si el texto parece no tener sentido para búsqueda de empresas
        
        :param text: Texto a evaluar
        :return: True si parece ser texto sin sentido, False en caso contrario
        """
        # Quitar espacios extras
        text = text.strip().lower()
        
        # Texto muy corto (menor a 3 caracteres)
        if len(text) < 3:
            return True
            
        # Solo números
        if re.match(r'^[0-9]+$', text):
            return True
            
        # Palabras cortas sin contexto como "dogs", "cat", etc.
        if re.match(r'^[a-z]+$', text.lower()) and len(text) < 5:
            return True
            
        # Verificar patrones comunes de teclado
        keyboard_patterns = ['asdf', 'qwer', 'zxcv', '1234', 'hjkl', 'uiop']
        for pattern in keyboard_patterns:
            if pattern in text.lower():
                return True
            
        # Texto aleatorio (una sola palabra larga sin espacios)
        if len(text.split()) == 1 and len(text) > 8:
            # Verificar si tiene una distribución de caracteres poco natural
            # Caracteres raros o poco comunes en muchos idiomas
            rare_chars = len(re.findall(r'[qwxzjkvfy]', text.lower()))
            if rare_chars / len(text) > 0.3:  # Alta proporción de caracteres poco comunes
                return True
            
            # Patrones repetitivos
            if any(text.count(c) > len(text) * 0.4 for c in text):  # Un carácter repetido muchas veces
                return True
                
        return False

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
            
            # Verificar si el texto parece no tener sentido
            if self._is_nonsense_text(validation_result['text']):
                guidance_message = self.chatgpt.translate_message(
                    "Please enter specific company names you're interested in (for example: 'Google, Microsoft, Amazon') or type 'no' if you don't have specific companies in mind.",
                    detected_language
                )
                
                return {
                    'success': False,
                    'message': guidance_message,
                    'preselected_companies': [],
                    'detected_language': detected_language,
                    'status_code': 400
                }

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