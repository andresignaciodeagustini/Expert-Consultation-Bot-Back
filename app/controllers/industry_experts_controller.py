from app.services.industry_experts_service import IndustryExpertsService
from src.utils.chatgpt_helper import ChatGPTHelper
# Importar funciones de gestión de idioma global
from app.constants.language import (
    get_last_detected_language, 
    update_last_detected_language, 
    reset_last_detected_language
)
import logging
import traceback
import json
import sys

# Configurar logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('IndustryExpertsController')

class IndustryExpertsController:
    def __init__(self, industry_experts_service=None, chatgpt=None):
        logger.info("Inicializando IndustryExpertsController")
        self.industry_experts_service = (
            industry_experts_service or 
            IndustryExpertsService()
        )
        self.chatgpt = chatgpt or ChatGPTHelper()
        logger.info("IndustryExpertsController inicializado correctamente")

        self.BASE_MESSAGES = {
            'no_data': "No data provided for industry experts search.",
            'missing_fields': "Missing required fields for industry experts search.",
            'processing_error': "An error occurred while searching for industry experts."
        }

    def validate_input(self, data):
        """
        Validar datos de entrada
        
        :param data: Datos de la solicitud
        :return: Resultado de validación
        """
        logger.info("=== Iniciando validación de entrada ===")
        logger.debug(f"Datos recibidos para validación: {json.dumps(data, default=str) if data else 'None'}")
        
        if not data:
            logger.warning("No se proporcionaron datos")
            return {
                'is_valid': False,
                'error': 'No data provided'
            }
        
        # Añade aquí validaciones específicas según tus requisitos
        required_fields = ['sector', 'region']
        missing_fields = [field for field in required_fields if field not in data]
        
        if missing_fields:
            logger.warning(f"Faltan campos requeridos: {missing_fields}")
            return {
                'is_valid': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }
        
        logger.info("Validación exitosa")
        return {
            'is_valid': True,
            'data': data
        }

    def get_industry_experts(self, data):
        """
        Obtener expertos de la industria
        
        :param data: Datos de la solicitud
        :return: Respuesta de expertos
        """
        try:
            logger.info("=== Iniciando búsqueda de expertos de la industria ===")
            logger.debug(f"Datos de entrada: {json.dumps(data, default=str) if data else 'None'}")
            
            # Validar entrada
            validation_result = self.validate_input(data)
            if not validation_result['is_valid']:
                # Procesar idioma para el mensaje de error
                logger.info("Validación fallida, procesando idioma para mensaje de error")
                detected_language = self._process_language(data)
                logger.debug(f"Idioma detectado: {detected_language}")
                
                error_key = 'missing_fields' if 'Missing required fields' in validation_result['error'] else 'no_data'
                logger.debug(f"Utilizando mensaje de error: {error_key}")
                
                try:
                    error_message = self.chatgpt.translate_message(
                        self.BASE_MESSAGES.get(error_key), 
                        detected_language
                    )
                    logger.debug(f"Mensaje de error traducido: {error_message}")
                except Exception as e:
                    logger.error(f"Error al traducir mensaje: {str(e)}")
                    error_message = self.BASE_MESSAGES.get(error_key)
                
                logger.warning(f"Retornando error de validación: {validation_result['error']}")
                return {
                    'success': False,
                    'error': error_message,
                    'status_code': 400,
                    'detected_language': detected_language
                }
            
            # Procesar idioma
            logger.info("Procesando idioma para la solicitud")
            detected_language = self._process_language(data)
            data['detected_language'] = detected_language
            logger.info(f"Idioma detectado configurado: {detected_language}")

            # Obtener expertos
            logger.info("Llamando a industry_experts_service.get_industry_experts")
            result = self.industry_experts_service.get_industry_experts(data)
            logger.debug(f"Resultado del servicio: {json.dumps(result, default=str)}")
            
            # Añadir código de estado a la respuesta
            result['status_code'] = 200 if result.get('success', False) else 400
            result['detected_language'] = detected_language
            
            logger.info(f"Retornando respuesta. Éxito: {result.get('success', False)}, Código: {result['status_code']}")
            return result

        except Exception as e:
            logger.error("=== Error en Get Industry Experts ===")
            logger.error(f"Tipo de error: {type(e)}")
            logger.error(f"Detalles del error: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # Procesar idioma para el mensaje de error
            try:
                current_language = get_last_detected_language()
                logger.info(f"Idioma actual para mensaje de error: {current_language}")
                
                error_message = self.chatgpt.translate_message(
                    self.BASE_MESSAGES['processing_error'], 
                    current_language
                )
                logger.debug(f"Mensaje de error traducido: {error_message}")
            except Exception as translation_error:
                logger.error(f"Error al traducir mensaje de error: {str(translation_error)}")
                error_message = self.BASE_MESSAGES['processing_error']
            
            return {
                'success': False,
                'message': error_message,
                'error': str(e),
                'status_code': 500,
                'detected_language': current_language if 'current_language' in locals() else 'en'
            }

    def _process_language(self, data):
        """
        Procesar y detectar idioma
        
        :param data: Datos de la solicitud
        :return: Idioma detectado
        """
        logger.info("=== Iniciando procesamiento de idioma ===")
        try:
            current_language = get_last_detected_language()
            logger.info(f"Idioma detectado actual: {current_language}")
            
            # Intentar obtener texto para detección de idioma
            text_to_detect = (
                data.get('sector', '') + ' ' + 
                data.get('region', '') + ' ' + 
                data.get('language', '')
            )
            logger.debug(f"Texto para detección de idioma: {text_to_detect}")
            
            if not text_to_detect.strip():
                logger.info("No hay texto para detectar, usando 'test'")
                text_to_detect = "test"
            
            logger.info("Llamando a chatgpt.process_text_input para detección de idioma")
            text_processing_result = self.chatgpt.process_text_input(
                text_to_detect, 
                current_language
            )
            logger.debug(f"Resultado de procesamiento de texto: {json.dumps(text_processing_result, default=str)}")
            
            detected_language = text_processing_result.get('detected_language', 'en')
            logger.info(f"Idioma detectado: {detected_language}")
            
            # Actualizar idioma si es diferente de inglés
            if detected_language != 'en':
                logger.info(f"Actualizando último idioma detectado a: {detected_language}")
                update_last_detected_language(detected_language)
            
            return detected_language
        except Exception as e:
            logger.error(f"Error en procesamiento de idioma: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            logger.info("Retornando idioma por defecto 'en'")
            return 'en'

    def reset_last_detected_language(self, language='en'):
        """
        Resetear el último idioma detectado
        
        :param language: Idioma por defecto
        """
        logger.info(f"=== Reseteando último idioma detectado a: {language} ===")
        reset_last_detected_language()