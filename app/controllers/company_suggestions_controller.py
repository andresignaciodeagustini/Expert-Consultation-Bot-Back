from src.utils.chatgpt_helper import ChatGPTHelper
from src.services.external.zoho_services import ZohoService
import logging
import re
# Importar funciones de gestión de idioma global
from app.constants.language import (
    get_last_detected_language, 
    update_last_detected_language, 
    reset_last_detected_language
)

class TextValidationService:
    """
    Servicio para validar y detectar texto sin sentido
    """
    @staticmethod
    def is_nonsense_text(text):
        """
        Detecta si el texto parece no tener sentido
        
        :param text: Texto a evaluar
        :return: True si parece ser texto sin sentido, False en caso contrario
        """
        if not text:
            return False
            
        # Asegurar que text sea una cadena
        if not isinstance(text, str):
            try:
                text = str(text)
            except:
                return True  # Si no se puede convertir a string, considerarlo como sin sentido
            
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
        
    @staticmethod
    def contains_nonsense_text(sector, region, specific_area):
        """
        Verifica si alguno de los campos contiene texto sin sentido
        
        :param sector: Sector
        :param region: Región
        :param specific_area: Área específica
        :return: True si algún campo contiene texto sin sentido
        """
        if TextValidationService.is_nonsense_text(sector):
            return True
            
        if TextValidationService.is_nonsense_text(region):
            return True
            
        if specific_area and TextValidationService.is_nonsense_text(specific_area):
            return True
            
        return False

# Ahora estas clases son independientes, no anidadas
class LanguageManagementService:
    """
    Servicio para gestionar la detección y configuración del idioma
    """
    
    def __init__(self, chatgpt_helper, logger=None):
        self.chatgpt = chatgpt_helper
        self.logger = logger or logging.getLogger(__name__)
        
    def get_language_for_error_message(self, validation_result):
        """
        Obtener el idioma para el mensaje de error
        
        :param validation_result: Resultado de validación
        :return: Código de idioma
        """
        # Primero intentar usar el idioma detectado en los datos
        if validation_result.get('detected_language'):
            return validation_result['detected_language']
            
        # Si no, obtener el último idioma detectado
        current_language = get_last_detected_language()
        if current_language:
            return current_language
            
        # Si no hay idioma detectado, usar inglés por defecto
        return 'en-US'

    def detect_and_set_language(self, validation_result):
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
            
    def reset_language(self, language='en-US'):
        """
        Resetear el idioma detectado a un valor predeterminado
        
        :param language: Idioma a establecer (predeterminado: 'en-US')
        """
        reset_last_detected_language(language)
        self.logger.info(f"Last detected language reset to: {language}")

class CompanyProcessingService:
    """
    Servicio para procesar y gestionar sugerencias de empresas
    """
    
    def __init__(self, chatgpt_helper, zoho_service, excluded_companies=None, logger=None):
        self.chatgpt = chatgpt_helper
        self.zoho_service = zoho_service
        self.excluded_companies = excluded_companies or set()
        self.logger = logger or logging.getLogger(__name__)
    
    def get_companies_suggestions(self, sector, region, specific_area, preselected_companies):
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
    
    def get_db_companies(self, all_candidates, suggested_companies):
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

    def compile_final_company_list(self, preselected_companies, db_companies, suggested_companies):
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
    
    def generate_final_response(self, suggested_companies, preselected_companies):
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
        db_companies = self.get_db_companies(all_candidates, suggested_companies)

        # Generar lista final de empresas
        final_companies = self.compile_final_company_list(
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

class CompanySuggestionsController:
    def __init__(self):
        self.chatgpt = ChatGPTHelper()
        self.zoho_service = ZohoService()
        self.logger = logging.getLogger(__name__)
        self.excluded_companies = set()
        
        # Inicializar servicios
        self.language_service = LanguageManagementService(self.chatgpt, self.logger)
        self.company_service = CompanyProcessingService(
            self.chatgpt, self.zoho_service, self.excluded_companies, self.logger
        )

    def validate_input(self, data):
        """
        Validar datos de entrada
        
        :param data: Datos de la solicitud
        :return: Resultado de validación
        """
        # Verificar si es una respuesta simple como "no"
        if isinstance(data, str) and data.strip().lower() == "no":
            return {
                'is_valid': True,
                'is_no_companies': True,
                'sector': None,
                'region': None,
                'specific_area': None,
                'preselected_companies': []
            }
                
        if not data:
            return {
                'is_valid': False,
                'error': 'No data provided'
            }
        
        sector = data.get('sector')
        region = data.get('processed_region') or data.get('region')
        
        # Manejar caso en que region sea un diccionario
        if isinstance(region, dict):
            # Intentar obtener el valor de región como texto
            region_text = region.get('name') or region.get('region') or region.get('original_location')
            # Si no podemos extraer un valor de texto, convertir a string
            if not region_text:
                self.logger.warning(f"Region is a dictionary without expected keys: {region}")
                region_text = str(region)
            region = region_text
        
        if not sector or not region:
            return {
                'is_valid': False,
                'error': 'Sector and region are required'
            }
        
        # Verificar si hay texto sin sentido en la entrada
        if TextValidationService.contains_nonsense_text(sector, region, data.get('specific_area', '')):
            return {
                'is_valid': False,
                'error': 'nonsense_input',
                'sector': sector,
                'region': region,
                'specific_area': data.get('specific_area'),
                'detected_language': data.get('detected_language')
            }
        
        return {
            'is_valid': True,
            'is_no_companies': False,
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
            # Verificar si es una respuesta "no" directa
            if isinstance(data, str) and data.strip().lower() == "no":
                self.logger.info("User responded 'no' to company suggestions prompt")
                # Usar datos de la sesión anterior (necesita implementarse en un nivel superior)
                # Por ahora, devolvemos mensaje de error informativo
                return {
                    'success': False,
                    'error': 'Session data required for processing "no" response',
                    'language': get_last_detected_language() or 'en-US',
                    'status_code': 400
                }

            # Validar entrada
            validation_result = self.validate_input(data)
            
            # Si el usuario respondió "no" (validado a nivel de objeto)
            if validation_result.get('is_valid') and validation_result.get('is_no_companies', False):
                self.logger.info("User responded 'no' to company suggestions - need previous session data")
                # Aquí deberías recuperar sector y region de la sesión anterior
                # Esta lógica debe implementarse según la estructura de sesiones de la app
                
                # Por ahora, mensaje informativo de error
                return {
                    'success': False,
                    'error': 'Session data required when no companies specified',
                    'language': get_last_detected_language() or 'en-US',
                    'status_code': 400
                }
                
            if not validation_result['is_valid']:
                # Verificar si es por texto sin sentido
                if validation_result.get('error') == 'nonsense_input':
                    # Primero detectamos el idioma para el mensaje de error
                    language = self.language_service.get_language_for_error_message(validation_result)
                    
                    # Mensaje guía para el usuario, simplificado y directo
                    guidance_message = self.chatgpt.translate_message(
                        "Please enter a valid response. Type 'yes' to proceed or 'no' to generate a new list.",
                        language
                    )
                    
                    return {
                        'success': False,
                        'message': guidance_message,
                        'language': language,
                        'status_code': 400
                    }
                
                return {
                    'success': False,
                    'error': validation_result['error'],
                    'language': get_last_detected_language(),
                    'status_code': 400
                }
            
            # Detectar y establecer idioma
            self.language_service.detect_and_set_language(validation_result)
            
            # Extraer datos validados
            sector = validation_result['sector']
            region = validation_result['region']
            specific_area = validation_result['specific_area']
            preselected_companies = validation_result['preselected_companies']

            # Registro de información
            self.logger.info(f"Processing company suggestions - Sector: {sector}, Region: {region}")

            # Obtener sugerencias de empresas
            companies_result = self.company_service.get_companies_suggestions(
                sector, region, specific_area, 
                preselected_companies
            )

            # Generar respuesta final
            result = self.company_service.generate_final_response(
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