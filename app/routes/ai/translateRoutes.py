from flask import Blueprint, request, jsonify
from app.controllers.translation_controller import TranslationController

translate_routes = Blueprint('translate', __name__)
translation_controller = TranslationController()

@translate_routes.route('/translate', methods=['POST', 'OPTIONS'])
def translate():
    print("\n=== New Request to /api/translate ===")
    print("Method:", request.method)
    print("Headers:", dict(request.headers))
    
    if request.method == 'OPTIONS':
        return jsonify({"status": "ok"})

    try:
        data = request.json
        response, status_code = translation_controller.translate(data)
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500