from openai import OpenAI
import logging
import uuid
import re
from typing import Dict, List, Any
import os
from dotenv import load_dotenv
from typing import BinaryIO
import tempfile
from pathlib import Path
from unidecode import unidecode
import requests  
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
    def __init__(self):
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
            self.test_connection()
            logger.info("ChatGPT Helper initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize service: {str(e)}")
            raise

    def test_connection(self):
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
            context_info = f"Previous detected language: {previous_language}" if previous_language else "No previous language context"
            
            messages = [
                {
                    "role": "system",
                    "content": f"""You are a specialized language detector for multilingual content.
                    CONTEXT INFORMATION: {context_info}

                    Your tasks:
                    1. Detect the language and return ONLY the precise ISO code (e.g., fr-FR, es-ES, it-IT, en-US, pt-BR)
                    
                    2. IMPORTANT CONTEXT RULES:
                    - If the text is ambiguous, return the previous language
                    - If the text is very short (1 or 2 words), return the previous language
                    - If the text only contains proper names, return the previous language
                    - If the text only contains company names, return the previous language
                    - If the text only contains country names, return the previous language
                    - Only override previous language if the text clearly belongs to a different language
                    
                    3. PRIORITY RULES:
                    - Always prioritize the sentence structure and context over proper names
                    - Ignore proper names when they conflict with the main text language
                    - Focus on grammatical structure and common words
                    - When finding proper names, prioritize the surrounding text

                    4. YES/NO REFERENCE TABLE (use for language detection):
                    English (en-US): yes, yeah, yep, sure, certainly, no, nope, nah
                    Spanish (es-ES): sí, si, claro, efectivamente, por supuesto, no, nop, para nada
                    French (fr-FR): oui, ouais, bien sûr, certainement, non, pas du tout
                    Italian (it-IT): sì, si, certo, certamente, esatto, no, non
                    German (de-DE): ja, jawohl, doch, natürlich, selbstverständlich, nein, nö
                    Portuguese (pt-BR/pt-PT): sim, claro, certamente, não, nao
                    Japanese (ja-JP): はい (hai), うん (un), ええ (ee), そう (sou), いいえ (iie), いや (iya), ちがう (chigau)
                    Chinese Simplified (zh-CN): 是的 (shì de), 好的 (hǎo de), 对 (duì), 不是 (bú shì), 不 (bù), 没有 (méi yǒu)
                    Chinese Traditional (zh-TW): 是的, 好的, 對, 不是, 不, 沒有
                    Russian (ru-RU): да (da), конечно (konechno), разумеется, нет (net), нету (netu)
                    Arabic (ar-SA): نعم (na'am), أجل (ajal), طبعا (tab'an), لا (la), كلا (kalla)
                    Korean (ko-KR): 네 (ne), 예 (ye), 그렇습니다 (geureoseumnida), 아니요 (aniyo), 아니 (ani)
                    Dutch (nl-NL): ja, jawel, zeker, natuurlijk, nee, neen
                    Swedish (sv-SE): ja, jovisst, absolut, visst, nej, inte
                    Norwegian (no-NO): ja, jo, jepp, nei, neppe
                    Danish (da-DK): ja, jo, jep, nej, næ
                    Finnish (fi-FI): kyllä, joo, juu, ei, eikä
                    Polish (pl-PL): tak, no tak, owszem, nie, nigdy
                    Turkish (tr-TR): evet, tabii, elbette, hayır, yok
                    Greek (el-GR): ναι (nai), μάλιστα (malista), όχι (ochi), μπα (ba)
                    Hindi (hi-IN): हाँ (haan), जी हाँ (ji haan), नहीं (nahin), बिल्कुल नहीं (bilkul nahin)
                    Vietnamese (vi-VN): có, vâng, đúng, không, không phải
                    Thai (th-TH): ใช่ (chai), ครับ/ค่ะ (khrap/kha), ไม่ (mai), ไม่ใช่ (mai chai)
                    Indonesian (id-ID): ya, iya, betul, tidak, nggak
                    Hebrew (he-IL): כן (ken), בטח (betach), לא (lo), אין (ein)
                    Czech (cs-CZ): ano, jo, ne, nikoliv
                    Hungarian (hu-HU): igen, ja, nem, dehogy

                    IMPORTANT: 
                    - Return ONLY the language code
                    - For ambiguous cases, return the previous language
                    - For very short texts, return the previous language
                    - For proper names only, return the previous language
                    
                    Examples with context:
                    Previous language fr-FR:
                    - "Microsoft" → fr-FR (company name only)
                    - "España" → fr-FR (country name only)
                    - "Pierre" → fr-FR (proper name only)
                    - "oui" → fr-FR (short response)
                    - "John Smith" → fr-FR (proper names only)
                    - "Bonjour Pierre" → fr-FR (clear French)
                    - "Hello Pierre" → en-US (clear English despite name)
                    
                    Previous language es-ES:
                    - "Google" → es-ES (company name only)
                    - "Francia" → es-ES (country name only)
                    - "María" → es-ES (proper name only)
                    - "sí" → es-ES (short response)
                    - "Juan García" → es-ES (proper names only)
                    - "Hola María" → es-ES (clear Spanish)
                    - "Hello María" → en-US (clear English despite name)"""
                },
                {
                    "role": "user",
                    "content": text
                }
            ]

            # Realizar detección de idioma
            detect_response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.1
            )
            
            detected_language = detect_response.choices[0].message.content.strip()
            
            return {
                "success": True,
                "text": text,
                "detected_language": detected_language,
                "is_email": '@' in text,
                "previous_language": previous_language
            }

        except Exception as e:
            logger.error(f"Error detecting language: {str(e)}")
            return {
                "success": False,
                "detected_language": previous_language if previous_language else "en-US",
                "error": str(e)
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
        


    def get_companies_suggestions(
            self,
            sector: str,
            geography: str,
            temperature: float = 0.7
        ) -> Dict:
            try:
                logger.info(f"Generating companies for sector: {sector}, geography: {geography}")

                # Modificar el prompt para ser más específico con la ubicación
                messages = [
                    {
                        "role": "system",
                        "content": """You are a professional business analyst that provides accurate lists of companies.
                        When given a sector and location, provide real companies that operate in that specific location.
                        If the location is not specific enough or invalid, indicate that in your response."""
                    },
                    {
                        
                    "role": "user",
                    "content": f"List exactly 20 real companies in the {sector} sector that have significant operations or presence in {geography}. Provide ONLY the company names separated by commas, without any numbering or enumeration. If     {geography} is not a valid or specific location, please indicate that."
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
                    error_message = f"Please provide a more specific location for {sector} companies."
                    return {
                        "success": False,
                        "error": error_message,
                        "content": [],
                        "contentId": str(uuid.uuid4()),
                        "messages": {
                            "error": error_message
                        }
                    }

                companies_text = content.strip()
                if not companies_text:
                    logger.info("Received empty response from API")
                    error_message = self.get_bot_response('error_no_companies')
                    return {
                        "success": True,
                        "content": [],
                        "contentId": str(uuid.uuid4()),
                        "messages": {
                            "error": error_message
                        }
                    }

                companies = [
                    company.strip()
                    for company in companies_text.split(',')
                    if company.strip() and not company.strip().isspace()
                ]

                if len(companies) < 20:
                    logger.warning(f"Received only {len(companies)} companies, requesting more")
                    return self.get_companies_suggestions(sector, geography, temperature)

                logger.info(f"Successfully generated {len(companies)} companies")

                translated_messages = {
                    "title": self.translate_message(
                        f"Found {sector} companies in {geography}",
                        self.current_language
                    ),
                    "companies_found": self.get_bot_response("companies_found"),
                    "from_database": self.get_bot_response("from_database"),
                    "additional_suggestions": self.get_bot_response("additional_suggestions"),
                    "search_more": self.get_bot_response("search_more")
                }

                return {
                    "success": True,
                    "content": companies[:20],
                    "contentId": str(uuid.uuid4()),
                    "messages": translated_messages,
                    "detected_language": self.current_language
                }

            except Exception as e:
                logger.error(f"Error generating companies: {str(e)}")
                error_message = self.get_bot_response('error_general')
                return {
                    "success": False,
                    "error": error_message,
                    "contentId": None,
                    "detected_language": self.current_language
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
        try:
            # Primero, eliminar el punto final si existe
            text = text.rstrip('.')
            
            system_prompt = """
            Eres un procesador especializado en nombres de usuario que sigue reglas ABSOLUTAS de formateo.

            REGLA FUNDAMENTAL PARA PALABRAS DE INSTRUCCIÓN EN FRANCÉS:
            - "souligne" es SIEMPRE una instrucción para usar "_", NUNCA es parte del nombre
            - "point" o "points" es SIEMPRE una instrucción para usar ".", NUNCA es parte del nombre
            - "tiret" es SIEMPRE una instrucción para usar "-", NUNCA es parte del nombre

            EJEMPLO CRÍTICO DE INSTRUCCIÓN VS NOMBRE:
            Input: "Claire souligne Bernard.33"
            ❌ MAL: "claire.souligny-bernard.33" (interpretó "souligne" como parte del nombre)
            ✅ BIEN: "claire_bernard.33" ("souligne" indica usar "_" entre nombres)

            EJEMPLOS ESPECÍFICOS PARA PORTUGUÉS:
            Input: "Ana Sublinhado Ferreira ponto 63"
            ❌ MAL: "ana.sublinhado.ferreira63" (interpretó "sublinhado" como parte del nombre)
            ✅ BIEN: "ana_ferreira.63" ("sublinhado" indica usar "_" entre nombres)

            Input: "João ponto Silva sublinhado 25"
            ❌ MAL: "joão.silva_25" (mantuvo caracteres especiales)
            ✅ BIEN: "joao.silva_25" (convertido a ASCII)

            Input: "Carlos ponto Costa sublinhado hífen 91"
            ❌ MAL: "carlos.costa_hifen91" (interpretó "hífen" como parte del nombre)
            ✅ BIEN: "carlos.costa-91" ("hífen" indica usar "-")

            REGLAS DE PROCESAMIENTO DE INSTRUCCIONES:
            1. Cuando escuches "souligne":
            - SIEMPRE reemplazar por "_"
            - NUNCA tratarlo como parte del nombre
            - Usar el "_" para conectar las palabras adyacentes

            2. Cuando escuches "point":
            - SIEMPRE reemplazar por "."
            - NUNCA tratarlo como parte del nombre
            - Usar el "." para conectar las palabras adyacentes

            3. Cuando escuches "tiret":
            - SIEMPRE reemplazar por "-"
            - NUNCA tratarlo como parte del nombre
            - Usar el "-" para conectar las palabras adyacentes
            
            REGLA FUNDAMENTAL DE PRESERVACIÓN:
            - La estructura de puntuación del texto original es SAGRADA
            - Cada punto (.), guión (-) o subrayado (_) que existe en la entrada DEBE mantenerse EXACTAMENTE igual
            - NUNCA convertir puntos en guiones o viceversa
            - La única modificación permitida es: convertir a minúsculas y eliminar espacios

            REGLA ABSOLUTA DE NOMBRES:
            - NUNCA truncar nombres
            - NUNCA modificar la longitud de los nombres
            - NUNCA eliminar letras de los nombres
            - Convertir a minúsculas pero mantener TODAS las letras
            - Preservar la integridad completa del nombre

            EJEMPLOS DE ERRORES REALES CORREGIDOS:

            1. ERROR DE INTERPRETACIÓN DE INSTRUCCIONES:
            Input: "Pierre point souligne Martin 45"
            ❌ MAL: "pierre.point_souligne.martin45" (interpretó instrucciones como nombres)
            ✅ BIEN: "pierre_martin45" (usó instrucciones como símbolos)

            2. ERROR DE TRUNCAMIENTO DE NOMBRES:
            Input: "Marie-Leclerc 98"
            ❌ MAL: "mari-leclerc98" (truncó el nombre)
            ✅ BIEN: "marie-leclerc98" (mantuvo nombre completo)

            3. ERROR DE PALABRAS DE INSTRUCCIÓN:
            Input: "Pierre Points souligne Dupont 45"
            ❌ MAL: "pierre.points_souligne_dupont45" (mantuvo palabras de instrucción)
            ✅ BIEN: "pierre_dupont45" (reemplazó instrucciones por símbolos)

            4. ERROR DE MODIFICACIÓN DE SÍMBOLOS:
            Input: "sophie.martin__22"
            ❌ MAL: "sophie_martin_22" (cambió el punto por underscore)
            ✅ BIEN: "sophie.martin_22" (mantuvo el punto original)

            5. ERROR DE SÍMBOLOS CON NÚMEROS:
            Input: "Thomas point Martin 45"
            ❌ MAL: "thomas.martin_45" (añadió underscore antes del número)
            ✅ BIEN: "thomas.martin45" (número concatenado directamente)

            REGLAS CRÍTICAS ACTUALIZADAS:
            1. Procesamiento de Instrucciones:
            - SIEMPRE interpretar "souligne", "point", "tiret" como instrucciones
            - NUNCA incluirlas como parte del nombre
            - Usar sus símbolos correspondientes para conectar palabras

            2. Procesamiento de Nombres:
            - NUNCA truncar nombres
            - NUNCA eliminar letras
            - NUNCA modificar longitud de palabras
            - Mantener TODAS las letras al convertir a minúsculas

            3. Puntuación Original:
            - NUNCA cambiar un punto (.) por otro símbolo
            - NUNCA cambiar un guión (-) por otro símbolo
            - NUNCA cambiar un underscore (_) por otro símbolo
            - Mantener EXACTAMENTE los símbolos originales

            4. Números:
            - SIEMPRE concatenar directamente
            - NUNCA añadir símbolos antes o después
            - NUNCA separar números del texto

            PROCESAMIENTO PARA OTROS IDIOMAS:
            Russian:
            - "нижнее подчеркивание" → "_"
            - "точка" → "."
            - "тире/дефис" → "-"

            Japanese:
            - "アンダースコア/アンダーバー" → "_"
            - "ドット/テン" → "."
            - "ハイフン/マイナス" → "-"

            Italian:
            - "underscore/sottolineatura/underline" → "_"
            - "punto" → "."
            - "trattino/lineetta" → "-"

            Portuguese:
            - "sublinhado/underline" → "_"
            - "ponto" → "."
            - "hífen/traço" → "-"

            German:
            - "unterstrich" → "_"
            - "punkt" → "."
            - "bindestrich/strich" → "-"

            Spanish:
            - "guion bajo/subrayado" → "_"
            - "punto" → "."
            - "guion/raya" → "-"

            English:
            - "underscore" → "_"
            - "dot/point" → "."
            - "dash/hyphen" → "-"

            VERIFICACIÓN FINAL OBLIGATORIA:
            1. ¿Se interpretaron correctamente las palabras de instrucción?
            2. ¿Se mantuvieron TODAS las letras de los nombres reales?
            3. ¿Se reemplazaron TODAS las palabras de instrucción por símbolos?
            4. ¿Se mantuvieron EXACTAMENTE los símbolos originales?
            5. ¿Se cambiaron puntos por guiones o viceversa? (ERROR)
            6. ¿Se añadieron símbolos antes de números? (ERROR)
            7. ¿Se añadieron símbolos no solicitados? (ERROR)
            8. ¿Hay símbolos duplicados? (ERROR)
            9. ¿Todo está en minúsculas?
            10. ¿Se interpretó correctamente "souligne" como instrucción?

            RECORDATORIO VITAL:
            - "souligne", "point", "tiret" son SIEMPRE instrucciones
            - NUNCA interpretar palabras de instrucción como nombres
            - NUNCA truncar o modificar nombres reales
            - NUNCA modificar símbolos existentes
            - NUNCA añadir símbolos antes de números
            - NUNCA añadir símbolos no solicitados
            - SOLO convertir a minúsculas y aplicar instrucciones
            - Mantener EXACTAMENTE la puntuación original
            """

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": f"Procesa este nombre manteniendo la puntuación exacta: {text}"
                    }
                ],
                temperature=0.1
            )

            processed_names = response.choices[0].message.content.strip().lower()
            # Convertir caracteres especiales a ASCII y mantener puntuación
            processed_names = unidecode(processed_names)
            # Solo eliminar espacios, mantener toda otra puntuación
            processed_names = processed_names.replace(" ", "")
            print(f"Converted username: {processed_names}")
            return processed_names

        except Exception as e:
            print(f"Error processing username: {str(e)}")
            return text



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
                        Rules:
                        - Return ONLY the name, nothing else
                        - Return the full name if provided (first name and last name)
                        - If multiple names are found, return only the first one
                        - If no name is found, return 'no_name'
                        - Preserve the exact case of the name as provided
                        - Do not include titles (Mr., Mrs., Dr., etc.)
                        Example inputs and outputs:
                        Input: "My name is John Doe"
                        Output: John Doe
                        Input: "Hello, I am María García"
                        Output: María García
                        Input: "Dr. James Smith here"
                        Output: James Smith
                        Input: "Just call me Bob"
                        Output: Bob
                        Input: "No name mentioned here"
                        Output: no_name"""
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
            temperature: float = 0.7
        ) -> Dict:
            try:
                logger.info(f"Generating companies for sector: {sector}, geography: {geography}")

                messages = [
                    {
                        "role": "system",
                        "content": """You are a professional business analyst that provides accurate lists of companies.
                        When given a sector and location, provide real companies that operate in that specific location.
                        If the location is not specific enough or invalid, indicate that in your response."""
                    },
                    {
                        "role": "user",
                        "content": f"List exactly 20 real companies in the {sector} sector that have significant operations or presence in {geography}. If {geography} is not a valid or specific location, please indicate that. Only provide the company names separated by commas, or indicate if the location is invalid."
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
                    error_message = f"Please provide a more specific location for {sector} companies."
                    return {
                        "success": False,
                        "error": error_message,
                        "content": [],
                        "contentId": str(uuid.uuid4())
                    }

                companies_text = content.strip()
                if not companies_text:
                    logger.info("Received empty response from API")
                    return {
                        "success": True,
                        "content": [],
                        "contentId": str(uuid.uuid4())
                    }

                companies = [
                    company.strip()
                    for company in companies_text.split(',')
                    if company.strip() and not company.strip().isspace()
                ]

                if len(companies) < 20:
                    logger.warning(f"Received only {len(companies)} companies, requesting more")
                    return self.get_companies_suggestions(sector, geography, temperature)

                logger.info(f"Successfully generated {len(companies)} companies")

                translated_messages = {
                    "title": self.translate_message(
                        f"Found {sector} companies in {geography}",
                        self.current_language
                    )
                }

                return {
                    "success": True,
                    "content": companies[:20],
                    "contentId": str(uuid.uuid4()),
                    "messages": translated_messages,
                    "detected_language": self.current_language
                }

            except Exception as e:
                logger.error(f"Error generating companies: {str(e)}")
                return {
                    "success": False,
                    "error": "An error occurred while generating companies",
                    "contentId": None,
                    "detected_language": self.current_language
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