from flask import Blueprint, request, jsonify
from ...handlers.voice_handler import VoiceHandler

voice_routes = Blueprint('voice_routes', __name__)
voice_handler = VoiceHandler()

@voice_routes.route('/process', methods=['POST'])
def process_voice():
    return voice_handler.handle_voice_request(request)

@voice_routes.route('/health', methods=['GET'])
def check_health():
    return jsonify({
        'status': 'ok',
        'service': 'voice processing',
        'version': '1.0'
    })