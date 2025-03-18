from openai import OpenAI
import logging
import uuid
import re
from typing import Dict, List, Any, Set, BinaryIO
import os
from dotenv import load_dotenv
import tempfile
from pathlib import Path
from unidecode import unidecode
from app.constants.language import update_last_detected_language, get_last_detected_language
import requests
import importlib.util
import sys
from ..utils.config import VALID_SECTORS

BOT_MESSAGES = {
    "region_prompt": "I've identified the region as {}. Please specify the business sector.",
    "sector_invalid": "Invalid sector. Please choose from: {}",
    "sector_success": "Perfect! Here are some companies in the {} sector for {}",
    "error_general": "Sorry, there was an error processing your request.",
    "error_no_region": "Region is required for this step",
    "error_voice_recognition": "I couldn't understand that. Could you please try again?",
    "companies_found": "Companies Found:",
    "from_database": "From Database:",
    "additional_suggestions": "Additional Suggestions:",
    "search_more": "Would you like to search for more companies? Please enter a new location:"
}

API_ENDPOINTS = {
    "detect_language": "http://localhost:8080/api/ai/detect-language",
    "translate": "http://localhost:8080/api/ai/translate"
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ChatGPTHelper:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            logging.info("Creando nueva instancia de ChatGPTHelper")
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        else:
            logging.info("Reutilizando instancia existente de ChatGPTHelper")
        return cls._instance

    def _initialize(self):
        """
        Método de inicialización único
        """
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.max_retries = 3
        self.retry_delay = 1
        self.current_language = 'en'

        if not self.api_key:
            logger.error("OPENAI_API_KEY not found in environment variables")
            raise ValueError("OPENAI_API_KEY not found in environment variables")

        try:
            self.client = OpenAI(api_key=self.api_key)
            
            # Inicializar UsernameProcessor
            UsernameProcessor = self._import_username_processor()
            if UsernameProcessor:
                self.username_processor = UsernameProcessor()
                logger.info("UsernameProcessor initialized successfully")
            else:
                logger.warning("UsernameProcessor not available, using fallback processing")
                self.username_processor = None
            
            self._test_connection()
            logger.info("ChatGPT Helper initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize service: {str(e)}")
            raise

    def _import_username_processor(self):
        """Función auxiliar para importar UsernameProcessor de manera segura"""
        try:
            # Intenta primero la importación directa
            from src.handlers.username_processor import UsernameProcessor
            return UsernameProcessor
        except ImportError:
            try:
                # Si falla, intenta con path relativo
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                processor_path = os.path.join(base_path, "handlers", "username_processor.py")
                
                if not os.path.exists(processor_path):
                    logger.error(f"Username processor not found at: {processor_path}")
                    return None
                    
                spec = importlib.util.spec_from_file_location("username_processor", processor_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                return module.UsernameProcessor
            except Exception as e:
                logger.error(f"Failed to import UsernameProcessor: {str(e)}")
                return None

    def _test_connection(self):
        """
        Prueba de conexión con OpenAI
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": "Hello, test connection"}
                ]
            )
            logger.info("Connection test successful")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            raise

    def detected_language_from_content(self, text: str) -> str:
        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a language detector. Analyze the following text and respond only with the language code(es,en,fr,it, etc.). Only respond with the language code, nothing else"
                },
                {
                    "role": "system",
                    "content": f"Detect the language of this text: {text}"
                }
            ]

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.3
            )

            detected_language = response.choices[0].message.content.strip().lower()
            logger.info(f"Language detected from content: {detected_language}")
            return detected_language

        except Exception as e:
            logger.error(f"Error detecting language: {str(e)}")
            return "en"

    def translate_message(self, message: str, target_language: str) -> str:
        try:
            messages = [
                {
                    "role": "system",
                    "content": f"You are a translator. Translate the following text to {target_language}. Only provide the translation, nothing else."
                },
                {
                    "role": "user",
                    "content": message
                }
            ]

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.3
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            return message  # Retorna el mensaje original si hay error
    
    def process_text_input(self, text: str, previous_language: str = None) -> Dict:
        try:
            # Log de depuración
            print(f"\n=== Language Detection Debug ===")
            print(f"Input Text: {text}")
            
            # Si no se proporciona un idioma previo, obtener el último detectado
            previous_language = previous_language or get_last_detected_language()
            print(f"Previous Language: {previous_language}")

            # Preparar mensajes para detección de idioma
            messages = [
                {
                    "role": "system",
                    "content": """You are a specialized language detector. 
                    Your task is to:
                    1. Detect the language of the given text
                    2. Return ONLY the language code (es-ES, en-US, fr-FR, etc.)
                    3. Consider context and full text for accurate detection
                    4. If the text is in Spanish, return 'es-ES'
                    5. If the text is in English, return 'en-US'
                    6. For other languages, use appropriate ISO codes"""
                },
                {
                    "role": "user",
                    "content": f"Detect the language code for this text: '{text}'"
                }
            ]

            # Realizar detección de idioma
            detect_response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.1
            )
            
            detected_language = detect_response.choices[0].message.content.strip()

            # Log adicional de depuración
            print(f"Detected Language: {detected_language}")

            # Validaciones y ajustes
            if not detected_language or detected_language == '':
                # Método de detección alternativo
                if any('á' in text.lower() or 'é' in text.lower() or 'í' in text.lower() or 
                    'ó' in text.lower() or 'ú' in text.lower()):
                    detected_language = 'es-ES'
                else:
                    detected_language = previous_language or 'en-US'

            # Asegurar que sea un código de idioma válido
            if detected_language not in ['es-ES', 'en-US', 'fr-FR', 'de-DE', 'it-IT']:
                detected_language = 'es-ES'  # Predeterminado a español si no está seguro

            # Actualizar el idioma global
            update_last_detected_language(detected_language)
            print(f"Final detected language: {detected_language}")

            return {
                "success": True,
                "text": text,
                "detected_language": detected_language,
                "is_email": '@' in text,
                "previous_language": previous_language
            }

        except Exception as e:
            print(f"Error detecting language: {str(e)}")
            return {
                "success": False,
                "detected_language": previous_language or "en-US",
                "error": str(e)
            }
        
    def detect_multilingual_region(self, text: str, previous_language: str = None) -> Dict:
        """
        Detectar región y lenguaje de manera multilingüe
        
        :param text: Texto a analizar
        :param previous_language: Idioma detectado previamente
        :return: Diccionario con información de detección
        """
        try:
            # Preprocesar texto
            text = text.lower().strip()
            
            # Mapeo multilingüe de regiones
            multilingual_regions = {
                'europe': {
                    'translations': {
                        'es': ['europa', 'europeo', 'europea'],
                        'en': ['europe', 'european'],
                        'fr': ['europe', 'européen', 'européenne'],
                        'de': ['europa', 'europäisch'],
                        'it': ['europa', 'europeo', 'europea'],
                        'pt': ['europa', 'europeu', 'europeia'],
                        'ru': ['европа', 'европейский'],
                        'pl': ['europa', 'europejski'],
                        'nl': ['europa', 'europees'],
                        'el': ['ευρώπη', 'ευρωπαϊκός'],
                        'ar': ['أوروبا', 'أوروبي'],
                        'zh': ['欧洲', '欧洲的']
                    },
                    'iso_code': 'Europe'
                },
                'north america': {
                    'translations': {
                        'es': ['norteamérica', 'norte de america', 'america del norte'],
                        'en': ['north america', 'north american'],
                        'fr': ['amérique du nord', 'nord-américain'],
                        'pt': ['norte da america', 'america do norte'],
                        'it': ['nord america', 'nord americano'],
                        'de': ['nordamerika', 'nordamerikanisch'],
                        'ru': ['северная америка', 'североамериканский'],
                        'ar': ['أمريكا الشمالية'],
                        'zh': ['北美', '北美洲']
                    },
                    'iso_code': 'North America'
                },
                'asia': {
                    'translations': {
                        'es': ['asia', 'asiático', 'asiática'],
                        'en': ['asia', 'asian'],
                        'fr': ['asie', 'asiatique'],
                        'ru': ['азия', 'азиатский'],
                        'ar': ['آسيا', 'آسيوي'],
                        'hi': ['एशिया', 'एशियाई'],
                        'zh': ['亚洲', '亚洲的'],
                        'ja': ['アジア', 'アジア人'],
                        'ko': ['아시아', '아시아인']
                    },
                    'iso_code': 'Asia'
                }
            }
            
            # Mapeo de códigos de idioma a códigos ISO
            lang_mapping = {
                'es': 'es-ES', 'en': 'en-US', 'fr': 'fr-FR', 
                'it': 'it-IT', 'de': 'de-DE', 'pt': 'pt-PT',
                'ru': 'ru-RU', 'ar': 'ar-SA', 'hi': 'hi-IN',
                'zh': 'zh-CN', 'ja': 'ja-JP', 'ko': 'ko-KR',
                'el': 'el-GR', 'pl': 'pl-PL', 'nl': 'nl-NL'
            }
            
            # Función para buscar coincidencias
            def find_region_match(text):
                for region, region_data in multilingual_regions.items():
                    for lang, translations in region_data['translations'].items():
                        if text in [t.lower() for t in translations]:
                            return {
                                'region': region_data['iso_code'],
                                'language': lang_mapping.get(lang, f'{lang}-{lang.upper()}')
                            }
                return None
            
            # Buscar coincidencia
            region_match = find_region_match(text)
            
            if region_match:
                return {
                    'success': True,
                    'text': text,
                    'detected_language': region_match['language'],
                    'region': region_match['region'],
                    'previous_language': previous_language
                }
            
            # Si no se encuentra coincidencia, intentar detección de idioma
            try:
                from langdetect import detect
                
                detected_lang = detect(text)
                detected_language = lang_mapping.get(detected_lang, f'{detected_lang}-{detected_lang.upper()}')
                
                return {
                    'success': False,
                    'text': text,
                    'detected_language': detected_language,
                    'region': None,
                    'previous_language': previous_language,
                    'message': 'No region detected'
                }
            
            except Exception:
                # Fallback al idioma anterior
                return {
                    'success': False,
                    'text': text,
                    'detected_language': previous_language or 'en-US',
                    'region': None,
                    'previous_language': previous_language,
                    'message': 'Language detection failed'
                }
        
        except Exception as e:
            logger.error(f"Error in multilingual region detection: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'detected_language': previous_language or 'en-US',
                'previous_language': previous_language
            }


















    def translate_sector(self, sector_input:str) -> Dict:
        try:
            messages = [
                {
                    "role":"system",
                    "content": """ You are a multilingual translator spececialized in business sector.
                    Your task is to identify if the input refers to any of these sectors:
                    -Technology(including tech, te, tecnologia, technologie,etc.)
                    -Financial Services (including finance, servicion financierons, servizi fiannziari, etc.)
                    -Manufacturing (including finance, servicios financieros, servici finanziari, etc.)

                    If the input matches any sector in ANY language, returnt the English version.
                    If it doesn't match, return 'invalid'.
                    Only return the exact English version or 'invalid', nothing else."""
                },
                {
                    "role":"user",
                    "content":f"Transalate this sector:  {sector_input}"
                }
            ]

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.3
            )

            english_sector = response.choices[0].message.content.strip()

            if english_sector == 'invalid':
                error_sectors = "Technology, Financial Services, Manufacturing"
                translated_sectors = self.translate_message(error_sectors, self.current_language)

                return { 
                    "success": True,
                    "translated_sector": None,
                    "is_valid": False,
                    "available_sectors": translated_sectors
                }
            
            displayed_sector = self.translate_message(english_sector, self.current_language)

            return {
                "success": True,
                "translated_sector":english_sector,
                "displayed_sector": displayed_sector,
                "is_valid": True
            }
        
        except Exception as e:
            logger.error(f"Error translating sector: {str(e)}")
            return {
                "success":False,
                "error": str(e)
            }

    def get_bot_response(self, response_key: str, *args) -> str:
        english_message = BOT_MESSAGES[response_key].format(*args) if args else BOT_MESSAGES[response_key]

        if not self.current_language or self.current_language == 'en':
            return english_message

        return self.translate_message(english_message, self.current_language)

    def identify_region(self, location: str) -> Dict:
        try:
            # Preprocesar la ubicación
            location = location.lower().strip()
            
            # Mapeo directo de ubicaciones
            region_mapping = {
                # Europa
                'europa': 'Europe',
                'europe': 'Europe',
                'españa': 'Europe',
                'spain': 'Europe',
                'madrid': 'Europe',
                'barcelona': 'Europe',
                'france': 'Europe',
                'paris': 'Europe',
                'germany': 'Europe',
                'berlin': 'Europe',
                'italia': 'Europe',
                'italy': 'Europe',
                'rome': 'Europe',
                'london': 'Europe',
                'uk': 'Europe',
                'united kingdom': 'Europe',
                'portugal': 'Europe',
                'netherlands': 'Europe',
                'amsterdam': 'Europe',
                
                # Norte América
                'usa': 'North America',
                'united states': 'North America',
                'canada': 'North America',
                'mexico': 'North America',
                'new york': 'North America',
                'california': 'North America',
                
                # Asia
                'china': 'Asia',
                'japan': 'Asia',
                'india': 'Asia',
                'tokyo': 'Asia',
                'beijing': 'Asia',
                'seoul': 'Asia',
                'singapore': 'Asia'
            }
            
            # Verificación directa
            if location in region_mapping:
                return {
                    "success": True,
                    "region": region_mapping[location],
                    "original_location": location
                }
            
            # Verificación parcial
            for key, region in region_mapping.items():
                if key in location:
                    return {
                        "success": True,
                        "region": region,
                        "original_location": location
                    }
            
            # Usar IA como último recurso
            messages = [
                {
                    "role": "system",
                    "content": """
                    You are an advanced geography expert. 
                    Categorize locations into these regions: 
                    - North America
                    - Europe
                    - Asia
                    
                    Strict rules:
                    - Be extremely precise in region identification
                    - Consider historical, cultural, and geographical context
                    - If location is ambiguous or not clearly in these regions, respond with 'Uncertain'
                    - Prioritize the most likely region based on the input
                    """
                },
                {
                    "role": "user",
                    "content": f"Determine the EXACT region for this location: {location}. Respond ONLY with the region name or 'Uncertain'."
                }
            ]

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.2  # Reducir variabilidad
            )

            region = response.choices[0].message.content.strip()

            # Validación final
            valid_regions = ["North America", "Europe", "Asia"]
            if region not in valid_regions:
                logger.warning(f"Uncertain region for location: {location}")
                return {
                    "success": False,
                    "error": f"Could not determine region for {location}",
                    "original_location": location
                }

            logger.info(f"Location '{location}' identified as {region}")
            return {
                "success": True,
                "region": region,
                "original_location": location
            }

        except Exception as e:
            logger.error(f"Comprehensive error identifying region: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "original_location": location
            }
        



    def get_companies_suggestions(
        self,
        sector: str,
        geography: str,
        specific_area: str = None,  # Nuevo parámetro
        preselected_companies: List[str] = None,
        excluded_companies: Set[str] = None,  # Añadido parámetro de exclusión
        temperature: float = 0.7
    ) -> Dict:
        try:
            # Si hay un área específica, modificar la descripción del sector
            if specific_area:
                sector_description = f"{specific_area} within the {sector} sector"
            else:
                sector_description = f"{sector} sector"

            logger.info(f"Generating companies for sector: {sector_description}, geography: {geography}")
            
            # Filtrar empresas preseleccionadas que estén en la lista de excluidas
            if preselected_companies and excluded_companies:
                preselected_companies = [
                    company for company in preselected_companies
                    if not any(excluded.lower() in company.lower() for excluded in excluded_companies)
                ]
                logger.info(f"Filtered preselected companies: {preselected_companies}")

            # Construir el prompt incluyendo preseleccionadas y excluidas
            prompt_parts = []
            if preselected_companies:
                logger.info(f"Including preselected companies: {preselected_companies}")
                prompt_parts.append(f"Please include these specific companies first in your suggestions: {', '.join(preselected_companies)}. ")
            if excluded_companies:
                logger.info(f"Excluding companies: {excluded_companies}")
                prompt_parts.append(f"Do not include these companies in your suggestions: {', '.join(excluded_companies)}. ")

            prompt_text = "".join(prompt_parts)

            messages = [
                {
                    "role": "system",
                    "content": """You are a professional business analyst that provides accurate lists of companies.
                    When given a sector and location, provide real companies that operate in that specific location.
                    If specific companies are requested, include them first in your response.
                    If companies are to be excluded, ensure they are not in your suggestions."""
                },
                {
                    "role": "user",
                    "content": f"{prompt_text}List exactly 20 real companies in the {sector_description} that have significant operations or presence in {geography}. If {geography} is not a valid or specific location, please indicate that. Only provide the company names separated by commas, or indicate if the location is invalid."
                }
            ]

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=temperature,
                max_tokens=250
            )

            content = response.choices[0].message.content
            if not content:
                logger.info("Received empty response from API")
                return {
                    "success": True,
                    "content": [],
                    "contentId": str(uuid.uuid4())
                }

            companies = [
                company.strip()
                for company in content.split(',')
                if company.strip() and not company.strip().isspace()
            ]

            # Filtrar empresas excluidas
            if excluded_companies:
                companies = [
                    company for company in companies
                    if not any(excluded.lower() in company.lower() for excluded in excluded_companies)
                ]

            # Asegurar que las empresas preseleccionadas (ya filtradas) estén incluidas
            final_companies = []
            if preselected_companies:
                # Primero las preseleccionadas
                for company in preselected_companies:
                    if company not in final_companies:
                        final_companies.append(company)
                # Luego el resto hasta completar 20
                for company in companies:
                    if company not in final_companies and len(final_companies) < 20:
                        final_companies.append(company)
                companies = final_companies

            logger.info(f"Successfully generated {len(companies)} companies")
            if preselected_companies:
                logger.info(f"Included {len(preselected_companies)} preselected companies")
            if excluded_companies:
                logger.info(f"Excluded {len(excluded_companies)} companies")

            return {
                "success": True,
                "content": companies[:20],
                "contentId": str(uuid.uuid4())
            }

        except Exception as e:
            logger.error(f"Error generating companies: {str(e)}")
            return {
                "success": False,
                "error": "An error occurred while generating companies",
                "contentId": None
            }


            
    def process_voice_input(self, audio_file: BinaryIO, step: str = 'transcribe') -> Dict:
        temp_path = None
        try:
            print("\n=== Processing Voice in ChatGPTHelper ===")
            print(f"Audio file: {audio_file.filename}")
            
            if not audio_file:
                raise ValueError("No audio file provided")

            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_audio:
                print(f"Creating temp file: {temp_audio.name}")
                audio_file.save(temp_audio)
                temp_path = temp_audio.name

            print(f"Temp file created: {temp_path}")
            
            # Verificar que el archivo existe y tiene contenido
            if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
                raise ValueError("Failed to save audio file")

            print(f"File size: {os.path.getsize(temp_path)} bytes")

            # Mapeo completo de nombres de idiomas a códigos ISO-639-1
            language_codes = {
                'afrikaans': 'af', 'albanian': 'sq', 'amharic': 'am', 'arabic': 'ar',
                'armenian': 'hy', 'azerbaijani': 'az', 'basque': 'eu', 'belarusian': 'be',
                'bengali': 'bn', 'bosnian': 'bs', 'bulgarian': 'bg', 'catalan': 'ca',
                'cebuano': 'ceb', 'chinese': 'zh', 'corsican': 'co', 'croatian': 'hr',
                'czech': 'cs', 'danish': 'da', 'dutch': 'nl', 'english': 'en',
                'esperanto': 'eo', 'estonian': 'et', 'finnish': 'fi', 'french': 'fr',
                'frisian': 'fy', 'galician': 'gl', 'georgian': 'ka', 'german': 'de',
                'greek': 'el', 'gujarati': 'gu', 'haitian creole': 'ht', 'hausa': 'ha',
                'hawaiian': 'haw', 'hebrew': 'he', 'hindi': 'hi', 'hmong': 'hmn',
                'hungarian': 'hu', 'icelandic': 'is', 'igbo': 'ig', 'indonesian': 'id',
                'irish': 'ga', 'italian': 'it', 'japanese': 'ja', 'javanese': 'jv',
                'kannada': 'kn', 'kazakh': 'kk', 'khmer': 'km', 'korean': 'ko',
                'kurdish': 'ku', 'kyrgyz': 'ky', 'lao': 'lo', 'latin': 'la',
                'latvian': 'lv', 'lithuanian': 'lt', 'luxembourgish': 'lb',
                'macedonian': 'mk', 'malagasy': 'mg', 'malay': 'ms', 'malayalam': 'ml',
                'maltese': 'mt', 'maori': 'mi', 'marathi': 'mr', 'mongolian': 'mn',
                'myanmar': 'my', 'nepali': 'ne', 'norwegian': 'no', 'nyanja': 'ny',
                'odia': 'or', 'pashto': 'ps', 'persian': 'fa', 'polish': 'pl',
                'portuguese': 'pt', 'punjabi': 'pa', 'romanian': 'ro', 'russian': 'ru',
                'samoan': 'sm', 'scots gaelic': 'gd', 'serbian': 'sr', 'sesotho': 'st',
                'shona': 'sn', 'sindhi': 'sd', 'sinhala': 'si', 'slovak': 'sk',
                'slovenian': 'sl', 'somali': 'so', 'spanish': 'es', 'sundanese': 'su',
                'swahili': 'sw', 'swedish': 'sv', 'tagalog': 'tl', 'tajik': 'tg',
                'tamil': 'ta', 'telugu': 'te', 'thai': 'th', 'turkish': 'tr',
                'ukrainian': 'uk', 'urdu': 'ur', 'uyghur': 'ug', 'uzbek': 'uz',
                'vietnamese': 'vi', 'welsh': 'cy', 'xhosa': 'xh', 'yiddish': 'yi',
                'yoruba': 'yo', 'zulu': 'zu'
            }

            # Primero detectar el idioma
            with open(temp_path, 'rb') as audio:
                print("Detecting language...")
                language_response = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio,
                    response_format="verbose_json"
                )
                
                # Obtener el código ISO-639-1 del idioma
                detected_language = getattr(language_response, 'language', 'en').lower()
                
                # Convertir a código ISO si es necesario
                if detected_language in language_codes:
                    detected_language = language_codes[detected_language]
                    
                print(f"Detected language code: {detected_language}")

            # Luego transcribir con el idioma detectado
            with open(temp_path, 'rb') as audio:
                print("Starting transcription...")
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio,
                    response_format="text",
                    language=detected_language  # Usar código ISO
                )
                
                # Obtener transcripción inicial
                raw_text = transcript if isinstance(transcript, str) else transcript.text
                raw_text = raw_text.strip()
                print(f"Initial transcription: {raw_text}")

                # Procesar según el paso indicado
                if step == 'username':
                    processed_text = self.process_username(raw_text)
                    print(f"Processed username: {processed_text}")
                    response_dict = {
                        "success": True,
                        "username": processed_text,
                        "original_transcription": raw_text,
                        "detected_language": detected_language,
                        "language_name": next((name for name, code in language_codes.items() 
                                            if code == detected_language), detected_language),
                        "transcription": processed_text  # Para mantener compatibilidad
                    }
                else:  # step == 'transcribe' u otros casos
                    response_dict = {
                        "success": True,
                        "transcription": raw_text,
                        "detected_language": detected_language,
                        "language_name": next((name for name, code in language_codes.items() 
                                            if code == detected_language), detected_language)
                    }

                return response_dict

        except Exception as e:
            print(f"Error in process_voice_input: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                    print(f"Temp file removed: {temp_path}")
                except Exception as e:
                    print(f"Error removing temp file: {str(e)}")



    def process_username(self, text: str) -> str:
        # Diccionario de transliteración ruso-latino
        russian_to_latin = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            'А': 'a', 'Б': 'b', 'В': 'v', 'Г': 'g', 'Д': 'd', 'Е': 'e', 'Ё': 'yo',
            'Ж': 'zh', 'З': 'z', 'И': 'i', 'Й': 'y', 'К': 'k', 'Л': 'l', 'М': 'm',
            'Н': 'n', 'О': 'o', 'П': 'p', 'Р': 'r', 'С': 's', 'Т': 't', 'У': 'u',
            'Ф': 'f', 'Х': 'h', 'Ц': 'ts', 'Ч': 'ch', 'Ш': 'sh', 'Щ': 'sch',
            'Ъ': '', 'Ы': 'y', 'Ь': '', 'Э': 'e', 'Ю': 'yu', 'Я': 'ya'
        }

        def transliterate_russian(text: str) -> str:
            """Convierte texto cirílico a caracteres latinos"""
            result = ""
            for char in text:
                result += russian_to_latin.get(char, char)
            return result.lower()  # Convertir todo a minúsculas

        def clean_username(username: str) -> str:
            """Limpia y formatea el nombre de usuario"""
            # Convertir a minúsculas y eliminar espacios extras
            cleaned = username.lower().strip()
            # Reemplazar espacios con guiones bajos
            cleaned = "_".join(cleaned.split())
            # Eliminar caracteres no permitidos
            cleaned = ''.join(c for c in cleaned if c.isalnum() or c in '_.-')
            return cleaned

        try:
            # Primer paso: Procesamiento con GPT-4
            print(f"\nProcesando username con GPT-4: {text}")
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "Procesa el nombre de usuario manteniendo solo letras, números y los símbolos permitidos (punto, guion bajo). Elimina palabras que describan símbolos."
                    },
                    {
                        "role": "user",
                        "content": f"Procesa este nombre: {text}"
                    }
                ],
                temperature=0.1
            )

            # Obtener y procesar la respuesta
            processed_text = response.choices[0].message.content.strip()
            
            # Transliterar si contiene caracteres cirílicos
            if any(char in russian_to_latin for char in processed_text):
                processed_text = transliterate_russian(processed_text)
            
            # Limpiar y formatear el nombre de usuario
            final_username = clean_username(processed_text)
            
            print(f"Resultado final: {final_username}")

            # Verificar palabras prohibidas
            prohibited_words = [
                'punto', 'point', 'dot', 'ponto', 'punkt',
                'guion', 'hyphen', 'dash', 'tiret', 'hífen',
                'underscore', 'souligne', 'sublinhado',
                'arroba', 'at', 'arobase'
            ]

            if any(word in final_username for word in prohibited_words):
                raise ValueError(f"Palabra prohibida encontrada en el resultado")

            return final_username

        except Exception as e:
            print(f"Error en process_username: {str(e)}")
            try:
                # Procesamiento de respaldo
                if any(char in russian_to_latin for char in text):
                    backup_processed = transliterate_russian(text)
                else:
                    backup_processed = text
                
                final_backup = clean_username(backup_processed)
                print(f"Resultado de respaldo: {final_backup}")
                return final_backup
                
            except Exception as backup_error:
                print(f"Error en procesamiento de respaldo: {str(backup_error)}")
                # Último recurso: devolver el texto original limpio
                return clean_username(text)


    def process_sector_input(self, audio_file: BinaryIO, previous_region: str) -> Dict:
        temp_path = None
        try:
            # Validación del archivo
            if not audio_file or not hasattr(audio_file, 'filename'):
                return {
                    "success": False,
                    "error": self.get_bot_response('error_no_audio')
                }

            filename = audio_file.filename.lower()
            valid_formats = ['flac', 'm4a', 'mp3', 'mp4', 'mpeg', 'mpga', 'oga', 'ogg', 'wav', 'webm']
            file_extension = filename.split('.')[-1] if '.' in filename else ''
            
            if file_extension not in valid_formats:
                return {
                    "success": False,
                    "error": f"Invalid file format. Supported formats: {valid_formats}"
                }

            # Procesar archivo de audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_audio:
                audio_file.seek(0)
                temp_audio.write(audio_file.read())
                temp_path = Path(temp_audio.name)

            # Transcribir audio
            with open(temp_path, 'rb') as audio:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio,
                    response_format="verbose_json",
                    temperature=0.7
                )

            transcribed_text = transcript.text.strip()
            self.current_language = self.detected_language_from_content(transcribed_text)

            # Usar translate_sector para procesar el sector
            sector_result = self.translate_sector(transcribed_text)
            
            if sector_result['success']:
                if sector_result['is_valid']:
                    # Si el sector es válido, obtener las compañías
                    companies_result = self.get_companies_suggestions(
                        sector=sector_result['translated_sector'],
                        geography=previous_region
                    )

                    if companies_result['success']:
                        return {
                            "success": True,
                            "transcription": transcribed_text,
                            "detected_language": self.current_language,
                            "region": previous_region,
                            "sector": sector_result['translated_sector'],
                            "displayed_sector": sector_result['displayed_sector'],
                            "companies": companies_result['content'],
                            "messages": companies_result['messages'],
                            "step": "complete"
                        }
                    else:
                        return {
                            "success": False,
                            "error": companies_result.get('error', self.get_bot_response('error_general')),
                            "detected_language": self.current_language
                        }
                else:
                    # Si el sector no es válido, devolver mensaje de error
                    return {
                        "success": False,
                        "message": self.get_bot_response('sector_invalid', sector_result.get('available_sectors')),
                        "detected_language": self.current_language
                    }
            else:
                return {
                    "success": False,
                    "error": sector_result.get('error', self.get_bot_response('error_general')),
                    "detected_language": self.current_language
                }

        except Exception as e:
            logger.error(f"Error processing sector input: {str(e)}")
            return {
                "success": False,
                "error": self.get_bot_response('error_general'),
                "detected_language": self.current_language if hasattr(self, 'current_language') else 'en'
            }
        finally:
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception as e:
                    logger.error(f"Error deleting temporary file: {str(e)}")



















        ####################################################

        
        

    def extract_email(self, text: str) -> Dict:
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are an email extractor. Your task is to find and return ONLY the email address from the input text.
                    Rules:
                    - Return ONLY the email address, nothing else
                    - If multiple emails are found, return only the first one
                    - If no email is found, return 'no_email'
                    - Preserve the exact case of the email as provided
                    Example inputs and outputs:
                    Input: "My email is john.doe@example.com thanks"
                    Output: john.doe@example.com
                    Input: "Contact me at JANE@company.co.uk or other@email.com"
                    Output: JANE@company.co.uk
                    Input: "Hello, how are you?"
                    Output: no_email"""
                },
                {
                    "role": "user",
                    "content": text
                }
            ]

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0,
                max_tokens=50
            )

            extracted_email = response.choices[0].message.content.strip()
            
            if extracted_email == 'no_email':
                return {
                    "success": False,
                    "error": "No email address found in the text",
                    "email": None
                }

            return {
                "success": True,
                "email": extracted_email
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "email": None
            }
        



        
    def extract_name(self, text: str) -> Dict:
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are a name extractor. Your task is to find and return ONLY the person's name from the input text.
                    CRITICAL RULES:
                    - Return ONLY the name, nothing else
                    - IMPORTANT: Capitalize ONLY the first letter of the name
                    - DO NOT modify or change any other part of the name
                    - Preserve the EXACT original capitalization of the rest of the name
                    - Return the full name if provided (first name and last name)
                    - If multiple names are found, return only the first one
                    - If no name is found, return 'no_name'
                    - Do not include titles (Mr., Mrs., Dr., etc.)

                    CAPITALIZATION EXAMPLES:
                    Input: "jENNIFER" → Output: "Jennyfer"
                    Input: "JENNIFER" → Output: "Jennifer"
                    Input: "maria jose" → Output: "Maria jose"
                    Input: "MARIA JOSE" → Output: "Maria jose"
                    Input: "mC dONALD" → Output: "Mc donald"

                    Strict rules:
                    - First letter MUST be uppercase
                    - Rest of the name MUST remain exactly as in the original text
                    - No additional modifications allowed"""
                },
                {
                    "role": "user",
                    "content": text
                }
            ]

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0,
                max_tokens=50
            )

            extracted_name = response.choices[0].message.content.strip()
            
            if extracted_name == 'no_name':
                return {
                    "success": False,
                    "error": "No name found in the text",
                    "name": None
                }

            return {
                "success": True,
                "name": extracted_name
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "name": None
            }





    def extract_intention(self, text: str) -> Dict:
        try:
            # Limpiar el texto de espacios y convertir a minúsculas
            cleaned_text = text.strip().lower()
            
            # Verificar si el texto es exactamente "yes" o "no"
            if cleaned_text == "yes" or cleaned_text == "no":
                return {
                    "success": True,
                    "intention": cleaned_text
                }
                
            messages = [
                {
                    "role": "system",
                    "content": """You are a binary intention classifier. Your ONLY task is to determine if a text expresses YES or NO.

    STRICT OUTPUT RULES:
    - You MUST respond ONLY with one of these three words: "yes", "no", or "unclear"
    - Never explain or add additional text
    - If there's any ambiguity, respond with "unclear"

    CLASSIFICATION RULES:
    1. Classify as "yes" when the text:
    - Expresses agreement, acceptance, or interest
    - Shows willingness to proceed or continue
    - Contains affirmative expressions in any language
    - Uses positive emoji or symbols

    2. Classify as "no" when the text:
    - Expresses disagreement, rejection, or disinterest
    - Shows unwillingness to proceed
    - Contains negative expressions in any language
    - Uses negative emoji or symbols

    3. Classify as "unclear" when:
    - The intention is ambiguous
    - The text is a question
    - The text is unrelated to yes/no
    - The meaning is not certain

    MULTILANGUAGE EXAMPLES:

    YES responses:
    - "Yes" / "Sí" / "Oui" / "Ja"
    - "Of course" / "Por supuesto" / "Bien sûr"
    - "I want to" / "Quiero" / "Je veux"
    - "Sure" / "Claro" / "Certainement"
    - "That works" / "Eso funciona" / "Ça marche"
    - "I'm interested" / "Me interesa" / "Je suis intéressé"
    - "👍" / "✅" / "♥"
    - "ok" / "vale" / "bueno"

    NO responses:
    - "No" / "No" / "Non" / "Nein"
    - "Not now" / "Ahora no" / "Pas maintenant"
    - "I'll pass" / "Paso" / "Je passe"
    - "Not interested" / "No me interesa" / "Pas intéressé"
    - "Maybe later" / "Quizás después" / "Peut-être plus tard"
    - "👎" / "❌" / "🚫"
    - "nope" / "para nada" / "non merci"

    Input: "Yes, please"
    Output: yes

    Input: "No gracias"
    Output: no

    Input: "How does this work?"
    Output: unclear"""
                },
                {
                    "role": "user",
                    "content": text
                }
            ]

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0,
                max_tokens=10
            )

            intention = response.choices[0].message.content.strip().lower()
            
            if intention == 'unclear':
                return {
                    "success": False,
                    "error": "Unclear intention in the text",
                    "intention": None
                }

            return {
                "success": True,
                "intention": intention
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "intention": None
            }









    def extract_sector(self, text: str) -> str:     
            

            try:
                messages = [
                  {
                        "role": "system",
                        "content": """You are an AI specialized in identifying professional sectors from any text input, including short phrases and multiple languages.

                        Return ONLY ONE WORD from this list:
                        - Business
                        - Technology
                        - Healthcare
                        - Education
                        - Creative
                        - Legal
                        - Finance
                        - Marketing
                        - Software
                        - Medical

                        Common variations in multiple languages:
                        Technology: tecnología, tech, IT, informatique, technologie, tecnologia
                        Healthcare: salud, santé, gesundheit, saúde, sanidad
                        Finance: finanzas, financial, financiero, finance, finanças
                        Business: negocios, business, entreprise, negócios, empresa
                        Education: educación, education, éducation, educação, ensino
                        Creative: creativo, créatif, criativo, diseño, design
                        Legal: legal, jurídico, droit, direito
                        Marketing: marketing, mercadeo, márqueting, mercadotecnia
                        Software: software, logiciel, programación, desenvolvimento
                        Medical: médico, medical, médical, medicina

                        Rules:
                        - Return ONLY ONE WORD from the approved list
                        - Understand short phrases like 'me interesa tecnología' → 'Technology'
                        - Convert related terms in any language to English sector name
                        - Handle informal expressions like 'quiero finanzas' → 'Finance'
                        - If no sector is clearly identified, return 'Unknown'
                        - Ignore additional context and focus on sector identification
                        """
                    },
                    {
                        "role": "user",
                        "content": text
                    }
                ]

                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=messages,
                    temperature=0.1,
                    max_tokens=10
                )

                return response.choices[0].message.content.strip()

            except Exception:
                return "Unknown"
            



    def extract_region(self, location: str) -> Dict:
            try:
                logger.info(f"Identifying region for location: {location}")

                messages = [
                    {
                        "role": "system",
                        "content": "You are a geography expert. You must categorize locations into one of these regions: North America, Europe, or Asia. Only respond with one of these three options."
                    },
                    {
                        "role": "user",
                        "content": f"Which region (North America, Europe, or Asia) does {location} belong to? Only respond with the region name."
                    }
                ]

                response = self.client.chat.completions.create(
                    model="gpt-4",
                    messages=messages,
                    temperature=0.3
                )

                region = response.choices[0].message.content.strip()

                if region not in ["North America", "Europe", "Asia"]:
                    logger.warning(f"Invalid region response: {region}")
                    return {
                        "success": False,
                        "error": f"Invalid region: {region}"
                    }

                logger.info(f"Location '{location}' identified as {region}")
                return {
                    "success": True,
                    "region": region,
                    "original_location": location
                }

            except Exception as e:
                logger.error(f"Error identifying region: {str(e)}")
                return {
                    "success": False,
                    "error": str(e)
                }
        
    def extract_work_timing(self, text: str) -> str:
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are an analyzer that determines user preferences regarding experts' work timing at companies.
                    Your task is to extract if the user wants experts who:
                    - currently work at the companies
                    - previously worked at the companies
                    - both options

                    IMPORTANT: Return ONLY ONE of these exact words: 'current', 'previous', or 'both'
                    Do not use any other variations.

                    Rules:
                    - If user writes 'both' → return 'both'
                    - If user writes 'previous' or 'previously' → return 'previous'
                    - If user writes 'current' or 'currently' → return 'current'
                    - For other expressions, interpret the meaning and return one of these three options
                    - Handle multiple languages and informal expressions

                    Examples:
                    Return 'current':
                    - "I want experts who currently work there"
                    - "Current employees"
                    - "People working there now"
                    - "Quiero expertos que trabajen actualmente"
                    - "Actuales empleados"
                    
                    Return 'previous':
                    - "I prefer former employees"
                    - "Those who worked there before"
                    - "Past experience is fine"
                    - "Ex empleados"
                    - "Personas que hayan trabajado antes"
                    
                    Return 'both':
                    - "Both options are good"
                    - "Current and former employees"
                    - "Either is fine"
                    - "Ambas opciones"
                    - "Los dos"
                    - "No tengo preferencia"

                    Direct matches:
                    Input: "both" → Output: both
                    Input: "previous" → Output: previous
                    Input: "current" → Output: current
                    Input: "previously" → Output: previous
                    Input: "currently" → Output: current

                    Other examples:
                    Input: "I want current employees"
                    Output: current

                    Input: "Prefiero ex empleados"
                    Output: previous

                    Input: "Both options would work"
                    Output: both"""
                },
                {
                    "role": "user",
                    "content": text
                }
            ]

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0,
                max_tokens=10
            )

            # Primero verificar si el texto coincide exactamente con una de las opciones
            cleaned_text = text.strip().lower()
            if cleaned_text in ['both', 'previous', 'current']:
                return cleaned_text
            elif cleaned_text == 'previously':
                return 'previous'
            elif cleaned_text == 'currently':
                return 'current'

            timing = response.choices[0].message.content.strip().lower()
            
            # Validar que la respuesta sea una de las opciones permitidas
            valid_responses = ['current', 'previous', 'both']
            if timing not in valid_responses:
                return None

            return timing

        except Exception as e:
            return None


    def process_company_response(self, text: str):
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are an AI specialized in processing responses about company preferences.
                    
                    Your task is to:
                    1. If the user mentions company names, extract and return them as a comma-separated list
                    2. If the user expresses no interest or a negative response, return exactly "no"
                    
                    Rules:
                    - For company names: Return ONLY the company names separated by commas, no additional text
                    - For negative responses: Return ONLY "no"
                    - Handle multilingual inputs
                    - Remove any extra spaces or punctuation
                    
                    Examples:
                    Input: "Me gustaría trabajar en Google y Microsoft"
                    Output: Google, Microsoft
                    
                    Input: "No tengo preferencias de empresas"
                    Output: no"""
                },
                {
                    "role": "user",
                    "content": text
                }
            ]

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=0.1,
                max_tokens=100
            )

            result = response.choices[0].message.content.strip()
            
            # Si es una respuesta negativa, devolver "no"
            if result.lower() == "no":
                return "no"
            
            # Si son compañías, devolver un diccionario
            companies = [company.strip() for company in result.split(',')]
            return {
                'interested_in_companies': True,
                'companies': companies
            }

        except Exception:
            return "no"


    def get_companies_suggestions(
        self,
        sector: str,
        geography: str,
        specific_area: str = None,
        preselected_companies: List[str] = None,
        excluded_companies: Set[str] = None,
        temperature: float = 0.7
    ) -> Dict:
        try:
            # Crear descripción del sector incluyendo área específica si está presente
            if specific_area:
                sector_description = f"{specific_area} within the {sector} sector"
            else:
                sector_description = f"{sector} sector"

            logger.info(f"Generating companies for sector: {sector_description}, geography: {geography}")

            # Construir el prompt incluyendo las empresas preseleccionadas y excluidas
            prompt_parts = []
            
            if preselected_companies:
                logger.info(f"Including preselected companies: {preselected_companies}")
                prompt_parts.append(f"Please include these companies first in your suggestions: {', '.join(preselected_companies)}.")
            
            if excluded_companies:
                logger.info(f"Excluding companies: {excluded_companies}")
                prompt_parts.append(f"Do not include these companies in your suggestions: {', '.join(excluded_companies)}.")
            
            custom_instructions = " ".join(prompt_parts)

            messages = [
                {
                    "role": "system",
                    "content": """You are a professional business analyst that provides accurate lists of companies.
                    When given a sector and location, provide real companies that operate in that specific location.
                    If specific companies are requested, include them first in your response.
                    If companies are to be excluded, ensure they are not in your suggestions.
                    If the location is not specific enough or invalid, indicate that in your response."""
                },
                {
                    "role": "user",
                    "content": f"{custom_instructions} List exactly 20 real companies in the {sector_description} that have significant operations or presence in {geography}. If {geography} is not a valid or specific location, please indicate that. Only provide the company names separated by commas, or indicate if the location is invalid."
                }
            ]

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=temperature,
                max_tokens=250
            )

            content = response.choices[0].message.content
            if content is None or "invalid" in content.lower() or "didn't specify" in content.lower():
                logger.info("Invalid or unspecified location")
                error_message = f"Please provide a more specific location for {sector_description} companies."
                return {
                    "success": False,
                    "error": error_message,
                    "content": [],
                    "contentId": str(uuid.uuid4())
                }

            companies = [
                company.strip()
                for company in content.split(',')
                if company.strip() and not company.strip().isspace()
            ]

            # Filtrar empresas excluidas
            if excluded_companies:
                companies = [
                    company for company in companies 
                    if not any(excluded.lower() in company.lower() for excluded in excluded_companies)
                ]

            # Asegurar que las empresas preseleccionadas estén primero
            if preselected_companies:
                final_companies = []
                # Primero las preseleccionadas
                for company in preselected_companies:
                    if company not in final_companies:
                        final_companies.append(company)
                # Luego el resto hasta completar 20
                for company in companies:
                    if company not in final_companies and len(final_companies) < 20:
                        final_companies.append(company)
                companies = final_companies

            if len(companies) < 20:
                logger.warning(f"Received only {len(companies)} companies, requesting more")
                return self.get_companies_suggestions(
                    sector, 
                    geography, 
                    specific_area,  # Añadir specific_area aquí
                    preselected_companies,
                    excluded_companies,
                    temperature
                )

            logger.info(f"Successfully generated {len(companies)} companies")
            if preselected_companies:
                logger.info(f"Included {len(preselected_companies)} preselected companies")
            if excluded_companies:
                logger.info(f"Excluded {len(excluded_companies)} companies")

            return {
                "success": True,
                "content": companies[:20],
                "contentId": str(uuid.uuid4()),
                "detected_language": self.current_language,
                "specific_area": specific_area  # Incluir specific_area en la respuesta
            }

        except Exception as e:
            logger.error(f"Error generating companies: {str(e)}")
            return {
                "success": False,
                "error": "An error occurred while generating companies",
                "contentId": None,
                "detected_language": self.current_language,
                "specific_area": specific_area  # Incluir specific_area en caso de error
            }

    def extract_expert_name(self, text: str) -> Dict:
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are a name extractor and formatter. Your task is to identify and properly format personal names from input text.
                    Rules:
                    - Extract only the name and surname
                    - Capitalize first letter of each name/surname
                    - Return ONLY the formatted name, nothing else
                    - If no clear name is found, return 'unclear'
                    - Handle multiple languages
                    - Remove any extra words or context

                    Examples:
                    Input: "me interesa john doe"
                    Output: John Doe

                    Input: "quiero trabajar con maría garcía"
                    Output: María García

                    Input: "I want to work with peter parker please"
                    Output: Peter Parker

                    Input: "je voudrais jean dupont"
                    Output: Jean Dupont

                    Input: "me gustaría trabajar con JUAN PEREZ"
                    Output: Juan Perez

                    Input: "hello how are you"
                    Output: unclear

                    Input: "robert downey jr me interesa"
                    Output: Robert Downey Jr

                    Input: "escojo a ANA MARÍA LÓPEZ"
                    Output: Ana María López"""
                },
                {
                    "role": "user",
                    "content": text
                }
            ]

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0,
                max_tokens=20
            )

            extracted_name = response.choices[0].message.content.strip()
            
            if extracted_name.lower() == 'unclear':
                return {
                    "success": False,
                    "error": "No clear name found in the text",
                    "name": None
                }

            return {
                "success": True,
                "name": extracted_name
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "name": None
            }

    def correct_email(self, email: str, instruction: str) -> Dict:
        try:
            # 1. Validación inicial del email
            email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
            if not re.match(email_pattern, email):
                return {
                    "success": False,
                    "original_email": email,
                    "correction_applied": False,
                    "error": "Invalid original email format"
                }

            # 2. Procesar instrucciones formateadas
            if instruction.startswith('REMOVE:'):
                # Extraer las partes de la instrucción
                parts = instruction.split(',')
                remove_part = parts[0].strip()
                
                # Extraer la palabra a remover
                remove_word = remove_part.split('"')[1] if '"' in remove_part else remove_part.replace('REMOVE:', '').strip()
                
                # Procesar el email
                email_parts = email.split('@')
                username = email_parts[0]
                
                # Aplicar la corrección
                corrected_username = username.lower().replace(remove_word.lower(), '').strip()
                corrected_email = f"{corrected_username}@gmail.com"
                correction_applied = email.lower() != corrected_email.lower()

                print(f"Processing removal: {remove_word}")
                print(f"Original email: {email}")
                print(f"Corrected email: {corrected_email}")
                
                return {
                    'success': True,
                    'original_email': email,
                    'corrected_email': corrected_email,
                    'correction_applied': correction_applied,
                    'correction_text': instruction
                }

            # 3. Procesar instrucciones REPLACE (para portugués y otros)
            if instruction.upper().startswith('REPLACE:'):
                try:
                    # Extraer las letras a reemplazar
                    match = re.search(r'REPLACE: "([^"]+)" WITH: "([^"]+)"', instruction)
                    if match:
                        old_char, new_char = match.groups()
                        username, domain = email.split('@')
                        corrected_username = username.replace(old_char, new_char)
                        corrected_email = f"{corrected_username}@{domain}"
                        correction_applied = email != corrected_email

                        print(f"Processing REPLACE command:")
                        print(f"Old char: {old_char}")
                        print(f"New char: {new_char}")
                        print(f"Original email: {email}")
                        print(f"Corrected email: {corrected_email}")

                        return {
                            'success': True,
                            'original_email': email,
                            'corrected_email': corrected_email,
                            'correction_applied': correction_applied,
                            'correction_text': instruction
                        }
                except Exception as e:
                    print(f"Error processing REPLACE command: {str(e)}")

            # 4. Procesar instrucciones regulares
            username, domain = email.split('@')
            corrected_username = username

            instruction_lower = instruction.lower()
            if "replace" in instruction_lower or "reemplaza" in instruction_lower:
                try:
                    if '"' in instruction:
                        old_char = instruction.split('"')[1]
                        new_char = instruction.split('"')[3]
                        corrected_username = username.replace(old_char, new_char)
                except Exception as e:
                    print(f"Error processing instruction: {str(e)}")
                    corrected_username = username

            # 5. Construir resultado final
            corrected_email = f"{corrected_username}@{domain}"
            correction_applied = email.lower() != corrected_email.lower()

            return {
                "success": True,
                "original_email": email,
                "correction_text": instruction,
                "correction_applied": correction_applied,
                "corrected_email": corrected_email
            }

        except Exception as e:
            print(f"Error in correct_email: {str(e)}")
            return {
                "success": False,
                "original_email": email,
                "correction_applied": False,
                "error": str(e),
                "corrected_email": email
            }
        




    def get_client_side_companies(
        self,
        sector: str,
        geography: str,
        excluded_companies: Set[str] = None,  # Añadir parámetro de exclusión
        temperature: float = 0.7
    ) -> Dict:
        try:
            logger.info(f"Generating client-side companies for sector: {sector}, geography: {geography}")
            if excluded_companies:
                logger.info(f"Excluding companies: {excluded_companies}")

            # Modificar el prompt para incluir exclusiones
            exclusion_text = ""
            if excluded_companies:
                exclusion_text = f" Do not include these companies: {', '.join(excluded_companies)}."

            messages = [
                {
                    "role": "system",
                    "content": """You are a professional business analyst that provides accurate lists of companies.
                    When given a sector and location, provide real companies that are CLIENTS or USERS of that industry's services.
                    For the financial services sector, think of large corporations, retailers, and industrial companies that USE financial services."""
                },
                {
                    "role": "user",
                    "content": f"""List exactly 15 major companies in {geography} that are CLIENTS of the {sector} industry.{exclusion_text}
                    For financial services, provide large corporate clients that use banking, investment, and financial services.
                    Examples:
                    - Major retailers (e.g., Carrefour, Tesco)
                    - Industrial companies (e.g., Siemens, Volkswagen)
                    - Technology companies (e.g., SAP, Nokia)
                    - Consumer goods companies (e.g., Nestlé, Unilever)
                    
                    Only provide company names separated by commas, focusing on well-known, large corporations in {geography} that USE financial services."""
                }
            ]

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=temperature,
                max_tokens=250
            )

            content = response.choices[0].message.content
            if not content:
                logger.info("Received empty response from API")
                return {
                    "success": True,
                    "content": [],
                    "contentId": str(uuid.uuid4())
                }

            companies = [
                company.strip()
                for company in content.split(',')
                if company.strip() and not company.strip().isspace()
            ]

            # Filtrar empresas excluidas
            if excluded_companies:
                companies = [
                    company for company in companies
                    if not any(excluded.lower() in company.lower() for excluded in excluded_companies)
                ]
                logger.info(f"Filtered out excluded companies, {len(companies)} remaining")

            logger.info(f"Successfully generated {len(companies)} client-side companies")

            return {
                "success": True,
                "content": companies[:15],
                "contentId": str(uuid.uuid4())
            }

        except Exception as e:
            logger.error(f"Error generating client-side companies: {str(e)}")
            return {
                "success": False,
                "error": "An error occurred while generating companies",
                "contentId": None
            }
        



    def get_supply_chain_companies(
        self,
        sector: str,
        geography: str,
        excluded_companies: Set[str] = None,  # Añadir parámetro de exclusión
        temperature: float = 0.7
    ) -> Dict:
        try:
            logger.info(f"Generating supply chain companies for sector: {sector}, geography: {geography}")
            if excluded_companies:
                logger.info(f"Excluding companies: {excluded_companies}")

            # Modificar el prompt para incluir exclusiones
            exclusion_text = ""
            if excluded_companies:
                exclusion_text = f" Do not include these companies: {', '.join(excluded_companies)}."

            messages = [
                {
                    "role": "system",
                    "content": """You are a professional business analyst that provides accurate lists of companies.
                    When given a sector and location, provide real companies that are SUPPLIERS or SERVICE PROVIDERS to that industry.
                    These are companies that PROVIDE technology, infrastructure, or essential services to the main players in that sector."""
                },
                {
                    "role": "user",
                    "content": f"""List exactly 15 companies that are on the SUPPLY SIDE of the {sector} industry in {geography}.{exclusion_text}
                    For financial services, provide companies that supply:
                    - Financial technology (trading platforms, payment systems)
                    - Data and analytics providers
                    - Infrastructure and security solutions
                    - Risk management systems
                    - Core banking software
                    
                    Examples for financial services:
                    - Bloomberg (market data and analytics)
                    - Temenos (banking software)
                    - FIS Global (financial technology)
                    - Finastra (financial software)
                    - Refinitiv (financial data)
                    
                    Only provide company names separated by commas, focusing on well-known, verifiable companies in {geography}."""
                }
            ]

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=temperature,
                max_tokens=250
            )

            content = response.choices[0].message.content
            if not content:
                logger.info("Received empty response from API")
                return {
                    "success": True,
                    "content": [],
                    "contentId": str(uuid.uuid4())
                }

            companies = [
                company.strip()
                for company in content.split(',')
                if company.strip() and not company.strip().isspace()
            ]

            # Filtrar empresas excluidas
            if excluded_companies:
                companies = [
                    company for company in companies
                    if not any(excluded.lower() in company.lower() for excluded in excluded_companies)
                ]
                logger.info(f"Filtered out excluded companies, {len(companies)} remaining")

            logger.info(f"Successfully generated {len(companies)} supply chain companies")

            return {
                "success": True,
                "content": companies[:15],
                "contentId": str(uuid.uuid4())
            }

        except Exception as e:
            logger.error(f"Error generating supply chain companies: {str(e)}")
            return {
                "success": False,
                "error": "An error occurred while generating companies",
                "contentId": None
            }