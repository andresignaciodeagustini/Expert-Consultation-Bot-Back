from app.services.evaluation_service import EvaluationService

class EvaluationController:
    def __init__(self, evaluation_service=None):
        """
        Inicializar controlador de evaluación
        
        :param evaluation_service: Servicio de evaluación
        """
        self.evaluation_service = evaluation_service or EvaluationService()
        self.last_detected_language = 'en'

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
        
        required_fields = ['project_id', 'evaluation_data']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            print(f"Missing fields: {missing_fields}")
            return {
                'is_valid': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }
        
        return {
            'is_valid': True,
            'project_id': data['project_id'],
            'evaluation_data': data['evaluation_data']
        }

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
            
            error_message = 'An error occurred while saving the evaluation'
            
            return {
                'success': False,
                'error': error_message,
                'details': str(e),
                'error_type': str(type(e)),
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
        Procesar y detectar idioma (método opcional)
        
        :param data: Datos de la solicitud
        :return: Idioma detectado
        """
        print("\n=== Language Processing ===")
        
        # Intentar detectar idioma de los datos de evaluación
        try:
            # Aquí podrías implementar una lógica de detección de idioma
            # Por ejemplo, usando el primer campo de texto de evaluation_data
            if isinstance(data.get('evaluation_data'), dict):
                text_sample = next((v for v in data['evaluation_data'].values() if isinstance(v, str)), None)
                
                if text_sample:
                    text_processing_result = self.chatgpt.process_text_input(
                        text_sample, 
                        self.last_detected_language
                    )
                    detected_language = text_processing_result.get('detected_language', 'en')
                    
                    print(f"Detected language from evaluation data: {detected_language}")
                    self.last_detected_language = detected_language
                    return detected_language
        except Exception as e:
            print(f"Error in language detection: {str(e)}")
        
        print(f"Defaulting to: {self.last_detected_language}")
        return self.last_detected_language