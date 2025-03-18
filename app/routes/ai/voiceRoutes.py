from flask import Blueprint, request, jsonify
from app.controllers.voice_processing_controller import VoiceProcessingController

voice_routes = Blueprint('voice', __name__)
voice_processing_controller = VoiceProcessingController()

@voice_routes.route('/process', methods=['POST'])
def process_voice():
    try:
        response = voice_processing_controller.process_voice(request)
        return jsonify(response)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500