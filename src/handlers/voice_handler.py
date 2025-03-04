from flask import Request, jsonify
from typing import Dict
import logging
from ..utils.chatgpt_helper import ChatGPTHelper
from ..utils.config import VALID_SECTORS

logger = logging.getLogger(__name__)

class VoiceHandler:
    def __init__(self):
        self.chatgpt_helper = ChatGPTHelper()

    def handle_voice_request(self, request: Request, step: str = 'transcribe') -> Dict:
        try:
            print("\n=== Processing Voice Request ===")
            print("Request files:", request.files)
            
            # Verificar archivo de audio
            if 'audio' not in request.files:
                print("No audio file found in request")
                return {
                    'success': False,
                    'error': "No audio file provided"
                }
            
            audio_file = request.files['audio']
            print(f"Audio file received: {audio_file.filename}")
            print(f"Content type: {audio_file.content_type}")
            print(f"File size: {audio_file.content_length} bytes")
            
            # Procesar el audio con el step especificado
            voice_result = self.chatgpt_helper.process_voice_input(
                audio_file=audio_file,
                step=step
            )
            
            print("Voice processing result:", voice_result)
            
            # Ajustar la respuesta según el tipo de procesamiento
            if step == 'username':
                return {
                    'success': True,
                    'detected_language': voice_result.get('detected_language', 'es'),
                    'username': voice_result.get('username'),
                    'original_transcription': voice_result.get('original_transcription'),
                    'transcription': voice_result.get('transcription'),
                    'error': voice_result.get('error')
                }
            else:
                return {
                    'success': True,
                    'detected_language': voice_result.get('detected_language', 'es'),
                    'transcription': voice_result.get('transcription'),
                    'original_transcription': voice_result.get('original_transcription'),
                    'was_corrected': voice_result.get('was_corrected', False),
                    'error': voice_result.get('error'),
                    'corrections_applied': voice_result.get('transcription') != voice_result.get('original_transcription')
                }

        except Exception as e:
            logger.error(f"Error in voice handler: {str(e)}")
            print(f"Error in voice handler: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }

    def _log_processing_details(self, voice_result: Dict) -> None:
        """
        Registra los detalles del procesamiento de voz
        """
        print("\n=== Voice Processing Details ===")
        if 'username' in voice_result:
            print(f"Processed username: {voice_result.get('username')}")
        print(f"Original transcription: {voice_result.get('original_transcription')}")
        print(f"Final transcription: {voice_result.get('transcription')}")
        print(f"Language detected: {voice_result.get('detected_language')}")
        if 'was_corrected' in voice_result:
            print(f"Corrections applied: {voice_result.get('was_corrected')}")
        if voice_result.get('error'):
            print(f"Errors encountered: {voice_result.get('error')}")