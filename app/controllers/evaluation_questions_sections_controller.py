from src.utils.chatgpt_helper import ChatGPTHelper
# Importar funciones de gestión de idioma global
from app.constants.language import (
    get_last_detected_language, 
    update_last_detected_language, 
    reset_last_detected_language
)

class EvaluationQuestionsSectionsController:
    def __init__(self, chatgpt=None):
        self.chatgpt = chatgpt or ChatGPTHelper()
        
        self.CATEGORY_MESSAGES = {
            'main': "Please provide screening questions for main companies in the sector.",
            'client': "Please provide screening questions for client companies.",
            'supply_chain': "Please provide screening questions for supply chain companies."
        }
        
        self.COMPLETION_MESSAGE = "All screening questions have been successfully gathered."

    def _translate_message(self, message, detected_language):
        """
        Método genérico para traducir mensajes
        """
        try:
            return self.chatgpt.translate_message(message, detected_language)
        except Exception as e:
            print(f"Translation error: {e}")
            return message

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
        
        required_fields = ['sector', 'region', 'selected_categories']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            print(f"Missing required fields: {', '.join(missing_fields)}")
            return {
                'is_valid': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }
        
        print(f"Received data: {data}")
        return {
            'is_valid': True,
            'data': data
        }

    def process_evaluation_questions_sections(self, data):
        """
        Procesar secciones de preguntas de evaluación
        
        :param data: Datos de la solicitud
        :return: Respuesta procesada
        """
        try:
            print("\n=== Processing Evaluation Questions Sections ===")
            
            # Importante: Verificar si hay un idioma explícito en los datos
            if data and isinstance(data, dict):
                if 'language' in data:
                    explicit_language = data['language']
                    print(f"Using explicit language from data: {explicit_language}")
                    update_last_detected_language(explicit_language)
                elif 'detected_language' in data:
                    explicit_language = data['detected_language']
                    print(f"Using detected_language from data: {explicit_language}")
                    update_last_detected_language(explicit_language)
                # Verificar en filtersApplied dentro de phase3_data
                elif 'phase3_data' in data and isinstance(data['phase3_data'], dict):
                    filters = data['phase3_data'].get('filtersApplied', {})
                    if filters and isinstance(filters, dict) and 'detected_language' in filters:
                        explicit_language = filters['detected_language']
                        print(f"Using language from phase3_data.filtersApplied: {explicit_language}")
                        update_last_detected_language(explicit_language)
            
            # Validar entrada
            validation_result = self.validate_input(data)
            if not validation_result['is_valid']:
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'status_code': 400
                }
            
            # Procesar idioma usando el método mejorado
            detected_language = self._process_language(validation_result['data'])
            print(f"Detected Language: {detected_language}")
            
            # IMPORTANTE: Asegurarse de que el idioma detectado se actualice correctamente
            update_last_detected_language(detected_language)
            
            # Procesar preguntas
            response = self._process_questions(validation_result['data'], detected_language)
            
            # Añadir código de estado a la respuesta
            response['status_code'] = 200 if response.get('success', False) else 400
            
            print("\n=== Final Response ===")
            print(f"Response: {response}")
            
            return response

        except Exception as e:
            print(f"\n=== Error in process_evaluation_questions_sections ===")
            print(f"Error details: {str(e)}")
            
            error_response = self._handle_error(e, get_last_detected_language())
            error_response['status_code'] = 500
            return error_response

    def _process_language(self, data):
        """
        Procesar y detectar idioma con método mejorado
        
        :param data: Datos de la solicitud
        :return: Idioma detectado
        """
        print("\n=== Language Processing ===")
        current_language = get_last_detected_language()
        print(f"Current detected language: {current_language}")
        
        try:
            # Priorizar el idioma si está explícitamente proporcionado
            if 'detected_language' in data:
                detected_language = data['detected_language']
                print(f"Language from data: {detected_language}")
                update_last_detected_language(detected_language)
                return detected_language
            
            # También verificar si hay un idioma en 'language'
            if 'language' in data:
                detected_language = data['language']
                print(f"Language from data 'language' field: {detected_language}")
                update_last_detected_language(detected_language)
                return detected_language
            
            # Si hay una respuesta, procesar su idioma
            if 'answer' in data:
                # Para respuestas normales, usar la detección
                text_processing_result = self.chatgpt.process_text_input(
                    data['answer'], 
                    current_language
                )
                detected_language = text_processing_result.get('detected_language', current_language)
                
                print(f"Input answer: {data['answer']}")
                print(f"Detected language: {detected_language}")
                
                # CLAVE: Mantener el idioma original de la conversación
                if detected_language != current_language:
                    print(f"Language detection attempted to change from {current_language} to {detected_language}")
                    detected_language = current_language
                
                # Actualizar el último idioma detectado
                update_last_detected_language(detected_language)
                
                return detected_language
            
            # Usar el último idioma detectado o el predeterminado
            return current_language
        
        except Exception as e:
            print(f"Error in language detection: {e}")
            return current_language

    def _process_questions(self, data, detected_language):
        """
        Procesar preguntas de evaluación
        
        :param data: Datos de la solicitud
        :param detected_language: Idioma detectado
        :return: Respuesta procesada
        """
        print("\n=== Processing Questions ===")
        current_questions = data.get('current_questions', {})
        selected_categories = data.get('selected_categories', {})
        current_category = data.get('current_category')
        answer = data.get('answer')
        client_perspective = data.get('clientPerspective', False)
        supply_chain_perspective = data.get('supplyChainPerspective', False)

        print(f"Current category: {current_category}")
        print(f"Answer received: {answer}")
        print(f"Client perspective: {client_perspective}")
        print(f"Supply chain perspective: {supply_chain_perspective}")

        # Guardar respuesta si existe
        if current_category and answer:
            print(f"Saving answer for category: {current_category}")
            current_questions[current_category] = answer

        # Determinar categorías pendientes
        pending_categories = self._determine_pending_categories(
            selected_categories, 
            current_questions, 
            client_perspective, 
            supply_chain_perspective
        )
        print(f"Pending categories: {pending_categories}")

        # Generar respuesta
        if pending_categories:
            return self._generate_pending_response(
                pending_categories, 
                current_questions, 
                detected_language
            )
        else:
            return self._generate_completion_response(
                current_questions, 
                detected_language
            )

    def _determine_pending_categories(
        self, 
        selected_categories, 
        current_questions, 
        client_perspective, 
        supply_chain_perspective
    ):
        """
        Determinar categorías pendientes
        
        :param selected_categories: Categorías seleccionadas
        :param current_questions: Preguntas actuales
        :param client_perspective: Perspectiva de cliente
        :param supply_chain_perspective: Perspectiva de cadena de suministro
        :return: Lista de categorías pendientes
        """
        pending_categories = []
        
        if selected_categories.get('main', False) and 'main' not in current_questions:
            pending_categories.append('main')
        
        if (selected_categories.get('client', False) and 
            'client' not in current_questions and 
            client_perspective):
            pending_categories.append('client')
        
        if (selected_categories.get('supply_chain', False) and 
            'supply_chain' not in current_questions and 
            supply_chain_perspective):
            pending_categories.append('supply_chain')
        
        return pending_categories

    def _generate_pending_response(
        self, 
        pending_categories, 
        current_questions, 
        detected_language
    ):
        """
        Generar respuesta para categorías pendientes
        
        :param pending_categories: Categorías pendientes
        :param current_questions: Preguntas actuales
        :param detected_language: Idioma detectado
        :return: Respuesta de categorías pendientes
        """
        print("\n=== Generating Pending Response ===")
        next_category = pending_categories[0]
        message = self.CATEGORY_MESSAGES.get(next_category)
        translated_message = self._translate_message(message, detected_language)
        
        print(f"Next category: {next_category}")
        print(f"Original message: {message}")
        print(f"Translated message: {translated_message}")
        
        return {
            'success': True,
            'status': 'pending',
            'message': translated_message,
            'current_category': next_category,
            'remaining_categories': pending_categories[1:],
            'completed_categories': list(current_questions.keys()),
            'current_questions': current_questions,
            'detected_language': detected_language
        }

    def _generate_completion_response(self, current_questions, detected_language):
        """
        Generar respuesta de finalización
        
        :param current_questions: Preguntas actuales
        :param detected_language: Idioma detectado
        :return: Respuesta de finalización
        """
        print("\n=== Generating Completion Response ===")
        translated_message = self._translate_message(
            self.COMPLETION_MESSAGE, 
            detected_language
        )
        
        print(f"Original message: {self.COMPLETION_MESSAGE}")
        print(f"Translated message: {translated_message}")
        
        return {
            'success': True,
            'status': 'completed',
            'message': translated_message,
            'screening_questions': current_questions,
            'detected_language': detected_language
        }

    def _handle_error(self, error, detected_language):
        """
        Manejar errores generales
        
        :param error: Excepción ocurrida
        :param detected_language: Idioma detectado
        :return: Respuesta de error
        """
        print(f"\n=== Error Handling ===")
        error_message = "An error occurred while processing your request."
        translated_error = self._translate_message(error_message, detected_language)
        
        print(f"Error: {str(error)}")
        print(f"Translated error message: {translated_error}")
        
        return {
            'success': False,
            'message': translated_error,
            'error': str(error),
            'detected_language': detected_language
        }

    def reset_language(self, language='en'):
        """
        Resetear el idioma detectado
        
        :param language: Idioma por defecto
        """
        print(f"\n=== Resetting Language to: {language} ===")
        reset_last_detected_language(language)