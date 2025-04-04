from src.utils.chatgpt_helper import ChatGPTHelper
from src.services.external.zoho_services import ZohoService

class IndustryExpertsService:
    def __init__(self, chatgpt=None, zoho_service=None):
        self.chatgpt = chatgpt or ChatGPTHelper()
        self.zoho_service = zoho_service or ZohoService()
        self.MAX_TOTAL_EXPERTS = 25

    def get_industry_experts(self, params):
        """
        Obtener expertos de la industria
        
        :param params: Parámetros de búsqueda
        :return: Expertos encontrados
        """
        try:
            # Validar parámetros de entrada
            validation_result = self._validate_input(params)
            if not validation_result['success']:
                return validation_result

            # Recopilar empresas
            all_companies = self._collect_companies(params)

            # Obtener candidatos
            all_candidates = self.zoho_service.get_candidates()
            if not isinstance(all_candidates, list):
                return {
                    'success': False,
                    'message': 'Error retrieving candidates'
                }

            # Categorizar expertos
            categorized_experts = self._categorize_experts(
                all_candidates, 
                all_companies, 
                params
            )

            # Preparar respuesta final
            return self._prepare_final_response(
                categorized_experts, 
                params.get('detected_language', 'en')
            )

        except Exception as e:
            return {
                'success': False,
                'message': 'An error occurred while processing industry experts',
                'error': str(e)
            }

    def _validate_input(self, params):
        """
        Validar parámetros de entrada
        
        :param params: Parámetros de búsqueda
        :return: Resultado de validación
        """
        sector = params.get('sector')
        region = params.get('region')

        if not sector or not region:
            return {
                'success': False,
                'message': 'Missing required fields: sector and region'
            }

        return {'success': True}

    def _collect_companies(self, params):
        """
        Recopilar empresas de diferentes categorías
        
        :param params: Parámetros de búsqueda
        :return: Diccionario de empresas
        """
        all_companies = {
            'main_companies': params.get('companies', []),
            'client_companies': [],
            'supply_companies': []
        }

        # Obtener empresas cliente
        if params.get('clientPerspective', False):
            client_result = self.chatgpt.get_client_side_companies(
                sector=params['sector'],
                geography=params['region']
            )
            if client_result['success']:
                all_companies['client_companies'] = client_result['content']

        # Obtener empresas supply chain
        if params.get('supplyChainRequired', False):
            supply_result = self.chatgpt.get_supply_chain_companies(
                sector=params['sector'],
                geography=params['region']
            )
            if supply_result['success']:
                all_companies['supply_companies'] = supply_result['content']

        return all_companies

    def _categorize_experts(self, all_candidates, all_companies, params):
        """
        Categorizar expertos por tipo de empresa
        
        :param all_candidates: Lista de candidatos
        :param all_companies: Empresas por categoría
        :param params: Parámetros de búsqueda
        :return: Expertos categorizados
        """
        categorized_experts = {
            'main_companies': {'experts': [], 'companies_found': set()},
            'client_companies': {'experts': [], 'companies_found': set()},
            'supply_companies': {'experts': [], 'companies_found': set()}
        }

        # Calcular expertos por categoría
        total_categories = sum([
            1,  # main_companies siempre cuenta
            bool(params.get('clientPerspective', False)),
            bool(params.get('supplyChainRequired', False))
        ])
        experts_per_category = self.MAX_TOTAL_EXPERTS // total_categories

        for candidate in all_candidates:
            current_employer = candidate.get('Current_Employer', '').lower()
            
            # Crear datos del experto
            expert_data = {
                'id': candidate.get('id'),
                'name': candidate.get('Full_Name'),
                'current_role': candidate.get('Current_Job_Title'),
                'current_employer': candidate.get('Current_Employer'),
                'experience': f"{candidate.get('Experience_in_Years')} years",
                'location': f"{candidate.get('City', '')}, {candidate.get('Country', '')}"
            }

            # Categorizar expertos
            self._add_expert_to_category(
                expert_data, 
                current_employer, 
                all_companies, 
                categorized_experts,
                experts_per_category,
                params
            )

        return categorized_experts

    def _add_expert_to_category(
        self, 
        expert_data, 
        current_employer, 
        all_companies, 
        categorized_experts,
        experts_per_category,
        params
    ):
        """
        Agregar experto a la categoría correspondiente
        
        :param expert_data: Datos del experto
        :param current_employer: Empleador actual
        :param all_companies: Empresas por categoría
        :param categorized_experts: Expertos categorizados
        :param experts_per_category: Máximo de expertos por categoría
        :param params: Parámetros de búsqueda
        """
        # Verificar empresas principales
        for company in all_companies['main_companies']:
            if company.lower() in current_employer:
                if len(categorized_experts['main_companies']['experts']) < experts_per_category:
                    categorized_experts['main_companies']['experts'].append(expert_data)
                    categorized_experts['main_companies']['companies_found'].add(expert_data['current_employer'])
                break

        # Verificar empresas cliente
        if params.get('clientPerspective', False):
            for company in all_companies['client_companies']:
                if company.lower() in current_employer:
                    if len(categorized_experts['client_companies']['experts']) < experts_per_category:
                        categorized_experts['client_companies']['experts'].append(expert_data)
                        categorized_experts['client_companies']['companies_found'].add(expert_data['current_employer'])
                    break

        # Verificar empresas supply chain
        if params.get('supplyChainRequired', False):
            for company in all_companies['supply_companies']:
                if company.lower() in current_employer:
                    if len(categorized_experts['supply_companies']['experts']) < experts_per_category:
                        categorized_experts['supply_companies']['experts'].append(expert_data)
                        categorized_experts['supply_companies']['companies_found'].add(expert_data['current_employer'])
                    break

    def _prepare_final_response(self, categorized_experts, detected_language):
        """
        Preparar respuesta final
        
        :param categorized_experts: Expertos categorizados
        :param detected_language: Idioma detectado
        :return: Respuesta final
        """
        # Traducir mensajes
        translated_messages = self._translate_messages(detected_language)
        
        final_response = {
            'success': True,
            'experts': {
                'main': {
                    'experts': [],  # Se llenará con expertos traducidos
                    'total_found': len(categorized_experts['main_companies']['experts']),
                    'companies': list(categorized_experts['main_companies']['companies_found'])
                }
            }
        }
        
        # Agregar categorías adicionales (estructuras vacías)
        if categorized_experts['client_companies']['experts']:
            final_response['experts']['client'] = {
                'experts': [],  # Se llenará con expertos traducidos
                'total_found': len(categorized_experts['client_companies']['experts']),
                'companies': list(categorized_experts['client_companies']['companies_found'])
            }
        
        if categorized_experts['supply_companies']['experts']:
            final_response['experts']['supply_chain'] = {
                'experts': [],  # Se llenará con expertos traducidos
                'total_found': len(categorized_experts['supply_companies']['experts']),
                'companies': list(categorized_experts['supply_companies']['companies_found'])
            }
        
        # Procesar y traducir cada experto por categoría
        for category_key, source_category in [
            ('main', 'main_companies'),
            ('client', 'client_companies'),
            ('supply_chain', 'supply_companies')
        ]:
            # Verificar si esta categoría existe en la respuesta
            if category_key in final_response['experts'] and categorized_experts[source_category]['experts']:
                for expert in categorized_experts[source_category]['experts']:
                    # Crear una copia del experto para traducir campos
                    translated_expert = expert.copy()
                    
                    # Traducir el rol
                    translated_expert['current_role'] = self.chatgpt.translate_message(
                        expert['current_role'], 
                        detected_language
                    )
                    
                    # Traducir la experiencia - reemplazar "years" con su traducción
                    years_translated = self.chatgpt.translate_message("years", detected_language)
                    translated_expert['experience'] = expert['experience'].replace("years", years_translated)
                    
                    # Traducir ubicación - dividir, traducir partes y volver a unir
                    location_parts = expert['location'].split(', ')
                    translated_location_parts = [
                        self.chatgpt.translate_message(part, detected_language) 
                        for part in location_parts
                    ]
                    translated_expert['location'] = ', '.join(translated_location_parts)
                    
                    # Crear formatted_data con etiquetas y valores traducidos
                    translated_expert['formatted_data'] = {
                        translated_messages['current_role_label']: translated_expert['current_role'],
                        translated_messages['company_label']: translated_expert['current_employer'],
                        translated_messages['experience_label']: translated_expert['experience'],
                        translated_messages['location_label']: translated_expert['location']
                    }
                    
                    # Agregar a la categoría correspondiente en la respuesta final
                    final_response['experts'][category_key]['experts'].append(translated_expert)
        
        # Agregar totales
        final_response['total_experts_shown'] = sum(
            len(cat['experts']) for cat in final_response['experts'].values()
        )
        final_response['total_experts_found'] = sum(
            cat['total_found'] for cat in final_response['experts'].values()
        )
        
        # Añadir mensajes traducidos
        final_response['messages'] = translated_messages
        
        return final_response

    def _translate_messages(self, detected_language):
        """
        Traducir mensajes
        
        :param detected_language: Idioma detectado
        :return: Mensajes traducidos
        """
        BASE_MESSAGES = {
            'experts_found_title': 'Experts Found',
            'main_experts_title': 'Main Company Experts',
            'client_experts_title': 'Client Company Experts',
            'supply_chain_experts_title': 'Supply Chain Experts',
            'selection_instructions': 'Please select an expert by entering their name exactly as it appears in the list.',
            'selection_example': 'For example: "{expert_name}"',
            'selection_prompt': 'Which expert would you like to select?',
            # Etiquetas de los datos de expertos
            'current_role_label': 'Current Role',
            'company_label': 'Company',
            'experience_label': 'Experience',
            'location_label': 'Location',
            # Roles comunes pre-traducidos (opcional - como respaldo)
            'role_translations': {
                'CFO': self.chatgpt.translate_message('CFO', detected_language),
                'Head of Finance': self.chatgpt.translate_message('Head of Finance', detected_language),
                'Financial Controller': self.chatgpt.translate_message('Financial Controller', detected_language),
                'Treasury Manager': self.chatgpt.translate_message('Treasury Manager', detected_language),
            },
            # Traducciones adicionales para UI
            'screening_questions_title': 'Screening Questions',
            'no_questions_available': 'No questions available'
        }

        # Traducir todos los mensajes base
        translated_messages = {
            key: self.chatgpt.translate_message(msg, detected_language) 
            for key, msg in BASE_MESSAGES.items()
        }
        
        return translated_messages