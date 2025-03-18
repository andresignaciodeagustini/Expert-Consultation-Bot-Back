from flask import Blueprint, request, jsonify
from app.controllers.welcome_controller import WelcomeController

welcome_routes = Blueprint('welcome', __name__)
welcome_controller = WelcomeController()

@welcome_routes.route('/welcome-message', methods=['GET'])
def get_welcome_message():
    try:
        response = welcome_controller.generate_welcome_message(request)
        return jsonify(response)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500