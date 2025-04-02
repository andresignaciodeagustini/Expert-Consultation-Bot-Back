from app.services.evaluation_service import EvaluationService
import re
from src.utils.chatgpt_helper import ChatGPTHelper  # Asegúrate de importar ChatGPTHelper

class EvaluationController:
    def __init__(self, evaluation_service=None, chatgpt=None):
        """
        Inicializar controlador de evaluación
        
        :param evaluation_service: Servicio de evaluación
        :param chatgpt: Servicio de ChatGPT para procesamiento de texto
        """
        self.evaluation_service = evaluation_service or EvaluationService()
        self.chatgpt = chatgpt or ChatGPTHelper()
        self.last_detected_language = 'en'
        
        # Añadir mensajes base como en los otros controladores
        self.BASE_MESSAGES = {
            'nonsense_input': "Please provide valid evaluation data. The information you've entered doesn't seem to make sense.",
            'processing_error': "An error occurred while processing your evaluation data."
        }

    def validate_input(self, data):
        """
        Validar campos de entrada
        
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
        
        # Validar campos requeridos
        required_fields = ['project_id', 'evaluation_data']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            print(f"Missing fields: {missing_fields}")
            return {
                'is_valid': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }
        
        # Verificar si alguno de los campos contiene texto sin sentido
        if isinstance(data.get('evaluation_data'), dict):
            for field, value in data['evaluation_data'].items():
                if isinstance(value, str) and self._is_nonsense_text(value):
                    print(f"Nonsense text detected in field '{field}': {value}")
                    return {
                        'is_valid': False,
                        'error': 'nonsense_input',
                        'data': data,
                        'field': field
                    }
        
        return {
            'is_valid': True,
            'project_id': data['project_id'],
            'evaluation_data': data['evaluation_data']
        }
        
    def _is_nonsense_text(self, text):
        """
        Detecta si el texto parece no tener sentido
        
        :param text: Texto a evaluar
        :return: True si parece ser texto sin sentido, False en caso contrario
        """
        if not text:
            return False
            
        # Quitar espacios extras
        text = text.strip().lower()
        
        # Texto muy corto (menor a 3 caracteres)
        if len(text) < 3 and not text.isdigit():  # Permitir números cortos
            return True
            
        # Solo números muy largos (podrían ser IDs válidos, pero improbable para texto)
        if re.match(r'^[0-9]+$', text) and len(text) > 10:
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
        if len(text.split()) == 1 and len(text) > 12:
            # Verificar si tiene una distribución de caracteres poco natural
            # Caracteres raros o poco comunes en muchos idiomas
            rare_chars = len(re.findall(r'[qwxzjkvfy]', text.lower()))
            if rare_chars / len(text) > 0.3:  # Alta proporción de caracteres poco comunes
                return True
            
            # Patrones repetitivos
            if any(text.count(c) > len(text) * 0.4 for c in text):  # Un carácter repetido muchas veces
                return True
                
        return False

    def save_evaluation(self, data):
        """
        Guardar evaluación
        
        :param data: Datos de la solicitud
        :return: Resultado de la operación
        """
        try:
            print("\n=== Save Evaluation ===")
            
            # Validar entrada
            validation_result = self.validate_input(data)
            if not validation_result['is_valid']:
                print(f"Validation failed: {validation_result['error']}")
                
                # Verificar si es por texto sin sentido
                if validation_result.get('error') == 'nonsense_input':
                    # Procesar idioma para el mensaje de error
                    detected_language = self._process_language(validation_result['data'])
                    
                    # Mensaje guía para el usuario
                    guidance_message = self.chatgpt.translate_message(
                        self.BASE_MESSAGES['nonsense_input'], 
                        detected_language
                    )
                    
                    return {
                        'success': False,
                        'message': guidance_message,
                        'detected_language': detected_language,
                        'field': validation_result.get('field'),
                        'status_code': 400
                    }
                
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'status_code': 400
                }

            # Extraer datos validados
            project_id = validation_result['project_id']
            evaluation_data = validation_result['evaluation_data']

            print(f"Project ID: {project_id}")
            print(f"Evaluation Data: {evaluation_data}")

            # Guardar evaluación
            print("Calling evaluation service to save evaluation")
            result = self.evaluation_service.save_evaluation(project_id, evaluation_data)
            
            print(f"Evaluation Service Result: {result}")
            
            # Añadir código de estado a la respuesta
            result['status_code'] = 200 if result.get('success', False) else 500
            
            print(f"Final Result: {result}")
            
            return result

        except Exception as e:
            print("\n=== Error in Save Evaluation ===")
            print(f"Error Type: {type(e)}")
            print(f"Error Details: {str(e)}")
            
            # Usar el mensaje base y traducirlo si es necesario
            current_language = self.last_detected_language
            error_message = self.chatgpt.translate_message(
                self.BASE_MESSAGES['processing_error'], 
                current_language
            )
            
            return {
                'success': False,
                'message': error_message,
                'error': str(e),
                'details': str(e),
                'error_type': str(type(e)),
                'detected_language': current_language,
                'status_code': 500
            }

    def reset_last_detected_language(self, language='en'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        print(f"\n=== Resetting Last Detected Language to: {language} ===")
        self.last_detected_language = language

    def _process_language(self, data):
        """
        Procesar y detectar idioma de manera mejorada
        
        :param data: Datos de la solicitud
        :return: Idioma detectado
        """
        print("\n=== Language Processing ===")
        current_language = self.last_detected_language
        print(f"Current detected language: {current_language}")
        
        try:
            # Priorizar el idioma si está explícitamente proporcionado
            if isinstance(data, dict):
                if 'detected_language' in data:
                    detected_language = data['detected_language']
                    print(f"Language from data: {detected_language}")
                    self.last_detected_language = detected_language
                    return detected_language
                
                # También verificar si hay un idioma en 'language'
                if 'language' in data:
                    detected_language = data['language']
                    print(f"Language from data 'language' field: {detected_language}")
                    self.last_detected_language = detected_language
                    return detected_language
                
                # Intentar detectar del campo evaluation_data si existe
                if 'evaluation_data' in data and isinstance(data['evaluation_data'], dict):
                    # Buscar el primer valor de texto
                    for field, value in data['evaluation_data'].items():
                        if isinstance(value, str) and len(value) > 10:  # Solo textos suficientemente largos
                            print(f"Attempting to detect language from field '{field}'")
                            text_processing_result = self.chatgpt.process_text_input(
                                value, 
                                current_language
                            )
                            detected_language = text_processing_result.get('detected_language', current_language)
                            
                            print(f"Detected language from field '{field}': {detected_language}")
                            self.last_detected_language = detected_language
                            return detected_language
            
            # Usar el último idioma detectado o el predeterminado
            return current_language
        
        except Exception as e:
            print(f"Error in language detection: {e}")
            return current_language