from flask import Blueprint, request, jsonify
from ...handlers.voice_handler import VoiceHandler

voice_routes = Blueprint('voice_routes', __name__)
voice_handler = VoiceHandler()

@voice_routes.route('/health', methods=['GET'])
def check_health():
    return jsonify({
        'status': 'ok',
        'service': 'voice processing',
        'version': '1.0'
    })

# Nuevos endpoints adicionales
@voice_routes.route('/conversation/status', methods=['GET'])
def get_conversation_status():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({
            'success': False,
            'error': 'User ID is required'
        }), 400

    status = voice_handler.get_conversation_status(user_id)
    return jsonify(status)

@voice_routes.route('/conversation/reset', methods=['POST'])
def reset_conversation():
    user_id = request.json.get('user_id')
    if not user_id:
        return jsonify({
            'success': False,
            'error': 'User ID is required'
        }), 400

    voice_handler.reset_conversation(user_id)
    return jsonify({
        'success': True,
        'message': 'Conversation reset successfully'
    })

@voice_routes.route('/sectors', methods=['GET'])
def get_sectors():
    return jsonify({
        'success': True,
        'sectors': voice_handler.get_valid_sectors()
    })