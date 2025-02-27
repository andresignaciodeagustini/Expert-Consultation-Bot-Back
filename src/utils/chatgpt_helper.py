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
                    "content": f"You are a translator. Translate the following text to {target_language}. Only respond with the translation, nothing else."
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

            translated_text = response.choices[0].message.content.strip()
            return translated_text

        except Exception as e:
            logger.error(f"Translation error: {str(e)}")
            return message

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












    def process_text_input(self, text: str) -> Dict:
        try:
            # Usar el endpoint de detección de idioma
            detect_response = requests.post(
                API_ENDPOINTS["detect_language"],
                json={'text': text},
                headers={'Content-Type': 'application/json'}
            )
            
            if detect_response.status_code == 200:
                detected_language = detect_response.json()['detected_language']
                self.current_language = detected_language
                
                # Si el texto no está en inglés, traducirlo para procesamiento
                if detected_language != 'en':
                    translate_response = requests.post(
                        API_ENDPOINTS["translate"],
                        json={
                            'text': text,
                            'target_language': 'english'
                        },
                        headers={'Content-Type': 'application/json'}
                    )
                    
                    if translate_response.status_code == 200:
                        text_for_processing = translate_response.json()['translated_text']
                    else:
                        text_for_processing = text
                else:
                    text_for_processing = text

                # Identificar la región usando el texto en inglés
                region_result = self.identify_region(text_for_processing)
                
                if region_result['success']:
                    # Preparar el mensaje base en inglés
                    base_message = BOT_MESSAGES["region_prompt"].format(region_result['region'])
                    # Traducir la respuesta al idioma detectado si es necesario
                    if detected_language != 'en':
                        translate_response = requests.post(
                            API_ENDPOINTS["translate"],
                            json={
                                'text': base_message,
                                'target_language': detected_language
                            },
                            headers={'Content-Type': 'application/json'}
                        )
                        
                        if translate_response.status_code == 200:
                            translated_message = translate_response.json()['translated_text']
                        else:
                            translated_message = base_message
                    else:
                        translated_message = base_message
                    
                    return {
                        "success": True,
                        "text": text,
                        "detected_language": detected_language,
                        "region": region_result['region'],
                        "step": "region",
                        "next_action": "request_sector",
                        "message": translated_message,
                        "language": detected_language
                    }
                else:
                    error_message = self.get_bot_response('error_general')
                    return {
                        "success": False,
                        "message": error_message,
                        "detected_language": detected_language
                    }
            
            else:
                # Fallback al método original si el endpoint falla
                return self._process_text_input_fallback(text)
                        
        except Exception as e:
            logger.error(f"Error processing text input: {str(e)}")
            return self._process_text_input_fallback(text)
    def _process_text_input_fallback(self, text: str) -> Dict:
        # Método de respaldo que usa la implementación original
        detected_language = self.detected_language_from_content(text)
        self.current_language = detected_language
        
        region_result = self.identify_region(text)
        
        if region_result['success']:
            response_message = self.get_bot_response(
                "region_prompt",
                region_result['region']
            )
            
            return {
                "success": True,
                "text": text,
                "detected_language": detected_language,
                "region": region_result['region'],
                "step": "region",
                "next_action": "request_sector",
                "message": response_message,
                "language": detected_language
            }
        else:
            error_message = self.get_bot_response('error_general')
            return {
                "success": False,
                "message": error_message,
                "detected_language": detected_language
            }
        














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
        





    def process_company_response(self, text: str) -> str:
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
                    
                    Input: "I'm interested in Apple, Meta and Amazon"
                    Output: Apple, Meta, Amazon
                    
                    Input: "No tengo preferencias de empresas"
                    Output: no
                    
                    Input: "I don't have any specific companies in mind"
                    Output: no
                    
                    Input: "Non, je n'ai pas d'entreprises spécifiques"
                    Output: no
                    
                    Input: "Quiero experiencia en Tesla, SpaceX"
                    Output: Tesla, SpaceX"""
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

            return response.choices[0].message.content.strip()

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
