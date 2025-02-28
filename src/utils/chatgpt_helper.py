from openai import OpenAI
import logging
import uuid
from typing import Dict
import os
from dotenv import load_dotenv
from typing import BinaryIO
import tempfile
from pathlib import Path
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
            


    def process_text_input(self, text: str) -> Dict:
        try:
            messages = [
                {
                    "role": "system",
                    "content": """You are a specialized language detector for multilingual content.
                    Your tasks:
                    1. Detect the language and return ONLY the precise ISO code (e.g., fr-FR, es-ES, it-IT, en-US, pt-BR)
                    2. PRIORITY RULES:
                    - Always prioritize the sentence structure and context over proper names
                    - Ignore proper names when they conflict with the main text language
                    - Focus on grammatical structure and common words
                    
                    3. For short texts and names:
                    - Ignore email addresses when detecting language
                    - Focus on the actual text content
                    - Consider common phrases and words
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
                    
                    IMPORTANT: Return ONLY the language code, nothing else.
                    
                    Examples:
                    - "I want to contact María González" → en-US (prioritize "I want to contact" over the name)
                    - "Ceci est mon email test@test.com" → fr-FR
                    - "Quiero contactar a María González" → es-ES
                    - "Je voudrais contacter María González" → fr-FR
                    - "This is my email" → en-US
                    - "Questo è il mio email" → it-IT
                    - "はい、お願いします" → ja-JP
                    - "Oui, bien sûr" → fr-FR
                    - "No, gracias" → es-ES
                    - "Yes, please" → en-US
                    - "네, 감사합니다" → ko-KR
                    - "Да, спасибо" → ru-RU
                    - "نعم، شكراً" → ar-SA
                    - "כן, תודה" → he-IL"""
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
                "is_email": '@' in text
            }

        except Exception as e:
            logger.error(f"Error detecting language: {str(e)}")
            return {
                "success": False,
                "detected_language": "en-US",
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
            logger.info(f"Processing voice input for transcription")

            # Validaciones básicas del archivo
            if not audio_file or not hasattr(audio_file, 'filename'):
                return {
                    "success": False,
                    "error": "No valid audio file provided"
                }

            # Crear y procesar archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_audio:
                audio_file.seek(0)
                temp_audio.write(audio_file.read())
                temp_path = Path(temp_audio.name)

            # Transcripción del audio
            with open(temp_path, 'rb') as audio:
                transcript = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio,
                    response_format="text"  # Cambiado a "text" para simplificar
                )

            # Obtener el texto transcrito
            transcribed_text = transcript.strip()
            print(f"Transcribed text: {transcribed_text}")  # Para debug

            return {
                "success": True,
                "transcription": transcribed_text,
                "detected_language": "es"
            }

        except Exception as e:
            logger.error(f"Error processing voice input: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            # Limpieza del archivo temporal
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception as e:
                    logger.error(f"Error deleting temporary file: {str(e)}")
    


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
                        "content": """You are an AI specialized in identifying professional sectors.
                        Return ONLY ONE WORD representing the sector from this list:
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
                        
                        Rules:
                        - Return ONLY ONE WORD, no additional text
                        - Convert related terms (e.g., 'salud' → 'Healthcare', 'tecnología' → 'Technology')
                        - If no sector is identified, return 'Unknown'
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



