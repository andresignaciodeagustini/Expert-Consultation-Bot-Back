from app.services.expert_selection_service import ExpertSelectionService
from src.utils.chatgpt_helper import ChatGPTHelper
# Importar funciones de gestión de idioma global
from app.constants.language import (
    get_last_detected_language, 
    update_last_detected_language, 
    reset_last_detected_language
)

class ExpertSelectionController:
    def __init__(self, expert_selection_service=None, chatgpt=None):
        self.expert_selection_service = (
            expert_selection_service or 
            ExpertSelectionService()
        )
        self.chatgpt = chatgpt or ChatGPTHelper()

        self.BASE_MESSAGES = {
            'no_data': "No data provided for expert selection.",
            'missing_fields': "Missing required fields for expert selection.",
            'invalid_experts_list': "Invalid experts list or structure.",
            'processing_error': "An error occurred while selecting experts."
        }

    def validate_input(self, data):
        """
        Validar datos de entrada para selección de expertos
        
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
        
        # Validaciones específicas para selección de expertos
        required_fields = [
            'selected_experts', 
            'all_experts_data', 
            'evaluation_questions'
        ]
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            print(f"Missing fields: {missing_fields}")
            return {
                'is_valid': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }
        
        # Validar estructura de all_experts_data
        experts_data = data.get('all_experts_data', {}).get('experts', {})
        required_expert_categories = ['main', 'client', 'supply_chain']
        
        for category in required_expert_categories:
            if category not in experts_data:
                print(f"Missing expert category: {category}")
                return {
                    'is_valid': False,
                    'error': f'Missing expert category: {category}'
                }
            
            # Validar que cada categoría tenga una lista de expertos
            if not isinstance(experts_data[category].get('experts', []), list):
                print(f"Invalid experts list for category: {category}")
                return {
                    'is_valid': False,
                    'error': f'Invalid experts list for category: {category}'
                }
        
        # Validar selected_experts
        if not isinstance(data['selected_experts'], list) or len(data['selected_experts']) == 0:
            print("Invalid selected experts")
            return {
                'is_valid': False,
                'error': 'Selected experts must be a non-empty list'
            }
        
        # Validar evaluation_questions
        if not isinstance(data['evaluation_questions'], dict):
            print("Invalid evaluation questions")
            return {
                'is_valid': False,
                'error': 'Evaluation questions must be a dictionary'
            }
        
        return {
            'is_valid': True,
            'data': data
        }

    def select_experts(self, data):
        """
        Seleccionar expertos
        
        :param data: Datos de la solicitud
        :return: Respuesta de selección
        """
        try:
            print("\n=== Processing Expert Selection ===")
            
            # Validar entrada
            validation_result = self.validate_input(data)
            if not validation_result['is_valid']:
                # Procesar idioma para el mensaje de error
                detected_language = self._process_language(data)
                error_message = self.chatgpt.translate_message(
                    self.BASE_MESSAGES.get(
                        'missing_fields' if 'Missing required fields' in validation_result['error'] 
                        else 'invalid_experts_list' if 'Invalid experts list' in validation_result['error']
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

            # Registro de datos validados
            print("Validated Data:")
            print(f"Selected Experts: {data['selected_experts']}")
            print(f"Experts Categories: {list(data['all_experts_data']['experts'].keys())}")
            print(f"Evaluation Questions: {list(data['evaluation_questions'].keys())}")

            # Seleccionar expertos
            result = self.expert_selection_service.select_experts(data)
            
            # Registro de resultado
            print("\n=== Expert Selection Result ===")
            print(f"Success: {result.get('success', False)}")
            print(f"Expert Details: {result.get('expert_details', 'No details')}")
            
            # Añadir código de estado a la respuesta
            result['status_code'] = 200 if result.get('success', False) else 404
            result['detected_language'] = detected_language
            
            return result

        except Exception as e:
            print("\n=== Error in Expert Selection ===")
            print(f"Error Type: {type(e)}")
            print(f"Error Details: {str(e)}")
            
            # Procesar idioma para el mensaje de error
            current_language = get_last_detected_language()
            error_message = self.chatgpt.translate_message(
                self.BASE_MESSAGES['processing_error'], 
                current_language
            )
            
            return {
                'success': False,
                'message': error_message,
                'error': str(e),
                'status_code': 500,
                'detected_language': current_language
            }

    def _process_language(self, data):
        """
        Procesar y detectar idioma
        
        :param data: Datos de la solicitud
        :return: Idioma detectado
        """
        print("\n=== Language Processing ===")
        current_language = get_last_detected_language()
        print(f"Current detected language: {current_language}")
        
        # Intentar obtener texto para detección de idioma
        text_to_detect = ' '.join([
            str(data.get('language', '')),
            ' '.join(data.get('selected_experts', [])),
            ' '.join(data.get('evaluation_questions', {}).keys())
        ])
        
        text_processing_result = self.chatgpt.process_text_input(
            text_to_detect if text_to_detect.strip() else "test", 
            current_language
        )
        detected_language = text_processing_result.get('detected_language', 'en')
        
        print(f"Detected language: {detected_language}")
        
        # Actualizar idioma si es diferente de inglés
        if detected_language != 'en':
            update_last_detected_language(detected_language)
        
        return detected_language

    def reset_last_detected_language(self, language='en'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        print(f"\n=== Resetting Last Detected Language to: {language} ===")
        reset_last_detected_language()