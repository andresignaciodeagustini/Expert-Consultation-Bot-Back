from flask import Request, jsonify
from typing import Dict
import logging
from ..utils.chatgpt_helper import ChatGPTHelper
from ..utils.config import VALID_SECTORS

logger = logging.getLogger(__name__)

class VoiceHandler:
    def __init__(self):
        self.chatgpt_helper = ChatGPTHelper()


    def handle_voice_request(self, request: Request) -> Dict:
        try:
            print("\n=== Processing Voice Request ===")
            
            # Verificar archivo de audio
            if 'audio' not in request.files:
                return {
                    'success': False,
                    'error': "No audio file provided"
                }
            
            audio_file = request.files['audio']
            
            # Procesar el audio (solo transcripción)
            voice_result = self.chatgpt_helper.process_voice_input(
                audio_file=audio_file,
                step='transcribe'  # Nuevo paso que solo transcribe
            )
            
            # Devolver solo la transcripción y el idioma
            return {
                'success': True,
                'transcription': voice_result.get('transcription', ''),
                'detected_language': voice_result.get('detected_language', 'es')
            }

        except Exception as e:
            logger.error(f"Error in voice handler: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }