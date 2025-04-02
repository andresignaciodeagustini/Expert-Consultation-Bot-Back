from src.utils.chatgpt_helper import ChatGPTHelper

class ExpertSelectionService:
    def __init__(self, chatgpt=None):
        self.chatgpt = chatgpt or ChatGPTHelper()
        
        self.BASE_MESSAGES = {
            'expert_required': 'At least one expert must be selected',
            'no_data_found': 'No expert data found',
            'expert_selected': 'You have selected the expert(s):',
            'expert_not_found': 'The expert name you provided does not match any expert in the list. Please choose an expert by typing their name exactly as it is shown in the list. For example: "{example_expert}". Which expert would you like to choose?',
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
            print("\n=== Processing Expert Selection ===")
            print(f"Input data: {data}")
            
            # Validar datos de entrada
            validation_result = self._validate_input(data)
            if not validation_result['success']:
                print(f"Validation failed: {validation_result}")
                return validation_result

            # Buscar expertos con coincidencia exacta primero
            found_experts = self._find_experts_exact_match(
                data['selected_experts'][0], 
                data['all_experts_data']
            )
            
            # Si no hay coincidencia exacta, buscar coincidencias parciales
            if not found_experts:
                print("No exact match found, trying partial match")
                found_experts = self._find_experts_partial_match(
                    data['selected_experts'][0], 
                    data['all_experts_data']
                )

            # Procesar resultado de búsqueda
            if found_experts:
                print(f"Found {len(found_experts)} experts matching the criteria")
                return self._prepare_success_response(
                    found_experts, 
                    data.get('evaluation_questions', {}),
                    data.get('detected_language', 'en')
                )
            else:
                print("No experts found matching the criteria")
                # Obtener un ejemplo de experto para mostrar en el mensaje de error
                example_expert = self._get_example_expert(data['all_experts_data'])
                
                return self._prepare_not_found_response(
                    data['selected_experts'][0],
                    data.get('detected_language', 'en'),
                    example_expert
                )

        except Exception as e:
            print(f"Error in select_experts: {str(e)}")
            return self._handle_error(e, data.get('detected_language', 'en'))

    def _validate_input(self, data):
        """
        Validar datos de entrada
        
        :param data: Datos de la solicitud
        :return: Resultado de validación
        """
        print("\n=== Validating Input ===")
        selected_experts = data.get('selected_experts')
        all_experts_data = data.get('all_experts_data')

        if not selected_experts:
            print("No experts selected")
            return {
                'success': False,
                'message': self.BASE_MESSAGES['expert_required'],
                'status_code': 400
            }

        if not all_experts_data or 'experts' not in all_experts_data:
            print("No expert data found")
            return {
                'success': False,
                'message': self.BASE_MESSAGES['no_data_found'],
                'status_code': 400
            }

        print("Input validation passed")
        return {'success': True}

    def _find_experts_exact_match(self, expert_name, all_experts_data):
        """
        Encontrar expertos con coincidencia exacta
        
        :param expert_name: Nombre del experto buscado
        :param all_experts_data: Datos de todos los expertos
        :return: Lista de expertos encontrados
        """
        print(f"\n=== Finding Experts (Exact Match) for: {expert_name} ===")
        found_experts = []
        search_term = expert_name.lower().strip()

        for category, category_data in all_experts_data['experts'].items():
            for expert in category_data.get('experts', []):
                expert_name_lower = expert.get('name', '').lower().strip()
                
                # Coincidencia exacta de nombres
                if expert_name_lower == search_term:
                    print(f"Exact match found: {expert.get('name')}")
                    found_experts.append({
                        'expert': expert,
                        'category': category
                    })

        return found_experts

    def _find_experts_partial_match(self, expert_name, all_experts_data):
        """
        Encontrar expertos con coincidencia parcial
        
        :param expert_name: Nombre del experto buscado
        :param all_experts_data: Datos de todos los expertos
        :return: Lista de expertos encontrados
        """
        print(f"\n=== Finding Experts (Partial Match) for: {expert_name} ===")
        found_experts = []
        search_term = expert_name.lower().strip()
        name_parts = search_term.split()

        for category, category_data in all_experts_data['experts'].items():
            for expert in category_data.get('experts', []):
                expert_name_lower = expert.get('name', '').lower()
                
                # Comprobar si hay una buena coincidencia (nombre y apellido)
                if len(name_parts) > 1:
                    if all(part in expert_name_lower for part in name_parts):
                        print(f"Good partial match found: {expert.get('name')}")
                        found_experts.append({
                            'expert': expert,
                            'category': category
                        })
                # Coincidencia de palabra individual (último recurso)
                elif any(part in expert_name_lower for part in name_parts):
                    print(f"Single word match found: {expert.get('name')}")
                    found_experts.append({
                        'expert': expert,
                        'category': category
                    })

        return found_experts

    def _get_example_expert(self, all_experts_data):
        """
        Obtener un ejemplo de experto para mensajes de error
        
        :param all_experts_data: Datos de todos los expertos
        :return: Nombre de ejemplo de un experto
        """
        print("\n=== Getting Example Expert ===")
        for category, category_data in all_experts_data.get('experts', {}).items():
            experts = category_data.get('experts', [])
            if experts and len(experts) > 0:
                example = experts[0].get('name', 'Victoria Ricci')
                print(f"Example expert: {example}")
                return example
        
        # Valor por defecto si no hay expertos
        print("No experts found, using default example")
        return "Victoria Ricci"

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
        print("\n=== Preparing Success Response ===")
        # Preparar detalles de expertos
        expert_responses = []
        for found_expert in found_experts:
            expert = found_expert['expert']
            category = found_expert['category']
            
            expert_response = {
                'name': expert['name'],
                'current_role': expert.get('current_role', 'N/A'),
                'current_employer': expert.get('current_employer', 'N/A'),
                'experience': expert.get('experience', 'N/A'),
                'location': expert.get('location', 'N/A'),
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

        print("Success response prepared")
        return {
            'success': True,
            'message': selection_message,
            'experts_found': len(expert_responses),
            'expert_details': expert_responses,
            'screening_questions': category_questions,
            'final_message': thank_you_message,
            'detected_language': detected_language,
            'status_code': 200
        }

    def _prepare_not_found_response(self, search_term, detected_language, example_expert=None):
        """
        Preparar respuesta cuando no se encuentran expertos
        
        :param search_term: Término de búsqueda
        :param detected_language: Idioma detectado
        :param example_expert: Nombre de ejemplo para mostrar
        :return: Respuesta de no encontrado
        """
        print("\n=== Preparing Not Found Response ===")
        # Si no tenemos un ejemplo específico, usar valor por defecto
        if not example_expert:
            example_expert = "Victoria Ricci"
            
        not_found_message = self.chatgpt.translate_message(
            self.BASE_MESSAGES['expert_not_found'].format(
                name=search_term, 
                example_expert=example_expert
            ),
            detected_language
        )
        
        print(f"Not found message prepared for: {search_term}")
        return {
            'success': False,
            'message': not_found_message,
            'status_code': 400,
            'detected_language': detected_language
        }

    def _handle_error(self, error, detected_language):
        """
        Manejar errores generales
        
        :param error: Excepción ocurrida
        :param detected_language: Idioma detectado
        :return: Respuesta de error
        """
        print(f"\n=== Handling Error: {str(error)} ===")
        
        error_message = self.chatgpt.translate_message(
            self.BASE_MESSAGES['processing_error'],
            detected_language
        )
        
        return {
            'success': False,
            'message': error_message,
            'error': str(error),
            'status_code': 500,
            'detected_language': detected_language
        }