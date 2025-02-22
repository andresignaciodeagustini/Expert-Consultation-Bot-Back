from openai import OpenAI
import logging
import uuid
from typing import Dict
import os
from dotenv import load_dotenv
from typing import BinaryIO
import tempfile
from pathlib import Path
from ..utils.config import VALID_SECTORS

BOT_MESSAGES =  {
    "region_prompt":"I've identified the region as  {}. Please specify the business setor.",
    "sector_invalid": "Invalid sector. Please choose from: {}",
    "sector_success": "Perfect! Here are som companies in the  {} sector for  {}",
    "error_general":"Sorry, there was an error processing your request.",
    "error_no_region":"Region is required for this step"
}


    


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)  

class ChatGPTHelper:
    def __init__(self): 
        load_dotenv()  
        self.api_key = os.getenv('OPENAI_API_KEY')
        self.max_retries = 3
        self.retry_delay = 1

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
    

    def detected_language_from_content(self, text:str) -> str:
        
        try:
            messages = [
                 {
                     "role":"system",
                     "content":"You are a langugage detector. Anlyze the following text and response only with the langugage code(es,en,fr,it, etc.). Only respond with the language code, nothing else"
                 },
                 {
                     "role":"system",
                     "content":f"Detect the language of this text:{text} "
                 }
            ]

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=0.3
            )

            detected_language = response.choise [0].message.content.strip().lower()
            logger.info(f"Language detected from content: {detected_language}")
            return detected_language
        
        except Exception as e:
            logger.error(f"Error detecting language: {str(e)}")
            return "en"
        
    def translate_message(self, message:str, target_language:str) -> str:
        try:
            messages = [
                {
                    "role":"system",
                    "content":f"You are a translator. Trnaslate the following text to {target_language}. Only respond with the translation, nothing else."
                },
                {
                    "role": "user",
                    "content":message
                }

            ]

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages= messages,
                temperature=0.3
            )

            translated_text = response.choices[0].message.content.strip()
            return translated_text
        
        except Exception as e:
            logger.error(f"Translation error:  {str(e)}")
            return message

    def get_bot_response(self, response_key:str, *args) ->str:

        english_message = BOT_MESSAGES [response_key].format(*args) if args else BOT_MESSAGES[response_key]

        if not self.current_language or self.current_language =='en':
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
            
            messages = [
                {
                    "role": "system",
                    "content": "You are a professional business analyst that provides accurate lists of companies based on sector and geography."
                },
                {
                    "role": "user",
                    "content": f"List exactly 20 major companies in the {sector} sector that operate in {geography}. Only provide the company names separated by commas."
                }
            ]

            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=temperature,
                max_tokens=250
            )

            content = response.choices[0].message.content
            if content is None:
                logger.info("Received None response from API")
                return {
                    "success": True,
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
            
            return {
                "success": True,
                "content": companies[:20],
                "contentId": str(uuid.uuid4())
            }

        except Exception as e:
            logger.error(f"Error generating companies: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "contentId": None
            }
    def process_dialogflow_request(self, request_json: Dict) -> Dict:
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "user", "content": str(request_json)}
                ],
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            if content is None:
                return {
                    "fulfillmentText": "Sorry, I could not process the request."
                }
            
            return {
                "fulfillmentText": content.strip()
            }
            
        except Exception as e:
            logger.error(f"Error processing Dialogflow request: {str(e)}")
            return {
                "fulfillmentText": "Sorry, there was an error processing your request."
            }

    def process_voice_input(self, audio_file: BinaryIO) -> Dict:
        try:
            logger.info("Processing voice input")
            
            # Validación inicial del archivo
            if not audio_file or not hasattr(audio_file, 'filename'):
                logger.error("No valid audio file provided")
                return {
                    "success": False,
                    "error": "No valid audio file provided"
                }

            # Logging detallado del archivo
            logger.info(f"File info:")
            logger.info(f"- Filename: {audio_file.filename}")
            logger.info(f"- Content Type: {getattr(audio_file, 'content_type', 'unknown')}")
            logger.info(f"- Size: {getattr(audio_file, 'content_length', 'unknown')}")

            # Validar formato de archivo
            filename = audio_file.filename.lower()
            valid_formats = ['flac', 'm4a', 'mp3', 'mp4', 'mpeg', 'mpga', 'oga', 'ogg', 'wav', 'webm']
            file_extension = filename.split('.')[-1] if '.' in filename else ''
            
            logger.info(f"- File Extension: {file_extension}")
            
            if file_extension not in valid_formats:
                logger.error(f"Invalid file format: {file_extension}")
                return {
                    "success": False,
                    "error": f"Invalid file format. Supported formats: {valid_formats}"
                }

            try:
                # Crear archivo temporal
                with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_audio:
                    logger.info(f"Creating temporary file: {temp_audio.name}")
                    # Leer y escribir en chunks para archivos grandes
                    audio_file.seek(0)  # Asegurarse de estar al inicio del archivo
                    chunk_size = 8192
                    while True:
                        chunk = audio_file.read(chunk_size)
                        if not chunk:
                            break
                        temp_audio.write(chunk)
                    temp_path = Path(temp_audio.name)

                logger.info("Temporary file created successfully")

                # Verificar que el archivo temporal existe y tiene contenido
                if not temp_path.exists() or temp_path.stat().st_size == 0:
                    logger.error("Temporary file is empty or doesn't exist")
                    return {
                        "success": False,
                        "error": "Failed to create temporary audio file"
                    }

                logger.info("Starting transcription with Whisper")
                # Transcribir con Whisper
                with open(temp_path, 'rb') as audio:
                    transcript = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio,
                        response_format="verbose_json",
                         temperature=0.7
                    )

                logger.info("Transcription completed successfully")
                transcribed_text = transcript.text

                #Detectar idioma con GPT

                self.current_language = self.detected_language_from_content(transcribed_text)
                logger.info(f"Transcribed text:{transcribed_text}")
                logger.info(f"Detected language from content:{self.current_language} ")

                #idioma desconocido intenta reconocer otra vez y si no ingles
                if self.current_language == "unknown":
                    self.current_language = self.detected_language_from_content(transcribed_text)
                    if self.current == "unknown":
                        self.current_language ="en"
                    
                        logger.warning("Language could not be detected, defaulting to English")
                
                #Identificar región
                logger.info("Identity region")
                region_result = self.identify_region(transcribed_text)
                logger.info(f"Region indentification result:{region_result} ")

                if region_result ['success']:
                    response_message = self.get_bot_response(
                        "region_prompt",
                        region_result ['region']
                    )
                
                    return {
                        "success": True,
                        "transcription": transcribed_text,
                        "detected_language": self.current_language,
                        "region": region_result['region'],
                        "step": "region",
                        "next_action":"request_sector",
                        "message": response_message
                    }
                

                

                return {
                    "success": False,
                    "message": self.get_bot_response('error_general'),
                    "detected_language": self.current_language
                }

            finally:
                # Limpieza del archivo temporal
                if 'temp_path' in locals() and temp_path.exists():
                    try:
                        temp_path.unlink()
                        logger.info("Temporary file cleaned up successfully")
                    except Exception as e:
                        logger.error(f"Error cleaning up temporary file: {e}")

        except Exception as e:
            logger.error(f"Error processing voice input: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def process_sector_input(self, audio_file: BinaryIO, previous_region: str) -> Dict:
        try:
            # Validar formato de archivo
            filename = audio_file.filename.lower()
            valid_formats = ['flac', 'm4a', 'mp3', 'mp4', 'mpeg', 'mpga', 'oga', 'ogg', 'wav', 'webm']
            file_extension = filename.split('.')[-1] if '.' in filename else ''
            
            if file_extension not in valid_formats:
                return {
                    "success": False,
                    "error": f"Invalid file format. Supported formats: {valid_formats}"
                }

            with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{file_extension}') as temp_audio:
                temp_audio.write(audio_file.read())
                temp_path = Path(temp_audio.name)

            try:
                with open(temp_path, 'rb') as audio:
                    transcript = self.client.audio.transcriptions.create(
                        model="whisper-1",
                        file=audio,
                        response_format="verbose_json",
                         temperature=0.7
                    )

                transcribed_text = transcript.text
                detected_language = "en" if any(word in transcribed_text.lower() for word in ['the', 'in', 'at', 'on']) else "es"

                # Validar sector
                if transcribed_text.lower() in [s.lower() for s in VALID_SECTORS]:
                    sector = next(s for s in VALID_SECTORS if s.lower() == transcribed_text.lower())
                    
                    # Obtener compañías
                    companies_result = self.get_companies_suggestions(
                        sector=sector,
                        geography=previous_region
                    )

                    return {
                        "success": True,
                        "transcription": transcribed_text,
                        "detected_language": detected_language,
                        "region": previous_region,
                        "sector": sector,
                        "companies": companies_result['content'],
                        "step": "complete"
                    }

                return {
                    "success": False,
                    "message": f"Invalid sector. Please choose from: {', '.join(VALID_SECTORS)}",
                    "detected_language": detected_language
                }

            finally:
                if temp_path.exists():
                    temp_path.unlink()

        except Exception as e:
            logger.error(f"Error processing sector input: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
        