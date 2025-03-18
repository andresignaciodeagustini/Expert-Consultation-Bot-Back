from flask import Blueprint, request, jsonify
from app.controllers.sector_detection_controller import SectorDetectionController

sector_routes = Blueprint('sector', __name__)
sector_detection_controller = SectorDetectionController()

@sector_routes.route('/test/detect-sector', methods=['POST'])
def test_detect_sector():
    try:
        data = request.json
        response, status_code = sector_detection_controller.detect_sector(data)
        return jsonify(response), status_code
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500