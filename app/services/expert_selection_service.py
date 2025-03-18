from src.utils.chatgpt_helper import ChatGPTHelper

class ExpertSelectionService:
    def __init__(self, chatgpt=None):
        self.chatgpt = chatgpt or ChatGPTHelper()
        
        self.BASE_MESSAGES = {
            'expert_required': 'At least one expert must be selected',
            'no_data_found': 'No expert data found',
            'expert_selected': 'You have selected the expert(s):',
            'expert_not_found': 'No expert found with the name {name}',
            'processing_error': 'An error occurred while processing your request.',
            'thank_you': 'Thank you for your selection! We will process your request.'
        }

    def select_experts(self, data):
        """
        Seleccionar expertos
        
        :param data: Datos de la solicitud
        :return: Resultado de la selección
        """
        try:
            # Validar datos de entrada
            validation_result = self._validate_input(data)
            if not validation_result['success']:
                return validation_result

            # Buscar expertos
            found_experts = self._find_experts(
                data['selected_experts'], 
                data['all_experts_data']
            )

            # Procesar resultado de búsqueda
            if found_experts:
                return self._prepare_success_response(
                    found_experts, 
                    data.get('evaluation_questions', {}),
                    data.get('detected_language', 'en')
                )
            else:
                return self._prepare_not_found_response(
                    data['selected_experts'][0],
                    data.get('detected_language', 'en')
                )

        except Exception as e:
            return self._handle_error(e, data.get('detected_language', 'en'))

    def _validate_input(self, data):
        """
        Validar datos de entrada
        
        :param data: Datos de la solicitud
        :return: Resultado de validación
        """
        selected_experts = data.get('selected_experts')
        all_experts_data = data.get('all_experts_data')

        if not selected_experts:
            return {
                'success': False,
                'message': self.BASE_MESSAGES['expert_required']
            }

        if not all_experts_data or 'experts' not in all_experts_data:
            return {
                'success': False,
                'message': self.BASE_MESSAGES['no_data_found']
            }

        return {'success': True}

    def _find_experts(self, selected_experts, all_experts_data):
        """
        Encontrar expertos que coincidan con la selección
        
        :param selected_experts: Expertos seleccionados
        :param all_experts_data: Datos de todos los expertos
        :return: Lista de expertos encontrados
        """
        found_experts = []
        search_term = selected_experts[0].lower()
        name_parts = search_term.split()

        for category, category_data in all_experts_data['experts'].items():
            for expert in category_data.get('experts', []):
                expert_name_lower = expert['name'].lower()
                
                # Verificar si cualquier parte del nombre buscado coincide
                if any(part in expert_name_lower for part in name_parts):
                    found_experts.append({
                        'expert': expert,
                        'category': category
                    })

        return found_experts

    def _prepare_success_response(
        self, 
        found_experts, 
        evaluation_questions, 
        detected_language
    ):
        """
        Preparar respuesta de éxito
        
        :param found_experts: Expertos encontrados
        :param evaluation_questions: Preguntas de evaluación
        :param detected_language: Idioma detectado
        :return: Respuesta de éxito
        """
        # Preparar detalles de expertos
        expert_responses = []
        for found_expert in found_experts:
            expert = found_expert['expert']
            category = found_expert['category']
            
            expert_response = {
                'name': expert['name'],
                'current_role': expert['current_role'],
                'current_employer': expert['current_employer'],
                'experience': expert['experience'],
                'location': expert['location'],
                'category': category
            }
            expert_responses.append(expert_response)

        # Copiar preguntas de evaluación
        category_questions = evaluation_questions.copy()

        # Traducir mensajes
        selection_message = self.chatgpt.translate_message(
            self.BASE_MESSAGES['expert_selected'],
            detected_language
        )
        
        thank_you_message = self.chatgpt.translate_message(
            self.BASE_MESSAGES['thank_you'],
            detected_language
        )

        return {
            'success': True,
            'message': selection_message,
            'experts_found': len(expert_responses),
            'expert_details': expert_responses,
            'screening_questions': category_questions,
            'final_message': thank_you_message,
            'detected_language': detected_language
        }

    def _prepare_not_found_response(self, search_term, detected_language):
        """
        Preparar respuesta cuando no se encuentran expertos
        
        :param search_term: Término de búsqueda
        :param detected_language: Idioma detectado
        :return: Respuesta de no encontrado
        """
        not_found_message = self.chatgpt.translate_message(
            self.BASE_MESSAGES['expert_not_found'].format(name=search_term),
            detected_language
        )
        
        return {
            'success': False,
            'message': not_found_message
        }

    def _handle_error(self, error, detected_language):
        """
        Manejar errores generales
        
        :param error: Excepción ocurrida
        :param detected_language: Idioma detectado
        :return: Respuesta de error
        """
        print(f"Error in select experts: {str(error)}")
        
        error_message = self.chatgpt.translate_message(
            self.BASE_MESSAGES['processing_error'],
            detected_language
        )
        
        return {
            'success': False,
            'message': error_message,
            'error': str(error)
        }