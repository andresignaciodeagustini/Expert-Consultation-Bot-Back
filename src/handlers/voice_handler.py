from flask import Request, jsonify
from typing import Dict
import logging
from ..utils.chatgpt_helper import ChatGPTHelper

logger = logging.getLogger(__name__)

class VoiceHandler:
    def __init__(self):
        self.chatgpt_helper = ChatGPTHelper()


    
    def handle_voice_request(self, request: Request) -> Dict:
        try:
            if 'audio' not in request.files:
                logger.error("No audio file provided")
                return {
                    'success': False,
                    'error': self.chatgpt_helper.get_bot_response("error_no_audio")
                }
            
            audio_file = request.files['audio']
            step = request.form.get('step', 'region')  # Por defecto es 'region'
            
            logger.info(f"Processing voice request. Step: {step}")

            if step == 'region':
                return self.chatgpt_helper.process_voice_input(audio_file)
            elif step == 'sector':
                previous_region = request.form.get('region')
                if not previous_region:
                    return {
                        'success': False,
                        'error': self.chatgpt_helper.get_bot_response("error_no_region")
                    }
                return self.chatgpt_helper.process_sector_input(audio_file, previous_region)
            else:
                return {
                    'success': False,
                    'error': self.chatgpt_helper.get_bot_response("error_general")
                }

        except Exception as e:
            logger.error(f"Error in voice handler: {str(e)}")
            return {
                'success': False,
                'error': self.chatgpt_helper.get_bot_response("error_general")
            }
    
    def process_bot_logic(self,request:Dict) -> Dict:
        try:
            message = request['message']
            language = request['language']

            return {
                'message': message,
                'language':language
            }
        except Exception as e:
            logger.error (f"Error in bot logic: {str(e)} ")
            raise