from src.utils.chatgpt_helper import ChatGPTHelper
from src.services.external.zoho_services import ZohoService
import logging
# Importar funciones de gestión de idioma global
from app.constants.language import (
    get_last_detected_language, 
    update_last_detected_language, 
    reset_last_detected_language
)

class CompanySuggestionsController:
    def __init__(self):
        self.chatgpt = ChatGPTHelper()
        self.zoho_service = ZohoService()
        self.logger = logging.getLogger(__name__)
        self.excluded_companies = set()

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
        
        sector = data.get('sector')
        region = data.get('processed_region') or data.get('region')
        
        if not sector or not region:
            return {
                'is_valid': False,
                'error': 'Sector and region are required'
            }
        
        return {
            'is_valid': True,
            'sector': sector,
            'region': region,
            'specific_area': data.get('specific_area'),
            'preselected_companies': data.get('preselected_companies', []),
            'detected_language': data.get('detected_language')
        }

    def get_company_suggestions(self, data):
        """
        Obtener sugerencias de empresas
        
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
                    'language': get_last_detected_language(),
                    'status_code': 400
                }
            
            # Detectar y establecer idioma
            self._detect_and_set_language(validation_result)
            
            # Extraer datos validados
            sector = validation_result['sector']
            region = validation_result['region']
            specific_area = validation_result['specific_area']
            preselected_companies = validation_result['preselected_companies']

            # Registro de información
            self.logger.info(f"Processing company suggestions - Sector: {sector}, Region: {region}")

            # Obtener sugerencias de empresas
            companies_result = self._get_companies_suggestions(
                sector, region, specific_area, 
                preselected_companies
            )

            # Generar respuesta final
            result = self._generate_final_response(
                companies_result, 
                preselected_companies
            )
            
            # Añadir código de estado a la respuesta
            result['status_code'] = 200
            
            return result

        except Exception as e:
            error_message = f"Error processing company suggestions: {str(e)}"
            self.logger.error(error_message, exc_info=True)
            return {
                'success': False,
                'error': error_message,
                'language': get_last_detected_language(),
                'status_code': 500
            }

    def _detect_and_set_language(self, validation_result):
        """
        Detectar y establecer el idioma
        
        :param validation_result: Resultado de validación de entrada
        """
        # Obtener el idioma actual
        current_language = get_last_detected_language()

        # Priorizar idioma detectado en los datos
        if validation_result.get('detected_language'):
            update_last_detected_language(validation_result['detected_language'])
            return

        # Intentar detectar idioma usando sector y región
        try:
            # Texto para detección de idioma
            text_to_detect = (
                f"{validation_result.get('sector', '')} "
                f"{validation_result.get('region', '')} "
                f"{validation_result.get('specific_area', '')}"
            ).strip()

            # Si no hay texto suficiente, mantener el idioma actual
            if not text_to_detect:
                return

            # Detección de idioma
            language_detection = self.chatgpt.detect_multilingual_region(
                text_to_detect,
                current_language
            )
            
            # Actualizar idioma si la detección fue exitosa
            if language_detection.get('success', False):
                detected_language = language_detection.get('detected_language', current_language)
                
                # Solo actualizar si el idioma detectado es diferente y no es inglés por defecto
                if detected_language != current_language and detected_language != 'en-US':
                    update_last_detected_language(detected_language)
            
        except Exception as e:
            self.logger.warning(f"Language detection failed: {str(e)}")
            # Mantener el idioma actual
            # No forzar cambio a inglés si ya hay un idioma establecido

    def _get_companies_suggestions(self, sector, region, specific_area, preselected_companies):
        """
        Obtener sugerencias de empresas desde ChatGPT
        
        :param sector: Sector de interés
        :param region: Región de interés
        :param specific_area: Área específica
        :param preselected_companies: Empresas preseleccionadas
        :return: Resultado de sugerencias de empresas
        """
        companies_result = self.chatgpt.get_companies_suggestions(
            sector=sector,
            geography=region,
            specific_area=specific_area,
            preselected_companies=preselected_companies,
            excluded_companies=self.excluded_companies
        )

        if not companies_result['success']:
            raise ValueError(companies_result.get('error', 'Error getting company suggestions'))

        return companies_result['content']

    def _generate_final_response(self, suggested_companies, preselected_companies):
        """
        Generar respuesta final con empresas
        
        :param suggested_companies: Empresas sugeridas
        :param preselected_companies: Empresas preseleccionadas
        :return: Diccionario de respuesta
        """
        # Obtener el idioma actual
        language = get_last_detected_language() or 'en-US'

        # Obtener candidatos de Zoho
        all_candidates = self.zoho_service.get_candidates()
        db_companies = self._get_db_companies(all_candidates, suggested_companies)

        # Generar lista final de empresas
        final_companies = self._compile_final_company_list(
            preselected_companies, 
            db_companies, 
            suggested_companies
        )

        # Mensaje base para diferentes idiomas
        base_messages = {
            'en-US': "Here are the recommended companies, with verified companies listed first. Do you agree with this list?",
            # Añadir más idiomas según sea necesario
        }

        # Seleccionar y traducir mensaje
        base_message = base_messages.get(language, base_messages['en-US'])
        translated_message = self.chatgpt.translate_message(base_message, language)

        # Preparar respuesta
        return {
            'success': True,
            'message': translated_message,
            'companies': final_companies,
            'db_companies_count': len(db_companies),
            'total_companies': len(final_companies),
            'language': language,
            'specific_area': None  # Ajustar según sea necesario
        }

    def _get_db_companies(self, all_candidates, suggested_companies):
        """
        Obtener empresas de la base de datos
        
        :param all_candidates: Lista de candidatos
        :param suggested_companies: Empresas sugeridas
        :return: Conjunto de empresas de la base de datos
        """
        db_companies = set()
        if isinstance(all_candidates, list):
            for candidate in all_candidates:
                current_employer = candidate.get('Current_Employer')
                if current_employer:
                    for company in suggested_companies:
                        if company.lower() in current_employer.lower():
                            db_companies.add(current_employer)
                            break
        return db_companies

    def _compile_final_company_list(self, preselected_companies, db_companies, suggested_companies):
        """
        Compilar lista final de empresas
        
        :param preselected_companies: Empresas preseleccionadas
        :param db_companies: Empresas de la base de datos
        :param suggested_companies: Empresas sugeridas
        :return: Lista final de empresas
        """
        final_companies = []
        
        # Agregar empresas preseleccionadas
        for company in preselected_companies:
            if (company not in final_companies and 
                company not in self.excluded_companies):
                final_companies.append(company)

        # Agregar empresas de la base de datos
        for company in db_companies:
            clean_company = company.strip()
            if (not any(preselected.lower() in clean_company.lower() for preselected in preselected_companies) and
                not any(excluded.lower() in clean_company.lower() for excluded in self.excluded_companies) and
                not any(existing.lower() == clean_company.lower() for existing in final_companies)):
                final_companies.append(clean_company)

        # Agregar empresas sugeridas
        for company in suggested_companies:
            clean_company = company.strip()
            if (not any(existing.lower() == clean_company.lower() for existing in final_companies) and
                not any(excluded.lower() in clean_company.lower() for excluded in self.excluded_companies)):
                final_companies.append(clean_company)
                if len(final_companies) >= 20:
                    break

        return final_companies[:20]

    def reset_last_detected_language(self, language='en-US'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        reset_last_detected_language()
        self.logger.info(f"Last detected language reset to: {language}")